#include "UAL_AnimGraphSupport.h"

#include "UAL_AnimGraphNames.h"
#include "UAL_BlueprintCompileReport.h"
#include "UAL_CommandUtils.h"
#include "UAL_PropertyPath.h"
#include "UAL_ScopedTransaction.h"

#include "Animation/AnimBlueprint.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimationAsset.h"
#include "Animation/AnimNodeBase.h"
#include "Animation/Skeleton.h"
#include "Engine/SkeletalMesh.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraphSchema_K2.h"
#include "Factories/AnimBlueprintFactory.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Misc/OutputDeviceNull.h"
#include "UObject/UObjectIterator.h"

// 动画图编辑器模块（Editor/AnimGraph）。九个版本里这些头文件都在 Public 下、
// 类名没变过（2026-10-08 对过 5.0 和 5.8 的头文件）。很多类是 MinimalAPI ——
// 只能用它们的数据成员、虚函数和 StaticClass，非虚的成员函数只调明确导出的那几个
#include "AnimGraphNode_Base.h"
#include "AnimGraphNode_StateMachineBase.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_StateResult.h"
#include "AnimGraphNode_TransitionResult.h"
#include "AnimGraphNode_SaveCachedPose.h"
#include "AnimGraphNode_UseCachedPose.h"
#include "AnimGraphNode_BlendListByEnum.h"
#include "AnimGraphNode_BlendListByInt.h"
#include "AnimGraphNode_LayeredBoneBlend.h"
#include "AnimGraphNode_MultiWayBlend.h"
#include "AnimationGraphSchema.h"
#include "AnimationStateMachineGraph.h"
#include "AnimStateNodeBase.h"
#include "AnimStateNode.h"
#include "AnimStateConduitNode.h"
#include "AnimStateAliasNode.h"
#include "AnimStateEntryNode.h"
#include "AnimStateTransitionNode.h"
#include "K2Node_TransitionRuleGetter.h"

// UAL_AnimGraphNames 里的取值表按引擎枚举的顺序写死，这里钉住
static_assert(ETransitionGetter::AnimationAsset_GetTimeFromEndFraction == 4, "ETransitionGetter order changed");
static_assert(ETransitionGetter::ArbitraryState_GetBlendWeight == 8, "ETransitionGetter order changed");

namespace UALAnimGraph
{
namespace
{
	FString GuidString(const FGuid& Guid)
	{
		return Guid.ToString(EGuidFormats::DigitsWithHyphens);
	}

	/** ImportText / ExportText 的跨版本包装：5.1 起改名带 `_Direct` 后缀，参数表没变 */
	bool ImportTextCompat(FProperty* Prop, const TCHAR* Text, void* ValueAddr, UObject* Owner)
	{
		FOutputDeviceNull Silent;
#if ENGINE_MAJOR_VERSION > 5 || (ENGINE_MAJOR_VERSION == 5 && ENGINE_MINOR_VERSION >= 1)
		return Prop->ImportText_Direct(Text, ValueAddr, Owner, PPF_None, &Silent) != nullptr;
#else
		return Prop->ImportText(Text, ValueAddr, PPF_None, Owner, &Silent) != nullptr;
#endif
	}

	FString ExportTextCompat(const FProperty* Prop, const void* ValueAddr)
	{
		FString Text;
#if ENGINE_MAJOR_VERSION > 5 || (ENGINE_MAJOR_VERSION == 5 && ENGINE_MINOR_VERSION >= 1)
		Prop->ExportTextItem_Direct(Text, ValueAddr, nullptr, nullptr, PPF_None);
#else
		Prop->ExportTextItem(Text, ValueAddr, nullptr, nullptr, PPF_None);
#endif
		return Text;
	}

	/** `/Game/A/B` → `/Game/A/B.B`：对象引用的文本形式要带对象名 */
	FString NormalizeObjectPath(const FString& Path)
	{
		if (!Path.StartsWith(TEXT("/")) || Path.Contains(TEXT(".")))
		{
			return Path;
		}
		FString AssetName;
		Path.Split(TEXT("/"), nullptr, &AssetName, ESearchCase::CaseSensitive, ESearchDir::FromEnd);
		return AssetName.IsEmpty() ? Path : FString::Printf(TEXT("%s.%s"), *Path, *AssetName);
	}

	void GatherAssetsOfClass(UClass* Class, TArray<FAssetData>& Out)
	{
		const FAssetRegistryModule& Registry = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
#if ENGINE_MAJOR_VERSION > 5 || (ENGINE_MAJOR_VERSION == 5 && ENGINE_MINOR_VERSION >= 1)
		Registry.Get().GetAssetsByClass(Class->GetClassPathName(), Out, /*bSearchSubClasses=*/true);
#else
		Registry.Get().GetAssetsByClass(Class->GetFName(), Out, /*bSearchSubClasses=*/true);
#endif
	}

	/**
	 * 资产按路径或名字找。模型手里常常只有 `Idle` 这种名字 ——
	 * 名字在给定的几类资产里唯一就用它，重名就报出各自的路径让它挑。
	 */
	UObject* LoadAssetLoose(const FString& Ref, const TArray<UClass*>& Classes, FString& OutError)
	{
		if (Ref.StartsWith(TEXT("/")))
		{
			UObject* Loaded = LoadObject<UObject>(nullptr, *NormalizeObjectPath(Ref));
			if (!Loaded)
			{
				OutError = FString::Printf(TEXT("no asset at '%s'"), *Ref);
				return nullptr;
			}
			for (UClass* Class : Classes)
			{
				if (Loaded->IsA(Class))
				{
					return Loaded;
				}
			}
			OutError = FString::Printf(TEXT("'%s' is a %s"), *Ref, *Loaded->GetClass()->GetName());
			return nullptr;
		}

		TArray<FAssetData> Matches;
		for (UClass* Class : Classes)
		{
			TArray<FAssetData> Assets;
			GatherAssetsOfClass(Class, Assets);
			for (const FAssetData& Asset : Assets)
			{
				if (Asset.AssetName.ToString().Equals(Ref, ESearchCase::IgnoreCase))
				{
					Matches.Add(Asset);
				}
			}
		}
		if (Matches.Num() == 1)
		{
			return Matches[0].GetAsset();
		}
		if (Matches.Num() > 1)
		{
			TArray<FString> Paths;
			for (const FAssetData& Asset : Matches)
			{
				Paths.Add(Asset.PackageName.ToString());
			}
			OutError = FString::Printf(TEXT("'%s' is ambiguous, pass the full path: %s"), *Ref, *FString::Join(Paths, TEXT(", ")));
			return nullptr;
		}
		OutError = FString::Printf(TEXT("no asset named '%s'"), *Ref);
		return nullptr;
	}

	FString ListAssetNames(UClass* Class, int32 Max)
	{
		TArray<FAssetData> Assets;
		GatherAssetsOfClass(Class, Assets);
		TArray<FString> Paths;
		for (const FAssetData& Asset : Assets)
		{
			if (Paths.Num() >= Max)
			{
				Paths.Add(TEXT("..."));
				break;
			}
			Paths.Add(Asset.PackageName.ToString());
		}
		return Paths.Num() > 0 ? FString::Join(Paths, TEXT(", ")) : TEXT("(none in this project)");
	}

	UEdGraphPin* FindPinIgnoreCase(UEdGraphNode* Node, const FString& PinName)
	{
		for (UEdGraphPin* Pin : Node->Pins)
		{
			if (Pin && Pin->PinName.ToString().Equals(PinName, ESearchCase::IgnoreCase))
			{
				return Pin;
			}
		}
		return nullptr;
	}

	/**
	 * 动画节点身上装设置的那个结构体属性（FAnimNode_* 类型、名字通常叫 Node）。
	 *
	 * 不调引擎的 `GetFNodeProperty()`：那个类在新版本里是 MinimalAPI，中间几个版本
	 * 导没导出这个函数没有逐个核过。它做的事就是这一个循环，自己写一份没有链接风险。
	 */
	FStructProperty* FindNodeStructProperty(const UClass* Class)
	{
		for (TFieldIterator<FStructProperty> It(Class); It; ++It)
		{
			if (It->Struct && It->Struct->IsChildOf(FAnimNode_Base::StaticStruct()))
			{
				return *It;
			}
		}
		return nullptr;
	}

	/** 姿势连线（FPoseLink / FComponentSpacePoseLink，或它们的数组）：那是图里的线，不是设置 */
	bool IsPoseLinkProperty(const FProperty* Prop)
	{
		if (const FArrayProperty* Array = CastField<FArrayProperty>(Prop))
		{
			Prop = Array->Inner;
		}
		const FStructProperty* Struct = CastField<FStructProperty>(Prop);
		return Struct && Struct->Struct && Struct->Struct->GetName().Contains(TEXT("PoseLink"));
	}

	/**
	 * 「加一个输入」那类节点（按整数混合、分层混合、多路混合）加一个输入。
	 * 走引擎自己的加引脚函数：它会把并排的几个数组（姿势、混合时长、权重、分层设置）
	 * 一起加长。只加其中一个数组，节点就坏了 —— 姿势比混合时长多一个，编译或运行时出错。
	 */
	bool AddBlendInput(UAnimGraphNode_Base* Anim)
	{
		if (UAnimGraphNode_BlendListByInt* ByInt = Cast<UAnimGraphNode_BlendListByInt>(Anim))
		{
			ByInt->AddPinToBlendList();
			return true;
		}
		if (UAnimGraphNode_LayeredBoneBlend* Layered = Cast<UAnimGraphNode_LayeredBoneBlend>(Anim))
		{
			Layered->AddPinToBlendByFilter();
			return true;
		}
		if (UAnimGraphNode_MultiWayBlend* MultiWay = Cast<UAnimGraphNode_MultiWayBlend>(Anim))
		{
			MultiWay->AddPinToBlendNode();
			return true;
		}
		return false;
	}

	/** Node 结构体里某个数组现在多长；不是数组返回 INDEX_NONE */
	int32 NodeArrayNum(UAnimGraphNode_Base* Anim, FStructProperty* NodeProp, const FString& ArrayName)
	{
		const FArrayProperty* Array = CastField<FArrayProperty>(NodeProp->Struct->FindPropertyByName(FName(*ArrayName)));
		if (!Array)
		{
			return INDEX_NONE;
		}
		FScriptArrayHelper Helper(Array, Array->ContainerPtrToValuePtr<void>(NodeProp->ContainerPtrToValuePtr<void>(Anim)));
		return Helper.Num();
	}

	const TCHAR* TypeForOwner(const UEdGraphNode* Owner, const UEdGraph* SubGraph)
	{
		if (Cast<UAnimGraphNode_StateMachineBase>(Owner))
		{
			return TEXT("state_machine");
		}
		if (Cast<UAnimStateConduitNode>(Owner))
		{
			return TEXT("conduit");
		}
		if (Cast<UAnimStateNode>(Owner))
		{
			return TEXT("state");
		}
		if (const UAnimStateTransitionNode* Transition = Cast<UAnimStateTransitionNode>(Owner))
		{
			return SubGraph == Transition->BoundGraph ? TEXT("transition") : TEXT("custom_blend");
		}
		return TEXT("sub_graph");
	}

	FString StateNameOf(const UEdGraphNode* Node)
	{
		if (const UAnimStateNodeBase* State = Cast<UAnimStateNodeBase>(Node))
		{
			return State->GetStateName();
		}
		if (Cast<UAnimStateEntryNode>(Node))
		{
			return TEXT("Entry");
		}
		return FString();
	}

	/** 同一对状态之间的第几条转换（从 1 数） */
	int32 TransitionOrdinal(const UAnimStateTransitionNode* Transition)
	{
		const UEdGraph* Graph = Transition->GetGraph();
		if (!Graph)
		{
			return 1;
		}
		const UAnimStateNodeBase* From = Transition->GetPreviousState();
		const UAnimStateNodeBase* To = Transition->GetNextState();
		int32 Ordinal = 0;
		for (const UEdGraphNode* Node : Graph->Nodes)
		{
			const UAnimStateTransitionNode* Other = Cast<UAnimStateTransitionNode>(Node);
			if (Other && Other->GetPreviousState() == From && Other->GetNextState() == To)
			{
				++Ordinal;
				if (Other == Transition)
				{
					break;
				}
			}
		}
		return FMath::Max(1, Ordinal);
	}

	FString TransitionSegmentOf(const UAnimStateTransitionNode* Transition)
	{
		return UAL_AnimGraphNames::MakeTransitionSegment(
			StateNameOf(Transition->GetPreviousState()),
			StateNameOf(Transition->GetNextState()),
			TransitionOrdinal(Transition));
	}

	struct FChildGraph
	{
		FString Segment;
		UEdGraph* Graph = nullptr;
		const TCHAR* Type = nullptr;
	};

	/**
	 * 一张图下面直接挂着的子图。转换的规则图按 `A->B` 认（它的对象名是引擎自动起的），
	 * 别的一律用子图自己的名字 —— 状态机、状态、导管的图名就是用户起的那个名字，
	 * 折叠图（K2Node_Composite）同理，所以普通蓝图的折叠图也顺带能按路径进去。
	 */
	void GetChildGraphs(const UEdGraph* Graph, TArray<FChildGraph>& Out)
	{
		for (UEdGraphNode* Node : Graph->Nodes)
		{
			if (!Node)
			{
				continue;
			}
			if (const UAnimStateTransitionNode* Transition = Cast<UAnimStateTransitionNode>(Node))
			{
				if (Transition->BoundGraph)
				{
					Out.Add({ TransitionSegmentOf(Transition), Transition->BoundGraph, TEXT("transition") });
				}
				continue;
			}
			for (UEdGraph* Sub : Node->GetSubGraphs())
			{
				if (Sub)
				{
					Out.Add({ Sub->GetName(), Sub, TypeForOwner(Node, Sub) });
				}
			}
		}
	}

	void CollectTopLevelGraphs(UBlueprint* Blueprint, TArray<UEdGraph*>& Out)
	{
		Out.Append(Blueprint->UbergraphPages);
		Out.Append(Blueprint->FunctionGraphs);
		Out.Append(Blueprint->MacroGraphs);
		Out.Append(Blueprint->DelegateSignatureGraphs);
	}

	UEdGraph* FindTopLevelGraph(UBlueprint* Blueprint, const FString& Name)
	{
		TArray<UEdGraph*> Graphs;
		CollectTopLevelGraphs(Blueprint, Graphs);
		for (UEdGraph* Graph : Graphs)
		{
			if (Graph && Graph->GetName().Equals(Name, ESearchCase::IgnoreCase))
			{
				return Graph;
			}
		}
		return nullptr;
	}

	/** 这个节点在它所在的状态机里，还有没有别的同名状态（状态、导管、别名共用一个名字空间） */
	UAnimStateNodeBase* FindStateByName(const UEdGraph* Graph, const FString& Name, const UEdGraphNode* Except = nullptr)
	{
		for (UEdGraphNode* Node : Graph->Nodes)
		{
			UAnimStateNodeBase* State = Cast<UAnimStateNodeBase>(Node);
			if (State && State != Except && !State->IsA<UAnimStateTransitionNode>()
				&& State->GetStateName().Equals(Name, ESearchCase::IgnoreCase))
			{
				return State;
			}
		}
		return nullptr;
	}

	UAnimStateEntryNode* FindEntryNode(const UEdGraph* Graph)
	{
		if (const UAnimationStateMachineGraph* Machine = Cast<UAnimationStateMachineGraph>(Graph))
		{
			if (Machine->EntryNode)
			{
				return Machine->EntryNode;
			}
		}
		for (UEdGraphNode* Node : Graph->Nodes)
		{
			if (UAnimStateEntryNode* Entry = Cast<UAnimStateEntryNode>(Node))
			{
				return Entry;
			}
		}
		return nullptr;
	}

	/** 入口节点只有一根输出引脚。不调 GetOutputPin()：那个函数 5.0 上没导出 */
	UEdGraphPin* EntryOutputPin(UAnimStateEntryNode* Entry)
	{
		for (UEdGraphPin* Pin : Entry->Pins)
		{
			if (Pin && Pin->Direction == EGPD_Output)
			{
				return Pin;
			}
		}
		return nullptr;
	}

	UAnimStateNodeBase* EntryTarget(UAnimStateEntryNode* Entry)
	{
		UEdGraphPin* Pin = Entry ? EntryOutputPin(Entry) : nullptr;
		if (Pin && Pin->LinkedTo.Num() > 0 && Pin->LinkedTo[0])
		{
			return Cast<UAnimStateNodeBase>(Pin->LinkedTo[0]->GetOwningNode());
		}
		return nullptr;
	}

	/** 键名的第一段：`LayerSetup[0].BranchFilters` → LayerSetup */
	FString TopNameOf(const FString& Key)
	{
		int32 Dot = INDEX_NONE, Bracket = INDEX_NONE;
		Key.FindChar(TEXT('.'), Dot);
		Key.FindChar(TEXT('['), Bracket);
		const int32 Cut = Dot == INDEX_NONE ? Bracket : (Bracket == INDEX_NONE ? Dot : FMath::Min(Dot, Bracket));
		return Cut == INDEX_NONE ? Key : Key.Left(Cut);
	}

	/** 反射读写一个 UPROPERTY() 字符串成员 —— 有几个是 private 的（UseCachedPose::NameOfCache），直接访问编不过 */
	FString GetStringMember(const UObject* Object, FName Name)
	{
		const FStrProperty* Prop = CastField<FStrProperty>(Object->GetClass()->FindPropertyByName(Name));
		return Prop ? Prop->GetPropertyValue_InContainer(Object) : FString();
	}

	void SetStringMember(UObject* Object, FName Name, const FString& Value)
	{
		if (FStrProperty* Prop = CastField<FStrProperty>(Object->GetClass()->FindPropertyByName(Name)))
		{
			Prop->SetPropertyValue_InContainer(Object, Value);
		}
	}

	/**
	 * 设置键对应的那根引脚名：`PlayRate` → PlayRate，`BlendTime[2]` → BlendTime_2。
	 * 动画节点的数组属性露成引脚时是一个元素一根，名字就是这么拼的。其余形状返回空
	 */
	FString PinNameForSettingKey(const FString& Key)
	{
		const FString Top = TopNameOf(Key);
		const FString Rest = Key.Mid(Top.Len());
		if (Rest.IsEmpty())
		{
			return Top;
		}
		if (Rest.StartsWith(TEXT("[")) && Rest.EndsWith(TEXT("]")))
		{
			const FString Index = Rest.Mid(1, Rest.Len() - 2);
			if (Index.IsNumeric())
			{
				return Top + TEXT("_") + Index;
			}
		}
		return FString();
	}

	/**
	 * 和 CDO 比，只回改过的。全量铺出来一个序列播放节点就有几十条，真正有用的是那两三条。
	 *
	 * 数组里 CDO 没有的那些元素（按整数混合加出来的第 3、4 个输入），拿 CDO 的第 0 个
	 * 元素当默认值比 —— 新加的元素就是照默认元素加的，不这么比的话每个新输入的混合时长
	 * 都会被当成「改过」回出来。
	 */
	void DiffAgainstDefaults(
		const TMap<FString, TSharedPtr<FJsonValue>>& Values,
		const TMap<FString, TSharedPtr<FJsonValue>>& Defaults,
		TFunctionRef<bool(const FString& Key)> Skip,
		const TSharedPtr<FJsonObject>& Out)
	{
		for (const auto& Pair : Values)
		{
			if (Skip(Pair.Key))
			{
				continue;
			}
			const TSharedPtr<FJsonValue>* Default = Defaults.Find(Pair.Key);
			if (!Default)
			{
				const FString Top = TopNameOf(Pair.Key);
				int32 Close = INDEX_NONE;
				if (Pair.Key.Mid(Top.Len()).StartsWith(TEXT("[")) && Pair.Key.FindChar(TEXT(']'), Close))
				{
					Default = Defaults.Find(Top + TEXT("[0]") + Pair.Key.Mid(Close + 1));
				}
			}
			if (Default && UAL_CommandUtils::JsonValueToString(*Default) == UAL_CommandUtils::JsonValueToString(Pair.Value))
			{
				continue;
			}
			// float 属性读出来是 0.30000001192092896 这种；按 float 的精度回，和细节面板上看到的一样
			if (Pair.Value.IsValid() && Pair.Value->Type == EJson::Number)
			{
				const double Number = Pair.Value->AsNumber();
				if (FMath::Abs(Number) < 1.0e7 && Number != FMath::RoundToDouble(Number))
				{
					Out->SetNumberField(Pair.Key, FCString::Atod(*FString::SanitizeFloat(static_cast<float>(Number))));
					continue;
				}
			}
			Out->SetField(Pair.Key, Pair.Value);
		}
	}

	/** 动画节点的设置：Node 结构体里改过的那些。引脚露在外面的不算（值在引脚上，读图的 pins 里有） */
	TSharedPtr<FJsonObject> AnimNodeSettings(UAnimGraphNode_Base* Node, const TSet<FString>& Exclude)
	{
		TSharedPtr<FJsonObject> Settings = MakeShared<FJsonObject>();
		FStructProperty* NodeProp = FindNodeStructProperty(Node->GetClass());
		if (!NodeProp)
		{
			return Settings;
		}
		const UObject* Defaults = Node->GetClass()->GetDefaultObject();

		TMap<FString, TSharedPtr<FJsonValue>> Values, DefaultValues;
		UALPropertyPath::FlattenStruct(NodeProp->Struct, NodeProp->ContainerPtrToValuePtr<void>(Node), Values, 4, 400);
		UALPropertyPath::FlattenStruct(NodeProp->Struct, NodeProp->ContainerPtrToValuePtr<void>(Defaults), DefaultValues, 4, 400);

		TSet<FString> VisiblePins;
		for (const UEdGraphPin* Pin : Node->Pins)
		{
			if (Pin && !Pin->bHidden && Pin->Direction == EGPD_Input)
			{
				VisiblePins.Add(Pin->PinName.ToString());
			}
		}

		DiffAgainstDefaults(Values, DefaultValues, [&](const FString& Key)
		{
			const FString TopName = TopNameOf(Key);
			// 露成引脚的那些值在引脚上（读图的 pins 里有 default_value），属性里那份不作数
			if (Exclude.Contains(TopName) || VisiblePins.Contains(PinNameForSettingKey(Key)))
			{
				return true;
			}
			// 姿势连线是图里的线，不是设置；它的 LinkID 编译时会被改写
			return IsPoseLinkProperty(NodeProp->Struct->FindPropertyByName(FName(*TopName)));
		}, Settings);
		return Settings;
	}

	/** 状态、转换、别名的设置：只看这几个类自己声明的属性，UEdGraphNode 上的坐标注释之类不算 */
	TSharedPtr<FJsonObject> StateNodeSettings(UEdGraphNode* Node)
	{
		TSharedPtr<FJsonObject> Settings = MakeShared<FJsonObject>();
		TMap<FString, TSharedPtr<FJsonValue>> Values, DefaultValues;
		UALPropertyPath::FlattenProperties(Node, Values, 4, 400);
		UALPropertyPath::FlattenProperties(Node->GetClass()->GetDefaultObject(), DefaultValues, 4, 400);
		UClass* NodeClass = Node->GetClass();
		DiffAgainstDefaults(Values, DefaultValues, [NodeClass](const FString& Key)
		{
			const FProperty* Prop = NodeClass->FindPropertyByName(FName(*TopNameOf(Key)));
			if (!Prop)
			{
				return true;
			}
			const UClass* Owner = Prop->GetOwnerClass();
			return !Owner || !Owner->IsChildOf(UAnimStateNodeBase::StaticClass());
		}, Settings);
		return Settings;
	}

	FString JsonValueToPinText(const TSharedPtr<FJsonValue>& Value)
	{
		if (Value.IsValid() && Value->Type == EJson::String)
		{
			return Value->AsString();
		}
		// 整数引脚不认 "1.0"：整数值按整数写
		if (Value.IsValid() && Value->Type == EJson::Number)
		{
			const double Number = Value->AsNumber();
			if (FMath::IsFinite(Number) && Number == FMath::RoundToDouble(Number) && FMath::Abs(Number) < 9.0e15)
			{
				return FString::Printf(TEXT("%lld"), static_cast<int64>(Number));
			}
		}
		return UAL_CommandUtils::JsonValueToImportText(Value);
	}

	bool IsObjectPin(const UEdGraphPin* Pin)
	{
		const FName Category = Pin->PinType.PinCategory;
		return Category == UEdGraphSchema_K2::PC_Object || Category == UEdGraphSchema_K2::PC_Class
			|| Category == UEdGraphSchema_K2::PC_SoftObject || Category == UEdGraphSchema_K2::PC_SoftClass;
	}

	/** 写到露在外面的引脚上。动画节点的引脚一露出来，值就以引脚为准，属性里那份会被覆盖 */
	bool SetPinValue(UEdGraphPin* Pin, const TSharedPtr<FJsonValue>& Value, FString& OutError)
	{
		const UEdGraphSchema_K2* Schema = Cast<UEdGraphSchema_K2>(Pin->GetSchema());
		if (!Schema)
		{
			OutError = TEXT("pin is not on a Blueprint graph");
			return false;
		}
		const FString Text = JsonValueToPinText(Value);
		if (IsObjectPin(Pin) && Text.StartsWith(TEXT("/")))
		{
			// 对象引脚要先把资产载进来：按字符串设值只会去找已经在内存里的对象
			UObject* Asset = LoadObject<UObject>(nullptr, *NormalizeObjectPath(Text));
			if (!Asset)
			{
				OutError = FString::Printf(TEXT("no asset at '%s'"), *Text);
				return false;
			}
			const FString Invalid = Schema->IsPinDefaultValid(Pin, FString(), Asset, FText::GetEmpty());
			if (!Invalid.IsEmpty())
			{
				OutError = Invalid;
				return false;
			}
			Schema->TrySetDefaultObject(*Pin, Asset);
			return true;
		}

		FString UseValue;
		TObjectPtr<UObject> UseObject = nullptr;
		FText UseText;
		Schema->GetPinDefaultValuesFromString(Pin->PinType, Pin->GetOwningNodeUnchecked(), Text, UseValue, UseObject, UseText, false);
		const FString Invalid = Schema->IsPinDefaultValid(Pin, UseValue, UseObject, UseText);
		if (!Invalid.IsEmpty())
		{
			OutError = Invalid;
			return false;
		}
		Schema->TrySetDefaultValue(*Pin, Text);
		return true;
	}

	/** 布尔属性常被写成不带 b 的样子（LoopAnimation） */
	FProperty* FindPropertyLoose(const UStruct* Struct, const FString& Name, FString& OutResolvedName)
	{
		if (FProperty* Prop = Struct->FindPropertyByName(FName(*Name)))
		{
			OutResolvedName = Prop->GetName();
			return Prop;
		}
		if (FProperty* Prop = Struct->FindPropertyByName(FName(*(TEXT("b") + Name))))
		{
			if (Prop->IsA<FBoolProperty>())
			{
				OutResolvedName = Prop->GetName();
				return Prop;
			}
		}
		return nullptr;
	}

	FString SuggestFields(const FString& Wanted, const UStruct* A, const UStruct* B)
	{
		TArray<FString> Known;
		for (const UStruct* Struct : { A, B })
		{
			if (!Struct)
			{
				continue;
			}
			for (TFieldIterator<FProperty> It(Struct); It; ++It)
			{
				if (It->HasAnyPropertyFlags(CPF_Edit))
				{
					Known.AddUnique(It->GetName());
				}
			}
		}
		TArray<FString> Suggestions;
		UAL_CommandUtils::SuggestProperties(Wanted, Known, Suggestions, 5);
		return Suggestions.Num() > 0
			? FString::Printf(TEXT(" Did you mean: %s?"), *FString::Join(Suggestions, TEXT(", ")))
			: FString();
	}

	/** 一条设置。错误信息不带键名前缀，调用方统一加 */
	bool ApplyOneSetting(UEdGraphNode* Node, const FString& Key, const TSharedPtr<FJsonValue>& Value, bool bNodeIsNew, FMutationLog& Log, FString& OutError)
	{
		const FString TopName = TopNameOf(Key);
		const FString Rest = Key.Mid(TopName.Len());

		if (UAnimGraphNode_Base* Anim = Cast<UAnimGraphNode_Base>(Node))
		{
			FStructProperty* NodeProp = FindNodeStructProperty(Anim->GetClass());
			FString Resolved;
			const bool bOnNodeStruct = NodeProp && FindPropertyLoose(NodeProp->Struct, TopName, Resolved);
			if (bOnNodeStruct)
			{
				if (!bNodeIsNew)
				{
					Log.Backup(Anim, NodeProp->GetFName());
					Log.NoteReconstruct(Anim);
				}
				// `BlendTime[2]` 写到第三个输入上：先按引擎的方式把输入加够，
				// 不能让 SetByPath 只把这一个数组撑长（见 AddBlendInput）
				if (Rest.StartsWith(TEXT("[")))
				{
					const int32 Index = FCString::Atoi(*Rest.Mid(1));
					for (int32 Guard = 0; Guard < 64; ++Guard)
					{
						const int32 Num = NodeArrayNum(Anim, NodeProp, Resolved);
						if (Num == INDEX_NONE || Num > Index || !AddBlendInput(Anim))
						{
							break;
						}
					}
				}
			}

			// 露成引脚的：值以引脚为准，属性里那份编译时会被引脚覆盖。
			// 数组元素也一样（BlendTime[2] 的引脚叫 BlendTime_2）
			const FString PinName = PinNameForSettingKey(bOnNodeStruct ? Resolved + Rest : Key);
			if (UEdGraphPin* Pin = PinName.IsEmpty() ? nullptr : FindPinIgnoreCase(Anim, PinName))
			{
				if (Pin->Direction == EGPD_Input && !Pin->bHidden && Pin->LinkedTo.Num() == 0
					&& Pin->PinType.PinCategory != UEdGraphSchema_K2::PC_Struct)
				{
					if (!bNodeIsNew)
					{
						// 引脚可能在回滚前被重建过，按名字找回来再写
						TWeakObjectPtr<UEdGraphNode> WeakNode = Anim;
						const FString OldValue = Pin->DefaultValue;
						TWeakObjectPtr<UObject> OldObject = Pin->DefaultObject;
						const FText OldText = Pin->DefaultTextValue;
						Log.AddUndo([WeakNode, PinName, OldValue, OldObject, OldText]()
						{
							UEdGraphNode* Restored = WeakNode.Get();
							UEdGraphPin* RestoredPin = Restored ? FindPinIgnoreCase(Restored, PinName) : nullptr;
							if (RestoredPin)
							{
								RestoredPin->DefaultValue = OldValue;
								RestoredPin->DefaultObject = OldObject.Get();
								RestoredPin->DefaultTextValue = OldText;
							}
						});
					}
					return SetPinValue(Pin, Value, OutError);
				}
				// 结构体引脚：先按属性写（能只改一个分量），再把整个字段的值抄到引脚上 ——
				// 编译时没连线的引脚字面值会盖掉属性，只写属性等于没写
				if (bOnNodeStruct && Pin->Direction == EGPD_Input && !Pin->bHidden && Pin->LinkedTo.Num() == 0
					&& Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_Struct)
				{
					const FProperty* Field = NodeProp->Struct->FindPropertyByName(FName(*Resolved));
					if (Field)
					{
						if (!bNodeIsNew)
						{
							TWeakObjectPtr<UEdGraphNode> WeakNode = Anim;
							const FString OldValue = Pin->DefaultValue;
							Log.AddUndo([WeakNode, PinName, OldValue]()
							{
								UEdGraphNode* Restored = WeakNode.Get();
								if (UEdGraphPin* RestoredPin = Restored ? FindPinIgnoreCase(Restored, PinName) : nullptr)
								{
									RestoredPin->DefaultValue = OldValue;
								}
							});
						}
						if (!UALPropertyPath::SetByPath(Anim, NodeProp->GetName() + TEXT(".") + Resolved + Rest, Value, OutError))
						{
							return false;
						}
						const uint8* StructMemory = NodeProp->ContainerPtrToValuePtr<uint8>(Anim);
						FString PinText;
						if (FBlueprintEditorUtils::PropertyValueToString_Direct(Field, Field->ContainerPtrToValuePtr<uint8>(StructMemory), PinText))
						{
							Pin->GetSchema()->TrySetDefaultValue(*Pin, PinText);
						}
						return true;
					}
				}
			}

			if (bOnNodeStruct)
			{
				return UALPropertyPath::SetByPath(Anim, NodeProp->GetName() + TEXT(".") + Resolved + Rest, Value, OutError);
			}
			if (FProperty* Prop = FindPropertyLoose(Anim->GetClass(), TopName, Resolved))
			{
				if (!bNodeIsNew)
				{
					Log.Backup(Anim, Prop->GetFName());
				}
				return UALPropertyPath::SetByPath(Anim, Resolved + Rest, Value, OutError);
			}
			OutError = FString::Printf(TEXT("no setting '%s' on %s.%s"),
				*TopName, *UAL_AnimGraphNames::WriteAsForClassName(Anim->GetClass()->GetName()),
				*SuggestFields(TopName, NodeProp ? NodeProp->Struct : nullptr, nullptr));
			return false;
		}

		if (Node->IsA<UAnimStateNodeBase>())
		{
			FString Resolved;
			FProperty* Prop = FindPropertyLoose(Node->GetClass(), TopName, Resolved);
			if (!Prop)
			{
				OutError = FString::Printf(TEXT("no setting '%s' on %s.%s"),
					*TopName, *Node->GetClass()->GetName(), *SuggestFields(TopName, Node->GetClass(), nullptr));
				return false;
			}
			if (!bNodeIsNew)
			{
				Log.Backup(Node, Prop->GetFName());
			}
			const FString Before = ExportTextCompat(Prop, Prop->ContainerPtrToValuePtr<void>(Node));
			if (!UALPropertyPath::SetByPath(Node, Resolved + Rest, Value, OutError))
			{
				return false;
			}
			// 转换的 LogicType 改成 Custom 时，自定义混合图是在这个回调里建出来的。
			// 值没变就别回调：已是 Custom 的转换再收一次回调，引擎会把现有的自定义混合图删掉
			if (ExportTextCompat(Prop, Prop->ContainerPtrToValuePtr<void>(Node)) != Before)
			{
				FPropertyChangedEvent Changed(Prop);
				Node->PostEditChangeProperty(Changed);
			}
			return true;
		}

		OutError = TEXT("settings only apply to animation nodes, states and transitions - use pin_defaults for this node");
		return false;
	}

	bool IsAssetPlayerGetterSource(UAnimGraphNode_Base* Node)
	{
		return Node && Node->DoesSupportTimeForTransitionGetter() && Node->GetAnimationAsset();
	}

	/**
	 * 转换取值节点认播放节点的名字：动画资产名；同一页里同一段动画不止一个播放节点时
	 * 用节点 GUID。建和读用同一套，读回来的 member_name 才写得回去
	 */
	FString PlayerLabel(const UAnimGraphNode_Base* Player)
	{
		const UAnimationAsset* Asset = Player->GetAnimationAsset();
		if (!Asset)
		{
			return GuidString(Player->NodeGuid);
		}
		int32 SameName = 0;
		if (const UEdGraph* PlayerGraph = Player->GetGraph())
		{
			for (const UEdGraphNode* Node : PlayerGraph->Nodes)
			{
				const UAnimGraphNode_Base* Other = Cast<UAnimGraphNode_Base>(Node);
				const UAnimationAsset* OtherAsset = Other ? Other->GetAnimationAsset() : nullptr;
				SameName += OtherAsset && OtherAsset->GetName() == Asset->GetName() ? 1 : 0;
			}
		}
		return SameName > 1 ? GuidString(Player->NodeGuid) : Asset->GetName();
	}

	/** 取值节点的 member_name：种类 + 绑的对象 */
	FString DescribeGetter(const UK2Node_TransitionRuleGetter* Getter)
	{
		const UAL_AnimGraphNames::FGetter* Kind = UAL_AnimGraphNames::GetterByIndex(static_cast<int32>(Getter->GetterType.GetValue()));
		FString Name = Kind ? Kind->Name : TEXT("Unknown");
		if (Kind && Kind->bNeedsAssetPlayer && Getter->AssociatedAnimAssetPlayerNode)
		{
			Name += TEXT(":") + PlayerLabel(Getter->AssociatedAnimAssetPlayerNode);
		}
		if (Kind && Kind->bNeedsState && Getter->AssociatedStateNode)
		{
			Name += TEXT(":") + Getter->AssociatedStateNode->GetStateName();
		}
		return Name;
	}

	/** 这张图挂在哪个状态机里（转换规则 / 状态内部都往上找） */
	UEdGraph* OwningStateMachineGraph(const UEdGraph* Graph)
	{
		const UEdGraphNode* Owner = Cast<UEdGraphNode>(Graph->GetOuter());
		return Owner ? Owner->GetGraph() : nullptr;
	}

	bool CreateTransitionGetter(UEdGraph* Graph, const FString& MemberName, int32 PosX, int32 PosY, UEdGraphNode*& OutNode, FString& OutError)
	{
		FString Target;
		const UAL_AnimGraphNames::FGetter* Kind = UAL_AnimGraphNames::ParseGetter(MemberName, Target);
		if (!Kind)
		{
			OutError = FString::Printf(TEXT("TransitionGetter needs member_name set to one of: %s (got '%s')"),
				*UAL_AnimGraphNames::GetterNameList(), *MemberName);
			return true;
		}

		UEdGraphNode* Owner = Cast<UEdGraphNode>(Graph->GetOuter());
		UAnimStateNode* SourceState = nullptr;
		if (const UAnimStateTransitionNode* Transition = Cast<UAnimStateTransitionNode>(Owner))
		{
			SourceState = Cast<UAnimStateNode>(Transition->GetPreviousState());
		}
		else if (UAnimStateNode* State = Cast<UAnimStateNode>(Owner))
		{
			SourceState = State;
		}
		else if (!Cast<UAnimStateConduitNode>(Owner))
		{
			OutError = TEXT("TransitionGetter only goes inside a transition rule, a conduit or a state");
			return true;
		}

		UAnimGraphNode_Base* Player = nullptr;
		if (Kind->bNeedsAssetPlayer)
		{
			if (!SourceState || !SourceState->BoundGraph)
			{
				OutError = FString::Printf(TEXT("%s reads an animation player in the state this transition leaves, but it leaves a conduit or alias"), Kind->Name);
				return true;
			}
			TArray<UAnimGraphNode_Base*> Players;
			for (UEdGraphNode* Node : SourceState->BoundGraph->Nodes)
			{
				UAnimGraphNode_Base* Anim = Cast<UAnimGraphNode_Base>(Node);
				if (IsAssetPlayerGetterSource(Anim))
				{
					Players.Add(Anim);
				}
			}
			// 同一段动画放了两个播放节点时名字分不开，那几个用节点 GUID 认（读图回的也是这个写法）
			TArray<FString> Choices;
			TArray<UAnimGraphNode_Base*> Matches;
			for (UAnimGraphNode_Base* Anim : Players)
			{
				const FString Label = PlayerLabel(Anim);
				Choices.Add(FString::Printf(TEXT("%s:%s"), Kind->Name, *Label));
				if (!Target.IsEmpty()
					&& (Label.Equals(Target, ESearchCase::IgnoreCase) || GuidString(Anim->NodeGuid).Equals(Target, ESearchCase::IgnoreCase)))
				{
					Matches.Add(Anim);
				}
			}
			if (Target.IsEmpty() && Players.Num() == 1)
			{
				Player = Players[0];
			}
			else if (Matches.Num() == 1)
			{
				Player = Matches[0];
			}
			if (!Player)
			{
				OutError = Players.Num() == 0
					? FString::Printf(TEXT("state '%s' has no animation player with an asset set, so %s has nothing to read"), *SourceState->GetStateName(), Kind->Name)
					: FString::Printf(TEXT("pick the animation player: member_name = one of %s"), *FString::Join(Choices, TEXT(", ")));
				return true;
			}
		}

		UAnimStateNode* ForState = nullptr;
		if (Kind->bNeedsState)
		{
			UEdGraph* MachineGraph = OwningStateMachineGraph(Graph);
			ForState = MachineGraph ? Cast<UAnimStateNode>(FindStateByName(MachineGraph, Target)) : nullptr;
			if (!ForState)
			{
				OutError = FString::Printf(TEXT("%s needs a state: member_name = \"%s:<StateName>\" (no state named '%s')"), Kind->Name, Kind->Name, *Target);
				return true;
			}
		}

		UK2Node_TransitionRuleGetter* Getter = NewObject<UK2Node_TransitionRuleGetter>(Graph, NAME_None, RF_Transactional);
		Getter->GetterType = static_cast<ETransitionGetter::Type>(Kind->Index);
		Getter->AssociatedAnimAssetPlayerNode = Player;
		Getter->AssociatedStateNode = ForState;
		Graph->AddNode(Getter, /*bFromUI=*/false, /*bSelectNewNode=*/false);
		Getter->CreateNewGuid();
		Getter->PostPlacedNewNode();
		Getter->AllocateDefaultPins();
		Getter->NodePosX = PosX;
		Getter->NodePosY = PosY;
		OutNode = Getter;
		return true;
	}

	UClass* ResolveAnimNodeClass(const FString& Type, const FString& RawClass)
	{
		TArray<FString> Candidates;
		if (!RawClass.IsEmpty())
		{
			Candidates.Add(RawClass);
		}
		else
		{
			const FString Aliased = UAL_AnimGraphNames::ClassNameForAlias(Type);
			if (!Aliased.IsEmpty())
			{
				Candidates.Add(Aliased);
			}
			const FString Compact = Type.Replace(TEXT(" "), TEXT(""));
			Candidates.Add(Compact.StartsWith(TEXT("AnimGraphNode_")) ? Compact : TEXT("AnimGraphNode_") + Compact);
		}
		for (const FString& Candidate : Candidates)
		{
			FString Ignored;
			if (UClass* Class = UAL_CommandUtils::ResolveClassFromIdentifier(Candidate, UAnimGraphNode_Base::StaticClass(), Ignored))
			{
				return Class;
			}
		}
		return nullptr;
	}

	UEnum* ResolveEnum(const FString& Ref)
	{
		if (Ref.StartsWith(TEXT("/")))
		{
			return LoadObject<UEnum>(nullptr, *NormalizeObjectPath(Ref));
		}
#if ENGINE_MAJOR_VERSION > 5 || (ENGINE_MAJOR_VERSION == 5 && ENGINE_MINOR_VERSION >= 3)
		if (UEnum* Found = FindFirstObject<UEnum>(*Ref, EFindFirstObjectOptions::NativeFirst))
		{
			return Found;
		}
#else
		if (UEnum* Found = FindObject<UEnum>(ANY_PACKAGE, *Ref))
		{
			return Found;
		}
#endif
		FString Ignored;
		return Cast<UEnum>(LoadAssetLoose(Ref, { UEnum::StaticClass() }, Ignored));
	}

	TArray<UAnimGraphNode_SaveCachedPose*> AllSaveCachedPoseNodes(UBlueprint* Blueprint)
	{
		TArray<UAnimGraphNode_SaveCachedPose*> Nodes;
		FBlueprintEditorUtils::GetAllNodesOfClass<UAnimGraphNode_SaveCachedPose>(Blueprint, Nodes);
		return Nodes;
	}
}

// ============================================================================
// FMutationLog
// ============================================================================

void FMutationLog::Backup(UObject* Object, FName PropertyName)
{
	if (!Object)
	{
		return;
	}
	for (const FEntry& Entry : Entries)
	{
		if (Entry.Object.Get() == Object && Entry.Property == PropertyName)
		{
			return;
		}
	}
	FProperty* Prop = Object->GetClass()->FindPropertyByName(PropertyName);
	if (!Prop)
	{
		return;
	}
	Object->Modify();
	Entries.Add({ Object, PropertyName, ExportTextCompat(Prop, Prop->ContainerPtrToValuePtr<void>(Object)) });
}

void FMutationLog::NoteReconstruct(UEdGraphNode* Node)
{
	if (Node && !ToReconstruct.Contains(Node))
	{
		ToReconstruct.Add(Node);
	}
}

void FMutationLog::AddUndo(TFunction<void()> Undo)
{
	Undos.Add(MoveTemp(Undo));
}

void FMutationLog::Rollback()
{
	for (int32 Index = Undos.Num() - 1; Index >= 0; --Index)
	{
		Undos[Index]();
	}
	for (int32 Index = Entries.Num() - 1; Index >= 0; --Index)
	{
		UObject* Object = Entries[Index].Object.Get();
		FProperty* Prop = Object ? Object->GetClass()->FindPropertyByName(Entries[Index].Property) : nullptr;
		if (Prop)
		{
			ImportTextCompat(Prop, *Entries[Index].Text, Prop->ContainerPtrToValuePtr<void>(Object), Object);
		}
	}
	for (const TWeakObjectPtr<UEdGraphNode>& Weak : ToReconstruct)
	{
		if (UEdGraphNode* Node = Weak.Get())
		{
			Node->ReconstructNode();
		}
	}
	Undos.Reset();
	Entries.Reset();
	ToReconstruct.Reset();
}

// ============================================================================
// 图
// ============================================================================

UEdGraph* FindGraphByPath(UBlueprint* Blueprint, const FString& Path, FString& OutError)
{
	OutError.Reset();
	const TArray<FString> Segments = UAL_AnimGraphNames::SplitPath(Path);
	if (!Blueprint || Segments.Num() < 2)
	{
		return nullptr;
	}

	UEdGraph* Current = FindTopLevelGraph(Blueprint, Segments[0]);
	if (!Current)
	{
		TArray<UEdGraph*> Graphs;
		CollectTopLevelGraphs(Blueprint, Graphs);
		TArray<FString> Names;
		for (const UEdGraph* Graph : Graphs)
		{
			if (Graph)
			{
				Names.Add(Graph->GetName());
			}
		}
		OutError = FString::Printf(TEXT("no top-level graph '%s' (graphs: %s)"), *Segments[0], *FString::Join(Names, TEXT(", ")));
		return nullptr;
	}

	FString Walked = Current->GetName();
	for (int32 Index = 1; Index < Segments.Num(); ++Index)
	{
		const FString& Segment = Segments[Index];
		UEdGraph* Next = nullptr;

		if (Segment.Equals(UAL_AnimGraphNames::CustomBlendSegment(), ESearchCase::IgnoreCase))
		{
			if (const UAnimStateTransitionNode* Transition = Cast<UAnimStateTransitionNode>(Current->GetOuter()))
			{
				if (!Transition->CustomTransitionGraph)
				{
					OutError = FString::Printf(
						TEXT("transition '%s' has no custom blend graph - set its LogicType to TLT_Custom first (settings on the transition)"),
						*Walked);
					return nullptr;
				}
				Next = Transition->CustomTransitionGraph;
			}
		}

		if (!Next)
		{
			TArray<FChildGraph> Children;
			GetChildGraphs(Current, Children);

			FString Canonical = Segment;
			FString From, To;
			int32 Ordinal = 1;
			if (UAL_AnimGraphNames::ParseTransitionSegment(Segment, From, To, Ordinal))
			{
				Canonical = UAL_AnimGraphNames::MakeTransitionSegment(From, To, Ordinal);
			}
			for (const FChildGraph& Child : Children)
			{
				if (Child.Segment.Equals(Canonical, ESearchCase::IgnoreCase))
				{
					Next = Child.Graph;
					break;
				}
			}
			if (!Next)
			{
				TArray<FString> Names;
				for (const FChildGraph& Child : Children)
				{
					Names.Add(Child.Segment);
				}
				OutError = FString::Printf(TEXT("'%s' has no sub-graph '%s' (its sub-graphs: %s)"),
					*Walked, *Segment, Names.Num() > 0 ? *FString::Join(Names, TEXT(", ")) : TEXT("none"));
				return nullptr;
			}
		}

		Walked = GetGraphPath(Next);
		Current = Next;
	}
	return Current;
}

FString GetGraphPath(const UEdGraph* Graph)
{
	TArray<FString> Segments;
	const UEdGraph* Current = Graph;
	for (int32 Guard = 0; Current && Guard < 32; ++Guard)
	{
		const UEdGraphNode* Owner = Cast<UEdGraphNode>(Current->GetOuter());
		if (!Owner)
		{
			Segments.Insert(Current->GetName(), 0);
			break;
		}
		if (const UAnimStateTransitionNode* Transition = Cast<UAnimStateTransitionNode>(Owner))
		{
			if (Current != Transition->BoundGraph)
			{
				Segments.Insert(UAL_AnimGraphNames::CustomBlendSegment(), 0);
			}
			Segments.Insert(TransitionSegmentOf(Transition), 0);
		}
		else
		{
			Segments.Insert(Current->GetName(), 0);
		}
		Current = Owner->GetGraph();
	}
	return FString::Join(Segments, TEXT("/"));
}

const TCHAR* GetGraphKind(const UEdGraph* Graph)
{
	if (!Graph)
	{
		return nullptr;
	}
	if (const UEdGraphNode* Owner = Cast<UEdGraphNode>(Graph->GetOuter()))
	{
		const TCHAR* Type = TypeForOwner(Owner, Graph);
		if (FCString::Strcmp(Type, TEXT("sub_graph")) != 0)
		{
			return Type;
		}
	}
	const UEdGraphSchema* Schema = Graph->GetSchema();
	return Schema && Schema->IsA<UAnimationGraphSchema>() ? TEXT("anim_graph") : nullptr;
}

bool IsStateMachineGraph(const UEdGraph* Graph)
{
	return Graph && Graph->IsA<UAnimationStateMachineGraph>();
}

bool IsAnimBlueprint(const UBlueprint* Blueprint)
{
	return Blueprint && Blueprint->IsA<UAnimBlueprint>();
}

void ForEachNestedGraph(UBlueprint* Blueprint, TFunctionRef<void(UEdGraph*, const FString&, const TCHAR*)> Visit)
{
	if (!Blueprint)
	{
		return;
	}
	TFunction<void(UEdGraph*, const FString&, int32)> Walk;
	Walk = [&Walk, &Visit](UEdGraph* Graph, const FString& Path, int32 Depth)
	{
		if (!Graph || Depth > 16)
		{
			return;
		}
		TArray<FChildGraph> Children;
		GetChildGraphs(Graph, Children);
		for (const FChildGraph& Child : Children)
		{
			const FString ChildPath = Path + TEXT("/") + Child.Segment;
			Visit(Child.Graph, ChildPath, Child.Type);
			if (const UAnimStateTransitionNode* Transition = Cast<UAnimStateTransitionNode>(Child.Graph->GetOuter()))
			{
				if (Transition->CustomTransitionGraph)
				{
					const FString BlendPath = ChildPath + TEXT("/") + UAL_AnimGraphNames::CustomBlendSegment();
					Visit(Transition->CustomTransitionGraph, BlendPath, TEXT("custom_blend"));
					Walk(Transition->CustomTransitionGraph, BlendPath, Depth + 1);
				}
			}
			Walk(Child.Graph, ChildPath, Depth + 1);
		}
	};

	TArray<UEdGraph*> Roots;
	CollectTopLevelGraphs(Blueprint, Roots);
	for (UEdGraph* Root : Roots)
	{
		if (Root)
		{
			Walk(Root, Root->GetName(), 0);
		}
	}
}

// ============================================================================
// 节点
// ============================================================================

bool IsSkeletonNode(const UEdGraphNode* Node)
{
	return Node && (Node->IsA<UAnimGraphNode_Root>() || Node->IsA<UAnimGraphNode_StateResult>() || Node->IsA<UAnimGraphNode_TransitionResult>());
}

FString DescribeGetterDependents(UBlueprint* Blueprint, const UEdGraphNode* Node)
{
	if (!Blueprint || !Node || !IsAnimBlueprint(Blueprint))
	{
		return FString();
	}
	TArray<UK2Node_TransitionRuleGetter*> Getters;
	FBlueprintEditorUtils::GetAllNodesOfClass<UK2Node_TransitionRuleGetter>(Blueprint, Getters);
	TArray<FString> Rules;
	for (const UK2Node_TransitionRuleGetter* Getter : Getters)
	{
		if (Getter && (Getter->AssociatedAnimAssetPlayerNode == Node || Getter->AssociatedStateNode == Node) && Getter->GetGraph())
		{
			Rules.AddUnique(GetGraphPath(Getter->GetGraph()));
		}
	}
	if (Rules.Num() == 0)
	{
		return FString();
	}
	return FString::Printf(
		TEXT("removed '%s', which TransitionGetter nodes in %s read - rewrite those rules (their getters now point at nothing and the Blueprint will not compile)"),
		*Node->GetNodeTitle(ENodeTitleType::ListView).ToString(), *FString::Join(Rules, TEXT(", ")));
}

bool TryCreateNode(
	UBlueprint* Blueprint,
	UEdGraph* Graph,
	const FString& Type,
	const FString& RawClass,
	const FString& MemberName,
	int32 PosX,
	int32 PosY,
	UEdGraphNode*& OutNode,
	bool& bOutReused,
	FString& OutError)
{
	OutNode = nullptr;
	bOutReused = false;
	if (!Blueprint || !Graph || IsStateMachineGraph(Graph))
	{
		return false;
	}

	const FString Normalized = UAL_AnimGraphNames::NormalizeTypeName(Type);

	// 输出节点每张动画图自带一个，删不掉也不该再建 —— 只复用
	if (RawClass.IsEmpty() && (Normalized == TEXT("outputpose") || Normalized == TEXT("result")))
	{
		for (UEdGraphNode* Node : Graph->Nodes)
		{
			if (IsSkeletonNode(Node))
			{
				OutNode = Node;
				bOutReused = true;
				return true;
			}
		}
		OutError = FString::Printf(TEXT("graph '%s' has no output node - %s only exists in animation graphs, states and transition rules"),
			*GetGraphPath(Graph), *Type);
		return true;
	}

	if (RawClass.IsEmpty() && Normalized == TEXT("transitiongetter"))
	{
		return CreateTransitionGetter(Graph, MemberName, PosX, PosY, OutNode, OutError);
	}

	UClass* NodeClass = ResolveAnimNodeClass(Type, RawClass);
	if (!NodeClass)
	{
		return false;
	}
	if (NodeClass->HasAnyClassFlags(CLASS_Abstract | CLASS_Deprecated))
	{
		OutError = FString::Printf(TEXT("%s is abstract or deprecated and cannot be placed"), *NodeClass->GetName());
		return true;
	}
	if (!NodeClass->GetDefaultObject<UEdGraphNode>()->IsCompatibleWithGraph(Graph))
	{
		OutError = FString::Printf(
			TEXT("%s cannot go in '%s'. Animation nodes go in AnimGraph, inside a state, or in an animation layer; SaveCachedPose only in the top-level AnimGraph"),
			*UAL_AnimGraphNames::WriteAsForClassName(NodeClass->GetName()), *GetGraphPath(Graph));
		return true;
	}

	// 按名字复用：整图重写时状态机和缓存姿势不能被重建 —— 重建一个空状态机
	// 等于把里面所有状态、转换整片删掉
	if (!MemberName.IsEmpty())
	{
		for (UEdGraphNode* Node : Graph->Nodes)
		{
			const UAnimGraphNode_StateMachineBase* Machine = Cast<UAnimGraphNode_StateMachineBase>(Node);
			const UAnimGraphNode_SaveCachedPose* Save = Cast<UAnimGraphNode_SaveCachedPose>(Node);
			const bool bSameMachine = Machine && NodeClass->IsChildOf(UAnimGraphNode_StateMachineBase::StaticClass())
				&& Machine->EditorStateMachineGraph && Machine->EditorStateMachineGraph->GetName().Equals(MemberName, ESearchCase::IgnoreCase);
			const bool bSameCache = Save && NodeClass->IsChildOf(UAnimGraphNode_SaveCachedPose::StaticClass())
				&& Save->CacheName.Equals(MemberName, ESearchCase::IgnoreCase);
			if (bSameMachine || bSameCache)
			{
				OutNode = Node;
				bOutReused = true;
				return true;
			}
		}
	}

	UAnimGraphNode_Base* Node = NewObject<UAnimGraphNode_Base>(Graph, NodeClass, NAME_None, RF_Transactional);
	Graph->AddNode(Node, /*bFromUI=*/false, /*bSelectNewNode=*/false);
	Node->CreateNewGuid();
	Node->PostPlacedNewNode();
	// 按位置混合这类节点在 PostPlacedNewNode 里已经重建过引脚，再建一遍会多出一整套（同引擎的 FGraphNodeCreator）
	if (Node->Pins.Num() == 0)
	{
		Node->AllocateDefaultPins();
	}
	Node->NodePosX = PosX;
	Node->NodePosY = PosY;
	OutNode = Node;
	return true;
}

bool FinishNode(UBlueprint* Blueprint, UEdGraphNode* Node, const FString& MemberName, FString& OutError)
{
	UAnimGraphNode_Base* Anim = Cast<UAnimGraphNode_Base>(Node);
	if (!Anim)
	{
		return true;
	}

	if (UAnimGraphNode_StateMachineBase* Machine = Cast<UAnimGraphNode_StateMachineBase>(Anim))
	{
		if (MemberName.IsEmpty() || !Machine->EditorStateMachineGraph)
		{
			return true;
		}
		for (UEdGraphNode* Other : Machine->GetGraph()->Nodes)
		{
			const UAnimGraphNode_StateMachineBase* OtherMachine = Cast<UAnimGraphNode_StateMachineBase>(Other);
			if (OtherMachine && OtherMachine != Machine && OtherMachine->EditorStateMachineGraph
				&& OtherMachine->EditorStateMachineGraph->GetName().Equals(MemberName, ESearchCase::IgnoreCase))
			{
				OutError = FString::Printf(TEXT("a state machine named '%s' already exists in this graph"), *MemberName);
				return false;
			}
		}
		Machine->OnRenameNode(MemberName);
		return true;
	}

	if (UAnimGraphNode_SaveCachedPose* Save = Cast<UAnimGraphNode_SaveCachedPose>(Anim))
	{
		if (MemberName.IsEmpty())
		{
			return true;
		}
		for (const UAnimGraphNode_SaveCachedPose* Other : AllSaveCachedPoseNodes(Blueprint))
		{
			if (Other != Save && Other->CacheName.Equals(MemberName, ESearchCase::IgnoreCase))
			{
				OutError = FString::Printf(TEXT("a cached pose named '%s' already exists in this Blueprint"), *MemberName);
				return false;
			}
		}
		Save->CacheName = MemberName;
		return true;
	}

	if (UAnimGraphNode_UseCachedPose* Use = Cast<UAnimGraphNode_UseCachedPose>(Anim))
	{
		TArray<FString> Names;
		for (UAnimGraphNode_SaveCachedPose* Save : AllSaveCachedPoseNodes(Blueprint))
		{
			Names.Add(Save->CacheName);
			if (Save->CacheName.Equals(MemberName, ESearchCase::IgnoreCase))
			{
				Use->SaveCachedPoseNode = Save;
				// NameOfCache 是 private 的 UPROPERTY，走反射
				SetStringMember(Use, TEXT("NameOfCache"), Save->CacheName);
				Use->ReconstructNode();
				return true;
			}
		}
		OutError = FString::Printf(TEXT("UseCachedPose needs member_name = the name of a SaveCachedPose (cached poses: %s)"),
			Names.Num() > 0 ? *FString::Join(Names, TEXT(", ")) : TEXT("none yet - add a SaveCachedPose in AnimGraph"));
		return false;
	}

	if (UAnimGraphNode_BlendListByEnum* EnumNode = Cast<UAnimGraphNode_BlendListByEnum>(Anim))
	{
		UEnum* Enum = MemberName.IsEmpty() ? nullptr : ResolveEnum(MemberName);
		if (!Enum)
		{
			OutError = FString::Printf(TEXT("BlendPosesByEnum needs member_name = the enum to switch on (path or name), got '%s'"), *MemberName);
			return false;
		}
		// 编辑器里放这个节点只带一个 Default 输入，再逐个右键「添加引脚」。
		// 这里一次把所有枚举项都加上 —— 想要的几乎总是每项一个姿势。
		// BoundEnum / VisibleEnumEntries 是 protected 的 UPROPERTY，走反射写
		TArray<TSharedPtr<FJsonValue>> Entries;
		const int32 Count = Enum->ContainsExistingMax() ? Enum->NumEnums() - 1 : Enum->NumEnums();
		for (int32 Index = 0; Index < Count; ++Index)
		{
#if WITH_EDITOR
			if (Enum->HasMetaData(TEXT("Hidden"), Index))
			{
				continue;
			}
#endif
			Entries.Add(MakeShared<FJsonValueString>(Enum->GetNameByIndex(Index).ToString()));
		}
		if (!UALPropertyPath::SetByPath(EnumNode, TEXT("BoundEnum"), MakeShared<FJsonValueString>(Enum->GetPathName()), OutError)
			|| !UALPropertyPath::SetByPath(EnumNode, TEXT("VisibleEnumEntries"), MakeShared<FJsonValueArray>(Entries), OutError))
		{
			return false;
		}
		for (int32 Index = 0; Index < Entries.Num(); ++Index)
		{
			EnumNode->Node.AddPose();
		}
		EnumNode->ReconstructNode();
		return true;
	}

	if (MemberName.IsEmpty())
	{
		return true;
	}

	// 播动画的节点：member_name 就是那段动画
	if (UClass* AssetClass = Anim->GetAnimationAssetClass())
	{
		FString LoadError;
		UObject* Asset = LoadAssetLoose(MemberName, { AssetClass }, LoadError);
		if (!Asset)
		{
			OutError = FString::Printf(TEXT("%s: %s"), *AssetClass->GetName(), *LoadError);
			return false;
		}
		FStructProperty* NodeProp = FindNodeStructProperty(Anim->GetClass());
		FString PropName;
		if (NodeProp)
		{
			for (TFieldIterator<FObjectPropertyBase> It(NodeProp->Struct); It; ++It)
			{
				if (It->PropertyClass && Asset->IsA(It->PropertyClass) && It->PropertyClass->IsChildOf(UAnimationAsset::StaticClass()))
				{
					PropName = It->GetName();
					break;
				}
			}
		}
		if (PropName.IsEmpty())
		{
			OutError = FString::Printf(TEXT("could not find where %s keeps its asset - set it through settings instead"), *Anim->GetClass()->GetName());
			return false;
		}
		FMutationLog Unused;
		return ApplyOneSetting(Anim, PropName, MakeShared<FJsonValueString>(Asset->GetPathName()), /*bNodeIsNew=*/true, Unused, OutError);
	}

	OutError = FString::Printf(TEXT("%s takes no member_name - put its options in settings"),
		*UAL_AnimGraphNames::WriteAsForClassName(Anim->GetClass()->GetName()));
	return false;
}

void ApplySettings(UEdGraphNode* Node, const TSharedPtr<FJsonObject>& Settings, bool bNodeIsNew, FMutationLog& Log, TArray<FString>& OutErrors)
{
	if (!Node || !Settings.IsValid() || Settings->Values.Num() == 0)
	{
		return;
	}
	Node->Modify();
	bool bChanged = false;
	for (const auto& Pair : Settings->Values)
	{
		const FString Key = UAL_JsonKey(Pair.Key);
		FString Error;
		if (ApplyOneSetting(Node, Key, Pair.Value, bNodeIsNew, Log, Error))
		{
			bChanged = true;
		}
		else
		{
			OutErrors.Add(FString::Printf(TEXT("settings.%s: %s"), *Key, *Error));
		}
	}

	// 动画节点的引脚是按设置长出来的（输入个数、暴露的属性），改完重建一次
	if (bChanged && Node->IsA<UAnimGraphNode_Base>())
	{
		if (!bNodeIsNew)
		{
			Log.NoteReconstruct(Node);
		}
		Node->ReconstructNode();
	}
}

UEdGraphPin* RevealPin(UEdGraphNode* Node, const FString& PinName, bool bNodeIsNew, FMutationLog& Log)
{
	UAnimGraphNode_Base* Anim = Cast<UAnimGraphNode_Base>(Node);
	if (!Anim)
	{
		return nullptr;
	}

	// 可选引脚（播放速率、混合权重这类默认藏着的）：编辑器里是细节面板上勾「作为引脚」。
	// 不调引擎的 SetPinVisibility —— MinimalAPI 类上的非虚函数，中间版本未必导出；
	// 它做的就是改这个标志再重建引脚，引脚的初值由重建时的可选引脚管理器从属性里抄
	for (FOptionalPinFromProperty& Optional : Anim->ShowPinForProperties)
	{
		if (Optional.PropertyName.ToString().Equals(PinName, ESearchCase::IgnoreCase) && !Optional.bShowPin && Optional.bCanToggleVisibility)
		{
			if (!bNodeIsNew)
			{
				Log.Backup(Anim, GET_MEMBER_NAME_CHECKED(UAnimGraphNode_Base, ShowPinForProperties));
				Log.NoteReconstruct(Anim);
			}
			Anim->Modify();
			Optional.bShowPin = true;
			Anim->ReconstructNode();
			return FindPinIgnoreCase(Anim, PinName);
		}
	}

	// 「加一个输入」那类节点：BlendPose_3 不存在就补到第 4 个
	FString Base;
	int32 Index = INDEX_NONE;
	FStructProperty* NodeProp = FindNodeStructProperty(Anim->GetClass());
	if (!NodeProp || !UAL_AnimGraphNames::ParseIndexedPinName(PinName, Base, Index) || Index >= 64
		|| !CastField<FArrayProperty>(NodeProp->Struct->FindPropertyByName(FName(*Base))))
	{
		return nullptr;
	}
	bool bBackedUp = false;
	for (int32 Added = 0; Added <= Index; ++Added)
	{
		if (UEdGraphPin* Found = FindPinIgnoreCase(Anim, PinName))
		{
			return Found;
		}
		if (!bNodeIsNew && !bBackedUp)
		{
			Log.Backup(Anim, NodeProp->GetFName());
			Log.NoteReconstruct(Anim);
			bBackedUp = true;
		}
		if (!AddBlendInput(Anim))
		{
			break;
		}
	}
	return FindPinIgnoreCase(Anim, PinName);
}

void AnnotateNode(UEdGraphNode* Node, const TSharedPtr<FJsonObject>& NodeObj)
{
	if (!Node || !NodeObj.IsValid())
	{
		return;
	}

	if (const UK2Node_TransitionRuleGetter* Getter = Cast<UK2Node_TransitionRuleGetter>(Node))
	{
		NodeObj->SetStringField(TEXT("write_as"), TEXT("TransitionGetter"));
		NodeObj->SetStringField(TEXT("member_name"), DescribeGetter(Getter));
		return;
	}

	if (UAnimStateNodeBase* State = Cast<UAnimStateNodeBase>(Node))
	{
		if (State->IsA<UAnimStateTransitionNode>())
		{
			return;
		}
		NodeObj->SetStringField(TEXT("write_as"),
			State->IsA<UAnimStateConduitNode>() ? TEXT("Conduit") : State->IsA<UAnimStateAliasNode>() ? TEXT("StateAlias") : TEXT("State"));
		NodeObj->SetStringField(TEXT("member_name"), State->GetStateName());
		if (UEdGraph* Bound = State->GetBoundGraph())
		{
			NodeObj->SetStringField(TEXT("sub_graph"), GetGraphPath(Bound));
		}
		if (UAnimStateAliasNode* Alias = Cast<UAnimStateAliasNode>(State))
		{
			NodeObj->SetBoolField(TEXT("global_alias"), Alias->bGlobalAlias);
			TArray<TSharedPtr<FJsonValue>> Aliased;
			for (const TWeakObjectPtr<UAnimStateNodeBase>& Weak : Alias->GetAliasedStates())
			{
				if (const UAnimStateNodeBase* Target = Weak.Get())
				{
					Aliased.Add(MakeShared<FJsonValueString>(Target->GetStateName()));
				}
			}
			NodeObj->SetArrayField(TEXT("aliased_states"), Aliased);
		}
		const TSharedPtr<FJsonObject> Settings = StateNodeSettings(State);
		if (Settings->Values.Num() > 0)
		{
			NodeObj->SetObjectField(TEXT("settings"), Settings);
		}
		return;
	}

	if (Cast<UAnimStateEntryNode>(Node))
	{
		NodeObj->SetStringField(TEXT("write_as"), TEXT("Entry"));
		NodeObj->SetStringField(TEXT("member_name"), TEXT("Entry"));
		return;
	}

	UAnimGraphNode_Base* Anim = Cast<UAnimGraphNode_Base>(Node);
	if (!Anim)
	{
		return;
	}
	if (IsSkeletonNode(Anim))
	{
		NodeObj->SetStringField(TEXT("write_as"), Anim->IsA<UAnimGraphNode_TransitionResult>() ? TEXT("Result") : TEXT("OutputPose"));
		return;
	}

	NodeObj->SetStringField(TEXT("write_as"), UAL_AnimGraphNames::WriteAsForClassName(Anim->GetClass()->GetName()));

	TSet<FString> Exclude;
	if (const UAnimGraphNode_StateMachineBase* Machine = Cast<UAnimGraphNode_StateMachineBase>(Anim))
	{
		if (Machine->EditorStateMachineGraph)
		{
			NodeObj->SetStringField(TEXT("member_name"), Machine->EditorStateMachineGraph->GetName());
			NodeObj->SetStringField(TEXT("sub_graph"), GetGraphPath(Machine->EditorStateMachineGraph));
		}
	}
	else if (const UAnimGraphNode_SaveCachedPose* Save = Cast<UAnimGraphNode_SaveCachedPose>(Anim))
	{
		NodeObj->SetStringField(TEXT("member_name"), Save->CacheName);
	}
	else if (const UAnimGraphNode_UseCachedPose* Use = Cast<UAnimGraphNode_UseCachedPose>(Anim))
	{
		NodeObj->SetStringField(TEXT("member_name"),
			Use->SaveCachedPoseNode.IsValid() ? Use->SaveCachedPoseNode->CacheName : GetStringMember(Use, TEXT("NameOfCache")));
	}
	else if (const UAnimGraphNode_BlendListByEnum* EnumNode = Cast<UAnimGraphNode_BlendListByEnum>(Anim))
	{
		if (const UEnum* Enum = EnumNode->GetEnum())
		{
			NodeObj->SetStringField(TEXT("member_name"), Enum->GetPathName());
		}
	}
	else if (UAnimationAsset* Asset = Anim->GetAnimationAsset())
	{
		NodeObj->SetStringField(TEXT("member_name"), Asset->GetPathName());
		if (FStructProperty* NodeProp = FindNodeStructProperty(Anim->GetClass()))
		{
			for (TFieldIterator<FObjectPropertyBase> It(NodeProp->Struct); It; ++It)
			{
				if (It->PropertyClass && Asset->IsA(It->PropertyClass))
				{
					Exclude.Add(It->GetName());
				}
			}
		}
	}
	else
	{
		// 混合空间图之类自带子图的节点
		const TArray<UEdGraph*> SubGraphs = Anim->GetSubGraphs();
		if (SubGraphs.Num() > 0 && SubGraphs[0])
		{
			NodeObj->SetStringField(TEXT("sub_graph"), GetGraphPath(SubGraphs[0]));
		}
	}

	const TSharedPtr<FJsonObject> Settings = AnimNodeSettings(Anim, Exclude);
	if (Settings->Values.Num() > 0)
	{
		NodeObj->SetObjectField(TEXT("settings"), Settings);
	}
}

FString DescribeNodeTypesForError(const UEdGraph* Graph)
{
	const TCHAR* Kind = GetGraphKind(Graph);
	if (!Kind)
	{
		return FString();
	}
	if (FCString::Strcmp(Kind, TEXT("transition")) == 0 || FCString::Strcmp(Kind, TEXT("conduit")) == 0)
	{
		return FString::Printf(
			TEXT(" This is a transition rule: wire a bool into Result.bCanEnterTransition. Besides the usual Blueprint nodes it takes ")
			TEXT("TransitionGetter (member_name = %s; the player ones read the animation in the state being left)."),
			*UAL_AnimGraphNames::GetterNameList());
	}
	return TEXT(" Animation nodes: OutputPose (this graph's own output, reused), SequencePlayer / BlendSpacePlayer / AimOffset ")
		TEXT("(member_name = the asset), StateMachine (member_name = its name), BlendPosesByBool / BlendPosesByInt / ")
		TEXT("BlendPosesByEnum (member_name = the enum), LayeredBlendPerBone, Slot, SaveCachedPose / UseCachedPose ")
		TEXT("(member_name = cache name), or any other animation node by its class name without the AnimGraphNode_ prefix ")
		TEXT("- blueprint_search_nodes lists them with their settings.");
}

// ============================================================================
// 状态机那一页
// ============================================================================

namespace
{
	TSharedPtr<FJsonObject> StateMachineNodeJson(UEdGraphNode* Node)
	{
		TSharedPtr<FJsonObject> Obj = MakeShared<FJsonObject>();
		Obj->SetStringField(TEXT("node_id"), GuidString(Node->NodeGuid));
		Obj->SetStringField(TEXT("class"), Node->GetClass()->GetName());
		Obj->SetStringField(TEXT("title"), Node->GetNodeTitle(ENodeTitleType::ListView).ToString());
		Obj->SetNumberField(TEXT("pos_x"), Node->NodePosX);
		Obj->SetNumberField(TEXT("pos_y"), Node->NodePosY);
		AnnotateNode(Node, Obj);
		return Obj;
	}

	TSharedPtr<FJsonObject> TransitionJson(UAnimStateTransitionNode* Transition)
	{
		TSharedPtr<FJsonObject> Obj = MakeShared<FJsonObject>();
		Obj->SetStringField(TEXT("from"), StateNameOf(Transition->GetPreviousState()));
		Obj->SetStringField(TEXT("to"), StateNameOf(Transition->GetNextState()));
		Obj->SetStringField(TEXT("node_id"), GuidString(Transition->NodeGuid));
		if (Transition->BoundGraph)
		{
			Obj->SetStringField(TEXT("rule_graph"), GetGraphPath(Transition->BoundGraph));
		}
		if (Transition->CustomTransitionGraph)
		{
			Obj->SetStringField(TEXT("custom_blend_graph"), GetGraphPath(Transition->CustomTransitionGraph));
		}
		const TSharedPtr<FJsonObject> Settings = StateNodeSettings(Transition);
		if (Settings->Values.Num() > 0)
		{
			Obj->SetObjectField(TEXT("settings"), Settings);
		}
		return Obj;
	}
}

void AppendStateMachineJson(UEdGraph* Graph, const TSharedPtr<FJsonObject>& Result)
{
	TArray<TSharedPtr<FJsonValue>> Nodes;
	TArray<TSharedPtr<FJsonValue>> Transitions;
	for (UEdGraphNode* Node : Graph->Nodes)
	{
		if (!Node)
		{
			continue;
		}
		if (UAnimStateTransitionNode* Transition = Cast<UAnimStateTransitionNode>(Node))
		{
			Transitions.Add(MakeShared<FJsonValueObject>(TransitionJson(Transition)));
			continue;
		}
		// 注释框照普通节点回，别的（状态、导管、别名、入口）走状态那套
		Nodes.Add(MakeShared<FJsonValueObject>(StateMachineNodeJson(Node)));
	}
	Result->SetStringField(TEXT("graph_kind"), TEXT("state_machine"));
	Result->SetArrayField(TEXT("nodes"), Nodes);
	Result->SetArrayField(TEXT("transitions"), Transitions);
	if (const UAnimStateNodeBase* First = EntryTarget(FindEntryNode(Graph)))
	{
		Result->SetStringField(TEXT("entry_state"), First->GetStateName());
	}
}

void HandleApplyStateMachine(UBlueprint* Blueprint, UEdGraph* Graph, const FString& ResolvedPath, const TSharedPtr<FJsonObject>& Payload, const FString& RequestId)
{
	const TArray<TSharedPtr<FJsonValue>>* NodesArray = nullptr;
	Payload->TryGetArrayField(TEXT("nodes"), NodesArray);
	const TArray<TSharedPtr<FJsonValue>>* ConnectionsArray = nullptr;
	Payload->TryGetArrayField(TEXT("connections"), ConnectionsArray);
	bool bClearExisting = false;
	Payload->TryGetBoolField(TEXT("clear_existing"), bClearExisting);
	bool bCompile = true;
	Payload->TryGetBoolField(TEXT("compile"), bCompile);

	const FString GraphPath = GetGraphPath(Graph);
	UAnimStateEntryNode* Entry = FindEntryNode(Graph);
	const UEdGraphSchema* Schema = Graph->GetSchema();
	if (!Entry || !Schema)
	{
		UAL_CommandUtils::SendError(RequestId, 500, FString::Printf(TEXT("state machine '%s' has no entry node"), *GraphPath));
		return;
	}

	// 事务只管「用户能一次撤销」，原子性靠下面的显式回退 —— 理由同 Handle_CreateGraphDeclarative
	TOptional<FUAL_ScopedTransaction> Transaction;
	Transaction.Emplace(NSLOCTEXT("UnrealAgentLink", "ApplyStateMachine", "Apply State Machine"));
	const bool bUndoable = Transaction->IsOutstanding();
	Blueprint->Modify();
	Graph->Modify();

	TArray<FString> Errors;
	TArray<FString> Warnings;
	FMutationLog Log;
	TArray<UEdGraphNode*> PreExisting;
	for (UEdGraphNode* Node : Graph->Nodes)
	{
		if (Node)
		{
			PreExisting.Add(Node);
		}
	}

	TMap<FString, UEdGraphNode*> IdMap;
	TArray<UEdGraphNode*> Created;
	TSet<FString> NamesThisBatch;
	TArray<TSharedPtr<FJsonValue>> NodesInfo;

	auto StateList = [Graph]()
	{
		TArray<FString> Names;
		for (UEdGraphNode* Node : Graph->Nodes)
		{
			const UAnimStateNodeBase* State = Cast<UAnimStateNodeBase>(Node);
			if (State && !State->IsA<UAnimStateTransitionNode>())
			{
				Names.Add(State->GetStateName());
			}
		}
		return Names.Num() > 0 ? FString::Join(Names, TEXT(", ")) : FString(TEXT("none yet"));
	};

	// ===== 1. 状态 =====
	int32 NextX = 0;
	const int32 Count = NodesArray ? NodesArray->Num() : 0;
	for (int32 Index = 0; Index < Count; ++Index)
	{
		const TSharedPtr<FJsonObject> NodeObj = (*NodesArray)[Index].IsValid() ? (*NodesArray)[Index]->AsObject() : nullptr;
		if (!NodeObj.IsValid())
		{
			Errors.Add(FString::Printf(TEXT("nodes[%d]: not an object"), Index));
			continue;
		}
		FString Id, Type, Name;
		NodeObj->TryGetStringField(TEXT("id"), Id);
		if (Id.IsEmpty())
		{
			Id = FString::Printf(TEXT("node_%d"), Index);
		}
		if (!NodeObj->TryGetStringField(TEXT("class"), Type))
		{
			NodeObj->TryGetStringField(TEXT("type"), Type);
		}
		if (!NodeObj->TryGetStringField(TEXT("member_name"), Name))
		{
			NodeObj->TryGetStringField(TEXT("name"), Name);
		}
		if (IdMap.Contains(Id))
		{
			Errors.Add(FString::Printf(TEXT("nodes[%d]: duplicate id '%s'"), Index, *Id));
			continue;
		}

		const FString Kind = UAL_AnimGraphNames::NormalizeTypeName(Type);
		if (Kind == TEXT("entry"))
		{
			IdMap.Add(Id, Entry);
			continue;
		}
		UClass* StateClass = Kind == TEXT("state") ? UAnimStateNode::StaticClass()
			: Kind == TEXT("conduit") ? UAnimStateConduitNode::StaticClass()
			: (Kind == TEXT("statealias") || Kind == TEXT("alias")) ? UAnimStateAliasNode::StaticClass()
			: nullptr;
		if (!StateClass)
		{
			Errors.Add(FString::Printf(
				TEXT("nodes[%d] '%s': a state machine page only holds State, Conduit and StateAlias (got '%s'). ")
				TEXT("Animation nodes go inside a state - write them to graph_name \"%s/<StateName>\"; a transition is a connection here, not a node"),
				Index, *Id, *Type, *GraphPath));
			continue;
		}
		if (Name.IsEmpty())
		{
			Errors.Add(FString::Printf(TEXT("nodes[%d] '%s': member_name is the %s's name and is required"), Index, *Id, *Type));
			continue;
		}
		if (NamesThisBatch.Contains(Name.ToLower()))
		{
			Errors.Add(FString::Printf(TEXT("nodes[%d] '%s': two nodes in this request are both named '%s'"), Index, *Id, *Name));
			continue;
		}
		NamesThisBatch.Add(Name.ToLower());

		TSharedPtr<FJsonObject> Info = MakeShared<FJsonObject>();
		Info->SetStringField(TEXT("id"), Id);

		if (UAnimStateNodeBase* Existing = FindStateByName(Graph, Name))
		{
			if (Existing->GetClass() != StateClass)
			{
				Errors.Add(FString::Printf(TEXT("nodes[%d] '%s': '%s' already exists here as a %s"), Index, *Id, *Name, *Existing->GetClass()->GetName()));
				continue;
			}
			IdMap.Add(Id, Existing);
			Info->SetBoolField(TEXT("reused"), true);
			Info->SetStringField(TEXT("node_id"), GuidString(Existing->NodeGuid));
			NodesInfo.Add(MakeShared<FJsonValueObject>(Info));
			continue;
		}

		UAnimStateNodeBase* State = NewObject<UAnimStateNodeBase>(Graph, StateClass, NAME_None, RF_Transactional);
		Graph->AddNode(State, /*bFromUI=*/false, /*bSelectNewNode=*/false);
		State->CreateNewGuid();
		State->PostPlacedNewNode();
		State->AllocateDefaultPins();
		const TSharedPtr<FJsonObject>* PosObj = nullptr;
		if (NodeObj->TryGetObjectField(TEXT("position"), PosObj) && PosObj && (*PosObj).IsValid())
		{
			(*PosObj)->TryGetNumberField(TEXT("x"), State->NodePosX);
			(*PosObj)->TryGetNumberField(TEXT("y"), State->NodePosY);
		}
		else
		{
			State->NodePosX = 300 + NextX;
			State->NodePosY = 0;
			NextX += 300;
		}
		State->OnRenameNode(Name);
		Created.Add(State);
		IdMap.Add(Id, State);
		if (!State->GetStateName().Equals(Name))
		{
			Warnings.Add(FString::Printf(TEXT("nodes '%s': named '%s' instead of '%s'"), *Id, *State->GetStateName(), *Name));
		}
		Info->SetStringField(TEXT("node_id"), GuidString(State->NodeGuid));
		NodesInfo.Add(MakeShared<FJsonValueObject>(Info));
	}

	// ===== 2. 别名指向、settings（要等全部状态建完：别名可以指向同一批后面的状态）=====
	for (int32 Index = 0; Index < Count; ++Index)
	{
		const TSharedPtr<FJsonObject> NodeObj = (*NodesArray)[Index].IsValid() ? (*NodesArray)[Index]->AsObject() : nullptr;
		FString Id;
		if (!NodeObj.IsValid())
		{
			continue;
		}
		NodeObj->TryGetStringField(TEXT("id"), Id);
		if (Id.IsEmpty())
		{
			Id = FString::Printf(TEXT("node_%d"), Index);
		}
		UEdGraphNode** Found = IdMap.Find(Id);
		if (!Found || !*Found || *Found == Entry)
		{
			continue;
		}
		UEdGraphNode* Node = *Found;
		const bool bIsNew = Created.Contains(Node);

		if (UAnimStateAliasNode* Alias = Cast<UAnimStateAliasNode>(Node))
		{
			bool bGlobal = false;
			if (NodeObj->TryGetBoolField(TEXT("global_alias"), bGlobal))
			{
				if (!bIsNew)
				{
					Log.Backup(Alias, GET_MEMBER_NAME_CHECKED(UAnimStateAliasNode, bGlobalAlias));
				}
				Alias->bGlobalAlias = bGlobal;
			}
			const TArray<TSharedPtr<FJsonValue>>* AliasedArray = nullptr;
			if (NodeObj->TryGetArrayField(TEXT("aliased_states"), AliasedArray) && AliasedArray)
			{
				TSet<TWeakObjectPtr<UAnimStateNodeBase>>& Aliased = Alias->GetAliasedStates();
				if (!bIsNew)
				{
					const TSet<TWeakObjectPtr<UAnimStateNodeBase>> Before = Aliased;
					TWeakObjectPtr<UAnimStateAliasNode> WeakAlias = Alias;
					Log.AddUndo([WeakAlias, Before]()
					{
						if (UAnimStateAliasNode* Restored = WeakAlias.Get())
						{
							Restored->GetAliasedStates() = Before;
						}
					});
				}
				Alias->Modify();
				Aliased.Reset();
				for (const TSharedPtr<FJsonValue>& Value : *AliasedArray)
				{
					const FString StateName = Value.IsValid() ? Value->AsString() : FString();
					UAnimStateNodeBase* Target = FindStateByName(Graph, StateName, Alias);
					if (!Target || Target->IsA<UAnimStateAliasNode>())
					{
						Errors.Add(FString::Printf(TEXT("nodes '%s': aliased state '%s' is not a state here (states: %s)"), *Id, *StateName, *StateList()));
						continue;
					}
					Aliased.Add(Target);
				}
			}
		}

		const TSharedPtr<FJsonObject>* SettingsObj = nullptr;
		if (NodeObj->TryGetObjectField(TEXT("settings"), SettingsObj) && SettingsObj)
		{
			TArray<FString> SettingErrors;
			ApplySettings(Node, *SettingsObj, bIsNew, Log, SettingErrors);
			for (const FString& Error : SettingErrors)
			{
				Errors.Add(FString::Printf(TEXT("nodes '%s': %s"), *Id, *Error));
			}
		}
	}

	// ===== 3. 连线 = 转换：只解析，不改图 =====
	struct FPending
	{
		int32 Index = 0;
		FString FromLabel;
		FString ToLabel;
		UAnimStateNodeBase* From = nullptr;
		UAnimStateNodeBase* To = nullptr;
		bool bFromEntry = false;
		TSharedPtr<FJsonObject> Settings;
	};
	TArray<FPending> Pending;

	auto Resolve = [&](const FString& Label) -> UEdGraphNode*
	{
		if (UEdGraphNode** Found = IdMap.Find(Label))
		{
			return *Found;
		}
		FGuid Guid;
		if (FGuid::Parse(Label, Guid))
		{
			for (UEdGraphNode* Node : Graph->Nodes)
			{
				if (Node && Node->NodeGuid == Guid)
				{
					return Node;
				}
			}
		}
		if (Label.Equals(TEXT("Entry"), ESearchCase::IgnoreCase))
		{
			return Entry;
		}
		return FindStateByName(Graph, Label);
	};

	const int32 ConnectionCount = ConnectionsArray ? ConnectionsArray->Num() : 0;
	for (int32 Index = 0; Index < ConnectionCount; ++Index)
	{
		const TSharedPtr<FJsonValue>& Value = (*ConnectionsArray)[Index];
		FPending Conn;
		Conn.Index = Index;
		const TArray<TSharedPtr<FJsonValue>>* Pair = nullptr;
		if (Value.IsValid() && Value->TryGetArray(Pair) && Pair && Pair->Num() >= 2)
		{
			Conn.FromLabel = (*Pair)[0]->AsString();
			Conn.ToLabel = (*Pair)[1]->AsString();
		}
		else if (const TSharedPtr<FJsonObject> Obj = Value.IsValid() ? Value->AsObject() : nullptr)
		{
			Obj->TryGetStringField(TEXT("from"), Conn.FromLabel);
			Obj->TryGetStringField(TEXT("to"), Conn.ToLabel);
			const TSharedPtr<FJsonObject>* SettingsObj = nullptr;
			if (Obj->TryGetObjectField(TEXT("settings"), SettingsObj) && SettingsObj)
			{
				Conn.Settings = *SettingsObj;
			}
		}
		if (Conn.FromLabel.IsEmpty() || Conn.ToLabel.IsEmpty())
		{
			Errors.Add(FString::Printf(TEXT("connections[%d]: expected {\"from\":\"<state>\",\"to\":\"<state>\"}"), Index));
			continue;
		}

		UEdGraphNode* FromNode = Resolve(Conn.FromLabel);
		UEdGraphNode* ToNode = Resolve(Conn.ToLabel);
		if (!FromNode || !ToNode)
		{
			Errors.Add(FString::Printf(TEXT("connections[%d]: '%s' is not a node id in this request, a state here, or Entry (states: %s)"),
				Index, FromNode ? *Conn.ToLabel : *Conn.FromLabel, *StateList()));
			continue;
		}
		if (ToNode == Entry)
		{
			Errors.Add(FString::Printf(TEXT("connections[%d]: nothing can transition into Entry"), Index));
			continue;
		}
		Conn.To = Cast<UAnimStateNodeBase>(ToNode);
		if (FromNode == Entry)
		{
			Conn.bFromEntry = true;
			if (Conn.Settings.IsValid() && Conn.Settings->Values.Num() > 0)
			{
				Errors.Add(FString::Printf(TEXT("connections[%d]: the Entry link is not a transition and takes no settings"), Index));
				continue;
			}
		}
		else
		{
			Conn.From = Cast<UAnimStateNodeBase>(FromNode);
		}
		if (!Conn.To || (!Conn.bFromEntry && !Conn.From))
		{
			Errors.Add(FString::Printf(TEXT("connections[%d]: both ends must be states"), Index));
			continue;
		}
		UEdGraphPin* FromPin = Conn.bFromEntry ? EntryOutputPin(Entry) : Conn.From->GetOutputPin();
		UEdGraphPin* ToPin = Conn.To->GetInputPin();
		if (!FromPin || !ToPin)
		{
			Errors.Add(FString::Printf(TEXT("connections[%d]: '%s' -> '%s' cannot be connected"), Index, *Conn.FromLabel, *Conn.ToLabel));
			continue;
		}
		const FPinConnectionResponse Response = Schema->CanCreateConnection(FromPin, ToPin);
		if (Response.Response == CONNECT_RESPONSE_DISALLOW)
		{
			Errors.Add(FString::Printf(TEXT("connections[%d]: '%s' -> '%s': %s"), Index, *Conn.FromLabel, *Conn.ToLabel,
				Response.Message.IsEmpty() ? TEXT("not allowed") : *Response.Message.ToString()));
			continue;
		}
		Pending.Add(Conn);
	}

	auto RollbackAndRespond = [&](const TArray<FString>& InErrors)
	{
		Log.Rollback();
		for (int32 Index = Created.Num() - 1; Index >= 0; --Index)
		{
			// 删状态时连着它的转换会自己销毁（转换两头少一头就自毁），所以先看还在不在图里
			UEdGraphNode* Node = Created[Index];
			if (Node && Graph->Nodes.Contains(Node))
			{
				FBlueprintEditorUtils::RemoveNode(Blueprint, Node, /*bDontRecompile=*/true);
			}
		}
		Transaction->Cancel();

		TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
		Result->SetBoolField(TEXT("ok"), false);
		Result->SetBoolField(TEXT("rolled_back"), true);
		Result->SetStringField(TEXT("blueprint_path"), ResolvedPath);
		Result->SetStringField(TEXT("graph_name"), GraphPath);
		Result->SetNumberField(TEXT("created_count"), 0);
		Result->SetNumberField(TEXT("connection_count"), 0);
		Result->SetBoolField(TEXT("compiled"), false);
		Result->SetStringField(TEXT("message"),
			TEXT("Nothing was applied - the state machine is unchanged. Fix the errors and resend the complete node/connection set."));
		TArray<TSharedPtr<FJsonValue>> ErrorValues;
		for (const FString& Error : InErrors)
		{
			ErrorValues.Add(MakeShared<FJsonValueString>(Error));
		}
		Result->SetArrayField(TEXT("errors"), ErrorValues);
		UAL_CommandUtils::SendResponse(RequestId, 200, Result);
	};

	if (Errors.Num() > 0)
	{
		RollbackAndRespond(Errors);
		return;
	}

	// ===== 4. 落转换 =====
	TArray<TSharedPtr<FJsonValue>> TransitionsInfo;
	TSet<UEdGraphNode*> UsedTransitions;
	int32 MadeCount = 0;
	for (const FPending& Conn : Pending)
	{
		if (Conn.bFromEntry)
		{
			UEdGraphPin* EntryPin = EntryOutputPin(Entry);
			UAnimStateNodeBase* OldTarget = EntryTarget(Entry);
			if (OldTarget != Conn.To)
			{
				TWeakObjectPtr<UAnimStateEntryNode> WeakEntry = Entry;
				TWeakObjectPtr<UAnimStateNodeBase> WeakOld = OldTarget;
				Log.AddUndo([WeakEntry, WeakOld]()
				{
					UAnimStateEntryNode* RestoredEntry = WeakEntry.Get();
					UEdGraphPin* Pin = RestoredEntry ? EntryOutputPin(RestoredEntry) : nullptr;
					if (!Pin)
					{
						return;
					}
					Pin->BreakAllPinLinks();
					if (UAnimStateNodeBase* Old = WeakOld.Get())
					{
						Pin->MakeLinkTo(Old->GetInputPin());
					}
				});
				EntryPin->Modify();
				EntryPin->BreakAllPinLinks();
				Schema->TryCreateConnection(EntryPin, Conn.To->GetInputPin());
			}
			++MadeCount;
			continue;
		}

		// 同一对状态之间已有转换就改它，不再叠一条 —— 「读回来改一改写回去」靠这个
		UAnimStateTransitionNode* Transition = nullptr;
		for (UEdGraphNode* Node : Graph->Nodes)
		{
			UAnimStateTransitionNode* Candidate = Cast<UAnimStateTransitionNode>(Node);
			if (Candidate && !UsedTransitions.Contains(Candidate)
				&& Candidate->GetPreviousState() == Conn.From && Candidate->GetNextState() == Conn.To)
			{
				Transition = Candidate;
				break;
			}
		}
		const bool bIsNew = Transition == nullptr;
		if (bIsNew)
		{
			Transition = NewObject<UAnimStateTransitionNode>(Graph, NAME_None, RF_Transactional);
			Graph->AddNode(Transition, /*bFromUI=*/false, /*bSelectNewNode=*/false);
			Transition->CreateNewGuid();
			Transition->PostPlacedNewNode();
			Transition->AllocateDefaultPins();
			Transition->CreateConnections(Conn.From, Conn.To);
			Transition->NodePosX = (Conn.From->NodePosX + Conn.To->NodePosX) / 2;
			Transition->NodePosY = (Conn.From->NodePosY + Conn.To->NodePosY) / 2;
			Created.Add(Transition);
		}
		UsedTransitions.Add(Transition);
		if (Conn.Settings.IsValid())
		{
			TArray<FString> SettingErrors;
			ApplySettings(Transition, Conn.Settings, bIsNew, Log, SettingErrors);
			for (const FString& Error : SettingErrors)
			{
				Errors.Add(FString::Printf(TEXT("connections[%d] '%s' -> '%s': %s"), Conn.Index, *Conn.FromLabel, *Conn.ToLabel, *Error));
			}
		}
		++MadeCount;
	}

	if (Errors.Num() > 0)
	{
		RollbackAndRespond(Errors);
		return;
	}

	// ===== 5. clear_existing：没提到的状态和转换删掉（放最后，前面失败时它们还在）=====
	int32 RemovedCount = 0;
	if (bClearExisting)
	{
		TSet<UEdGraphNode*> Keep;
		for (const auto& Pair : IdMap)
		{
			Keep.Add(Pair.Value);
		}
		Keep.Append(UsedTransitions);
		// 连线里按名字 / GUID 点到的已有状态也算「提到了」：删了它，刚连上的转换也跟着没了
		for (const auto& Conn : Pending)
		{
			if (Conn.From) Keep.Add(Conn.From);
			if (Conn.To) Keep.Add(Conn.To);
		}
		for (UEdGraphNode* Node : PreExisting)
		{
			if (Node && Node->IsA<UAnimStateTransitionNode>() && !Keep.Contains(Node) && Graph->Nodes.Contains(Node))
			{
				FBlueprintEditorUtils::RemoveNode(Blueprint, Node, /*bDontRecompile=*/true);
				++RemovedCount;
			}
		}
		for (UEdGraphNode* Node : PreExisting)
		{
			if (Node && Node != Entry && !Keep.Contains(Node) && Graph->Nodes.Contains(Node) && Node->CanUserDeleteNode())
			{
				const FString DependentNote = DescribeGetterDependents(Blueprint, Node);
				if (!DependentNote.IsEmpty())
				{
					Warnings.Add(DependentNote);
				}
				FBlueprintEditorUtils::RemoveNode(Blueprint, Node, /*bDontRecompile=*/true);
				++RemovedCount;
			}
		}
	}

	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
	Graph->NotifyGraphChanged();
	Transaction.Reset();

	TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
	Result->SetBoolField(TEXT("ok"), true);
	Result->SetStringField(TEXT("blueprint_path"), ResolvedPath);
	Result->SetStringField(TEXT("graph_name"), GraphPath);
	Result->SetStringField(TEXT("graph_kind"), TEXT("state_machine"));
	int32 CreatedStates = 0;
	for (UEdGraphNode* Node : Created)
	{
		CreatedStates += Node && !Node->IsA<UAnimStateTransitionNode>() ? 1 : 0;
	}
	Result->SetNumberField(TEXT("created_count"), CreatedStates);
	Result->SetNumberField(TEXT("connection_count"), MadeCount);
	if (RemovedCount > 0)
	{
		Result->SetNumberField(TEXT("removed_count"), RemovedCount);
	}
	Result->SetBoolField(TEXT("undoable"), bUndoable);

	TMap<UEdGraphNode*, FString> NodeToCallerId;
	for (const auto& Pair : IdMap)
	{
		NodeToCallerId.Add(Pair.Value, Pair.Key);
	}
	if (bCompile)
	{
		UAL_CompileAndReport(Blueprint, NodeToCallerId, Result);
	}
	else
	{
		Result->SetBoolField(TEXT("compiled"), false);
	}

	// 回执在编译之后读：名字、子图路径、转换两端都以引擎此刻的样子为准
	for (const TSharedPtr<FJsonValue>& InfoValue : NodesInfo)
	{
		const TSharedPtr<FJsonObject> Info = InfoValue->AsObject();
		FString Id;
		Info->TryGetStringField(TEXT("id"), Id);
		if (UEdGraphNode** Found = IdMap.Find(Id))
		{
			Info->SetStringField(TEXT("class"), (*Found)->GetClass()->GetName());
			AnnotateNode(*Found, Info);
		}
	}
	Result->SetArrayField(TEXT("nodes"), NodesInfo);
	for (UEdGraphNode* Node : Graph->Nodes)
	{
		if (UAnimStateTransitionNode* Transition = Cast<UAnimStateTransitionNode>(Node))
		{
			if (UsedTransitions.Contains(Transition))
			{
				TSharedPtr<FJsonObject> Info = TransitionJson(Transition);
				if (Created.Contains(Transition))
				{
					Info->SetBoolField(TEXT("created"), true);
				}
				TransitionsInfo.Add(MakeShared<FJsonValueObject>(Info));
			}
		}
	}
	Result->SetArrayField(TEXT("transitions"), TransitionsInfo);
	if (const UAnimStateNodeBase* First = EntryTarget(Entry))
	{
		Result->SetStringField(TEXT("entry_state"), First->GetStateName());
	}
	if (Warnings.Num() > 0)
	{
		TArray<TSharedPtr<FJsonValue>> WarningValues;
		for (const FString& Warning : Warnings)
		{
			WarningValues.Add(MakeShared<FJsonValueString>(Warning));
		}
		Result->SetArrayField(TEXT("warnings"), WarningValues);
	}
	UAL_CommandUtils::SendResponse(RequestId, 200, Result);
}

// ============================================================================
// 资产
// ============================================================================

bool IsAnimInstanceClass(const UClass* Class)
{
	return Class && Class->IsChildOf(UAnimInstance::StaticClass());
}

UBlueprint* CreateAnimBlueprint(UClass* ParentClass, UPackage* Package, FName Name, const FString& SkeletonRef, FString& OutError)
{
	if (SkeletonRef.IsEmpty())
	{
		OutError = FString::Printf(
			TEXT("An Animation Blueprint is bound to one skeleton: pass skeleton = a Skeleton or a Skeletal Mesh. Skeletons in this project: %s"),
			*ListAssetNames(USkeleton::StaticClass(), 15));
		return nullptr;
	}

	FString LoadError;
	UObject* Loaded = LoadAssetLoose(SkeletonRef, { USkeleton::StaticClass(), USkeletalMesh::StaticClass() }, LoadError);
	USkeletalMesh* Mesh = Cast<USkeletalMesh>(Loaded);
	USkeleton* Skeleton = Mesh ? Mesh->GetSkeleton() : Cast<USkeleton>(Loaded);
	if (!Skeleton)
	{
		OutError = FString::Printf(TEXT("skeleton: %s. Skeletons in this project: %s"),
			LoadError.IsEmpty() ? TEXT("the mesh has no skeleton") : *LoadError, *ListAssetNames(USkeleton::StaticClass(), 15));
		return nullptr;
	}

	UAnimBlueprintFactory* Factory = NewObject<UAnimBlueprintFactory>();
	Factory->BlueprintType = BPTYPE_Normal;
	Factory->ParentClass = ParentClass;
	Factory->TargetSkeleton = Skeleton;
	Factory->PreviewSkeletalMesh = Mesh;
	Factory->bTemplate = false;
	UObject* Created = Factory->FactoryCreateNew(
		UAnimBlueprint::StaticClass(), Package, Name, RF_Public | RF_Standalone | RF_Transactional, nullptr, GWarn);
	UBlueprint* Blueprint = Cast<UBlueprint>(Created);
	if (!Blueprint)
	{
		OutError = TEXT("the Animation Blueprint factory did not create an asset");
	}
	return Blueprint;
}

void AppendBlueprintInfo(UBlueprint* Blueprint, const TSharedPtr<FJsonObject>& Result)
{
	const UAnimBlueprint* AnimBlueprint = Cast<UAnimBlueprint>(Blueprint);
	if (!AnimBlueprint || !Result.IsValid())
	{
		return;
	}
	TSharedPtr<FJsonObject> Info = MakeShared<FJsonObject>();
	Info->SetStringField(TEXT("target_skeleton"), AnimBlueprint->TargetSkeleton ? AnimBlueprint->TargetSkeleton->GetPathName() : TEXT("None"));
	Result->SetObjectField(TEXT("anim_blueprint"), Info);
}

void SearchAnimNodes(const FString& Query, int32 Limit, TArray<TSharedPtr<FJsonValue>>& OutResults, int32& OutTotal)
{
	OutTotal = 0;
	const FString Wanted = UAL_AnimGraphNames::NormalizeTypeName(Query);
	auto Score = [&Wanted](const FString& Name) -> int32
	{
		const FString Have = UAL_AnimGraphNames::NormalizeTypeName(Name);
		if (Have == Wanted) return 100;
		if (Have.StartsWith(Wanted)) return 75;
		if (Have.Contains(Wanted)) return 50;
		return 0;
	};

	struct FHit
	{
		UClass* Class = nullptr;
		int32 Score = 0;
	};
	TArray<FHit> Hits;
	for (TObjectIterator<UClass> It; It; ++It)
	{
		UClass* Class = *It;
		if (!Class->IsChildOf(UAnimGraphNode_Base::StaticClass())
			|| Class->HasAnyClassFlags(CLASS_Abstract | CLASS_Deprecated | CLASS_NewerVersionExists)
			|| Class->GetName().StartsWith(TEXT("SKEL_")) || Class->GetName().StartsWith(TEXT("REINST_"))
			|| Class->IsChildOf(UAnimGraphNode_Root::StaticClass()) || Class->IsChildOf(UAnimGraphNode_StateResult::StaticClass())
			|| Class->IsChildOf(UAnimGraphNode_TransitionResult::StaticClass()))
		{
			continue;
		}
		const int32 Best = FMath::Max3(
			Score(UAL_AnimGraphNames::WriteAsForClassName(Class->GetName())),
			Score(Class->GetName()),
			Score(Class->GetDisplayNameText().ToString()));
		if (Best > 0)
		{
			Hits.Add({ Class, Best });
		}
	}
	Hits.Sort([](const FHit& A, const FHit& B)
	{
		return A.Score != B.Score ? A.Score > B.Score : A.Class->GetName() < B.Class->GetName();
	});
	OutTotal = Hits.Num();

	for (int32 Index = 0; Index < Hits.Num() && OutResults.Num() < Limit; ++Index)
	{
		UClass* Class = Hits[Index].Class;
		TSharedPtr<FJsonObject> Entry = MakeShared<FJsonObject>();
		Entry->SetStringField(TEXT("write_as"), UAL_AnimGraphNames::WriteAsForClassName(Class->GetName()));
		Entry->SetStringField(TEXT("raw_class"), Class->GetName());
		// 类的显示名是「Anim Graph Node Blend List by Int」这种，去掉前缀才像编辑器里的叫法
		FString Title = Class->GetDisplayNameText().ToString();
		Title.RemoveFromStart(TEXT("Anim Graph Node "));
		Entry->SetStringField(TEXT("title"), Title);
		// 没写注释的类，提示文字就是类名本身，回了也没用
		const FString Tooltip = Class->GetToolTipText().ToString();
		if (!Tooltip.IsEmpty() && !Tooltip.StartsWith(TEXT("Anim Graph Node")))
		{
			Entry->SetStringField(TEXT("summary"), Tooltip.Left(160).Replace(TEXT("\n"), TEXT(" ")));
		}
		// 能写进 settings 的字段。引脚要建出来才看得到，这里先给设置名单
		TArray<TSharedPtr<FJsonValue>> Settings;
		if (FStructProperty* NodeProp = FindNodeStructProperty(Class))
		{
			for (TFieldIterator<FProperty> It(NodeProp->Struct); It && Settings.Num() < 30; ++It)
			{
				if (!It->HasAnyPropertyFlags(CPF_Edit) || IsPoseLinkProperty(*It))
				{
					continue;
				}
				Settings.Add(MakeShared<FJsonValueString>(FString::Printf(TEXT("%s (%s)"), *It->GetName(), *It->GetCPPType())));
			}
		}
		Entry->SetArrayField(TEXT("settings"), Settings);
		OutResults.Add(MakeShared<FJsonValueObject>(Entry));
	}
}
}
