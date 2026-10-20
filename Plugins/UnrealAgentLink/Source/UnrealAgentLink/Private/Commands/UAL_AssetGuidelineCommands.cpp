#include "UAL_AssetGuidelineCommands.h"
#include "UAL_CommandUtils.h"

#include "Editor/AssetGuideline.h"
#include "HAL/IConsoleManager.h"
#include "HAL/FileManager.h"
#include "Interfaces/IPluginManager.h"
#include "Interfaces/IProjectManager.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "ProjectDescriptor.h"
#include "Serialization/Archive.h"
#include "UObject/Package.h"
#include "UObject/PackageFileSummary.h"
#include "UObject/UObjectHash.h"
#include "UObject/UObjectIterator.h"

DEFINE_LOG_CATEGORY_STATIC(LogUALAssetGuideline, Log, All);

/*
 * 和引擎 AssetGuideline.cpp（UAssetGuideline::PostLoad / EnableMissingGuidelines）对齐的地方：
 *
 * - 同名的说明只算一张（引擎按 GuidelineName 去重，一次启动只弹一次）。
 * - 工程设置只比「键是控制台变量」的那些 —— 引擎就是这么挑的，别的键它不弹也不改。
 * - 比的是工程 Config 目录下那份 ini（说明里写的 Filename，一般是 /Config/DefaultEngine.ini），
 *   FString 比较，不分大小写。
 * - 修的时候把说明里写的值原样写进那份 ini（不换写法），所以写完以后引擎下次启动的比对
 *   一定对得上，不会因为 True / 1 这类写法差异又弹一次。
 *
 * 比引擎多做的：从磁盘读回来核对；告诉调用方哪些已经写好、只差重启。
 */
namespace UALAssetGuideline
{
	static const TCHAR* GuidelineClassName = TEXT("AssetGuideline");

	/** 一次最多扫多少个包、最多加载多少个可疑包。扫的只是包头，加载才是贵的 */
	static constexpr int32 MaxScannedPackages = 50000;
	static constexpr int32 MaxLoadedCandidates = 300;

	/**
	 * 在这段作用域里，引擎加载到说明时只写日志、不弹框（5.3 起引擎才有这个开关）。
	 * 我们自己加载可疑包是为了读说明，结果会交给盒子，不该让用户再看一遍那几个框。
	 */
	struct FScopedGuidelinePopupsOff
	{
#if ENGINE_MAJOR_VERSION > 5 || (ENGINE_MAJOR_VERSION == 5 && ENGINE_MINOR_VERSION >= 3)
		bool bWasEnabled;
		FScopedGuidelinePopupsOff() : bWasEnabled(UAssetGuideline::AreAssetGuidelinesEnabled())
		{
			UAssetGuideline::EnableAssetGuidelines(false);
		}
		~FScopedGuidelinePopupsOff()
		{
			UAssetGuideline::EnableAssetGuidelines(bWasEnabled);
		}
		static constexpr bool bSupported = true;
#else
		// 5.0–5.2 没有这个开关，什么都不做。写出构造/析构，免得 MSVC 报「未引用的局部变量」
		FScopedGuidelinePopupsOff() {}
		~FScopedGuidelinePopupsOff() {}
		static constexpr bool bSupported = false;
#endif
	};

	/**
	 * 包头的名字表里有没有 "AssetGuideline" 这个名字 —— 有就说明包里有说明对象，
	 * 或者包本身是一张说明（蓝图子类）。只读包头，不加载。
	 *
	 * 不用 FUALPackageReader：它把名字表全转成 FName，扫几万个包会往全局名字表里
	 * 塞一堆永远不释放的名字。这里逐条比字符串，读完就扔。
	 */
	static bool PackageMentionsGuideline(const FString& Filename, bool& bOutReadable)
	{
		bOutReadable = false;
		TUniquePtr<FArchive> Ar(IFileManager::Get().CreateFileReader(*Filename));
		if (!Ar)
		{
			return false;
		}

		FPackageFileSummary Summary;
		*Ar << Summary;
		if (Ar->IsError() || Summary.Tag != PACKAGE_FILE_TAG)
		{
			return false;
		}
		Ar->SetUEVer(Summary.GetFileVersionUE());
		Ar->SetLicenseeUEVer(Summary.GetFileVersionLicenseeUE());
		Ar->SetEngineVer(Summary.SavedByEngineVersion);
		Ar->SetCustomVersions(Summary.GetCustomVersionContainer());

		const int64 Size = Ar->TotalSize();
		if (Summary.NameCount <= 0 || Summary.NameOffset <= 0 || Summary.NameOffset >= Size)
		{
			bOutReadable = Summary.NameCount <= 0;
			return false;
		}

		Ar->Seek(Summary.NameOffset);
		for (int32 i = 0; i < Summary.NameCount; ++i)
		{
			FNameEntrySerialized Entry(ENAME_LinkerConstructor);
			*Ar << Entry;
			if (Ar->IsError())
			{
				return false;
			}
			if (Entry.GetPlainNameString().Equals(GuidelineClassName, ESearchCase::IgnoreCase))
			{
				bOutReadable = true;
				return true;
			}
		}
		bOutReadable = true;
		return false;
	}

	/**
	 * 把调用方给的内容路径（目录或包）展开成磁盘上的包文件。
	 *
	 * 不扫关卡（.umap）：加载关卡包等于把整张图读进来，太重；指南挂在资产上，关卡里的
	 * 资产自己会被扫到。
	 */
	static void CollectPackageFiles(const TArray<FString>& ContentPaths, TArray<FString>& OutFiles, TArray<FString>& OutBadPaths)
	{
		for (FString Path : ContentPaths)
		{
			Path.TrimStartAndEndInline();
			Path.ReplaceInline(TEXT("\\"), TEXT("/"));
			// 带对象名的写法 /Game/A/B.B 只取包名
			{
				int32 LastSlash = INDEX_NONE;
				int32 Dot = INDEX_NONE;
				if (Path.FindLastChar(TEXT('/'), LastSlash) && Path.FindLastChar(TEXT('.'), Dot) && Dot > LastSlash)
				{
					Path.LeftInline(Dot);
				}
			}
			while (Path.Len() > 1 && Path.EndsWith(TEXT("/")))
			{
				Path.LeftChopInline(1);
			}

			FString PackageFile;
			if (FPackageName::IsValidLongPackageName(Path) && FPackageName::DoesPackageExist(Path, &PackageFile))
			{
				if (PackageFile.EndsWith(TEXT(".umap"), ESearchCase::IgnoreCase))
				{
					continue;
				}
				OutFiles.Add(FPaths::ConvertRelativePathToFull(PackageFile));
				continue;
			}

			FString Dir;
			if (!FPackageName::TryConvertLongPackageNameToFilename(Path + TEXT("/"), Dir) || !IFileManager::Get().DirectoryExists(*Dir))
			{
				OutBadPaths.Add(Path);
				continue;
			}
			TArray<FString> Found;
			IFileManager::Get().FindFilesRecursive(Found, *Dir, TEXT("*.uasset"), true, false, false);
			for (const FString& F : Found)
			{
				OutFiles.Add(FPaths::ConvertRelativePathToFull(F));
			}
		}
	}

	/** 说明里的 Filename（如 /Config/DefaultEngine.ini）→ 工程里的绝对路径。不是工程 Config 下的 Default*.ini 就拒绝 */
	static bool ResolveIniPath(const FString& GuidelineFilename, FString& OutPath)
	{
		FString Rel = GuidelineFilename;
		Rel.ReplaceInline(TEXT("\\"), TEXT("/"));
		if (!Rel.StartsWith(TEXT("/")))
		{
			Rel = TEXT("/") + Rel;
		}
		if (!Rel.StartsWith(TEXT("/Config/Default"), ESearchCase::IgnoreCase) ||
			!Rel.EndsWith(TEXT(".ini"), ESearchCase::IgnoreCase) ||
			Rel.Contains(TEXT("..")) ||
			Rel.Mid(8).Contains(TEXT("/")))
		{
			return false;
		}
		OutPath = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() + Rel.Mid(1));
		FPaths::NormalizeFilename(OutPath);
		return true;
	}

	/** 「引擎现在跑着的值」和要求的值是不是一回事：True/1、False/0 当成一样，数字按数值比 */
	static bool SameMeaning(const FString& A, const FString& B)
	{
		auto Canon = [](const FString& In) -> FString
		{
			FString S = In.TrimStartAndEnd();
			// 布尔先换成数字，再和数字走同一条规范化 —— 否则 True→"1" 和 1→"1.0" 对不上
			if (S.Equals(TEXT("true"), ESearchCase::IgnoreCase)) S = TEXT("1");
			else if (S.Equals(TEXT("false"), ESearchCase::IgnoreCase)) S = TEXT("0");
			if (S.IsNumeric()) return FString::SanitizeFloat(FCString::Atod(*S));
			return S.ToLower();
		};
		return Canon(A) == Canon(B);
	}

	/** 按磁盘读 ini，一次请求里同一个文件只读一遍 */
	struct FIniDiskCache
	{
		TMap<FString, TSharedPtr<FConfigFile>> Files;

		const FConfigFile* Get(const FString& Path)
		{
			if (const TSharedPtr<FConfigFile>* Found = Files.Find(Path))
			{
				return Found->Get();
			}
			TSharedPtr<FConfigFile> File = MakeShared<FConfigFile>();
			if (IFileManager::Get().FileExists(*Path))
			{
				File->Read(Path);
			}
			Files.Add(Path, File);
			return File.Get();
		}

		void Forget(const FString& Path) { Files.Remove(Path); }
	};

	struct FSettingState
	{
		FString Section;
		FString Key;
		FString Required;
		FString Filename;
		FString IniPath;
		bool bHasCurrent = false;
		FString Current;
		bool bHasLive = false;
		FString Live;
		/** ok / missing / pending_restart / unchecked / bad_file */
		FString Status;
	};

	struct FPluginState
	{
		FString Name;
		FString FriendlyName;
		/** ok / missing / pending_restart / not_installed */
		FString Status;
	};

	struct FGuidelineState
	{
		FString Name;
		FString Asset;
		FString ClassPath;
		TArray<FSettingState> Settings;
		TArray<FPluginState> Plugins;

		int32 UnmetSettings() const
		{
			int32 N = 0;
			for (const FSettingState& S : Settings) { N += S.Status == TEXT("missing") ? 1 : 0; }
			return N;
		}
		int32 UnmetPlugins() const
		{
			int32 N = 0;
			for (const FPluginState& P : Plugins) { N += (P.Status == TEXT("missing") || P.Status == TEXT("not_installed")) ? 1 : 0; }
			return N;
		}
	};

	static FSettingState EvaluateSetting(const FIniStringValue& Setting, FIniDiskCache& Cache)
	{
		FSettingState S;
		S.Section = Setting.Section;
		S.Key = Setting.Key;
		S.Required = Setting.Value;
		S.Filename = Setting.Filename;

		IConsoleVariable* CVar = IConsoleManager::Get().FindConsoleVariable(*Setting.Key);
		if (!CVar)
		{
			S.Status = TEXT("unchecked");
			return S;
		}
		S.bHasLive = true;
		S.Live = CVar->GetString();

		if (!ResolveIniPath(Setting.Filename, S.IniPath))
		{
			S.Status = TEXT("bad_file");
			return S;
		}
		const FConfigFile* File = Cache.Get(S.IniPath);
		S.bHasCurrent = File && File->GetString(*Setting.Section, *Setting.Key, S.Current);
		if (!S.bHasCurrent || !S.Current.Equals(Setting.Value, ESearchCase::IgnoreCase))
		{
			S.Status = TEXT("missing");
		}
		else
		{
			S.Status = SameMeaning(S.Live, Setting.Value) ? TEXT("ok") : TEXT("pending_restart");
		}
		return S;
	}

	static FPluginState EvaluatePlugin(const FString& PluginName)
	{
		FPluginState P;
		P.Name = PluginName;
		P.FriendlyName = PluginName;
		TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(PluginName);
		if (!Plugin.IsValid())
		{
			P.Status = TEXT("not_installed");
			return P;
		}
		P.FriendlyName = Plugin->GetFriendlyName();
		if (Plugin->IsEnabled())
		{
			P.Status = TEXT("ok");
			return P;
		}
		// 已经在工程描述里打开、只是这次启动还没加载
		if (const FProjectDescriptor* Project = IProjectManager::Get().GetCurrentProject())
		{
			for (const FPluginReferenceDescriptor& Ref : Project->Plugins)
			{
				if (Ref.Name.Equals(PluginName, ESearchCase::IgnoreCase) && Ref.bEnabled)
				{
					P.Status = TEXT("pending_restart");
					return P;
				}
			}
		}
		P.Status = TEXT("missing");
		return P;
	}

	/** 内存里所有说明对象（实例 + 蓝图子类的默认对象），按说明名去重 */
	static TArray<UAssetGuideline*> LoadedGuidelines()
	{
		TArray<UObject*> Objects;
		GetObjectsOfClass(UAssetGuideline::StaticClass(), Objects, true, RF_NoFlags);

		TArray<UAssetGuideline*> Out;
		TSet<FString> Seen;
		for (UObject* Obj : Objects)
		{
			UAssetGuideline* G = Cast<UAssetGuideline>(Obj);
			if (!G || !IsValid(G) || G->GetOutermost() == GetTransientPackage())
			{
				continue;
			}
			UClass* Class = G->GetClass();
			// 原生类自己的默认对象是空的；蓝图编译留下的骨架类、旧版本类也不算
			if (Class == UAssetGuideline::StaticClass() && G->HasAnyFlags(RF_ClassDefaultObject))
			{
				continue;
			}
			if (Class->HasAnyClassFlags(CLASS_NewerVersionExists) ||
				Class->GetName().StartsWith(TEXT("SKEL_")) ||
				Class->GetName().StartsWith(TEXT("REINST_")))
			{
				continue;
			}
			if (G->Plugins.Num() == 0 && G->ProjectSettings.Num() == 0)
			{
				continue;
			}
			const FString Key = G->GuidelineName.IsNone() ? G->GetPathName() : G->GuidelineName.ToString();
			if (Seen.Contains(Key))
			{
				continue;
			}
			Seen.Add(Key);
			Out.Add(G);
		}
		return Out;
	}

	static FGuidelineState Evaluate(UAssetGuideline* G, FIniDiskCache& Cache)
	{
		FGuidelineState State;
		State.Name = G->GuidelineName.IsNone() ? G->GetName() : G->GuidelineName.ToString();
		State.Asset = G->GetOutermost()->GetName();
		State.ClassPath = G->GetClass()->GetPathName();
		for (const FIniStringValue& Setting : G->ProjectSettings)
		{
			State.Settings.Add(EvaluateSetting(Setting, Cache));
		}
		for (const FString& PluginName : G->Plugins)
		{
			State.Plugins.Add(EvaluatePlugin(PluginName));
		}
		return State;
	}

	static TSharedPtr<FJsonObject> ToJson(const FGuidelineState& State)
	{
		TSharedPtr<FJsonObject> Obj = MakeShared<FJsonObject>();
		Obj->SetStringField(TEXT("name"), State.Name);
		Obj->SetStringField(TEXT("asset"), State.Asset);
		Obj->SetStringField(TEXT("class"), State.ClassPath);

		TArray<TSharedPtr<FJsonValue>> Settings;
		for (const FSettingState& S : State.Settings)
		{
			TSharedPtr<FJsonObject> J = MakeShared<FJsonObject>();
			J->SetStringField(TEXT("section"), S.Section);
			J->SetStringField(TEXT("key"), S.Key);
			J->SetStringField(TEXT("required"), S.Required);
			J->SetStringField(TEXT("file"), S.Filename);
			if (S.bHasCurrent)
			{
				J->SetStringField(TEXT("current"), S.Current);
			}
			if (S.bHasLive)
			{
				J->SetStringField(TEXT("live"), S.Live);
			}
			J->SetStringField(TEXT("status"), S.Status);
			Settings.Add(MakeShared<FJsonValueObject>(J));
		}
		Obj->SetArrayField(TEXT("settings"), Settings);

		TArray<TSharedPtr<FJsonValue>> Plugins;
		for (const FPluginState& P : State.Plugins)
		{
			TSharedPtr<FJsonObject> J = MakeShared<FJsonObject>();
			J->SetStringField(TEXT("name"), P.Name);
			J->SetStringField(TEXT("friendly_name"), P.FriendlyName);
			J->SetStringField(TEXT("status"), P.Status);
			Plugins.Add(MakeShared<FJsonValueObject>(J));
		}
		Obj->SetArrayField(TEXT("plugins"), Plugins);
		return Obj;
	}

	static void ReadStringArray(const TSharedPtr<FJsonObject>& Payload, const TCHAR* Field, TArray<FString>& Out)
	{
		const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
		if (Payload.IsValid() && Payload->TryGetArrayField(Field, Arr) && Arr)
		{
			for (const TSharedPtr<FJsonValue>& V : *Arr)
			{
				FString S;
				if (V.IsValid() && V->TryGetString(S) && !S.TrimStartAndEnd().IsEmpty())
				{
					Out.Add(S.TrimStartAndEnd());
				}
			}
		}
	}
}

void FUAL_AssetGuidelineCommands::RegisterCommands(TMap<FString, FHandlerFunc>& CommandMap)
{
	CommandMap.Add(TEXT("project.check_asset_guidelines"), [](const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
	{
		Handle_Check(Payload, RequestId);
	});

	CommandMap.Add(TEXT("project.apply_asset_guidelines"), [](const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
	{
		Handle_Apply(Payload, RequestId);
	});
}

// ============================================================================
// project.check_asset_guidelines
// ============================================================================
//
// 入参 paths（可选）：内容路径，目录或包都行（/Game/CitySampleVehicles）。给了就先扫这些包的
// 包头，名字表里提到 AssetGuideline 的才加载 —— 刚拷进工程、还没人打开过的资产，说明还在
// 磁盘上睡着，不加载读不到。不给就只报编辑器里已经加载过的说明（打开工程时弹框的那些）。
void FUAL_AssetGuidelineCommands::Handle_Check(const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
{
	using namespace UALAssetGuideline;

	TArray<FString> Paths;
	ReadStringArray(Payload, TEXT("paths"), Paths);

	int32 Scanned = 0;
	int32 Unreadable = 0;
	bool bTruncated = false;
	TArray<FString> Candidates;
	TArray<FString> BadPaths;
	TArray<FString> LoadFailed;

	if (Paths.Num() > 0)
	{
		TArray<FString> Files;
		CollectPackageFiles(Paths, Files, BadPaths);
		for (const FString& File : Files)
		{
			if (Scanned >= MaxScannedPackages)
			{
				bTruncated = true;
				break;
			}
			++Scanned;
			bool bReadable = false;
			const bool bMentions = PackageMentionsGuideline(File, bReadable);
			Unreadable += bReadable ? 0 : 1;
			if (!bMentions)
			{
				continue;
			}
			FString PackageName;
			if (FPackageName::TryConvertFilenameToLongPackageName(File, PackageName))
			{
				Candidates.AddUnique(PackageName);
			}
		}

		FScopedGuidelinePopupsOff PopupsOff;
		int32 Loaded = 0;
		for (const FString& PackageName : Candidates)
		{
			if (Loaded >= MaxLoadedCandidates)
			{
				bTruncated = true;
				break;
			}
			++Loaded;
			if (!FindPackage(nullptr, *PackageName) && !LoadPackage(nullptr, *PackageName, LOAD_NoWarn | LOAD_Quiet))
			{
				LoadFailed.Add(PackageName);
			}
		}
	}

	FIniDiskCache Cache;
	TArray<FGuidelineState> States;
	for (UAssetGuideline* G : LoadedGuidelines())
	{
		States.Add(Evaluate(G, Cache));
	}
	// 没满足的排前面
	States.StableSort([](const FGuidelineState& A, const FGuidelineState& B)
	{
		return (A.UnmetSettings() + A.UnmetPlugins()) > (B.UnmetSettings() + B.UnmetPlugins());
	});

	int32 UnmetSettings = 0;
	int32 UnmetPlugins = 0;
	int32 PendingRestart = 0;
	TArray<TSharedPtr<FJsonValue>> Guidelines;
	for (const FGuidelineState& State : States)
	{
		UnmetSettings += State.UnmetSettings();
		UnmetPlugins += State.UnmetPlugins();
		for (const FSettingState& S : State.Settings) { PendingRestart += S.Status == TEXT("pending_restart") ? 1 : 0; }
		for (const FPluginState& P : State.Plugins) { PendingRestart += P.Status == TEXT("pending_restart") ? 1 : 0; }
		Guidelines.Add(MakeShared<FJsonValueObject>(ToJson(State)));
	}

	auto ToJsonArray = [](const TArray<FString>& In)
	{
		TArray<TSharedPtr<FJsonValue>> Out;
		for (const FString& S : In) { Out.Add(MakeShared<FJsonValueString>(S)); }
		return Out;
	};

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetArrayField(TEXT("guidelines"), Guidelines);
	Data->SetNumberField(TEXT("unmet_settings"), UnmetSettings);
	Data->SetNumberField(TEXT("unmet_plugins"), UnmetPlugins);
	Data->SetNumberField(TEXT("pending_restart"), PendingRestart);
	Data->SetNumberField(TEXT("scanned_packages"), Scanned);
	Data->SetNumberField(TEXT("unreadable_packages"), Unreadable);
	Data->SetArrayField(TEXT("candidate_packages"), ToJsonArray(Candidates));
	Data->SetArrayField(TEXT("load_failed"), ToJsonArray(LoadFailed));
	Data->SetArrayField(TEXT("bad_paths"), ToJsonArray(BadPaths));
	Data->SetBoolField(TEXT("truncated"), bTruncated);
	Data->SetBoolField(TEXT("popups_suppressed_while_loading"), FScopedGuidelinePopupsOff::bSupported);

	UE_LOG(LogUALAssetGuideline, Log, TEXT("project.check_asset_guidelines: %d guideline(s), %d unmet setting(s), %d unmet plugin(s), scanned %d package(s)"),
		States.Num(), UnmetSettings, UnmetPlugins, Scanned);
	UAL_CommandUtils::SendResponse(RequestId, 200, Data);
}

// ============================================================================
// project.apply_asset_guidelines
// ============================================================================
//
// 入参 names（可选）：只修这几张说明（check 回执里的 name）。不给就修全部已加载的。
// 只写工程设置；插件由盒子侧调 system.manage_plugin。
//
// 每一项都从磁盘读回来核对，回执逐项给状态，顶层给 failed_count（AGENTS.md §5 第 14 条）。
// 两张说明对同一个键要不同的值：两边都不写，标 conflict，交给人选。
void FUAL_AssetGuidelineCommands::Handle_Apply(const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
{
	using namespace UALAssetGuideline;

	TArray<FString> Names;
	ReadStringArray(Payload, TEXT("names"), Names);

	FIniDiskCache Cache;
	TArray<FGuidelineState> States;
	for (UAssetGuideline* G : LoadedGuidelines())
	{
		FGuidelineState State = Evaluate(G, Cache);
		if (Names.Num() == 0 || Names.ContainsByPredicate([&](const FString& N) { return N.Equals(State.Name, ESearchCase::IgnoreCase); }))
		{
			States.Add(MoveTemp(State));
		}
	}

	struct FWrite
	{
		FString Guideline;
		FSettingState Setting;
		FString Result;
		FString Error;
		FString OnDisk;
	};
	TArray<FWrite> Writes;
	for (const FGuidelineState& State : States)
	{
		for (const FSettingState& S : State.Settings)
		{
			if (S.Status == TEXT("missing"))
			{
				Writes.Add({ State.Name, S, FString(), FString(), FString() });
			}
			else if (S.Status == TEXT("bad_file") && !SameMeaning(S.Live, S.Required))
			{
				// 说明指的不是工程 Config 下的 Default*.ini，改不了也不能当成已满足
				Writes.Add({ State.Name, S, TEXT("failed"),
					FString::Printf(TEXT("%s is not a project Config/Default*.ini - change [%s] %s by hand"),
						*S.Filename, *S.Section, *S.Key), FString() });
			}
		}
	}

	// 同一个文件、同一节、同一键，要的值不一样 → 冲突
	for (FWrite& W : Writes)
	{
		for (const FWrite& Other : Writes)
		{
			if (&W != &Other &&
				W.Setting.IniPath == Other.Setting.IniPath &&
				W.Setting.Section.Equals(Other.Setting.Section, ESearchCase::IgnoreCase) &&
				W.Setting.Key.Equals(Other.Setting.Key, ESearchCase::IgnoreCase) &&
				!W.Setting.Required.Equals(Other.Setting.Required, ESearchCase::IgnoreCase))
			{
				W.Result = TEXT("conflict");
				W.Error = FString::Printf(TEXT("guideline %s wants %s"), *Other.Guideline, *Other.Setting.Required);
			}
		}
	}

	// 同一个键第二次出现时照抄第一次写的结果（成败、磁盘读回值都跟它走）
	TMap<FString, int32> Done;
	for (int32 Index = 0; Index < Writes.Num(); ++Index)
	{
		FWrite& W = Writes[Index];
		if (!W.Result.IsEmpty())
		{
			continue;
		}
		const FString Id = (W.Setting.IniPath + TEXT("|") + W.Setting.Section + TEXT("|") + W.Setting.Key).ToLower();
		if (const int32* First = Done.Find(Id))
		{
			W.Result = Writes[*First].Result;
			W.OnDisk = Writes[*First].OnDisk;
			W.Error = Writes[*First].Error;
			continue;
		}
		Done.Add(Id, Index);

		if (IFileManager::Get().FileExists(*W.Setting.IniPath) && IFileManager::Get().IsReadOnly(*W.Setting.IniPath))
		{
			W.Result = TEXT("failed");
			W.Error = FString::Printf(TEXT("%s is read-only (probably locked by source control)"), *W.Setting.IniPath);
			continue;
		}

		// 和引擎「启用缺失」同一种写法：只动这一个键，文件里其他内容原样保留
		FConfigFile Single;
		Single.SetString(*W.Setting.Section, *W.Setting.Key, *W.Setting.Required);
		Single.UpdateSinglePropertyInSection(*W.Setting.IniPath, *W.Setting.Key, *W.Setting.Section);

		Cache.Forget(W.Setting.IniPath);
		const FConfigFile* Disk = Cache.Get(W.Setting.IniPath);
		FString OnDisk;
		if (Disk && Disk->GetString(*W.Setting.Section, *W.Setting.Key, OnDisk) && OnDisk.Equals(W.Setting.Required, ESearchCase::IgnoreCase))
		{
			W.Result = TEXT("written");
			W.OnDisk = OnDisk;
		}
		else
		{
			W.Result = TEXT("failed");
			W.OnDisk = OnDisk;
			W.Error = OnDisk.IsEmpty()
				? FString::Printf(TEXT("[%s] %s is not in %s after writing"), *W.Setting.Section, *W.Setting.Key, *W.Setting.IniPath)
				: FString::Printf(TEXT("[%s] %s reads back \"%s\" from %s"), *W.Setting.Section, *W.Setting.Key, *OnDisk, *W.Setting.IniPath);
		}
	}

	int32 Written = 0;
	int32 Failed = 0;
	TArray<TSharedPtr<FJsonValue>> Results;
	for (const FWrite& W : Writes)
	{
		Written += W.Result == TEXT("written") ? 1 : 0;
		Failed += W.Result == TEXT("written") ? 0 : 1;
		TSharedPtr<FJsonObject> J = MakeShared<FJsonObject>();
		J->SetStringField(TEXT("guideline"), W.Guideline);
		J->SetStringField(TEXT("section"), W.Setting.Section);
		J->SetStringField(TEXT("key"), W.Setting.Key);
		J->SetStringField(TEXT("required"), W.Setting.Required);
		J->SetStringField(TEXT("file"), W.Setting.IniPath);
		J->SetStringField(TEXT("result"), W.Result);
		if (!W.OnDisk.IsEmpty())
		{
			J->SetStringField(TEXT("on_disk"), W.OnDisk);
		}
		if (!W.Error.IsEmpty())
		{
			J->SetStringField(TEXT("error"), W.Error);
		}
		Results.Add(MakeShared<FJsonValueObject>(J));
	}

	// 插件不在这里改，原样列给盒子
	TArray<TSharedPtr<FJsonValue>> PluginsToEnable;
	TSet<FString> PluginSeen;
	for (const FGuidelineState& State : States)
	{
		for (const FPluginState& P : State.Plugins)
		{
			if ((P.Status == TEXT("missing") || P.Status == TEXT("not_installed")) && !PluginSeen.Contains(P.Name.ToLower()))
			{
				PluginSeen.Add(P.Name.ToLower());
				TSharedPtr<FJsonObject> J = MakeShared<FJsonObject>();
				J->SetStringField(TEXT("name"), P.Name);
				J->SetStringField(TEXT("friendly_name"), P.FriendlyName);
				J->SetStringField(TEXT("status"), P.Status);
				J->SetStringField(TEXT("guideline"), State.Name);
				PluginsToEnable.Add(MakeShared<FJsonValueObject>(J));
			}
		}
	}

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetArrayField(TEXT("results"), Results);
	Data->SetArrayField(TEXT("plugins_to_enable"), PluginsToEnable);
	Data->SetNumberField(TEXT("written_count"), Written);
	Data->SetNumberField(TEXT("failed_count"), Failed);
	Data->SetNumberField(TEXT("guidelines_matched"), States.Num());
	// 这些设置（虚拟纹理、蒙皮缓存……）都是引擎启动时读的，写进文件以后要重启编辑器才生效
	Data->SetBoolField(TEXT("restart_required"), Written > 0);

	UE_LOG(LogUALAssetGuideline, Log, TEXT("project.apply_asset_guidelines: %d written, %d failed, %d plugin(s) left to the caller"),
		Written, Failed, PluginsToEnable.Num());
	UAL_CommandUtils::SendResponse(RequestId, 200, Data);
}
