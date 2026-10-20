#include "UAL_DataTableCommands.h"

#include "UAL_CommandUtils.h"
#include "UAL_PropertyPath.h"
#include "UAL_ScopedTransaction.h"

#include "DataTableEditorUtils.h"
#include "EditorFramework/AssetImportData.h"
#include "Engine/CompositeDataTable.h"
#include "Engine/DataTable.h"
#include "Engine/UserDefinedEnum.h"
#include "HAL/FileManager.h"
#include "Serialization/ObjectReader.h"
#include "Serialization/ObjectWriter.h"

DEFINE_LOG_CATEGORY_STATIC(LogUALDataTable, Log, All);

namespace
{
	/** rows 没点名时一次给几行。表常有几百上千行，全塞给模型是浪费 */
	constexpr int32 UAL_DT_DEFAULT_ROW_LIMIT = 20;
	constexpr int32 UAL_DT_MAX_ROW_LIMIT = 200;
	/** 行名列表的上限。超过就截断并标出来，模型可以按 offset 翻 */
	constexpr int32 UAL_DT_MAX_ROW_NAMES = 1000;

	TArray<TSharedPtr<FJsonValue>> UAL_DtJsonStrings(const TArray<FString>& Values)
	{
		TArray<TSharedPtr<FJsonValue>> Out;
		Out.Reserve(Values.Num());
		for (const FString& Value : Values)
		{
			Out.Add(MakeShared<FJsonValueString>(Value));
		}
		return Out;
	}

	/**
	 * 加载数据表。认 `/Game/Data/DT_X`、`/Game/Data/DT_X.DT_X`、带 `.uasset` 的写法。
	 * 加载到的不是数据表时，错误里说清楚它是什么。
	 */
	UDataTable* UAL_LoadDataTable(const FString& RawPath, FString& OutPath, FString& OutError)
	{
		OutPath = UAL_CommandUtils::NormalizeAssetPath(RawPath);
		UObject* Loaded = LoadObject<UObject>(nullptr, *OutPath);
		if (!Loaded && !OutPath.Contains(TEXT(".")))
		{
			FString AssetName;
			OutPath.Split(TEXT("/"), nullptr, &AssetName, ESearchCase::CaseSensitive, ESearchDir::FromEnd);
			Loaded = LoadObject<UObject>(nullptr, *FString::Printf(TEXT("%s.%s"), *OutPath, *AssetName));
		}
		if (!Loaded)
		{
			OutError = FString::Printf(TEXT("Data table not found: %s"), *OutPath);
			return nullptr;
		}
		UDataTable* Table = Cast<UDataTable>(Loaded);
		if (!Table)
		{
			OutError = FString::Printf(TEXT("%s is a %s, not a DataTable"), *OutPath, *Loaded->GetClass()->GetName());
			return nullptr;
		}
		if (!Table->GetRowStruct())
		{
			OutError = FString::Printf(
				TEXT("%s has no row structure (the struct it used is missing or failed to load)"), *OutPath);
			return nullptr;
		}
		return Table;
	}

	/** 列名按编辑器里显示的名字认，C++ 真名也认，大小写不敏感 */
	FProperty* UAL_FindColumn(const UScriptStruct* RowStruct, const FString& Name)
	{
		for (TFieldIterator<FProperty> It(RowStruct); It; ++It)
		{
			if (It->GetAuthoredName().Equals(Name, ESearchCase::IgnoreCase) ||
				It->GetName().Equals(Name, ESearchCase::IgnoreCase))
			{
				return *It;
			}
		}
		return nullptr;
	}

	TArray<FString> UAL_ColumnNames(const UScriptStruct* RowStruct)
	{
		TArray<FString> Names;
		for (TFieldIterator<FProperty> It(RowStruct); It; ++It)
		{
			Names.Add(It->GetAuthoredName());
		}
		return Names;
	}

	FString UAL_UnknownWithSuggestions(const TCHAR* What, const FString& Name, const TArray<FString>& Candidates)
	{
		TArray<FString> Suggestions;
		UAL_CommandUtils::SuggestProperties(Name, Candidates, Suggestions, 5);
		FString Message = FString::Printf(TEXT("no %s '%s'"), What, *Name);
		if (Suggestions.Num() > 0)
		{
			Message += FString::Printf(TEXT(". Did you mean: %s"), *FString::Join(Suggestions, TEXT(", ")));
		}
		return Message;
	}

	/** 这一列的枚举（枚举列或带枚举的 byte 列），不是枚举返回空 */
	const UEnum* UAL_ColumnEnum(const FProperty* Prop)
	{
		if (const FEnumProperty* EnumProp = CastField<FEnumProperty>(Prop))
		{
			return EnumProp->GetEnum();
		}
		if (const FByteProperty* ByteProp = CastField<FByteProperty>(Prop))
		{
			return ByteProp->Enum;
		}
		return nullptr;
	}

	/**
	 * 枚举取值对外用哪个名字。
	 *
	 * 蓝图里建的枚举（UserDefinedEnum）真名是 `NewEnumerator0` 这种，编辑器里显示的
	 * 才是 `Fire`。对外一律给显示名，写回时再翻回真名 —— 不然模型看到的值和用户
	 * 在表格里看到的对不上。C++ 枚举两者一致，用短名。
	 */
	FString UAL_EnumEntryName(const UEnum* Enum, int32 Index)
	{
		if (Enum->IsA<UUserDefinedEnum>())
		{
			return Enum->GetDisplayNameTextByIndex(Index).ToString();
		}
		return Enum->GetNameStringByIndex(Index);
	}

	TArray<FString> UAL_EnumEntries(const UEnum* Enum)
	{
		TArray<FString> Out;
		// 最后一项是编译器补的 _MAX，不是可选值
		for (int32 Index = 0; Index < Enum->NumEnums() - 1; ++Index)
		{
			Out.Add(UAL_EnumEntryName(Enum, Index));
		}
		return Out;
	}

	TSharedPtr<FJsonValue> UAL_ColumnValueToJson(FProperty* Prop, const uint8* RowData)
	{
		const void* ValuePtr = Prop->ContainerPtrToValuePtr<void>(RowData);
		if (const UEnum* Enum = UAL_ColumnEnum(Prop))
		{
			int64 Value = 0;
			if (const FEnumProperty* EnumProp = CastField<FEnumProperty>(Prop))
			{
				Value = EnumProp->GetUnderlyingProperty()->GetSignedIntPropertyValue(ValuePtr);
			}
			else
			{
				Value = *static_cast<const uint8*>(ValuePtr);
			}
			const int32 Index = Enum->GetIndexByValue(Value);
			if (Index != INDEX_NONE)
			{
				return MakeShared<FJsonValueString>(UAL_EnumEntryName(Enum, Index));
			}
		}
		return UAL_CommandUtils::PropertyToJsonValueCompat(Prop, ValuePtr);
	}

	/**
	 * 写枚举列时，把显示名翻回真名。认不出就原样交给 ImportText，由它报错。
	 */
	TSharedPtr<FJsonValue> UAL_TranslateEnumInput(const FProperty* Prop, const TSharedPtr<FJsonValue>& Value)
	{
		const UEnum* Enum = UAL_ColumnEnum(Prop);
		if (!Enum || !Value.IsValid() || Value->Type != EJson::String)
		{
			return Value;
		}
		const FString Text = Value->AsString();
		if (Enum->GetIndexByNameString(Text) != INDEX_NONE)
		{
			return Value;
		}
		for (int32 Index = 0; Index < Enum->NumEnums() - 1; ++Index)
		{
			if (Enum->GetDisplayNameTextByIndex(Index).ToString().Equals(Text, ESearchCase::IgnoreCase))
			{
				return MakeShared<FJsonValueString>(Enum->GetNameStringByIndex(Index));
			}
		}
		return Value;
	}

	/** 列的类型描述：给模型看「这一列该写什么」 */
	TSharedPtr<FJsonObject> UAL_DescribeColumn(FProperty* Prop)
	{
		TSharedPtr<FJsonObject> Column = MakeShared<FJsonObject>();
		Column->SetStringField(TEXT("name"), Prop->GetAuthoredName());
		Column->SetStringField(TEXT("type"), Prop->GetCPPType());
		if (const UEnum* Enum = UAL_ColumnEnum(Prop))
		{
			Column->SetArrayField(TEXT("enum_values"), UAL_DtJsonStrings(UAL_EnumEntries(Enum)));
		}
		return Column;
	}

	/** 源文件信息：从 CSV/JSON 导入的表，重新导入会盖掉编辑器里的改动 */
	void UAL_AddSourceFileInfo(UDataTable* Table, const TSharedPtr<FJsonObject>& Out)
	{
#if WITH_EDITORONLY_DATA
		if (Table->AssetImportData)
		{
			const FString SourceFile = Table->AssetImportData->GetFirstFilename();
			if (!SourceFile.IsEmpty())
			{
				Out->SetStringField(TEXT("source_file"), SourceFile);
				Out->SetBoolField(TEXT("source_file_exists"), IFileManager::Get().FileExists(*SourceFile));
			}
		}
#endif
	}

	TSharedPtr<FJsonObject> UAL_RowToJson(const uint8* RowData, const TArray<FProperty*>& Columns)
	{
		TSharedPtr<FJsonObject> Row = MakeShared<FJsonObject>();
		for (FProperty* Prop : Columns)
		{
			if (TSharedPtr<FJsonValue> Value = UAL_ColumnValueToJson(Prop, RowData))
			{
				Row->SetField(Prop->GetAuthoredName(), Value);
			}
		}
		return Row;
	}

	TArray<FString> UAL_RowNameStrings(const UDataTable* Table)
	{
		TArray<FString> Names;
		for (const FName& Name : Table->GetRowNames())
		{
			Names.Add(Name.ToString());
		}
		return Names;
	}

	// ────────────────────────────────────────────────────────────────────────
	// edit
	// ────────────────────────────────────────────────────────────────────────

	enum class EUAL_DtOp : uint8
	{
		Set,
		Add,
		Remove,
		Rename
	};

	struct FUAL_DtOp
	{
		EUAL_DtOp Kind = EUAL_DtOp::Set;
		FString Row;
		FString CopyFrom;
		FString NewName;
		TSharedPtr<FJsonObject> Values;
	};

	/** 先把整批解析完，结构不对的一条都不执行 */
	bool UAL_ParseOps(const TSharedPtr<FJsonObject>& Payload, TArray<FUAL_DtOp>& OutOps, FString& OutError)
	{
		const TArray<TSharedPtr<FJsonValue>>* OpsJson = nullptr;
		if (!Payload->TryGetArrayField(TEXT("ops"), OpsJson) || !OpsJson || OpsJson->Num() == 0)
		{
			OutError = TEXT("Missing required field: ops (a non-empty array)");
			return false;
		}
		for (int32 Index = 0; Index < OpsJson->Num(); ++Index)
		{
			const TSharedPtr<FJsonObject>* OpObj = nullptr;
			if (!(*OpsJson)[Index]->TryGetObject(OpObj) || !OpObj)
			{
				OutError = FString::Printf(TEXT("ops[%d] is not an object"), Index);
				return false;
			}
			FUAL_DtOp Op;
			FString Kind;
			(*OpObj)->TryGetStringField(TEXT("op"), Kind);
			if (Kind == TEXT("set"))
			{
				Op.Kind = EUAL_DtOp::Set;
			}
			else if (Kind == TEXT("add"))
			{
				Op.Kind = EUAL_DtOp::Add;
			}
			else if (Kind == TEXT("remove"))
			{
				Op.Kind = EUAL_DtOp::Remove;
			}
			else if (Kind == TEXT("rename"))
			{
				Op.Kind = EUAL_DtOp::Rename;
			}
			else
			{
				OutError = FString::Printf(TEXT("ops[%d].op must be set / add / remove / rename, got '%s'"), Index, *Kind);
				return false;
			}

			(*OpObj)->TryGetStringField(TEXT("row"), Op.Row);
			Op.Row.TrimStartAndEndInline();
			if (Op.Row.IsEmpty() || Op.Row == TEXT("None"))
			{
				OutError = FString::Printf(TEXT("ops[%d].row is missing"), Index);
				return false;
			}
			(*OpObj)->TryGetStringField(TEXT("copy_from"), Op.CopyFrom);
			(*OpObj)->TryGetStringField(TEXT("new_name"), Op.NewName);
			Op.NewName.TrimStartAndEndInline();
			const TSharedPtr<FJsonObject>* Values = nullptr;
			if ((*OpObj)->TryGetObjectField(TEXT("values"), Values) && Values)
			{
				Op.Values = *Values;
			}

			if (Op.Kind == EUAL_DtOp::Set && (!Op.Values.IsValid() || Op.Values->Values.Num() == 0))
			{
				OutError = FString::Printf(TEXT("ops[%d] (set %s) has no values"), Index, *Op.Row);
				return false;
			}
			if (Op.Kind == EUAL_DtOp::Rename && (Op.NewName.IsEmpty() || Op.NewName == TEXT("None")))
			{
				OutError = FString::Printf(TEXT("ops[%d] (rename %s) is missing new_name"), Index, *Op.Row);
				return false;
			}
			OutOps.Add(MoveTemp(Op));
		}
		return true;
	}

	/** 往一行里写一组值。键是列名，或 `列名.成员[0].字段` 这样的路径 */
	bool UAL_WriteValues(
		UDataTable* Table,
		const FName RowName,
		const TSharedPtr<FJsonObject>& Values,
		TMap<FString, TSharedPtr<FJsonValue>>& OutReadback,
		FString& OutError)
	{
		const UScriptStruct* RowStruct = Table->GetRowStruct();
		uint8* RowData = Table->FindRowUnchecked(RowName);
		if (!RowData)
		{
			OutError = FString::Printf(TEXT("row '%s' does not exist"), *RowName.ToString());
			return false;
		}
		for (const auto& Pair : Values->Values)
		{
			const FString Key = UAL_JsonKey(Pair.Key);
			int32 Cut = INDEX_NONE;
			FString ColumnName = Key;
			FString Rest;
			if (Key.FindChar(TEXT('.'), Cut) || Key.FindChar(TEXT('['), Cut))
			{
				ColumnName = Key.Left(Cut);
				Rest = Key.Mid(Cut);
			}
			FProperty* Column = UAL_FindColumn(RowStruct, ColumnName);
			if (!Column)
			{
				OutError = UAL_UnknownWithSuggestions(TEXT("column"), ColumnName, UAL_ColumnNames(RowStruct));
				return false;
			}
			const TSharedPtr<FJsonValue> Value = Rest.IsEmpty() ? UAL_TranslateEnumInput(Column, Pair.Value) : Pair.Value;

			// 用真名走路径：蓝图结构体的列名带 GUID 后缀，显示名在这一层已经翻译过了
			const FString Path = Column->GetName() + Rest;
			FString SetError;
			if (!UALPropertyPath::SetInStruct(RowStruct, RowData, Table, Path, Value, SetError))
			{
				OutError = FString::Printf(TEXT("column '%s': %s"), *Key, *SetError);
				// 枚举写错时 ImportText 只说「写不进去」，把可选值附上，模型照着改一次就对
				const UEnum* Enum = Rest.IsEmpty() ? UAL_ColumnEnum(Column) : nullptr;
				if (Enum)
				{
					OutError += FString::Printf(TEXT(" Allowed values: %s"),
						*FString::Join(UAL_EnumEntries(Enum), TEXT(", ")));
				}
				return false;
			}
			const FString OutKey = Column->GetAuthoredName() + Rest;
			if (Rest.IsEmpty())
			{
				OutReadback.Add(OutKey, UAL_ColumnValueToJson(Column, RowData));
			}
			else
			{
				FString ReadError;
				OutReadback.Add(OutKey, UALPropertyPath::GetInStruct(RowStruct, RowData, Path, ReadError));
			}
		}
		return true;
	}

	FString UAL_DescribeOp(const FUAL_DtOp& Op)
	{
		switch (Op.Kind)
		{
		case EUAL_DtOp::Set:
			return FString::Printf(TEXT("set %s"), *Op.Row);
		case EUAL_DtOp::Add:
			return FString::Printf(TEXT("add %s"), *Op.Row);
		case EUAL_DtOp::Remove:
			return FString::Printf(TEXT("remove %s"), *Op.Row);
		case EUAL_DtOp::Rename:
			return FString::Printf(TEXT("rename %s -> %s"), *Op.Row, *Op.NewName);
		}
		return Op.Row;
	}

	/** 执行一条。行写过哪些列记进 Touched，改名时跟着搬，删行时清掉 */
	bool UAL_ApplyOp(
		UDataTable* Table,
		const FUAL_DtOp& Op,
		TMap<FName, TMap<FString, TSharedPtr<FJsonValue>>>& Touched,
		TArray<FString>& Removed,
		TArray<TSharedPtr<FJsonValue>>& Renamed,
		FString& OutError)
	{
		const FName RowName(*Op.Row);
		// 只在报错时才需要全部行名（拼「你是不是想写」），别每条都现算一遍
		auto Existing = [Table]() { return UAL_RowNameStrings(Table); };
		const bool bExists = Table->FindRowUnchecked(RowName) != nullptr;

		switch (Op.Kind)
		{
		case EUAL_DtOp::Set:
		{
			if (!bExists)
			{
				OutError = UAL_UnknownWithSuggestions(TEXT("row"), Op.Row, Existing()) +
					TEXT(". To create it, use op \"add\"");
				return false;
			}
			return UAL_WriteValues(Table, RowName, Op.Values, Touched.FindOrAdd(RowName), OutError);
		}
		case EUAL_DtOp::Add:
		{
			if (bExists)
			{
				OutError = FString::Printf(TEXT("row '%s' already exists. To change it, use op \"set\"."), *Op.Row);
				return false;
			}
			if (!Op.CopyFrom.IsEmpty())
			{
				const FName Source(*Op.CopyFrom);
				if (!Table->FindRowUnchecked(Source))
				{
					OutError = TEXT("copy_from: ") + UAL_UnknownWithSuggestions(TEXT("row"), Op.CopyFrom, Existing());
					return false;
				}
				if (!FDataTableEditorUtils::DuplicateRow(Table, Source, RowName))
				{
					OutError = FString::Printf(TEXT("could not copy row '%s' to '%s'"), *Op.CopyFrom, *Op.Row);
					return false;
				}
			}
			else if (!FDataTableEditorUtils::AddRow(Table, RowName))
			{
				OutError = FString::Printf(TEXT("could not add row '%s'"), *Op.Row);
				return false;
			}
			TMap<FString, TSharedPtr<FJsonValue>>& Readback = Touched.FindOrAdd(RowName);
			if (Op.Values.IsValid() && Op.Values->Values.Num() > 0)
			{
				return UAL_WriteValues(Table, RowName, Op.Values, Readback, OutError);
			}
			return true;
		}
		case EUAL_DtOp::Remove:
		{
			if (!bExists)
			{
				OutError = UAL_UnknownWithSuggestions(TEXT("row"), Op.Row, Existing());
				return false;
			}
			if (!FDataTableEditorUtils::RemoveRow(Table, RowName))
			{
				OutError = FString::Printf(TEXT("could not remove row '%s'"), *Op.Row);
				return false;
			}
			Touched.Remove(RowName);
			Removed.Add(Op.Row);
			return true;
		}
		case EUAL_DtOp::Rename:
		{
			if (!bExists)
			{
				OutError = UAL_UnknownWithSuggestions(TEXT("row"), Op.Row, Existing());
				return false;
			}
			const FName NewName(*Op.NewName);
			if (Table->FindRowUnchecked(NewName))
			{
				OutError = FString::Printf(TEXT("cannot rename to '%s': that row already exists"), *Op.NewName);
				return false;
			}
			if (!FDataTableEditorUtils::RenameRow(Table, RowName, NewName))
			{
				OutError = FString::Printf(TEXT("could not rename row '%s' to '%s'"), *Op.Row, *Op.NewName);
				return false;
			}
			TMap<FString, TSharedPtr<FJsonValue>> Moved;
			if (Touched.RemoveAndCopyValue(RowName, Moved))
			{
				Touched.Add(NewName, MoveTemp(Moved));
			}
			TSharedPtr<FJsonObject> Entry = MakeShared<FJsonObject>();
			Entry->SetStringField(TEXT("from"), Op.Row);
			Entry->SetStringField(TEXT("to"), Op.NewName);
			Renamed.Add(MakeShared<FJsonValueObject>(Entry));
			return true;
		}
		}
		return false;
	}
}

void FUAL_DataTableCommands::RegisterCommands(
	TMap<FString, TFunction<void(const TSharedPtr<FJsonObject>&, const FString)>>& CommandMap)
{
	CommandMap.Add(TEXT("datatable.describe"), &Handle_Describe);
	CommandMap.Add(TEXT("datatable.edit"), &Handle_Edit);
	UE_LOG(LogUALDataTable, Log, TEXT("Registered 2 data table commands"));
}

void FUAL_DataTableCommands::Handle_Describe(const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
{
	FString RawPath;
	if (!Payload->TryGetStringField(TEXT("asset_path"), RawPath) || RawPath.IsEmpty())
	{
		UAL_CommandUtils::SendError(RequestId, 400, TEXT("Missing required field: asset_path"));
		return;
	}
	FString AssetPath;
	FString Error;
	UDataTable* Table = UAL_LoadDataTable(RawPath, AssetPath, Error);
	if (!Table)
	{
		UAL_CommandUtils::SendError(RequestId, 404, Error);
		return;
	}
	const UScriptStruct* RowStruct = Table->GetRowStruct();

	TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
	Result->SetBoolField(TEXT("ok"), true);
	Result->SetStringField(TEXT("asset_path"), Table->GetPathName());

	TSharedPtr<FJsonObject> StructInfo = MakeShared<FJsonObject>();
	StructInfo->SetStringField(TEXT("name"), RowStruct->GetName());
	StructInfo->SetStringField(TEXT("path"), RowStruct->GetPathName());
	StructInfo->SetBoolField(TEXT("user_defined"), !RowStruct->IsNative());
	Result->SetObjectField(TEXT("row_struct"), StructInfo);

	// 列：没点名就全给，点了名就只给那几列，认不出的单列出来
	TArray<FProperty*> Columns;
	TArray<FString> UnknownColumns;
	const TArray<TSharedPtr<FJsonValue>>* WantedColumns = nullptr;
	if (Payload->TryGetArrayField(TEXT("columns"), WantedColumns) && WantedColumns && WantedColumns->Num() > 0)
	{
		for (const TSharedPtr<FJsonValue>& Wanted : *WantedColumns)
		{
			const FString Name = Wanted->AsString();
			if (FProperty* Prop = UAL_FindColumn(RowStruct, Name))
			{
				Columns.AddUnique(Prop);
			}
			else
			{
				UnknownColumns.Add(UAL_UnknownWithSuggestions(TEXT("column"), Name, UAL_ColumnNames(RowStruct)));
			}
		}
	}
	else
	{
		for (TFieldIterator<FProperty> It(RowStruct); It; ++It)
		{
			Columns.Add(*It);
		}
	}
	TArray<TSharedPtr<FJsonValue>> ColumnsJson;
	for (TFieldIterator<FProperty> It(RowStruct); It; ++It)
	{
		ColumnsJson.Add(MakeShared<FJsonValueObject>(UAL_DescribeColumn(*It)));
	}
	Result->SetArrayField(TEXT("columns"), ColumnsJson);

	const TArray<FName> RowNames = Table->GetRowNames();
	Result->SetNumberField(TEXT("row_count"), RowNames.Num());

	TArray<FString> AllNames = UAL_RowNameStrings(Table);
	const bool bNamesTruncated = AllNames.Num() > UAL_DT_MAX_ROW_NAMES;
	TArray<FString> ListedNames = AllNames;
	if (bNamesTruncated)
	{
		ListedNames.SetNum(UAL_DT_MAX_ROW_NAMES);
	}
	Result->SetArrayField(TEXT("row_names"), UAL_DtJsonStrings(ListedNames));
	Result->SetBoolField(TEXT("row_names_truncated"), bNamesTruncated);

	// 行：点了名就给那几行；没点就按 offset/limit 取一段
	TArray<FName> Selected;
	TArray<TSharedPtr<FJsonValue>> UnknownRows;
	const TArray<TSharedPtr<FJsonValue>>* WantedRows = nullptr;
	if (Payload->TryGetArrayField(TEXT("rows"), WantedRows) && WantedRows && WantedRows->Num() > 0)
	{
		for (const TSharedPtr<FJsonValue>& Wanted : *WantedRows)
		{
			const FString Name = Wanted->AsString();
			if (Table->FindRowUnchecked(FName(*Name)))
			{
				Selected.AddUnique(FName(*Name));
			}
			else
			{
				UnknownRows.Add(MakeShared<FJsonValueString>(UAL_UnknownWithSuggestions(TEXT("row"), Name, AllNames)));
			}
		}
	}
	else
	{
		double OffsetNum = 0.0;
		double LimitNum = UAL_DT_DEFAULT_ROW_LIMIT;
		Payload->TryGetNumberField(TEXT("offset"), OffsetNum);
		Payload->TryGetNumberField(TEXT("limit"), LimitNum);
		const int32 Offset = FMath::Max(0, static_cast<int32>(OffsetNum));
		const int32 Limit = FMath::Clamp(static_cast<int32>(LimitNum), 0, UAL_DT_MAX_ROW_LIMIT);
		for (int32 Index = Offset; Index < RowNames.Num() && Selected.Num() < Limit; ++Index)
		{
			Selected.Add(RowNames[Index]);
		}
	}

	TSharedPtr<FJsonObject> RowsJson = MakeShared<FJsonObject>();
	for (const FName& Name : Selected)
	{
		RowsJson->SetObjectField(Name.ToString(), UAL_RowToJson(Table->FindRowUnchecked(Name), Columns));
	}
	Result->SetObjectField(TEXT("rows"), RowsJson);
	if (UnknownRows.Num() > 0)
	{
		Result->SetArrayField(TEXT("unknown_rows"), UnknownRows);
	}
	if (UnknownColumns.Num() > 0)
	{
		Result->SetArrayField(TEXT("unknown_columns"), UAL_DtJsonStrings(UnknownColumns));
	}

	if (Table->IsA<UCompositeDataTable>())
	{
		Result->SetBoolField(TEXT("composite"), true);
		FString ReadError;
		if (TSharedPtr<FJsonValue> Parents = UALPropertyPath::GetByPath(Table, TEXT("ParentTables"), ReadError))
		{
			Result->SetField(TEXT("parent_tables"), Parents);
		}
	}
	UAL_AddSourceFileInfo(Table, Result);

	UAL_CommandUtils::SendResponse(RequestId, 200, Result);
}

void FUAL_DataTableCommands::Handle_Edit(const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
{
	FString RawPath;
	if (!Payload->TryGetStringField(TEXT("asset_path"), RawPath) || RawPath.IsEmpty())
	{
		UAL_CommandUtils::SendError(RequestId, 400, TEXT("Missing required field: asset_path"));
		return;
	}
	FString AssetPath;
	FString Error;
	UDataTable* Table = UAL_LoadDataTable(RawPath, AssetPath, Error);
	if (!Table)
	{
		UAL_CommandUtils::SendError(RequestId, 404, Error);
		return;
	}
	if (Table->IsA<UCompositeDataTable>())
	{
		// 合并表的行是从父表里合出来的，改它等于改一份随时会被重算掉的缓存
		UAL_CommandUtils::SendError(RequestId, 400, FString::Printf(
			TEXT("%s is a composite data table: its rows come from its parent tables and are rebuilt from them. ")
			TEXT("Edit the parent table that owns the row instead (datatable.describe lists parent_tables)."),
			*Table->GetPathName()));
		return;
	}

	TArray<FUAL_DtOp> Ops;
	if (!UAL_ParseOps(Payload, Ops, Error))
	{
		UAL_CommandUtils::SendError(RequestId, 400, Error);
		return;
	}

	/**
	 * 整批的原子性靠快照，不靠事务。
	 *
	 * 事务只管「之后能撤销」，不管「中途失败时把已经改的退回去」—— Cancel 只是
	 * 丢掉撤销记录，内存里的表还是改了一半的样子。所以动手前把整张表序列化一份，
	 * 任何一条失败就读回去，再丢掉事务：表和撤销栈都像这次调用没发生过。
	 */
	TArray<uint8> Snapshot;
	{
		FObjectWriter Writer(Table, Snapshot);
	}

	FUAL_ScopedTransaction Transaction(FText::FromString(
		UAL_CommandUtils::LStr(TEXT("编辑数据表 "), TEXT("Edit data table ")) + Table->GetName()));
	FDataTableEditorUtils::BroadcastPreChange(Table, FDataTableEditorUtils::EDataTableChangeInfo::RowList);
	Table->Modify();

	TMap<FName, TMap<FString, TSharedPtr<FJsonValue>>> Touched;
	TArray<FString> Removed;
	TArray<TSharedPtr<FJsonValue>> Renamed;
	for (int32 Index = 0; Index < Ops.Num(); ++Index)
	{
		FString OpError;
		if (UAL_ApplyOp(Table, Ops[Index], Touched, Removed, Renamed, OpError))
		{
			continue;
		}

		{
			FObjectReader Reader(Table, Snapshot);
		}
		Transaction.Cancel();
		Table->HandleDataTableChanged();
		FDataTableEditorUtils::BroadcastPostChange(Table, FDataTableEditorUtils::EDataTableChangeInfo::RowList);

		TSharedPtr<FJsonObject> Details = MakeShared<FJsonObject>();
		Details->SetNumberField(TEXT("failed_op_index"), Index);
		Details->SetBoolField(TEXT("table_unchanged"), true);
		OpError.TrimEndInline();
		OpError.RemoveFromEnd(TEXT("."));
		UAL_CommandUtils::SendError(RequestId, 400,
			FString::Printf(TEXT("ops[%d] (%s) failed: %s. Nothing was changed - the whole batch was rolled back."),
				Index, *UAL_DescribeOp(Ops[Index]), *OpError),
			Details);
		return;
	}

	Table->HandleDataTableChanged();
	FDataTableEditorUtils::BroadcastPostChange(Table, FDataTableEditorUtils::EDataTableChangeInfo::RowList);
	Table->MarkPackageDirty();

	TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
	Result->SetBoolField(TEXT("ok"), true);
	Result->SetStringField(TEXT("asset_path"), Table->GetPathName());
	Result->SetStringField(TEXT("package"), Table->GetOutermost()->GetName());
	Result->SetNumberField(TEXT("applied"), Ops.Num());
	Result->SetNumberField(TEXT("row_count"), Table->GetRowNames().Num());

	TSharedPtr<FJsonObject> RowsJson = MakeShared<FJsonObject>();
	for (const auto& Pair : Touched)
	{
		TSharedPtr<FJsonObject> Row = MakeShared<FJsonObject>();
		for (const auto& Field : Pair.Value)
		{
			Row->SetField(Field.Key, Field.Value.IsValid() ? Field.Value : MakeShared<FJsonValueNull>());
		}
		RowsJson->SetObjectField(Pair.Key.ToString(), Row);
	}
	Result->SetObjectField(TEXT("rows"), RowsJson);
	if (Removed.Num() > 0)
	{
		Result->SetArrayField(TEXT("removed"), UAL_DtJsonStrings(Removed));
	}
	if (Renamed.Num() > 0)
	{
		Result->SetArrayField(TEXT("renamed"), Renamed);
	}
	UAL_AddSourceFileInfo(Table, Result);

	UAL_CommandUtils::SendResponse(RequestId, 200, Result);
}
