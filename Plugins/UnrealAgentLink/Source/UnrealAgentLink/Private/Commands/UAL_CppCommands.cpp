#include "UAL_CppCommands.h"
#include "UAL_CommandUtils.h"

#include "Containers/Ticker.h"
#include "ClassTemplateEditorSubsystem.h"
#include "Components/SceneComponent.h"
#include "Editor.h"
#include "GameFramework/Character.h"
#include "GameFramework/Pawn.h"
#include "GameProjectUtils.h"
#include "GeneralProjectSettings.h"
#include "HAL/FileManager.h"
#include "Interfaces/IProjectManager.h"
#include "ISourceControlModule.h"
#include "ISourceControlProvider.h"
#include "Misc/App.h"
#include "Misc/CompilationResult.h"
#include "Misc/EngineVersionComparison.h"
#include "Misc/FileHelper.h"
#include "Misc/HotReloadInterface.h"
#include "Misc/Paths.h"
#include "ModuleDescriptor.h"
#include "Modules/ModuleManager.h"
#include "ProjectDescriptor.h"
#include "SourceControlOperations.h"
#include "UObject/Interface.h"
#include "UObject/Package.h"
#include "UObject/UObjectGlobals.h"

/*
 * Live Coding 只有 Windows 有（模块住在 Engine/Source/Developer/Windows/ 下），
 * 而且引擎自己的接法就是「只加 include 路径、不链接、运行时用 GetModulePtr 取」——
 * 见 UnrealEd.Build.cs / LevelEditor.Build.cs 里的
 *   if (Target.bWithLiveCoding) { PrivateIncludePathModuleNames.Add("LiveCoding"); }
 * 我们照抄，所以这里的调用点必须全部包在 WITH_LIVE_CODING 里。
 */
#if WITH_LIVE_CODING
#include "ILiveCodingModule.h"
#endif

DEFINE_LOG_CATEGORY_STATIC(LogUALCpp, Log, All);

void FUAL_CppCommands::RegisterCommands(TMap<FString, FHandlerFunc>& CommandMap)
{
	CommandMap.Add(TEXT("cpp.probe"), [](const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
	{
		Handle_Probe(Payload, RequestId);
	});

	CommandMap.Add(TEXT("cpp.list_modules"), [](const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
	{
		Handle_ListModules(Payload, RequestId);
	});

	CommandMap.Add(TEXT("cpp.compile"), [](const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
	{
		Handle_Compile(Payload, RequestId);
	});

	CommandMap.Add(TEXT("cpp.add_class"), [](const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
	{
		Handle_AddClass(Payload, RequestId);
	});
}

// ──────────────────────────── cpp.add_class ────────────────────────────
//
// ## 为什么不再调 GameProjectUtils::AddCodeToProject
//
// 它在真实工程上**不返回**（2026-09-08 真机验收案例 5，三轮都卡在「正在添加代码到项目…… 14%」）。
// 卡点定位到 AddCodeToProject → FSourceCodeNavigation::AddSourceFiles → GetSourceFileDatabase()：
// 同步把引擎 + 工程 + 所有插件的源码扫一遍，装了多个引擎的机器上不收敛，扫完什么也不做
// （VS 那个 AddSourceFiles 在 5.5 里是 #if 0）。除此之外它还会：
//   - 起 FScopedSlowTask::MakeDialog() 进度框；
//   - 没走通 AddSourceFiles 时同步跑一遍 GenerateProjectFiles（UBT，几十秒）；
//   - 热重载路上 WaitForCompletion 同步等编译；
//   - 纯蓝图工程 + Live Coding 时弹模态框。
// 每一样都把游戏线程（也就是我们的命令）钉住。
//
// ## 所以这里自己走一遍它的「生成」那一半，「编译」交给 cpp.compile
//
// 生成那一半照抄 GameProjectUtils::AddCodeToProject_Internal / GenerateClassHeaderFile /
// GenerateClassCPPFile（5.0–5.8 逐版本对过，只有 5.3 起「按父类链找类模板」这一处不同，
// 下面按版本分开）：同一份 Engine/Content/Editor/Templates 模板、同一套占位符、
// 同样的 API 宏规则、同样的 .uproject AdditionalDependencies 登记。
// **产出和用户在编辑器里点「新建 C++ 类」得到的逐字相同** —— 这是这条路成立的前提，
// 「AI 建的类」和「引擎建的类」长得不一样本身就是 bug 的来源。
//
// 抄而不调，是因为那几个生成函数和 FNewClassInfo 的成员函数都**不导出**
// （GenerateClassHeaderFile 等在 private 段；FNewClassInfo 没有 API 宏，5.8 起
// GameProjectUtils 也改成逐函数 UE_API），链接不到。
//
// 跳过的三步和理由：
//   - AddSourceFiles / GenerateProjectFiles：只是让 IDE 的解决方案里看得见新文件，
//     编译不依赖它们（UBT 自己扫目录）。回执里如实说「IDE 里要刷新一下才看得见」。
//   - 编译：调用方接着调 cpp.compile（异步，不卡编辑器，编不过有行号）。
//     一般会先把实现填完再编，比引擎「建完立刻空编一次」少编一轮。

/**
 * .uproject 的 Modules 段里声明了几个模块。
 *
 * **不能用 GameProjectUtils::GetCurrentProjectModules().Num()。** 那个函数在工程没有代码时
 * 会塞一个以工程名命名的**占位模块**（「这样新建类向导才有东西可选，建类时再真的建出来」，
 * GameProjectUtils.cpp 的 GetCurrentProjectModules），所以纯蓝图工程上它恒为 1；
 * 反过来，声明了模块但找不到 .Build.cs 的那些它又直接跳过。两头都不准。
 *
 * 2026-10-12 真机实测：纯蓝图工程 BPOnly52 上它返回 1，cpp.probe 因此把每一个纯蓝图工程
 * 都报成了「源码缺失的 C++ 工程」。09-03 在 ProbeHost 上看到的「has_code=false 但列出一个模块」
 * 也是这个占位，不是源码丢了。
 */
static int32 DeclaredProjectModuleCount()
{
	const FProjectDescriptor* Project = IProjectManager::Get().GetCurrentProject();
	return Project ? Project->Modules.Num() : 0;
}

namespace UALAddClass
{

enum class EKind : uint8
{
	UObject,     // 继承某个 UClass
	Interface,   // UINTERFACE（U + I 一对）
	SlateWidget, // SCompoundWidget 派生
	EmptyCpp     // 不继承 UObject 的普通类
};

struct FClassSpec
{
	EKind Kind = EKind::EmptyCpp;
	const UClass* BaseClass = nullptr;

	// 下面这些对应 FNewClassInfo 的同名成员（GameProjectUtils.cpp 里的实现，原样翻过来）

	FString PrefixCPP() const
	{
		switch (Kind)
		{
		case EKind::UObject:     return BaseClass ? BaseClass->GetPrefixCPP() : TEXT("U");
		case EKind::EmptyCpp:    return TEXT("F");
		case EKind::SlateWidget: return TEXT("S");
		case EKind::Interface:   return TEXT("U");
		}
		return FString();
	}

	FString BaseNameCPP() const
	{
		switch (Kind)
		{
		case EKind::UObject:     return BaseClass ? BaseClass->GetName() : FString();
		case EKind::EmptyCpp:    return FString();
		case EKind::SlateWidget: return TEXT("CompoundWidget");
		case EKind::Interface:   return TEXT("Interface");
		}
		return FString();
	}

	bool IncludePath(FString& Out) const
	{
		if (Kind == EKind::UObject && BaseClass && BaseClass->HasMetaData(TEXT("IncludePath")))
		{
			Out = BaseClass->GetMetaData(TEXT("IncludePath"));
			return true;
		}
		if (Kind == EKind::SlateWidget)
		{
			Out = TEXT("Widgets/SCompoundWidget.h");
			return true;
		}
		return false;
	}

	FString HeaderFilename(const FString& ClassName) const
	{
		return (Kind == EKind::SlateWidget ? TEXT("S") : TEXT("")) + ClassName + TEXT(".h");
	}

	FString SourceFilename(const FString& ClassName) const
	{
		return (Kind == EKind::SlateWidget ? TEXT("S") : TEXT("")) + ClassName + TEXT(".cpp");
	}

	/** 引擎内置模板的文件名。插件注册的类模板（UClassTemplate）优先，见 FindRegisteredTemplate */
	FString TemplateFilename(bool bHeader) const
	{
		const TCHAR* Ext = bHeader ? TEXT(".h.template") : TEXT(".cpp.template");
		switch (Kind)
		{
		case EKind::UObject:
			if (BaseClass == UActorComponent::StaticClass() || BaseClass == USceneComponent::StaticClass())
			{
				return FString(TEXT("ActorComponentClass")) + Ext;
			}
			if (BaseClass == AActor::StaticClass())     return FString(TEXT("ActorClass")) + Ext;
			if (BaseClass == APawn::StaticClass())      return FString(TEXT("PawnClass")) + Ext;
			if (BaseClass == ACharacter::StaticClass()) return FString(TEXT("CharacterClass")) + Ext;
			return FString(TEXT("UObjectClass")) + Ext;
		case EKind::EmptyCpp:    return FString(TEXT("EmptyClass")) + Ext;
		case EKind::SlateWidget: return FString(TEXT("SlateWidget")) + Ext;
		case EKind::Interface:   return FString(TEXT("InterfaceClass")) + Ext;
		}
		return FString();
	}

	/** GameProjectUtils::GetRequiredAdditionalDependencies */
	TArray<FString> RequiredDependencies() const
	{
		TArray<FString> Out;
		if (Kind == EKind::SlateWidget)
		{
			Out.Add(TEXT("Slate"));
			Out.Add(TEXT("SlateCore"));
		}
		else if (Kind == EKind::UObject && BaseClass)
		{
			const FString Package = BaseClass->GetOutermost()->GetName();
			if (Package.StartsWith(TEXT("/Script/")))
			{
				Out.Add(Package.Mid(8));
			}
		}
		return Out;
	}
};

/** 插件（或引擎）给某个父类注册的类模板。5.3 起沿父类链往上找，5.0–5.2 只认父类本身 —— 和引擎一致 */
const UClassTemplate* FindRegisteredTemplate(const FClassSpec& Spec)
{
	if (!GEditor || !Spec.BaseClass) return nullptr;
	const UClassTemplateEditorSubsystem* Subsystem = GEditor->GetEditorSubsystem<UClassTemplateEditorSubsystem>();
	if (!Subsystem) return nullptr;
#if UE_VERSION_OLDER_THAN(5, 3, 0)
	return Subsystem->FindClassTemplate(Spec.BaseClass);
#else
	for (const UClass* Class = Spec.BaseClass; Class; Class = Class->GetSuperClass())
	{
		if (const UClassTemplate* Template = Subsystem->FindClassTemplate(Class))
		{
			return Template;
		}
	}
	return nullptr;
#endif
}

bool ReadTemplate(const FClassSpec& Spec, bool bHeader, FString& Out, FText& OutFailReason)
{
	if (const UClassTemplate* Registered = FindRegisteredTemplate(Spec))
	{
		return bHeader ? Registered->ReadHeader(Out, OutFailReason) : Registered->ReadSource(Out, OutFailReason);
	}
	return GameProjectUtils::ReadTemplateFile(Spec.TemplateFilename(bHeader), Out, OutFailReason);
}

/** GameProjectUtils::MakeCopyrightLine（private） */
FString MakeCopyrightLine()
{
	const FString& Notice = GetDefault<UGeneralProjectSettings>()->CopyrightNotice;
	return Notice.IsEmpty() ? FString() : FString(TEXT("// ")) + Notice;
}

/** GameProjectUtils::ReplaceWildcard（private）：先连着前导 Tab / 结尾换行一起换，换不到再只换占位符本身 */
FString ReplaceWildcard(const FString& Input, const FString& From, const FString& To, bool bLeadingTab, bool bTrailingNewLine)
{
	FString Result = Input;
	FString WildCard = bLeadingTab ? TEXT("\t") : TEXT("");
	WildCard.Append(From);
	if (bTrailingNewLine)
	{
		WildCard.Append(LINE_TERMINATOR);
	}
	if (Result.ReplaceInline(*WildCard, *To, ESearchCase::CaseSensitive) == 0)
	{
		Result = Result.Replace(*From, *To, ESearchCase::CaseSensitive);
	}
	return Result;
}

/** GameProjectUtils::GetIncludePathForFile（private） */
FString IncludePathForFile(const FString& FullFilePath, const FString& ModuleRootPath)
{
	const FString HeaderPath = FPaths::ChangeExtension(FullFilePath, TEXT("h"));
	const FString PublicDir = ModuleRootPath / TEXT("Public") / TEXT("");
	if (HeaderPath.StartsWith(PublicDir))
	{
		return HeaderPath.RightChop(PublicDir.Len());
	}
	const FString PrivateDir = ModuleRootPath / TEXT("Private") / TEXT("");
	if (HeaderPath.StartsWith(PrivateDir))
	{
		return HeaderPath.RightChop(PrivateDir.Len());
	}
	return HeaderPath.RightChop(ModuleRootPath.Len());
}

/** GameProjectUtils.cpp 里文件内 static 的 TryParseIncludeDirective */
bool TryParseIncludeDirective(const FString& Text, int32 Pos, int32 EndPos, FString& OutIncludePath)
{
	while (Pos < EndPos && FChar::IsWhitespace(Text[Pos])) Pos++;
	if (Pos == EndPos || Text[Pos++] != TEXT('#')) return false;
	while (Pos < EndPos && FChar::IsWhitespace(Text[Pos])) Pos++;
	for (const TCHAR* Include = TEXT("include"); *Include; ++Include)
	{
		if (Pos == EndPos || Text[Pos] != *Include) return false;
		Pos++;
	}
	while (Pos < EndPos && FChar::IsWhitespace(Text[Pos])) Pos++;
	if (Pos == EndPos || Text[Pos++] != TEXT('"')) return false;
	const int32 Start = Pos;
	while (Pos < EndPos && Text[Pos] != TEXT('"')) Pos++;
	OutIncludePath = Text.Mid(Start, Pos - Start);
	return true;
}

/** 同上，IsUsingOldStylePch：模块里每个 .cpp 第一行 include 都是同一个文件，就是老式 PCH */
bool IsUsingOldStylePch(const FString& BaseDir)
{
	TArray<FString> Files;
	IFileManager::Get().FindFilesRecursive(Files, *BaseDir, TEXT("*.cpp"), true, false, false);

	TArray<FString> FirstIncluded;
	for (int32 Idx = 0; Idx < Files.Num() && Idx < 16; Idx++)
	{
		FString Text;
		FFileHelper::LoadFileToString(Text, *Files[Idx]);
		int32 LinePos = 0;
		while (LinePos < Text.Len())
		{
			int32 LineEnd = LinePos;
			while (LineEnd < Text.Len() && Text[LineEnd] != TEXT('\n')) LineEnd++;
			FString IncludePath;
			if (TryParseIncludeDirective(Text, LinePos, LineEnd, IncludePath))
			{
				FirstIncluded.AddUnique(FPaths::GetCleanFilename(IncludePath));
				break;
			}
			LinePos = LineEnd + 1;
		}
	}
	return FirstIncluded.Num() == 1 && Files.Num() > 1;
}

/** 去掉占位符 %CURSORFOCUSLOCATION%（引擎拿它定位 IDE 光标，HarvestCursorSyncLocation 里删掉） */
void StripCursorMarker(FString& Text)
{
	Text.ReplaceInline(TEXT("%CURSORFOCUSLOCATION%"), TEXT(""), ESearchCase::CaseSensitive);
}

/** GenerateClassHeaderFile 的生成部分（不落盘） */
bool RenderHeader(const FString& HeaderFile, const FString& ClassName, const FClassSpec& Spec,
	const FModuleContextInfo& Module, FString& Out, FText& OutFailReason)
{
	FString Template;
	if (!ReadTemplate(Spec, true, Template, OutFailReason)) return false;

	const FString Prefix = Spec.PrefixCPP();

	FString BaseInclude;
	FString BaseIncludePath;
	if (Spec.IncludePath(BaseIncludePath))
	{
		BaseInclude = FString::Printf(TEXT("#include \"%s\""), *BaseIncludePath);
	}

	// 类不在 Private 下就带模块导出宏，别的模块才链得到它
	FString ApiMacro;
	GameProjectUtils::EClassLocation Location = GameProjectUtils::EClassLocation::UserDefined;
	if (GameProjectUtils::GetClassLocation(HeaderFile, Module, Location) && Location != GameProjectUtils::EClassLocation::Private)
	{
		ApiMacro = Module.ModuleName.ToUpper() + TEXT("_API ");
	}

	TArray<FString> Specifiers;
	if (Spec.Kind == EKind::Interface)
	{
		Specifiers.Add(TEXT("MinimalAPI"));
	}

	Out = Template.Replace(TEXT("%COPYRIGHT_LINE%"), *MakeCopyrightLine(), ESearchCase::CaseSensitive);
	Out = Out.Replace(TEXT("%UNPREFIXED_CLASS_NAME%"), *ClassName, ESearchCase::CaseSensitive);
	Out = Out.Replace(TEXT("%CLASS_MODULE_API_MACRO%"), *ApiMacro, ESearchCase::CaseSensitive);
	Out = Out.Replace(TEXT("%UCLASS_SPECIFIER_LIST%"), *GameProjectUtils::MakeCommaDelimitedList(Specifiers, false), ESearchCase::CaseSensitive);
	Out = Out.Replace(TEXT("%PREFIXED_CLASS_NAME%"), *(Prefix + ClassName), ESearchCase::CaseSensitive);
	Out = Out.Replace(TEXT("%PREFIXED_BASE_CLASS_NAME%"), *(Prefix + Spec.BaseNameCPP()), ESearchCase::CaseSensitive);
	Out = Out.Replace(TEXT("%MODULE_NAME%"), *Module.ModuleName, ESearchCase::CaseSensitive);
	Out = ReplaceWildcard(Out, TEXT("%EVENTUAL_CONSTRUCTOR_DECLARATION%"), TEXT(""), true, true);
	Out = ReplaceWildcard(Out, TEXT("%CLASS_PROPERTIES%"), TEXT(""), true, true);
	Out = ReplaceWildcard(Out, TEXT("%CLASS_FUNCTION_DECLARATIONS%"), TEXT(""), true, true);
	if (BaseInclude.IsEmpty())
	{
		Out = Out.Replace(TEXT("%BASE_CLASS_INCLUDE_DIRECTIVE%") LINE_TERMINATOR, TEXT(""), ESearchCase::CaseSensitive);
	}
	Out = Out.Replace(TEXT("%BASE_CLASS_INCLUDE_DIRECTIVE%"), *BaseInclude, ESearchCase::CaseSensitive);
	StripCursorMarker(Out);
	return true;
}

/** GenerateClassCPPFile 的生成部分（不落盘） */
bool RenderSource(const FString& CppFile, const FString& ClassName, const FClassSpec& Spec,
	const FModuleContextInfo& Module, FString& Out, FText& OutFailReason)
{
	FString Template;
	if (!ReadTemplate(Spec, false, Template, OutFailReason)) return false;

	GameProjectUtils::EClassLocation Location = GameProjectUtils::EClassLocation::UserDefined;
	if (!GameProjectUtils::GetClassLocation(CppFile, Module, Location, &OutFailReason)) return false;

	FString PchInclude;
	if (IsUsingOldStylePch(Module.ModuleSourcePath))
	{
		const FString ModuleInclude = GameProjectUtils::DetermineModuleIncludePath(Module, CppFile);
		if (!ModuleInclude.IsEmpty())
		{
			PchInclude = FString::Printf(TEXT("#include \"%s\""), *ModuleInclude);
		}
	}

	const FString Prefixed = Spec.PrefixCPP() + ClassName;
	Out = Template.Replace(TEXT("%COPYRIGHT_LINE%"), *MakeCopyrightLine(), ESearchCase::CaseSensitive);
	Out = Out.Replace(TEXT("%UNPREFIXED_CLASS_NAME%"), *ClassName, ESearchCase::CaseSensitive);
	Out = Out.Replace(TEXT("%PREFIXED_CLASS_NAME%"), *Prefixed, ESearchCase::CaseSensitive);
	Out = Out.Replace(TEXT("%MODULE_NAME%"), *Module.ModuleName, ESearchCase::CaseSensitive);
	Out = Out.Replace(TEXT("%PCH_INCLUDE_DIRECTIVE%"), *PchInclude, ESearchCase::CaseSensitive);

	// 本类头文件的 include：先删掉老模板里不带子目录的写法，再换成带子目录的
	const FString RelativeHeader = IncludePathForFile(CppFile, Module.ModuleSourcePath);
	Out = Out.Replace(*FString::Printf(TEXT("#include \"%s\""), *FPaths::GetCleanFilename(RelativeHeader)), TEXT(""), ESearchCase::CaseSensitive);
	Out = Out.Replace(TEXT("%MY_HEADER_INCLUDE_DIRECTIVE%"), *FString::Printf(TEXT("#include \"%s\""), *RelativeHeader), ESearchCase::CaseSensitive);

	Out = ReplaceWildcard(Out, TEXT("%ADDITIONAL_INCLUDE_DIRECTIVES%"), TEXT(""), false, true);
	Out = ReplaceWildcard(Out, TEXT("%EVENTUAL_CONSTRUCTOR_DEFINITION%"), TEXT(""), false, true);
	Out = ReplaceWildcard(Out, TEXT("%ADDITIONAL_MEMBER_DEFINITIONS%"), TEXT(""), false, true);
	StripCursorMarker(Out);
	return true;
}

/**
 * 把父类所在模块登记进 .uproject 的 AdditionalDependencies（UBT 会把它当成私有依赖）。
 *
 * 和引擎有一处**有意的**不同：模块的 .Build.cs 里已经写了这个模块名，就不登记。
 * 引擎是无条件补（所以老工程的 .uproject 里常见 "AdditionalDependencies": ["Engine"]）。
 * 补了也无害，但改了 .uproject 会让 cpp.compile 报 needs_full_rebuild（它比的是配置和产物
 * 的时间戳）—— 建一个 Actor 就提示要完整重编，是一条假警报，模型会照着去关编辑器。
 *
 * 返回实际新登记的模块。.uproject 写不进去（只读、被源码管理锁着）时 OutFailReason 非空。
 */
TArray<FString> RegisterDependencies(const FModuleContextInfo& Module, TArray<FString> Required, FText& OutFailReason)
{
	TArray<FString> Added;
	Required.Remove(Module.ModuleName);
	if (Required.Num() == 0) return Added;

	FString BuildCs;
	FFileHelper::LoadFileToString(BuildCs, *(Module.ModuleSourcePath / Module.ModuleName + TEXT(".Build.cs")));
	Required.RemoveAll([&BuildCs](const FString& Dep)
	{
		return BuildCs.Contains(TEXT("\"") + Dep + TEXT("\""));
	});
	if (Required.Num() == 0) return Added;

	const FString ProjectFile = FPaths::GetProjectFilePath();
	FProjectDescriptor Descriptor;
	if (!Descriptor.Load(ProjectFile, OutFailReason)) return Added;

	for (FModuleDescriptor& Desc : Descriptor.Modules)
	{
		if (Desc.Name != FName(*Module.ModuleName)) continue;
		for (const FString& Dep : Required)
		{
			if (!Desc.AdditionalDependencies.Contains(Dep))
			{
				Desc.AdditionalDependencies.Add(Dep);
				Added.Add(Dep);
			}
		}
	}
	// 插件模块不在 .uproject 里，引擎那条路也是什么都不做
	if (Added.Num() == 0) return Added;

	GameProjectUtils::TryMakeProjectFileWriteable(ProjectFile);
	if (!Descriptor.Save(ProjectFile, OutFailReason))
	{
		Added.Reset();
		return Added;
	}
	IProjectManager::Get().LoadProjectFile(ProjectFile);
	GameProjectUtils::ResetCurrentProjectModulesCache();
	return Added;
}

/** 新文件登记进源码管理。异步：Perforce 慢的时候别把编辑器钉住 */
bool MarkForAdd(const TArray<FString>& Files)
{
	ISourceControlModule& Scc = ISourceControlModule::Get();
	if (!Scc.IsEnabled() || !Scc.GetProvider().IsAvailable()) return false;

	TArray<FString> Absolute;
	for (const FString& File : Files)
	{
		Absolute.Add(IFileManager::Get().ConvertToAbsolutePathForExternalAppForRead(*File));
	}
	Scc.GetProvider().Execute(ISourceControlOperation::Create<FMarkForAdd>(), Absolute, EConcurrency::Asynchronous);
	return true;
}

/** 名字是不是合法的 C++ 标识符（工程名要当模块名用时检查） */
bool IsCppIdentifier(const FString& Name)
{
	if (Name.IsEmpty() || FChar::IsDigit(Name[0])) return false;
	for (const TCHAR C : Name)
	{
		if (!(FChar::IsAlnum(C) && C < 128) && C != TEXT('_')) return false;
	}
	return true;
}

/** 某个模块里已经有这个头文件的话，返回它的路径（给「已存在」的报错指路） */
FString FindExistingHeader(const FModuleContextInfo& Module, const FString& HeaderName)
{
	TArray<FString> Found;
	IFileManager::Get().FindFilesRecursive(Found, *Module.ModuleSourcePath, *HeaderName, true, false, false);
	return Found.Num() > 0 ? FPaths::ConvertRelativePathToFull(Found[0]) : FString();
}

} // namespace UALAddClass

void FUAL_CppCommands::Handle_AddClass(const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
{
	using namespace UALAddClass;

	FString RawName;
	if (!Payload->TryGetStringField(TEXT("name"), RawName) || RawName.TrimStartAndEnd().IsEmpty())
	{
		UAL_CommandUtils::SendError(RequestId, 400, TEXT("缺少字段: name"));
		return;
	}
	RawName.TrimStartAndEndInline();

	FString ParentClass, ModuleName, Location;
	Payload->TryGetStringField(TEXT("parent_class"), ParentClass);
	Payload->TryGetStringField(TEXT("module"), ModuleName);
	Payload->TryGetStringField(TEXT("location"), Location);
	ParentClass.TrimStartAndEndInline();

	// ── 父类 → 类别 ──
	FClassSpec Spec;
	{
		const FString P = ParentClass;
		if (P.IsEmpty() || P.Equals(TEXT("None"), ESearchCase::IgnoreCase))
		{
			Spec.Kind = EKind::EmptyCpp;
		}
		else if (P.Equals(TEXT("Interface"), ESearchCase::IgnoreCase) || P.Equals(TEXT("UInterface"), ESearchCase::IgnoreCase)
			|| P.Equals(TEXT("UnrealInterface"), ESearchCase::IgnoreCase))
		{
			// 选 UInterface 当父类时，引擎走的是专门的「虚幻接口」模板（U/I 一对），不是 UObject 模板
			Spec.Kind = EKind::Interface;
		}
		else if (P.Equals(TEXT("SlateWidget"), ESearchCase::IgnoreCase) || P.Equals(TEXT("SCompoundWidget"), ESearchCase::IgnoreCase)
			|| P.Equals(TEXT("CompoundWidget"), ESearchCase::IgnoreCase))
		{
			Spec.Kind = EKind::SlateWidget;
		}
		else
		{
			FString ResolveError;
			UClass* Base = UAL_CommandUtils::ResolveClassFromIdentifier(P, nullptr, ResolveError);
			if (!Base)
			{
				UAL_CommandUtils::SendError(RequestId, 400,
					FString::Printf(TEXT("找不到父类 %s：%s"), *P, *ResolveError));
				return;
			}
			if (Base == UInterface::StaticClass())
			{
				Spec.Kind = EKind::Interface;
			}
			else
			{
				Spec.Kind = EKind::UObject;
				Spec.BaseClass = Base;
			}
		}
	}

	// 名字带了前缀（ASurvivorDirector / UHealthComponent / IDamageable）就剥掉 —— 引擎按父类
	// 加前缀，不剥会建出 AASurvivorDirector。
	//
	// 只在「前缀和父类对得上 + 后面是一个大写字母再跟小写字母」时剥：AIDirector、UIManager
	// 这种名字本身就以缩写开头（AI、UI），剥了会变成 IDirector / IManager，换掉的是用户要的名字。
	// 宁可偶尔多一层前缀（回执里看得见最终类名），也不悄悄改名。
	FString ClassName = RawName;
	{
		const bool bInterfaceI = Spec.Kind == EKind::Interface && ClassName.StartsWith(TEXT("I"), ESearchCase::CaseSensitive);
		const FString Strip = bInterfaceI ? FString(TEXT("I")) : Spec.PrefixCPP();
		const int32 N = Strip.Len();
		if (N > 0 && ClassName.Len() > N + 1
			&& ClassName.StartsWith(Strip, ESearchCase::CaseSensitive)
			&& FChar::IsUpper(ClassName[N]) && FChar::IsLower(ClassName[N + 1]))
		{
			ClassName.RightChopInline(N);
		}
	}

	// ── 纯蓝图工程：先补上工程的主模块（引擎在同一情况下做的事，GenerateBasicSourceCode） ──
	const bool bHadCode = GameProjectUtils::ProjectHasCodeFiles();
	bool bCreatedPrimaryModule = false;
	TArray<FString> CreatedFiles;

	if (!bHadCode)
	{
		if (DeclaredProjectModuleCount() > 0)
		{
			// .uproject 声明了模块但 Source/ 不在：工程是坏的，补一个模块盖不住
			UAL_CommandUtils::SendError(RequestId, 409,
				TEXT(".uproject 声明了 C++ 模块，但磁盘上找不到源码（Source 目录不存在或是空的）。")
				TEXT("这是源码缺失的 C++ 工程，不是纯蓝图工程 —— 在这上面建类会和缺掉的那份源码冲突。")
				TEXT("请让用户确认工程拷贝时有没有漏掉 Source 目录。"));
			return;
		}
		const FString ProjectName = FApp::GetProjectName();
		if (!IsCppIdentifier(ProjectName))
		{
			UAL_CommandUtils::SendError(RequestId, 409, FString::Printf(
				TEXT("工程名 %s 不能当 C++ 模块名用（只能是英文字母、数字、下划线，且不以数字开头）。")
				TEXT("第一个 C++ 类会以工程名建主模块，引擎在这里也会失败。需要先给工程改一个英文名。"), *ProjectName));
			return;
		}
		if (!ModuleName.IsEmpty() && !ModuleName.Equals(ProjectName, ESearchCase::IgnoreCase))
		{
			UAL_CommandUtils::SendError(RequestId, 400, FString::Printf(
				TEXT("这是纯蓝图工程，第一个类只能放进以工程名命名的主模块 %s（引擎的规矩）。module 留空即可。"), *ProjectName));
			return;
		}

		// 和引擎一样：先清掉 Intermediate/Source，蓝图工程带着自定义构建设置转 C++ 时不清会出错
		IFileManager::Get().DeleteDirectory(*(FPaths::ProjectIntermediateDir() / TEXT("Source")), false, true);

		FText Reason;
		if (!GameProjectUtils::GenerateBasicSourceCode(CreatedFiles, Reason))
		{
			GameProjectUtils::DeleteCreatedFiles(FPaths::GameSourceDir().LeftChop(1), CreatedFiles);
			UAL_CommandUtils::SendError(RequestId, 500,
				FString::Printf(TEXT("给工程生成主模块失败：%s"), *Reason.ToString()));
			return;
		}
		bCreatedPrimaryModule = true;
		GameProjectUtils::ResetCurrentProjectModulesCache();
	}

	// ── 选模块 ──
	//
	// **取副本，不取引用。** GetCurrentProjectModules() 返回 IProjectManager 内部数组的引用，
	// 下面 RegisterDependencies 会 LoadProjectFile 把它清掉重建 —— 拿着元素指针就悬空了
	// （2026-09-08 案例 5 的乱码 fail_reason 就是这么来的）。插件模块也收进来：引擎的
	// 新建类对话框允许选插件模块。
	TArray<FModuleContextInfo> Modules = GameProjectUtils::GetCurrentProjectModules();
	Modules.Append(GameProjectUtils::GetCurrentProjectPluginModules());
	// 我们自己（UnrealAgentLink 装在工程的 Plugins/ 下，所以也在插件模块里）不能当落点：
	// 盒子每次更新插件都会整个替换这个目录，写进去的类下次就没了
	Modules.RemoveAll([](const FModuleContextInfo& M)
	{
		return M.ModuleName == TEXT("UnrealAgentLink");
	});
	if (Modules.Num() == 0)
	{
		UAL_CommandUtils::SendError(RequestId, 500,
			TEXT("工程报告有 C++ 代码，但一个模块都列不出来。请让用户确认工程能否正常编译。"));
		return;
	}
	const FModuleContextInfo* FoundModule = ModuleName.IsEmpty()
		? &Modules[0] // 第一个是工程的主游戏模块
		: Modules.FindByPredicate([&ModuleName](const FModuleContextInfo& M)
		{
			return M.ModuleName.Equals(ModuleName, ESearchCase::IgnoreCase);
		});
	if (!FoundModule && ModuleName.Equals(TEXT("UnrealAgentLink"), ESearchCase::IgnoreCase))
	{
		UAL_CommandUtils::SendError(RequestId, 400,
			TEXT("UnrealAgentLink 是虚幻盒子自己的插件，每次更新都会整个替换，类不能建在这里。module 留空用工程主模块。"));
		return;
	}
	if (!FoundModule)
	{
		FString Available;
		for (const FModuleContextInfo& M : Modules)
		{
			Available += (Available.IsEmpty() ? TEXT("") : TEXT("、")) + M.ModuleName;
		}
		UAL_CommandUtils::SendError(RequestId, 400,
			FString::Printf(TEXT("找不到模块 %s。这个工程有：%s"), *ModuleName, *Available));
		return;
	}
	const FModuleContextInfo Module = *FoundModule;

	// ── 校验：名字、父类、落点、文件 ──
	FText FailReason;
	if (!GameProjectUtils::IsValidClassNameForCreation(ClassName, Module, TSet<FString>(), FailReason))
	{
		// 最常见的原因是「已经有了」—— 多半是上一轮建过、还没编进来。指给它看文件在哪，
		// 别让模型换个名字再建一个
		const FString Existing = FindExistingHeader(Module, Spec.HeaderFilename(ClassName));
		UAL_CommandUtils::SendError(RequestId, Existing.IsEmpty() ? 400 : 409, Existing.IsEmpty()
			? FString::Printf(TEXT("类名 %s 不能用：%s"), *ClassName, *FailReason.ToString())
			: FString::Printf(TEXT("类 %s 已经存在：%s。不要换个名字重建 —— 直接读这个文件接着改，改完调 cpp_compile。"),
				*ClassName, *Existing));
		return;
	}
	if (Spec.Kind == EKind::UObject && !GameProjectUtils::IsValidBaseClassForCreation(Spec.BaseClass, Module))
	{
		UAL_CommandUtils::SendError(RequestId, 400, FString::Printf(
			TEXT("%s 不能作为父类：模块 %s 够不着它（它所在的模块没有导出这个类），或者它被标记为不可继承。"),
			*Spec.BaseClass->GetName(), *Module.ModuleName));
		return;
	}

	// 默认放模块根目录（引擎新建类对话框的初始路径就是这里）；public/private 进对应子目录，
	// CalculateSourcePaths 会把 .h 和 .cpp 分到 Public/Private 两边
	FString ClassPath = Module.ModuleSourcePath;
	if (Location.Equals(TEXT("public"), ESearchCase::IgnoreCase))
	{
		ClassPath = Module.ModuleSourcePath / TEXT("Public");
	}
	else if (Location.Equals(TEXT("private"), ESearchCase::IgnoreCase))
	{
		ClassPath = Module.ModuleSourcePath / TEXT("Private");
	}
	FString HeaderDir, SourceDir;
	if (!GameProjectUtils::CalculateSourcePaths(ClassPath, Module, HeaderDir, SourceDir, &FailReason))
	{
		UAL_CommandUtils::SendError(RequestId, 400,
			FString::Printf(TEXT("落点不合法：%s"), *FailReason.ToString()));
		return;
	}
	const FString HeaderFile = FPaths::ConvertRelativePathToFull(HeaderDir / Spec.HeaderFilename(ClassName));
	const FString SourceFile = FPaths::ConvertRelativePathToFull(SourceDir / Spec.SourceFilename(ClassName));
	for (const FString& File : { HeaderFile, SourceFile })
	{
		if (IFileManager::Get().FileExists(*File))
		{
			UAL_CommandUtils::SendError(RequestId, 409, FString::Printf(
				TEXT("%s 已经存在，没有覆盖。如果它就是要建的类，直接读它接着改。"), *File));
			return;
		}
	}

	// ── 先在内存里把两份文件都生成好，再落盘：模板读不到时一个文件都不留 ──
	FString HeaderText, SourceText;
	if (!RenderHeader(HeaderFile, ClassName, Spec, Module, HeaderText, FailReason)
		|| !RenderSource(SourceFile, ClassName, Spec, Module, SourceText, FailReason))
	{
		UAL_CommandUtils::SendError(RequestId, 500,
			FString::Printf(TEXT("读引擎的类模板失败：%s"), *FailReason.ToString()));
		return;
	}
	if (!GameProjectUtils::WriteOutputFile(HeaderFile, HeaderText, FailReason))
	{
		UAL_CommandUtils::SendError(RequestId, 500,
			FString::Printf(TEXT("写 %s 失败：%s"), *HeaderFile, *FailReason.ToString()));
		return;
	}
	if (!GameProjectUtils::WriteOutputFile(SourceFile, SourceText, FailReason))
	{
		IFileManager::Get().Delete(*HeaderFile);
		UAL_CommandUtils::SendError(RequestId, 500,
			FString::Printf(TEXT("写 %s 失败：%s（已删掉刚写的头文件）"), *SourceFile, *FailReason.ToString()));
		return;
	}
	CreatedFiles.Add(HeaderFile);
	CreatedFiles.Add(SourceFile);

	// ── 依赖登记、源码管理。都不影响「类建出来了」，失败只记警告 ──
	TArray<TSharedPtr<FJsonValue>> Warnings;
	FText DepFail;
	const TArray<FString> DepsAdded = RegisterDependencies(Module, Spec.RequiredDependencies(), DepFail);
	if (!DepFail.IsEmpty())
	{
		Warnings.Add(MakeShared<FJsonValueString>(FString::Printf(
			TEXT("父类所在模块没能登记进 .uproject（%s）。编译时如果报找不到父类的符号（LNK2019），")
			TEXT("在模块的 .Build.cs 里把它加进 PrivateDependencyModuleNames。"), *DepFail.ToString())));
	}
	const bool bMarkedForAdd = MarkForAdd(CreatedFiles);

	// 状态字段一律从磁盘读回，不回显入参（AGENTS.md §5 第 14 条）
	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("result"), TEXT("Succeeded"));
	Data->SetStringField(TEXT("class_name"), Spec.PrefixCPP() + ClassName);
	if (Spec.Kind == EKind::Interface)
	{
		Data->SetStringField(TEXT("interface_name"), TEXT("I") + ClassName);
	}
	if (ClassName != RawName)
	{
		Data->SetStringField(TEXT("requested_name"), RawName);
	}
	Data->SetStringField(TEXT("module"), Module.ModuleName);
	Data->SetStringField(TEXT("header_path"), HeaderFile);
	Data->SetStringField(TEXT("cpp_path"), SourceFile);
	Data->SetBoolField(TEXT("header_exists"), IFileManager::Get().FileExists(*HeaderFile));
	Data->SetBoolField(TEXT("cpp_exists"), IFileManager::Get().FileExists(*SourceFile));

	TArray<TSharedPtr<FJsonValue>> Created;
	for (const FString& File : CreatedFiles)
	{
		Created.Add(MakeShared<FJsonValueString>(FPaths::ConvertRelativePathToFull(File)));
	}
	Data->SetArrayField(TEXT("created_files"), Created);

	TArray<TSharedPtr<FJsonValue>> Deps;
	for (const FString& Dep : DepsAdded)
	{
		Deps.Add(MakeShared<FJsonValueString>(Dep));
	}
	Data->SetArrayField(TEXT("dependencies_added"), Deps);
	Data->SetBoolField(TEXT("created_primary_module"), bCreatedPrimaryModule);
	Data->SetBoolField(TEXT("marked_for_add"), bMarkedForAdd);
	Data->SetBoolField(TEXT("reloaded"), false);
	Data->SetArrayField(TEXT("warnings"), Warnings);

	UE_LOG(LogUALCpp, Log, TEXT("cpp.add_class %s -> %s / %s (primary_module=%d)"),
		*ClassName, *HeaderFile, *SourceFile, bCreatedPrimaryModule ? 1 : 0);
	UAL_CommandUtils::SendResponse(RequestId, 200, Data);
}

// ───────────────────────────── cpp.compile ─────────────────────────────

namespace
{

/** 编译最多等多久。超时后如实说「不知道成没成」，不报成功 */
constexpr double kCompileTimeoutSeconds = 15.0 * 60.0;

/**
 * Live Coding 说「不编了」之后，再给结果日志多少秒才认输。
 *
 * 引擎清标志和打印结果不在同一个线程、也不在同一帧（见 FCompileJob::StoppedCompilingAt
 * 那段注释）。5 秒对一次帧回调是天文数字，而代价只是极少数真·Unknown 的场景多等 5 秒。
 */
constexpr double kResultLogGraceSeconds = 5.0;

/**
 * 引擎眼里「热重载得动」的模块有几个。
 *
 * 判据抄 DoHotReloadFromEditor 自己那两步（HotReload.cpp:761 → :517）：
 * 先取所有**已加载的游戏模块**，再看有没有对应的 `/Script/<模块名>` 包。
 *
 * 关键在第二步：**那个包只有在模块里声明过 UObject（UCLASS / USTRUCT / UENUM）
 * 时才存在。** 一个只有普通 C++ 类和函数的游戏模块，这里数出来就是 0，
 * 而引擎会在 13 毫秒内同步拒绝，一行都不编。
 *
 * 2026-09-08 真机验收案例 2 就翻在这里：测试工程的游戏模块一个 UObject 都没有，
 * 编辑器日志里只留下一句 `RebindPackages not possible (no packages specified)`，
 * 然后工具等一个永远不会广播的完成事件等到超时。
 */
int32 CountHotReloadablePackages()
{
	TArray<FModuleStatus> Statuses;
	FModuleManager::Get().QueryModules(Statuses);

	int32 Count = 0;
	for (const FModuleStatus& Status : Statuses)
	{
		if (!Status.bIsLoaded || !Status.bIsGameModule)
		{
			continue;
		}
		if (FindPackage(nullptr, *(TEXT("/Script/") + Status.Name)) != nullptr)
		{
			++Count;
		}
	}
	return Count;
}

/**
 * Live Coding 处在「已经关掉勾选，但会话还在这个进程里跑」的半吊子状态吗？
 *
 * 判据是两个状态位的组合，不是任何一个单独的位：
 *   HasStarted() == true       控制台进程还在（EState::Running 也算 started）
 *   IsEnabledForSession() == false   这个会话不再用它编译
 *
 * 用户是这么走进来的：在编辑器偏好设置里把 Enable Live Coding 取消勾选。
 * 引擎当场只做了 HideConsole()（LiveCodingModule.cpp:690-697），并且自己在日志里
 * 说得很清楚：
 *
 *   "Console will be hidden but remain running in the background.
 *    Restart to disable completely."
 *
 * **这个状态下热重载会把编辑器卡死。** 2026-09-08 真机验收案例 9 实测：
 * cpp.probe 报 hotreload（两个引擎守卫只看 IsEnabledForSession，都放行了），
 * 然后 cpp.compile 一发出去，游戏线程 20 分钟不动一帧，
 * 没有任何编译进程起来，编辑器点什么都没反应，最后只能关掉。
 *
 * 所以这里必须**当场拦住**：把 20 分钟的假死换成一句「请重启编辑器」。
 * 我原来在验收单里推断「关掉不重启也能编」，依据是那两个守卫的判据 ——
 * 推断错在只看了守卫放不放行，没看放行之后那条路还走不走得通。
 */
bool LiveCodingHalfDisabled()
{
#if WITH_LIVE_CODING
	if (ILiveCodingModule* Lc = FModuleManager::GetModulePtr<ILiveCodingModule>(LIVE_CODING_MODULE_NAME))
	{
		return Lc->HasStarted() && !Lc->IsEnabledForSession();
	}
#endif
	return false;
}

/** 半吊子状态下给用户的那句话。探测和编译两处都要用 */
FString LiveCodingHalfDisabledHint()
{
	return TEXT("这个编辑器会话处在一个「关了但没关干净」的状态：Live Coding 的勾选被取消了，")
		TEXT("但它的会话还在这个进程里跑着（引擎自己在日志里说的：Console will be hidden ")
		TEXT("but remain running in the background. Restart to disable completely）。")
		TEXT("**这个状态下走热重载会把编辑器卡死**（实测：20 分钟不动一帧，只能强制关闭）。")
		TEXT("解法是重启编辑器：先保存，然后调 ue_restart_editor（盒子会等它回来并自动重连），")
		TEXT("重启之后热重载就正常了，编不过时也能拿到完整的文件名和行号。");
}

/** 热重载编不动时给用户的那句话。两处要用（探测和编译），所以抽出来 */
FString NoReloadablePackagesHint()
{
	return TEXT("这个工程当前加载的游戏模块里，没有任何一个声明过 UObject 类")
		TEXT("（UCLASS / USTRUCT / UENUM）。引擎的热重载是按 UObject 包来重新绑定的，")
		TEXT("模块里没有 UObject 就没有可绑定的包，引擎会直接拒绝，一行都不会编 ——")
		TEXT("哪怕你刚往模块里加了 UCLASS，没编进来之前它也不算。")
		TEXT("解法：调 cpp_full_rebuild（盒子替用户关编辑器、完整编译、再打开，有未保存的改动会先拦下来）。");
}

/**
 * 只收 LogLiveCoding 的一次性输出设备。
 *
 * Live Coding 的结果**没有任何接口能查**：`OnPatchCompleteDelegate` 只在成功时
 * 广播（LiveCodingModule.cpp:898），`LastResults` 也没有 getter。
 * 唯一的出口是它自己 UE_LOG 出来的那四条固定文案，所以只能在这里捞。
 *
 * 只留 LogLiveCoding 一个类别 —— 编译期间引擎会刷大量别的日志，全存下来
 * 既占内存又要在后面过滤一遍。
 */
class FLiveCodingLogSink : public FOutputDevice
{
public:
	TArray<FString> Lines;

	virtual void Serialize(const TCHAR* V, ELogVerbosity::Type, const FName& Category) override
	{
		static const FName LiveCodingCategory(TEXT("LogLiveCoding"));
		if (Category == LiveCodingCategory)
		{
			Lines.Add(FString(V));
		}
	}
};

/** 回给盒子的 UBT 日志最多多长。一次失败的 Log.txt 通常二三十 KB，报错在尾部 */
constexpr int32 kMaxBuildLogChars = 256 * 1024;

/**
 * 读 Live Coding 这次编译的 UBT 日志。找不到或者是旧的就返回 false。
 *
 * Live Coding 控制台窗口里那些编译器报错，是它拉起的 UnrealBuildTool 的输出，
 * **UBT 自己会把同样的内容写进 Log.txt**（2026-09-29 在 5.8 上对过：窗口里的
 * error C2065 在 %LOCALAPPDATA%/UnrealBuildTool/Log.txt 里逐行都有）。
 * 编辑器这边的 LogLiveCoding 只有一句「失败了，去看控制台」，所以只能来这里读。
 *
 * 两个候选位置：安装版引擎写 LocalAppData，源码版 / 老引擎写 Engine/Programs 下。
 * 取**比这次编译开始时间新**的那一份 —— 同机别的 UBT（IDE 编译、打包）也写这个文件，
 * 读到上一次的旧日志会把别人的报错安到这次头上，那比读不到还糟。
 */
bool ReadUbtLogSince(const FDateTime& SinceUtc, FString& OutLog, FString& OutPath)
{
	TArray<FString> Candidates;
	const FString LocalAppData = FPlatformMisc::GetEnvironmentVariable(TEXT("LOCALAPPDATA"));
	if (!LocalAppData.IsEmpty())
	{
		Candidates.Add(LocalAppData / TEXT("UnrealBuildTool/Log.txt"));
	}
	Candidates.Add(FPaths::EngineDir() / TEXT("Programs/UnrealBuildTool/Log.txt"));

	IFileManager& FM = IFileManager::Get();
	FDateTime Newest = FDateTime::MinValue();
	for (const FString& Candidate : Candidates)
	{
		const FDateTime Stamp = FM.GetTimeStamp(*Candidate);
		// 文件系统时间精度有限，放两秒余量
		if (Stamp > Newest && Stamp >= SinceUtc - FTimespan::FromSeconds(2))
		{
			Newest = Stamp;
			OutPath = FPaths::ConvertRelativePathToFull(Candidate);
		}
	}
	if (Newest == FDateTime::MinValue()) return false;

	// AllowWrite：万一 UBT 还没松手，别因为共享模式打不开
	if (!FFileHelper::LoadFileToString(OutLog, *OutPath, FFileHelper::EHashOptions::None, FILEREAD_AllowWrite))
	{
		return false;
	}
	if (OutLog.Len() > kMaxBuildLogChars)
	{
		OutLog = OutLog.Right(kMaxBuildLogChars);
	}
	return true;
}

/** 一次编译的在途状态。同一时间只允许一个，插件端和工具的 sequential 各挡一道 */
struct FCompileJob
{
	FString RequestId;
	FString Path;
	double StartedAt = 0.0;
	/** 和 StartedAt 同一刻，但用来跟文件时间戳比（那是 UTC 墙钟，不是单调时钟） */
	FDateTime StartedAtUtc;
	FDelegateHandle CompilerFinished;
	FTSTicker::FDelegateHandle Ticker;
	TUniquePtr<FLiveCodingLogSink> Sink;

	/**
	 * Live Coding 说「不编了」的那一刻。0 表示还在编。
	 *
	 * 存它是因为**「编译结束」和「结果日志」不是同一件事**：
	 * `LiveCodingPostCompile()` 在客户端命令线程上先把 GIsCompileActive 清掉
	 * （LiveCodingModule.cpp:1623），四条结果文案要等到游戏线程的
	 * `FLiveCodingModule::Tick()` 才打印（:933）。
	 * 我们轮询的 IsCompiling() 就是那个标志，所以它一变假就收工的话，
	 * 会跑在引擎打印之前，捞到一份空日志。
	 */
	double StoppedCompilingAt = 0.0;
};

TUniquePtr<FCompileJob> GJob;

/** 摘钩子。必须在发响应**之前**做，否则超时那条路会和真正的完成事件抢着回 */
void ClearJob()
{
	if (!GJob) return;

	if (GJob->Ticker.IsValid())
	{
		FTSTicker::GetCoreTicker().RemoveTicker(GJob->Ticker);
	}
	if (GJob->CompilerFinished.IsValid() && FModuleManager::Get().IsModuleLoaded(TEXT("HotReload")))
	{
		FModuleManager::LoadModuleChecked<IHotReloadInterface>(TEXT("HotReload"))
			.OnModuleCompilerFinished().Remove(GJob->CompilerFinished);
	}
	if (GJob->Sink && GLog)
	{
		GLog->RemoveOutputDevice(GJob->Sink.Get());
	}
	GJob.Reset();
}

/**
 * 发编译结果。**永远用 200。**
 *
 * 真机第一次跑就栽在这上面：编译如期失败，我按「失败就回 500」发了响应，
 * 结果模型收到的是一句
 *
 *     cpp.compile 失败：未提供失败原因（错误码 500）
 *
 * ——result、output、needs_full_rebuild 全没了。
 *
 * 原因在盒子这一侧：`services/websocket/server.ts` 见到 `code >= 400` 就往
 * 载荷里注入 `ok:false`，而 `defineUeTool` 的 `callUe` 见到 `ok === false`
 * 就直接抛异常，工具的 `toOutcome` 根本不会执行。也就是说
 * **非 200 会把整个业务载荷吞掉，只剩一句通用错误。**
 *
 * 所以这里的分界不是「编译成没成」，而是「这次 RPC 有没有完成它的工作」：
 * 编译跑完了并且我知道结果 = RPC 成功 = 200，好坏写在 `result` 字段里。
 * 只有真正的 RPC 级失败（没有 C++、已经在编了）才用 SendError 走 4xx，
 * 那条路本来就带 message，不会出现「未提供失败原因」。
 */
void RespondAndClear(const TSharedPtr<FJsonObject>& Data)
{
	constexpr int32 Code = 200;
	if (!GJob) return;
	const FString RequestId = GJob->RequestId;
	Data->SetStringField(TEXT("path"), GJob->Path);
	Data->SetNumberField(TEXT("duration_ms"),
		FMath::RoundToInt((FPlatformTime::Seconds() - GJob->StartedAt) * 1000.0));
	ClearJob();
	UAL_CommandUtils::SendResponse(RequestId, Code, Data);
}

/**
 * 改了 .Build.cs / .uproject 之后，热补丁和热重载都可能给出一个「成功」而实际
 * 没把新依赖链进去 —— 那正是这个项目最怕的假成功。
 *
 * 判法故意不存状态：比**磁盘上最新的 .Build.cs / .uproject** 和
 * **工程 Binaries 里最新的 .dll**。产物比配置旧，就说明配置改过还没完整重编。
 * 不记「上次编译时间」是因为那份状态跨不了重启，也管不住用户在 VS 里的改动。
 *
 * ponytail: 只报 needs_full_rebuild 不拦截。拦截要求判断永远正确，而误拦一次
 * 就是把一次合法编译堵死；如实说出来的代价小得多。真出现误报再收紧。
 */
bool BuildConfigNewerThanBinaries()
{
	IFileManager& FM = IFileManager::Get();

	/*
	 * 直接比 FDateTime，不转时间戳数字。
	 *
	 * 初版写的是 `FMath::Max(Newest, Stamp.ToUnixTimestampDecimal())` ——
	 * 那个方法 **5.3 才有**，5.0/5.1/5.2 上直接编不过（真机出全套包时炸了三个版本）。
	 * 而这里根本不需要数字：FDateTime 自己就能比大小，换成比较更短也更没有版本风险。
	 *
	 * 这就是 说的那件事的实例 ——
	 * 跨九个版本的正确性不是靠写的时候小心，是靠编译器在发版前告诉我们。
	 */
	auto NewestTimeStamp = [&FM](const TArray<FString>& Files)
	{
		FDateTime Newest = FDateTime::MinValue();
		for (const FString& File : Files)
		{
			const FDateTime Stamp = FM.GetTimeStamp(*File);
			if (Stamp > Newest) Newest = Stamp;
		}
		return Newest;
	};

	TArray<FString> ConfigFiles;
	FM.FindFilesRecursive(ConfigFiles, *FPaths::GameSourceDir(), TEXT("*.Build.cs"), true, false);
	ConfigFiles.Add(FPaths::GetProjectFilePath());
	const FDateTime NewestConfig = NewestTimeStamp(ConfigFiles);
	if (NewestConfig == FDateTime::MinValue()) return false;

	TArray<FString> Binaries;
	FM.FindFilesRecursive(Binaries, *(FPaths::ProjectDir() / TEXT("Binaries")), TEXT("*.dll"), true, false);
	const FDateTime NewestBinary = NewestTimeStamp(Binaries);
	if (NewestBinary == FDateTime::MinValue()) return false;

	return NewestConfig > NewestBinary;
}

} // namespace

void FUAL_CppCommands::Handle_Compile(const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
{
	if (GJob)
	{
		UAL_CommandUtils::SendError(RequestId, 409, TEXT("已经有一次编译在进行中。"));
		return;
	}
	if (!GameProjectUtils::ProjectHasCodeFiles())
	{
		UAL_CommandUtils::SendError(RequestId, 400,
			TEXT("这个工程没有 C++ 源码，没有可编译的东西。先用 cpp.probe 看一眼。"));
		return;
	}

	/*
	 * 半吊子状态直接拒，别开工。
	 *
	 * 这条必须在选路**之前**：那时候 IsEnabledForSession() 已经是假了，
	 * 按常规判据会走热重载 —— 而那条路在这个状态下会把编辑器卡死 20 分钟。
	 * 拒绝的代价是一句话，走进去的代价是用户强制关编辑器。见 LiveCodingHalfDisabled()。
	 */
	if (LiveCodingHalfDisabled())
	{
		UAL_CommandUtils::SendError(RequestId, 409, LiveCodingHalfDisabledHint());
		return;
	}

	bool bLiveCoding = false;
#if WITH_LIVE_CODING
	ILiveCodingModule* Lc = FModuleManager::GetModulePtr<ILiveCodingModule>(LIVE_CODING_MODULE_NAME);
	// 只认 IsEnabledForSession —— 判据见 Handle_Probe 里那段长注释。
	// 判错的代价不对称：错走 Live Coding 会把用户的会话永久切过去
	bLiveCoding = (Lc != nullptr) && Lc->IsEnabledForSession();
#endif

	GJob = MakeUnique<FCompileJob>();
	GJob->RequestId = RequestId;
	GJob->Path = bLiveCoding ? TEXT("livecoding") : TEXT("hotreload");
	GJob->StartedAt = FPlatformTime::Seconds();
	GJob->StartedAtUtc = FDateTime::UtcNow();

	const bool bNeedsFullRebuild = BuildConfigNewerThanBinaries();

	// 超时兜底。轮询和委托都可能永远不到达（编辑器崩了、Live Coding 控制台被杀），
	// 那时候必须说「不知道成没成」而不是让调用方挂到自己超时
	GJob->Ticker = FTSTicker::GetCoreTicker().AddTicker(
		FTickerDelegate::CreateLambda([bNeedsFullRebuild](float) -> bool
		{
			if (!GJob) return false;

			bool bDone = false;
			FString Result;
			FString Output;

#if WITH_LIVE_CODING
			if (GJob->Path == TEXT("livecoding"))
			{
				ILiveCodingModule* Module =
					FModuleManager::GetModulePtr<ILiveCodingModule>(LIVE_CODING_MODULE_NAME);
				if (!Module || !Module->IsCompiling())
				{
					Output = FString::Join(GJob->Sink->Lines, TEXT("\n"));
					// 引擎的四条固定文案（LiveCodingModule.cpp:937-950）。
					// 2026-09-03 在 5.0–5.8 九个引擎上逐版本 grep 过，字面量逐字相同
					// （5.8 换成 UE_LOGF，输出文本没变）。。
					//
					// 顺序有讲究，**别整理**：Success 分支带 re-instancing 时是
					// "Live coding succeeded, data type changes..."（Warning 级），
					// NoChanges 是 "Live coding succeeded, no code changes detected" ——
					// 两条都含 "succeeded"。先判 NoChanges，否则「没改动」会被报成
					// 「编译成功」，模型就会以为它的改动生效了。
					if (Output.Contains(TEXT("no code changes detected"))) Result = TEXT("NoChanges");
					else if (Output.Contains(TEXT("Live coding succeeded"))) Result = TEXT("Success");
					else if (Output.Contains(TEXT("Live coding canceled"))) Result = TEXT("Cancelled");
					else if (Output.Contains(TEXT("Live coding failed"))) Result = TEXT("Failure");

					/*
					 * **「不编了」不等于「结果已经打印了」——中间要留一个宽限窗口。**
					 *
					 * 引擎把这两件事拆在了两个线程上：
					 *   LiveCodingPostCompile()（客户端命令线程）先清 GIsCompileActive（:1623），
					 *   四条结果文案要等游戏线程的 FLiveCodingModule::Tick() 才打印（:933）。
					 * 而 IsCompiling() 读的就是那个标志。所以标志一变假就下结论，
					 * 有概率跑在打印前面，捞到一份空日志。
					 *
					 * 2026-09-08 真机验收案例 7 就是这么翻的：Live Coding 真的编译失败了，
					 * 我们回的是 Unknown 而不是 Failure。案例 6（成功）当时侥幸没翻 ——
					 * **同一个竞态，只是那次我们跑输了，反而拿到了对的结果。**
					 *
					 * 所以：匹配上任何一条就立刻收工；一条都没匹配上时**再等一会儿**，
					 * 等满 kResultLogGraceSeconds 还是空的，才承认 Unknown。
					 * 宁可多等两秒，也不要把一次真实的失败说成「不知道」。
					 */
					if (!Result.IsEmpty())
					{
						bDone = true;
					}
					else
					{
						if (GJob->StoppedCompilingAt == 0.0)
						{
							GJob->StoppedCompilingAt = FPlatformTime::Seconds();
						}
						else if (FPlatformTime::Seconds() - GJob->StoppedCompilingAt > kResultLogGraceSeconds)
						{
							bDone = true;
							Result = TEXT("Unknown");
						}
					}
				}
			}
#endif

			if (!bDone && FPlatformTime::Seconds() - GJob->StartedAt > kCompileTimeoutSeconds)
			{
				bDone = true;
				Result = TEXT("Timeout");
			}
			if (!bDone) return true;

			TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
			Data->SetStringField(TEXT("result"), Result);
			Data->SetStringField(TEXT("output"), Output);
			Data->SetBoolField(TEXT("needs_full_rebuild"), bNeedsFullRebuild);

			// 编不过（或没确认上）时把 UBT 日志带回去，解析在 TS 侧做，和热重载那条路一样
			if (GJob->Path == TEXT("livecoding") && (Result == TEXT("Failure") || Result == TEXT("Unknown")))
			{
				FString BuildLog, BuildLogPath;
				if (ReadUbtLogSince(GJob->StartedAtUtc, BuildLog, BuildLogPath))
				{
					Data->SetStringField(TEXT("build_log"), BuildLog);
					Data->SetStringField(TEXT("build_log_path"), BuildLogPath);
				}
			}

			RespondAndClear(Data);
			return false;
		}),
		0.5f);

	if (bLiveCoding)
	{
#if WITH_LIVE_CODING
		GJob->Sink = MakeUnique<FLiveCodingLogSink>();
		GLog->AddOutputDevice(GJob->Sink.Get());

		ELiveCodingCompileResult Kick = ELiveCodingCompileResult::Failure;
		// 不传 WaitForCompletion —— 那会在游戏线程上死等，编辑器整个卡住
		Lc->Compile(ELiveCodingCompileFlags::None, &Kick);
		if (Kick != ELiveCodingCompileResult::InProgress)
		{
			TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
			Data->SetStringField(TEXT("result"),
				Kick == ELiveCodingCompileResult::CompileStillActive ? TEXT("CompileStillActive") : TEXT("NotStarted"));
			Data->SetStringField(TEXT("output"), TEXT(""));
			Data->SetStringField(TEXT("reason"),
				TEXT("Live Coding 没能启动这次编译，一行都没编。多半是它的控制台进程起不来")
				TEXT("（引擎设置里的 Live Coding 控制台路径不对，或者进程被杀了）。"));
			Data->SetBoolField(TEXT("needs_full_rebuild"), bNeedsFullRebuild);
			RespondAndClear(Data);
		}
#endif
		return;
	}

	// ── 热重载 ──
	//
	// 用 DoHotReloadFromEditor 而不是 RecompileModule：后者内部 MakeDialog() +
	// WaitForCompletion，在游戏线程上同步等 UBT 跑完（HotReload.cpp:661/690），
	// 编辑器会整个转圈。异步这条路的完成事件还顺带把 UBT 的完整输出带回来。
	IHotReloadInterface& Hr = FModuleManager::LoadModuleChecked<IHotReloadInterface>(TEXT("HotReload"));
	GJob->CompilerFinished = Hr.OnModuleCompilerFinished().AddLambda(
		[bNeedsFullRebuild](const FString& FinalOutput, ECompilationResult::Type CompileResult, bool)
		{
			if (!GJob || GJob->Path != TEXT("hotreload")) return;

			const bool bOk = !ECompilationResult::Failed(CompileResult);
			// UpToDate = UBT 判定没有要编的东西，一行都没编。和 Live Coding 那条路一样报 NoChanges，
			// 否则「改了代码却没进编译」会被说成编译成功，调用方就去验一个根本没生效的改动
			const TCHAR* ResultName = CompileResult == ECompilationResult::UpToDate
				? TEXT("NoChanges")
				: (bOk ? TEXT("Success") : TEXT("Failure"));
			TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
			Data->SetStringField(TEXT("result"), ResultName);
			// UBT 的完整 stdout。诊断解析在 TS 侧做 —— 那是纯字符串处理，
			// 放在能跑单测的地方比放在要出九个包才能验的地方划算
			Data->SetStringField(TEXT("output"), FinalOutput);
			Data->SetNumberField(TEXT("compilation_result"), static_cast<int32>(CompileResult));
			Data->SetBoolField(TEXT("needs_full_rebuild"), bNeedsFullRebuild);
			RespondAndClear(Data);
		});

	/*
	 * **返回值必须看。**
	 *
	 * 异步这条路上，只有 ECompilationResult::Succeeded 代表「编译已经启动了」
	 * （HotReload.cpp:1041，那之前每一个提前 return 都是「什么都没做」）。
	 * 没启动的话 OnModuleCompilerFinished 永远不会广播 ——
	 * 不在这里收口，工具就会一直等到 20 分钟超时。
	 *
	 * 2026-09-08 真机验收案例 2 翻的就是这一条：引擎 13 毫秒同步拒绝，
	 * 日志里只有一句 RebindPackages not possible，而工具在那儿转圈。
	 * 这正是 §8.2 第 2 条要防的「永远不回响应」。
	 */
	const ECompilationResult::Type Kick = Hr.DoHotReloadFromEditor(EHotReloadFlags::None);
	if (Kick == ECompilationResult::Succeeded)
	{
		return; // 编译起来了，等委托
	}

	FString Reason;
	if (CountHotReloadablePackages() == 0)
	{
		Reason = NoReloadablePackagesHint();
	}
	else
	{
		// 别的拒绝原因（已经在编、包没绑定、编译器起不来）引擎只写日志不给理由码，
		// 如实报「引擎拒绝了，没说为什么」，让人去看编辑器日志，别猜
		Reason = FString::Printf(
			TEXT("引擎拒绝了这次热重载，一行都没编（ECompilationResult=%d）。")
			TEXT("引擎没有给出结构化的原因，具体那一行警告在编辑器的输出日志里，")
			TEXT("搜 RebindPackages 或 HotReload 就能看到。"),
			static_cast<int32>(Kick));
	}

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("result"), TEXT("NotStarted"));
	Data->SetStringField(TEXT("output"), TEXT(""));
	Data->SetStringField(TEXT("reason"), Reason);
	Data->SetNumberField(TEXT("compilation_result"), static_cast<int32>(Kick));
	Data->SetBoolField(TEXT("needs_full_rebuild"), bNeedsFullRebuild);
	RespondAndClear(Data);
}

/**
 * 把一组模块序列化成 JSON 数组。
 *
 * `source_path` 给的是模块 Source 目录的绝对路径 —— 调用方（盒子里的 agent）
 * 拿它去 grep/读文件，相对路径在那边一定拼错：引擎的相对路径相对的是
 * 引擎二进制目录，不是任何调用方的工作目录。
 */
static void AppendModules(
	TArray<TSharedPtr<FJsonValue>>& Out,
	const TArray<FModuleContextInfo>& Modules,
	const TCHAR* Origin)
{
	for (const FModuleContextInfo& Module : Modules)
	{
		TSharedPtr<FJsonObject> Item = MakeShared<FJsonObject>();
		Item->SetStringField(TEXT("name"), Module.ModuleName);
		Item->SetStringField(TEXT("source_path"),
			FPaths::ConvertRelativePathToFull(Module.ModuleSourcePath));
		// Runtime / Editor / Developer / Program …
		// 类型不是装饰：Runtime 模块 include UnrealEd 会在打包时炸，而编辑器里编得过去
		Item->SetStringField(TEXT("type"), EHostType::ToString(Module.ModuleType));
		Item->SetStringField(TEXT("origin"), Origin);
		Out.Add(MakeShared<FJsonValueObject>(Item));
	}
}

void FUAL_CppCommands::Handle_ListModules(const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
{
	bool bIncludePlugins = false;
	if (Payload.IsValid())
	{
		Payload->TryGetBoolField(TEXT("include_plugins"), bIncludePlugins);
	}

	// 纯蓝图工程上引擎会塞一个占位模块（见 DeclaredProjectModuleCount），它在磁盘上并不存在，
	// 列出来会让调用方以为工程有 C++ 模块
	TArray<TSharedPtr<FJsonValue>> Modules;
	if (GameProjectUtils::ProjectHasCodeFiles() || DeclaredProjectModuleCount() > 0)
	{
		AppendModules(Modules, GameProjectUtils::GetCurrentProjectModules(), TEXT("project"));
	}
	if (bIncludePlugins)
	{
		AppendModules(Modules, GameProjectUtils::GetCurrentProjectPluginModules(), TEXT("plugin"));
	}

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetArrayField(TEXT("modules"), Modules);
	Data->SetNumberField(TEXT("count"), Modules.Num());
	Data->SetBoolField(TEXT("has_code"), GameProjectUtils::ProjectHasCodeFiles());
	Data->SetNumberField(TEXT("declared_module_count"), DeclaredProjectModuleCount());

	UAL_CommandUtils::SendResponse(RequestId, 200, Data);
}

void FUAL_CppCommands::Handle_Probe(const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
{
	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();

	const bool bHasCode = GameProjectUtils::ProjectHasCodeFiles();
	Data->SetBoolField(TEXT("has_code"), bHasCode);

	/*
	 * .uproject 声明了几个模块。**这个数和 has_code 不一致时是有意义的**：
	 * ProjectHasCodeFiles() 数的是磁盘上的源文件，这里读的是 .uproject 的 Modules 段，
	 * 「声明了模块但 Source/ 不在」是源码丢了的 C++ 工程（拷贝漏了、被删过），不是纯蓝图工程。
	 * 判据为什么不能用 GetCurrentProjectModules()，见 DeclaredProjectModuleCount。
	 */
	const int32 DeclaredModuleCount = DeclaredProjectModuleCount();
	Data->SetNumberField(TEXT("declared_module_count"), DeclaredModuleCount);
	Data->SetStringField(TEXT("engine_dir"), FPaths::ConvertRelativePathToFull(FPaths::EngineDir()));
	Data->SetStringField(TEXT("engine_source_dir"), FPaths::ConvertRelativePathToFull(FPaths::EngineSourceDir()));
	Data->SetStringField(TEXT("project_source_dir"), FPaths::ConvertRelativePathToFull(FPaths::GameSourceDir()));

	// ── Live Coding ────────────────────────────────────────────────────────
	//
	// 这四个状态位长得很像，但只有 enabled_for_session 能用来选路，理由见下面
	// compile_path 那段。全都报出来是为了让「为什么走不了这条路」有据可查。
	TSharedPtr<FJsonObject> LiveCoding = MakeShared<FJsonObject>();
	bool bLcAvailable = false;
	bool bLcEnabledForSession = false;

#if WITH_LIVE_CODING
	if (ILiveCodingModule* Lc = FModuleManager::GetModulePtr<ILiveCodingModule>(LIVE_CODING_MODULE_NAME))
	{
		bLcAvailable = true;
		bLcEnabledForSession = Lc->IsEnabledForSession();
		LiveCoding->SetBoolField(TEXT("started"), Lc->HasStarted());
		LiveCoding->SetBoolField(TEXT("enabled_by_default"), Lc->IsEnabledByDefault());
		LiveCoding->SetBoolField(TEXT("enabled_for_session"), bLcEnabledForSession);
		LiveCoding->SetBoolField(TEXT("can_enable"), Lc->CanEnableForSession());
		LiveCoding->SetBoolField(TEXT("is_compiling"), Lc->IsCompiling());
		LiveCoding->SetStringField(TEXT("enable_error"), Lc->GetEnableErrorText().ToString());
	}
#endif

	LiveCoding->SetBoolField(TEXT("available"), bLcAvailable);
	if (!bLcAvailable)
	{
		// 非 Windows（Target.bWithLiveCoding 为假）或模块没加载。
		// 说清楚是「这台机器没有」而不是「查询失败」——后者会让模型去重试。
		LiveCoding->SetStringField(TEXT("unavailable_reason"),
			TEXT("这个平台或这份引擎构建没有 Live Coding 模块（它只在 Windows 上有）。"));
	}
	Data->SetObjectField(TEXT("live_coding"), LiveCoding);

	// ── HotReload ──────────────────────────────────────────────────────────
	TSharedPtr<FJsonObject> HotReload = MakeShared<FJsonObject>();
	bool bHotReloadUsable = false;
	if (FModuleManager::Get().IsModuleLoaded(TEXT("HotReload")))
	{
		IHotReloadInterface& Hr = FModuleManager::LoadModuleChecked<IHotReloadInterface>(TEXT("HotReload"));
		bHotReloadUsable = true;
		HotReload->SetBoolField(TEXT("any_game_module_loaded"), Hr.IsAnyGameModuleLoaded());
		HotReload->SetBoolField(TEXT("is_compiling"), Hr.IsCurrentlyCompiling());
		/*
		 * **`any_game_module_loaded` 为真不代表热重载编得动。**
		 *
		 * 引擎要的不是「有游戏模块」，是「有能重新绑定的 UObject 包」。
		 * 模块里一个 UCLASS 都没有的话，前者真、后者 0，引擎同步拒绝。
		 * 只报前者就会给出一个自信但错误的结论 —— 真机验收案例 2 上撞到过。
		 */
		HotReload->SetNumberField(TEXT("reloadable_package_count"), CountHotReloadablePackages());
	}
	HotReload->SetBoolField(TEXT("available"), bHotReloadUsable);
	Data->SetObjectField(TEXT("hot_reload"), HotReload);

	/*
	 * ── 选路 ───────────────────────────────────────────────────────────────
	 *
	 * **只认 IsEnabledForSession()。** started / enabled_by_default /
	 * can_enable 三个都不算数：
	 *
	 *   - started        说的是控制台进程起没起，不是「这个会话在用它」
	 *   - enabled_by_default 说的是设置里的默认值，用户可以在会话中途关掉
	 *   - can_enable     说的是「能不能开」，不是「开着没有」
	 *
	 * 判错的代价是不对称的，所以只能认最严的那一个：
	 * ILiveCodingModule::Compile() 一进门就 EnableForSession(true)
	 * （LiveCodingModule.cpp:697），在没启动时会把 Live Coding **启动起来**并弹出
	 * 控制台窗口。一个明确关掉了 Live Coding、打算用热重载的用户，只要我们判错一次
	 * 并调了 Compile()，他的会话就被永久切成 Live Coding 模式 ——
	 * FHotReloadModule::RecompileModule 从此一律返回 false
	 * （"Unable to hot-reload modules while Live Coding is enabled."），
	 * 不重启编辑器出不来。
	 *
	 * 反过来判错（该走 Live Coding 却走了 HotReload）代价小得多：
	 * 那边会干干净净地拒绝，什么都没被改变。
	 *
	 * 所以：**我们永远不主动开启 Live Coding。开不开是用户的编辑器设置。**
	 */
	const TCHAR* CompilePath = TEXT("none");
	if (!bHasCode)
	{
		CompilePath = TEXT("none");
	}
	else if (bLcEnabledForSession)
	{
		CompilePath = TEXT("livecoding");
	}
	else if (LiveCodingHalfDisabled())
	{
		// 两条路都走不了：Live Coding 这个会话不用了，热重载会卡死。
		// 报 hotreload 就是一个自信但错误的结论 —— 案例 9 上真发生过
		CompilePath = TEXT("none");
	}
	else if (bHotReloadUsable)
	{
		CompilePath = TEXT("hotreload");
	}
	Data->SetStringField(TEXT("compile_path"), CompilePath);

	/*
	 * 把「为什么是这条路」也说出来。
	 *
	 * 只回一个枚举的话，模型遇到 none 只能猜；而这三种 none 的处置完全不同：
	 * 纯蓝图工程直接建第一个类（cpp_add_class 会补主模块），没有热重载模块是环境问题，
	 * 两条路都不可用则要报告而不是重试。
	 */
	FString Why;
	if (!bHasCode && DeclaredModuleCount > 0)
	{
		// 见上面 declared_module_count 那段注释：这是个坏掉的工程，不是纯蓝图工程。
		// 把两个信号都摆出来，别让人以为「加一个类就好了」
		Why = FString::Printf(
			TEXT(".uproject 声明了 %d 个模块，但磁盘上找不到源码文件（Source 目录不存在或是空的）。")
			TEXT("这不是纯蓝图工程，是一个源码缺失的 C++ 工程 —— 加新类解决不了，")
			TEXT("需要用户确认这个工程是不是拷贝时漏了 Source 目录。"),
			DeclaredModuleCount);
	}
	else if (!bHasCode)
	{
		Why = TEXT("这是纯蓝图工程（没有 C++ 源码，.uproject 里也没有声明模块）。")
			TEXT("直接调 cpp_add_class 建第一个类，它会和编辑器一样顺带建好工程的主模块；")
			TEXT("新模块编辑器当场加载不了，建完填好实现后调 cpp_full_rebuild 编译并重开编辑器。");
	}
	else if (bLcEnabledForSession)
	{
		Why = TEXT("这个会话启用了 Live Coding，编译走它。编不过时会从 UnrealBuildTool 的日志（Log.txt）里捞出带文件名和行号的报错；个别情况（日志找不到、或者失败发生在打补丁阶段）只能拿到一句失败。");
	}
	else if (LiveCodingHalfDisabled())
	{
		Why = LiveCodingHalfDisabledHint();
	}
	else if (bHotReloadUsable && CountHotReloadablePackages() == 0)
	{
		// 路是对的，但这条路现在走不通。先说堵在哪，别先说它的优点 ——
		// 模型只读第一句就会去调 cpp_compile
		Why = TEXT("编译本该走热重载，但现在走不通：") + NoReloadablePackagesHint();
	}
	else if (bHotReloadUsable)
	{
		Why = TEXT("这个会话没有启用 Live Coding，编译走热重载。这条路编不过时能拿到完整的编译器输出（文件名、行号、原文）。");
	}
	else
	{
		Why = TEXT("Live Coding 没有为这个会话启用，热重载模块也没加载 —— 两条路都不可用。");
	}
	Data->SetStringField(TEXT("compile_path_reason"), Why);

	UE_LOG(LogUALCpp, Log, TEXT("cpp.probe: has_code=%d path=%s"), bHasCode ? 1 : 0, CompilePath);

	UAL_CommandUtils::SendResponse(RequestId, 200, Data);
}
