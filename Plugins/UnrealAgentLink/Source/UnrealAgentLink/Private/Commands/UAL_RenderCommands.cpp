#include "UAL_RenderCommands.h"

#include "UAL_CommandUtils.h"
#include "UAL_ReflectCall.h"
#include "UAL_RenderListener.h"

#include "Editor.h"
#include "Editor/EditorEngine.h"
#include "Engine/World.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "LevelSequence.h"
#include "Misc/DateTime.h"
#include "Misc/Guid.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Misc/Timespan.h"
#include "MovieScene.h"
#include "Runtime/Launch/Resources/Version.h"
#include "UObject/Package.h"
#include "UObject/SoftObjectPath.h"
#include "UObject/StrongObjectPtr.h"
#include "UObject/UObjectHash.h"
#include "UObject/UnrealType.h"

DEFINE_LOG_CATEGORY_STATIC(LogUALRender, Log, All);

/**
 * 本文件的辅助函数放在**具名**命名空间里，不用匿名的。
 *
 * unity build 会把好几个 .cpp 拼成一个翻译单元，匿名命名空间挡不住撞名 ——
 * `UAL_SequencerCommands.cpp` 里也有一个 `PlaybackInDisplayFrames`，5.0 上当场 C2084。
 * 命名空间外的调用一律写 `UALR::`。
 */
namespace UALRenderImpl
{
	// ========================================================================
	// MRQ 的类。全部按 /Script 路径查，插件没开时查不到
	// ========================================================================

	const TCHAR* QUEUE_CLASS = TEXT("/Script/MovieRenderPipelineCore.MoviePipelineQueue");
	const TCHAR* JOB_CLASS = TEXT("/Script/MovieRenderPipelineCore.MoviePipelineExecutorJob");
	const TCHAR* LIBRARY_CLASS = TEXT("/Script/MovieRenderPipelineCore.MoviePipelineBlueprintLibrary");
	const TCHAR* PIPELINE_CLASS = TEXT("/Script/MovieRenderPipelineCore.MoviePipeline");
	const TCHAR* OUTPUT_SETTING_CLASS = TEXT("/Script/MovieRenderPipelineCore.MoviePipelineOutputSetting");
	const TCHAR* AA_SETTING_CLASS = TEXT("/Script/MovieRenderPipelineCore.MoviePipelineAntiAliasingSetting");
	const TCHAR* OUTPUT_BASE_CLASS = TEXT("/Script/MovieRenderPipelineCore.MoviePipelineOutputBase");
	const TCHAR* PIE_EXECUTOR_CLASS = TEXT("/Script/MovieRenderPipelineEditor.MoviePipelinePIEExecutor");
	const TCHAR* SUBSYSTEM_CLASS = TEXT("/Script/MovieRenderPipelineEditor.MoviePipelineQueueSubsystem");
	const TCHAR* DEFERRED_PASS_CLASS = TEXT("/Script/MovieRenderPipelineRenderPasses.MoviePipelineDeferredPassBase");
	const TCHAR* PATH_TRACER_PASS_CLASS = TEXT("/Script/MovieRenderPipelineRenderPasses.MoviePipelineDeferredPass_PathTracer");

	/** 5.2 起叫 PrimaryConfig；5.0/5.1 叫 MasterConfig（5.2–5.4 的旧名只剩 C++ typedef，没有 UClass） */
	UClass* FindPrimaryConfigClass()
	{
		if (UClass* Cls = UALReflect::FindScriptClass(TEXT("/Script/MovieRenderPipelineCore.MoviePipelinePrimaryConfig")))
		{
			return Cls;
		}
		return UALReflect::FindScriptClass(TEXT("/Script/MovieRenderPipelineCore.MoviePipelineMasterConfig"));
	}

	/** 输出格式 → 输出设置类。MP4 在单独的模块里，5.6 才有 */
	UClass* FindOutputClass(const FString& Format)
	{
		if (Format == TEXT("png")) { return UALReflect::FindScriptClass(TEXT("/Script/MovieRenderPipelineRenderPasses.MoviePipelineImageSequenceOutput_PNG")); }
		if (Format == TEXT("jpg")) { return UALReflect::FindScriptClass(TEXT("/Script/MovieRenderPipelineRenderPasses.MoviePipelineImageSequenceOutput_JPG")); }
		if (Format == TEXT("bmp")) { return UALReflect::FindScriptClass(TEXT("/Script/MovieRenderPipelineRenderPasses.MoviePipelineImageSequenceOutput_BMP")); }
		if (Format == TEXT("exr")) { return UALReflect::FindScriptClass(TEXT("/Script/MovieRenderPipelineRenderPasses.MoviePipelineImageSequenceOutput_EXR")); }
		if (Format == TEXT("mp4")) { return UALReflect::FindScriptClass(TEXT("/Script/MovieRenderPipelineMP4Encoder.MoviePipelineMP4EncoderOutput")); }
		return nullptr;
	}

	/**
	 * 画质档 → 采样数与预热。
	 *
	 * 档位制来自 UNTRender（维护者早年的 MRQ 插件）的「低 / 中 / 高 / 极高」。
	 * 预热是为了黑屏成因 B4 / B7（`ue-sequencer/references/black-screen-causes.md`）：
	 * 曝光、Lumen、TSR 历史、粒子在第一帧都没收敛，不预热的话每个镜头开头几帧是脏的。
	 *
	 * Lumen 高两档关掉引擎 AA、纯靠子采样累积 —— 子采样够多时这样边缘更干净，
	 * 也不会有 TSR 在子采样之间串历史的拖影。路径追踪的采样全给空间，
	 * 它每个子采样就是一次完整的追踪，时间采样只在要运动模糊时才有意义。
	 */
	struct FQualityPreset
	{
		int32 Spatial;
		int32 Temporal;
		bool bOverrideAAToNone;
		int32 EngineWarmUp;
		int32 RenderWarmUp; // 0 = 不渲预热帧
	};

	bool LookupQuality(const FString& Quality, bool bPathTracer, FQualityPreset& Out)
	{
		if (bPathTracer)
		{
			if (Quality == TEXT("draft"))    { Out = { 16, 1, false, 0, 0 };    return true; }
			if (Quality == TEXT("standard")) { Out = { 64, 1, false, 32, 0 };   return true; }
			if (Quality == TEXT("high"))     { Out = { 256, 1, false, 32, 0 };  return true; }
			if (Quality == TEXT("ultra"))    { Out = { 1024, 1, false, 64, 0 }; return true; }
			return false;
		}
		if (Quality == TEXT("draft"))    { Out = { 1, 1, false, 0, 0 };    return true; }
		if (Quality == TEXT("standard")) { Out = { 1, 4, false, 32, 32 };  return true; }
		if (Quality == TEXT("high"))     { Out = { 2, 8, true, 32, 32 };   return true; }
		if (Quality == TEXT("ultra"))    { Out = { 4, 16, true, 64, 64 };  return true; }
		return false;
	}

	// ========================================================================
	// 反射写属性。UALReflect 里没有的几种类型放这里，只有本文件用
	// ========================================================================

	bool SetBool(UObject* Obj, const TCHAR* Name, bool Value)
	{
		FBoolProperty* Prop = Obj ? FindFProperty<FBoolProperty>(Obj->GetClass(), Name) : nullptr;
		if (!Prop)
		{
			UE_LOG(LogUALRender, Warning, TEXT("%s has no bool property %s"), Obj ? *Obj->GetClass()->GetName() : TEXT("null"), Name);
			return false;
		}
		Prop->SetPropertyValue_InContainer(Obj, Value);
		return true;
	}

	bool GetBool(const UObject* Obj, const TCHAR* Name, bool Default = false)
	{
		bool Out = Default;
		return UALReflect::GetBoolProp(Obj, Name, Out) ? Out : Default;
	}

	int32 GetInt(const UObject* Obj, const TCHAR* Name, int32 Default = 0)
	{
		int32 Out = Default;
		return UALReflect::GetIntProp(Obj, Name, Out) ? Out : Default;
	}

	/** TEnumAsByte 是 FByteProperty，enum class 是 FEnumProperty，两种都认 */
	bool SetByte(UObject* Obj, const TCHAR* Name, uint8 Value)
	{
		FProperty* Prop = Obj ? FindFProperty<FProperty>(Obj->GetClass(), Name) : nullptr;
		if (FByteProperty* AsByte = CastField<FByteProperty>(Prop))
		{
			AsByte->SetPropertyValue_InContainer(Obj, Value);
			return true;
		}
		if (FEnumProperty* AsEnum = CastField<FEnumProperty>(Prop))
		{
			AsEnum->GetUnderlyingProperty()->SetIntPropertyValue(AsEnum->ContainerPtrToValuePtr<void>(Obj), static_cast<int64>(Value));
			return true;
		}
		UE_LOG(LogUALRender, Warning, TEXT("%s has no enum property %s"), Obj ? *Obj->GetClass()->GetName() : TEXT("null"), Name);
		return false;
	}

	FStructProperty* FindStruct(const UObject* Obj, const TCHAR* Name, const UScriptStruct* Expected)
	{
		FStructProperty* Prop = Obj ? FindFProperty<FStructProperty>(Obj->GetClass(), Name) : nullptr;
		return (Prop && Prop->Struct == Expected) ? Prop : nullptr;
	}

	/**
	 * 按结构体名认。`TBaseStructure<FIntPoint>` 在 5.0 上没有特化（编不过），
	 * 而 FIntPoint 的内存布局 5.0–5.8 都是两个 int32
	 */
	FStructProperty* FindStructByName(const UObject* Obj, const TCHAR* Name, const TCHAR* StructName)
	{
		FStructProperty* Prop = Obj ? FindFProperty<FStructProperty>(Obj->GetClass(), Name) : nullptr;
		return (Prop && Prop->Struct->GetFName() == FName(StructName)) ? Prop : nullptr;
	}

	bool SetIntPoint(UObject* Obj, const TCHAR* Name, const FIntPoint& Value)
	{
		FStructProperty* Prop = FindStructByName(Obj, Name, TEXT("IntPoint"));
		if (!Prop)
		{
			return false;
		}
		*Prop->ContainerPtrToValuePtr<FIntPoint>(Obj) = Value;
		return true;
	}

	FIntPoint GetIntPoint(const UObject* Obj, const TCHAR* Name, const FIntPoint& Default)
	{
		const FStructProperty* Prop = FindStructByName(Obj, Name, TEXT("IntPoint"));
		return Prop ? *Prop->ContainerPtrToValuePtr<FIntPoint>(Obj) : Default;
	}

	bool SetSoftPath(UObject* Obj, const TCHAR* Name, const FSoftObjectPath& Value)
	{
		FStructProperty* Prop = FindStruct(Obj, Name, TBaseStructure<FSoftObjectPath>::Get());
		if (!Prop)
		{
			return false;
		}
		*Prop->ContainerPtrToValuePtr<FSoftObjectPath>(Obj) = Value;
		return true;
	}

	/**
	 * FDirectoryPath 只有一个 `Path` 成员。按名字认结构体、按名字写成员，
	 * 不 include 它的声明 —— 它在 NoExportTypes 里，各版本的头位置不一样
	 */
	bool SetDirectoryPath(UObject* Obj, const TCHAR* Name, const FString& Value)
	{
		FStructProperty* Prop = Obj ? FindFProperty<FStructProperty>(Obj->GetClass(), Name) : nullptr;
		if (!Prop || Prop->Struct->GetFName() != TEXT("DirectoryPath"))
		{
			return false;
		}
		FStrProperty* PathProp = FindFProperty<FStrProperty>(Prop->Struct, TEXT("Path"));
		if (!PathProp)
		{
			return false;
		}
		PathProp->SetPropertyValue_InContainer(Prop->ContainerPtrToValuePtr<void>(Obj), Value);
		return true;
	}

	/** 在配置里找或加一个设置。5.2 起有 bExactMatch：路径追踪是延迟渲染的子类，不精确匹配会拿错 */
	UObject* FindOrAddSetting(UObject* Config, UClass* SettingClass)
	{
		UALReflect::FCall Call(Config, TEXT("FindOrAddSettingByClass"));
		Call.Cls(TEXT("InClass"), SettingClass).Bool(TEXT("bIncludeDisabledSettings"), true);
		if (Call.HasParam(TEXT("bExactMatch")))
		{
			Call.Bool(TEXT("bExactMatch"), true);
		}
		if (!Call.Invoke())
		{
			UE_LOG(LogUALRender, Warning, TEXT("FindOrAddSettingByClass failed: %s"), *Call.GetError());
			return nullptr;
		}
		UObject* Setting = Call.OutObject(TEXT("ReturnValue"));
		// 用户预设里可能有被禁用的同类设置，拿到了就得打开，不然等于没加
		if (Setting)
		{
			SetBool(Setting, TEXT("bEnabled"), true);
		}
		return Setting;
	}

	/** 配置里所有属于 Base 子类的设置（`Settings` 是私有 UPROPERTY，反射照样读得到） */
	TArray<UObject*> SettingsOfClass(const UObject* Config, UClass* Base)
	{
		TArray<UObject*> All, Out;
		UALReflect::GetObjectArrayProp(Config, TEXT("Settings"), All);
		for (UObject* S : All)
		{
			if (S && Base && S->IsA(Base))
			{
				Out.Add(S);
			}
		}
		return Out;
	}

	void RemoveSetting(UObject* Config, UObject* Setting)
	{
		UALReflect::FCall Call(Config, TEXT("RemoveSetting"));
		Call.Obj(TEXT("InSetting"), Setting);
		Call.Invoke();
	}

	// ========================================================================
	// 帧号：MovieScene 内部是 tick，对外一律说显示帧（同 UAL_SequencerCommands）
	// ========================================================================

	void PlaybackInDisplayFrames(const UMovieScene* MovieScene, int32& OutStart, int32& OutEnd)
	{
		OutStart = 0;
		OutEnd = 0;
		const TRange<FFrameNumber> Range = MovieScene->GetPlaybackRange();
		const FFrameRate TickRes = MovieScene->GetTickResolution();
		const FFrameRate DisplayRate = MovieScene->GetDisplayRate();
		if (Range.GetLowerBound().IsClosed())
		{
			OutStart = FFrameRate::TransformTime(FFrameTime(Range.GetLowerBoundValue()), TickRes, DisplayRate).FloorToFrame().Value;
		}
		if (Range.GetUpperBound().IsClosed())
		{
			OutEnd = FFrameRate::TransformTime(FFrameTime(Range.GetUpperBoundValue()), TickRes, DisplayRate).FloorToFrame().Value;
		}
	}

	// ========================================================================
	// 任务状态。一次只有一个
	// ========================================================================

	enum class ERenderState : uint8 { Rendering, Finished, Failed, Canceled };

	const TCHAR* StateName(ERenderState State)
	{
		switch (State)
		{
		case ERenderState::Rendering: return TEXT("rendering");
		case ERenderState::Finished:  return TEXT("finished");
		case ERenderState::Failed:    return TEXT("failed");
		case ERenderState::Canceled:  return TEXT("canceled");
		}
		return TEXT("none");
	}

	struct FRenderJob
	{
		FString JobId;
		FString OutputDir;
		/** 开始时的墙钟时间。数文件只数这之后写的，免得把用户目录里原有的算进来 */
		FDateTime StartedAtUtc;
		double StartSeconds = 0.0;
		double EndSeconds = 0.0;

		ERenderState State = ERenderState::Rendering;
		bool bCancelRequested = false;
		FString Error;

		/** 最近一次读到的进度。管线在每个任务结束时就被清空，渲完再查也要有数 */
		float Progress = 0.f;
		int32 OutputFrame = 0;
		int32 TotalFrames = 0;

		TStrongObjectPtr<UObject> Queue;
		TStrongObjectPtr<UObject> Executor;
		TStrongObjectPtr<UUAL_RenderListener> Listener;
	};

	TUniquePtr<FRenderJob> GJob;

	// ------------------------------------------------------------------------
	// 无人值守开关：只在「提交」到「PIE 起来」之间打开
	// ------------------------------------------------------------------------

	bool GUnattendedRaised = false;
	bool GUnattendedPrev = false;
	FDelegateHandle GPostPIEStartedHandle;

	void RestoreUnattended()
	{
		if (GPostPIEStartedHandle.IsValid())
		{
			FEditorDelegates::PostPIEStarted.Remove(GPostPIEStartedHandle);
			GPostPIEStartedHandle.Reset();
		}
		if (GUnattendedRaised)
		{
			GIsRunningUnattendedScript = GUnattendedPrev;
			GUnattendedRaised = false;
		}
	}

	void RaiseUnattended()
	{
		RestoreUnattended();
		GUnattendedPrev = GIsRunningUnattendedScript;
		GIsRunningUnattendedScript = true;
		GUnattendedRaised = true;
		GPostPIEStartedHandle = FEditorDelegates::PostPIEStarted.AddLambda([](bool)
		{
			RestoreUnattended();
		});
	}

	/** 执行器不用了就放掉，GC 自己收 */
	void ReleaseObjects(FRenderJob& Job)
	{
		Job.Executor.Reset();
		Job.Queue.Reset();
		Job.Listener.Reset();
	}

	/** 渲染中：从执行器当前的管线读进度 */
	void RefreshProgress(FRenderJob& Job)
	{
		UObject* Executor = Job.Executor.Get();
		UObject* Pipeline = Executor ? UALReflect::GetObjectProp(Executor, TEXT("ActiveMoviePipeline")) : nullptr;
		UClass* PipelineClass = UALReflect::FindScriptClass(PIPELINE_CLASS);
		UClass* LibraryClass = UALReflect::FindScriptClass(LIBRARY_CLASS);
		if (!Pipeline || !PipelineClass || !Pipeline->IsA(PipelineClass) || !LibraryClass)
		{
			return;
		}
		UObject* Library = LibraryClass->GetDefaultObject();

		{
			UALReflect::FCall Call(Library, TEXT("GetCompletionPercentage"));
			Call.Obj(TEXT("InPipeline"), Pipeline);
			if (Call.Invoke())
			{
				Job.Progress = static_cast<float>(Call.OutFloat(TEXT("ReturnValue"), Job.Progress));
			}
		}
		{
			UALReflect::FCall Call(Library, TEXT("GetOverallOutputFrames"));
			Call.Obj(TEXT("InMoviePipeline"), Pipeline);
			if (Call.Invoke())
			{
				Job.OutputFrame = Call.OutInt(TEXT("OutCurrentIndex"), Job.OutputFrame);
				Job.TotalFrames = Call.OutInt(TEXT("OutTotalCount"), Job.TotalFrames);
			}
		}
	}

	/** 剩余时间要现算，不缓存 —— 管线没了就是估不出来 */
	bool EstimateRemaining(const FRenderJob& Job, double& OutSeconds)
	{
		UObject* Executor = Job.Executor.Get();
		UObject* Pipeline = Executor ? UALReflect::GetObjectProp(Executor, TEXT("ActiveMoviePipeline")) : nullptr;
		UClass* PipelineClass = UALReflect::FindScriptClass(PIPELINE_CLASS);
		UClass* LibraryClass = UALReflect::FindScriptClass(LIBRARY_CLASS);
		if (!Pipeline || !PipelineClass || !Pipeline->IsA(PipelineClass) || !LibraryClass)
		{
			return false;
		}
		UALReflect::FCall Call(LibraryClass->GetDefaultObject(), TEXT("GetEstimatedTimeRemaining"));
		Call.Obj(TEXT("InPipeline"), Pipeline);
		if (!Call.Invoke() || !Call.OutBool(TEXT("ReturnValue")))
		{
			return false;
		}
		const FStructProperty* Prop = nullptr;
		const void* Addr = nullptr;
		if (!Call.OutStruct(TEXT("OutEstimate"), Prop, Addr) || !Prop || Prop->Struct->GetFName() != TEXT("Timespan"))
		{
			return false;
		}
		OutSeconds = static_cast<const FTimespan*>(Addr)->GetTotalSeconds();
		return true;
	}

	/** 输出目录里这次任务写出的文件（按修改时间筛），排好序 */
	TArray<FString> ListWrittenFiles(const FRenderJob& Job)
	{
		TArray<FString> Found;
		IFileManager::Get().FindFilesRecursive(Found, *Job.OutputDir, TEXT("*"), /*Files=*/true, /*Directories=*/false);
		// 文件系统时间戳精度有限，留两秒余量
		const FDateTime Since = Job.StartedAtUtc - FTimespan::FromSeconds(2.0);
		TArray<FString> Out;
		for (const FString& File : Found)
		{
			if (IFileManager::Get().GetTimeStamp(*File) >= Since)
			{
				Out.Add(FPaths::ConvertRelativePathToFull(File));
			}
		}
		Out.Sort();
		return Out;
	}

	TSharedPtr<FJsonObject> StatusJson(FRenderJob& Job)
	{
		if (Job.State == ERenderState::Rendering)
		{
			RefreshProgress(Job);
		}

		TSharedPtr<FJsonObject> Json = MakeShared<FJsonObject>();
		Json->SetStringField(TEXT("job_id"), Job.JobId);
		Json->SetStringField(TEXT("state"), StateName(Job.State));
		Json->SetNumberField(TEXT("progress"), Job.State == ERenderState::Finished ? 1.0 : Job.Progress);
		Json->SetNumberField(TEXT("output_frame"), Job.OutputFrame);
		Json->SetNumberField(TEXT("total_frames"), Job.TotalFrames);
		const double End = Job.State == ERenderState::Rendering ? FPlatformTime::Seconds() : Job.EndSeconds;
		Json->SetNumberField(TEXT("elapsed_seconds"), FMath::Max(0.0, End - Job.StartSeconds));
		Json->SetStringField(TEXT("output_dir"), Job.OutputDir);

		if (Job.State == ERenderState::Rendering)
		{
			double Eta = 0.0;
			if (EstimateRemaining(Job, Eta))
			{
				Json->SetNumberField(TEXT("eta_seconds"), Eta);
			}
		}
		else
		{
			const TArray<FString> Files = ListWrittenFiles(Job);
			Json->SetNumberField(TEXT("files_written"), Files.Num());
			TArray<TSharedPtr<FJsonValue>> Samples;
			for (int32 i = 0; i < Files.Num() && i < 3; ++i)
			{
				Samples.Add(MakeShared<FJsonValueString>(Files[i]));
			}
			Json->SetArrayField(TEXT("sample_files"), Samples);
		}

		if (!Job.Error.IsEmpty())
		{
			Json->SetStringField(TEXT("error"), Job.Error);
		}
		return Json;
	}

	/** 编辑器里有没有 MRQ 窗口发起的渲染在跑。子系统没加载就当没有 */
	bool IsQueueSubsystemRendering(UObject*& OutSubsystem)
	{
		OutSubsystem = nullptr;
		UClass* SubsystemClass = UALReflect::FindScriptClass(SUBSYSTEM_CLASS);
		if (!SubsystemClass)
		{
			return false;
		}
		// 不经 GEditor->GetEditorSubsystemBase：那要依赖 EditorSubsystem 模块，
		// 而编辑器子系统本来就只有一个实例，按类找就行
		TArray<UObject*> Instances;
		GetObjectsOfClass(SubsystemClass, Instances, /*bIncludeDerivedClasses=*/false);
		for (UObject* Obj : Instances)
		{
			if (Obj && !Obj->HasAnyFlags(RF_ClassDefaultObject | RF_ArchetypeObject))
			{
				OutSubsystem = Obj;
				break;
			}
		}
		if (!OutSubsystem)
		{
			return false;
		}
		UALReflect::FCall Call(OutSubsystem, TEXT("IsRendering"));
		return Call.Invoke() && Call.OutBool(TEXT("ReturnValue"));
	}

	/** 把执行器的两条多播挂到监听者上 */
	bool BindExecutorDelegates(UObject* Executor, UUAL_RenderListener* Listener)
	{
		auto Bind = [Executor, Listener](const TCHAR* PropName, const TCHAR* FuncName)
		{
			FMulticastDelegateProperty* Prop = FindFProperty<FMulticastDelegateProperty>(Executor->GetClass(), PropName);
			if (!Prop)
			{
				UE_LOG(LogUALRender, Warning, TEXT("%s has no delegate %s"), *Executor->GetClass()->GetName(), PropName);
				return false;
			}
			FScriptDelegate Delegate;
			Delegate.BindUFunction(Listener, FName(FuncName));
			Prop->AddDelegate(MoveTemp(Delegate), Executor);
			return true;
		};
		const bool bFinished = Bind(TEXT("OnExecutorFinishedDelegate"), TEXT("HandleExecutorFinished"));
		Bind(TEXT("OnExecutorErroredDelegate"), TEXT("HandleExecutorErrored"));
		// 出错那条挂不上还能靠完成那条收尾；完成那条挂不上就永远不知道渲完了
		return bFinished;
	}

	FString CurrentEditorMapPackage()
	{
		UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
		return World ? World->GetOutermost()->GetName() : FString();
	}
}

namespace UALR = UALRenderImpl;

// ============================================================================
// 监听者
// ============================================================================

void UUAL_RenderListener::HandleExecutorFinished(UObject* PipelineExecutor, bool bSuccess)
{
	FUAL_RenderCommands::OnExecutorFinished(bSuccess);
}

void UUAL_RenderListener::HandleExecutorErrored(UObject* PipelineExecutor, UObject* PipelineWithError, bool bIsFatal, FText ErrorText)
{
	FUAL_RenderCommands::OnExecutorErrored(ErrorText.ToString(), bIsFatal);
}

void FUAL_RenderCommands::OnExecutorFinished(bool bSuccess)
{
	UALR::RestoreUnattended();
	if (!UALR::GJob.IsValid() || UALR::GJob->State != UALR::ERenderState::Rendering)
	{
		return;
	}
	UALR::FRenderJob& Job = *UALR::GJob;
	UALR::RefreshProgress(Job);
	Job.EndSeconds = FPlatformTime::Seconds();
#if ENGINE_MAJOR_VERSION == 5 && ENGINE_MINOR_VERSION <= 2
	// 5.0–5.2 的 OnExecutorErroredImpl 出致命错时广播的是 Finished(bFatal=true)，
	// 成功标志靠不住；这几个版本没有 MRQ 自带的视频输出，渲完至少每帧一个文件
	if (bSuccess && !Job.bCancelRequested && Job.TotalFrames > 0
		&& UALR::ListWrittenFiles(Job).Num() < Job.TotalFrames)
	{
		bSuccess = false;
		if (Job.Error.IsEmpty())
		{
			Job.Error = FString::Printf(TEXT("MRQ 中途出错停下了：%d 帧只写出了 %d 个文件。看输出日志里的 LogMovieRenderPipeline"),
				Job.TotalFrames, UALR::ListWrittenFiles(Job).Num());
		}
	}
#endif
	if (Job.bCancelRequested)
	{
		Job.State = UALR::ERenderState::Canceled;
	}
	else if (bSuccess)
	{
		Job.State = UALR::ERenderState::Finished;
		// 管线在广播完成之前就清空了，最后读到的帧号停在上一次轮询那一刻。
		// 引擎说渲成功了就是全渲完了；实际写了几个文件另由扫盘回答
		Job.OutputFrame = Job.TotalFrames;
	}
	else
	{
		Job.State = UALR::ERenderState::Failed;
		if (Job.Error.IsEmpty())
		{
			Job.Error = TEXT("MRQ 报告渲染失败，没有给出原因。看输出日志里的 LogMovieRenderPipeline");
		}
	}
	UE_LOG(LogUALRender, Log, TEXT("Render job %s ended: %s"), *Job.JobId, UALR::StateName(Job.State));
	UALR::ReleaseObjects(Job);
}

void FUAL_RenderCommands::OnExecutorErrored(const FString& ErrorText, bool bIsFatal)
{
	if (!UALR::GJob.IsValid())
	{
		return;
	}
	UE_LOG(LogUALRender, Warning, TEXT("Render job %s error (fatal=%d): %s"), *UALR::GJob->JobId, bIsFatal ? 1 : 0, *ErrorText);
	// 只留第一条：后面的通常是它引起的连锁
	if (UALR::GJob->Error.IsEmpty())
	{
		UALR::GJob->Error = ErrorText;
	}
}

// ============================================================================
// 注册
// ============================================================================

void FUAL_RenderCommands::RegisterCommands(
	TMap<FString, TFunction<void(const TSharedPtr<FJsonObject>&, const FString)>>& CommandMap)
{
	CommandMap.Add(TEXT("sequence.render"), [](const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
	{
		Handle_Render(Payload, RequestId);
	});
	CommandMap.Add(TEXT("sequence.render_status"), [](const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
	{
		Handle_Status(Payload, RequestId);
	});
	CommandMap.Add(TEXT("sequence.render_cancel"), [](const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
	{
		Handle_Cancel(Payload, RequestId);
	});
}

// ============================================================================
// sequence.render
// ============================================================================

void FUAL_RenderCommands::Handle_Render(const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
{
	// ---- MRQ 在不在 ----
	UClass* QueueClass = UALReflect::FindScriptClass(UALR::QUEUE_CLASS);
	UClass* JobClass = UALReflect::FindScriptClass(UALR::JOB_CLASS);
	UClass* ExecutorClass = UALReflect::FindScriptClass(UALR::PIE_EXECUTOR_CLASS);
	UClass* OutputSettingClass = UALReflect::FindScriptClass(UALR::OUTPUT_SETTING_CLASS);
	if (!QueueClass || !JobClass || !ExecutorClass || !OutputSettingClass)
	{
		UAL_CommandUtils::SendError(RequestId, 412,
			TEXT("项目没有启用 Movie Render Queue 插件（MovieRenderPipeline）。启用后要重启编辑器"));
		return;
	}

	// ---- 不和别的渲染、别的 PIE 抢 ----
	if (UALR::GJob.IsValid() && UALR::GJob->State == UALR::ERenderState::Rendering)
	{
		UAL_CommandUtils::SendError(RequestId, 409,
			FString::Printf(TEXT("上一次渲染（%s）还没结束。等它渲完，或者先取消"), *UALR::GJob->JobId),
			UALR::StatusJson(*UALR::GJob));
		return;
	}
	if (!GEditor)
	{
		UAL_CommandUtils::SendError(RequestId, 500, TEXT("编辑器还没就绪"));
		return;
	}
	if (GEditor->PlayWorld)
	{
		// 不拒绝的话引擎会静默结束用户这次 PIE，再起渲染
		UAL_CommandUtils::SendError(RequestId, 409, TEXT("编辑器正在运行 PIE（Play），先停掉再渲染"));
		return;
	}
	UObject* Subsystem = nullptr;
	if (UALR::IsQueueSubsystemRendering(Subsystem))
	{
		UAL_CommandUtils::SendError(RequestId, 409, TEXT("MRQ 窗口里已经有一次渲染在跑，等它结束再开始"));
		return;
	}

	// ---- 序列 ----
	FString SequencePath;
	if (!Payload->TryGetStringField(TEXT("sequence_path"), SequencePath) || SequencePath.IsEmpty())
	{
		UAL_CommandUtils::SendError(RequestId, 400, TEXT("Missing field: sequence_path"));
		return;
	}
	ULevelSequence* Sequence = Cast<ULevelSequence>(StaticLoadObject(UObject::StaticClass(), nullptr, *SequencePath));
	if (!Sequence || !Sequence->GetMovieScene())
	{
		UAL_CommandUtils::SendError(RequestId, 404, FString::Printf(TEXT("找不到 Level Sequence：%s"), *SequencePath));
		return;
	}
	const FString SequenceName = Sequence->GetName();
	const FSoftObjectPath SequenceSoftPath(Sequence);

	// ---- 关卡：必须是存过盘的包（5.0 遇到无效地图会弹模态框，所以先自己查） ----
	FString MapPackage;
	if (Payload->TryGetStringField(TEXT("map_path"), MapPackage) && !MapPackage.IsEmpty())
	{
		MapPackage = FPackageName::ObjectPathToPackageName(MapPackage);
	}
	else
	{
		MapPackage = UALR::CurrentEditorMapPackage();
	}
	if (MapPackage.IsEmpty() || !FPackageName::IsValidLongPackageName(MapPackage) || !FPackageName::DoesPackageExist(MapPackage))
	{
		UAL_CommandUtils::SendError(RequestId, 400, MapPackage.StartsWith(TEXT("/Temp/"))
			? TEXT("当前关卡还没存过盘，MRQ 渲不了没存过的关卡。先保存关卡，或者用 map_path 指定一个")
			: FString::Printf(TEXT("找不到关卡：%s"), *MapPackage));
		return;
	}
	const FSoftObjectPath MapSoftPath(MapPackage + TEXT(".") + FPackageName::GetShortName(MapPackage));

	// ---- 预设（可选） ----
	UObject* Preset = nullptr;
	FString PresetPath;
	if (Payload->TryGetStringField(TEXT("preset_path"), PresetPath) && !PresetPath.IsEmpty())
	{
		UClass* ConfigClass = UALR::FindPrimaryConfigClass();
		Preset = StaticLoadObject(UObject::StaticClass(), nullptr, *PresetPath);
		if (!Preset || !ConfigClass || !Preset->IsA(ConfigClass))
		{
			UAL_CommandUtils::SendError(RequestId, 404,
				FString::Printf(TEXT("%s 不是 MRQ 预设（Movie Pipeline Primary Config）"), *PresetPath));
			return;
		}
	}

	// ---- 格式 / 渲染器 / 画质 ----
	TArray<FString> Warnings;
	FString Format, Renderer, Quality;
	const bool bFormatGiven = Payload->TryGetStringField(TEXT("format"), Format) && !Format.IsEmpty();
	const bool bRendererGiven = Payload->TryGetStringField(TEXT("renderer"), Renderer) && !Renderer.IsEmpty();
	const bool bQualityGiven = Payload->TryGetStringField(TEXT("quality"), Quality) && !Quality.IsEmpty();
	if (!bFormatGiven) { Format = TEXT("png"); }
	if (!bRendererGiven) { Renderer = TEXT("lumen"); }
	if (!bQualityGiven) { Quality = TEXT("standard"); }
	Format = Format.ToLower();

	UClass* OutputClass = nullptr;
	if (!Preset || bFormatGiven)
	{
		OutputClass = UALR::FindOutputClass(Format);
		if (!OutputClass)
		{
			UAL_CommandUtils::SendError(RequestId, 400, Format == TEXT("mp4")
				? TEXT("这个引擎版本的 MRQ 没有 MP4 输出（5.6 起才有）。改用 png 序列帧，再用剪辑软件合成视频")
				: FString::Printf(TEXT("不支持的输出格式：%s（可选 png / jpg / exr / bmp / mp4）"), *Format));
			return;
		}
	}

	const bool bPathTracer = Renderer == TEXT("path_tracer");
	UALR::FQualityPreset QualityPreset = { 1, 1, false, 0, 0 };
	UClass* PassClass = nullptr;
	UClass* AAClass = UALReflect::FindScriptClass(UALR::AA_SETTING_CLASS);
	if (Preset)
	{
		if (bRendererGiven || bQualityGiven)
		{
			Warnings.Add(TEXT("用了预设，renderer / quality 没有生效 —— 采样和渲染方式以预设为准"));
		}
	}
	else
	{
		if (!UALR::LookupQuality(Quality, bPathTracer, QualityPreset))
		{
			UAL_CommandUtils::SendError(RequestId, 400,
				FString::Printf(TEXT("不认识的画质档：%s（可选 draft / standard / high / ultra）"), *Quality));
			return;
		}
		PassClass = UALReflect::FindScriptClass(bPathTracer ? UALR::PATH_TRACER_PASS_CLASS : UALR::DEFERRED_PASS_CLASS);
		if (!PassClass || !AAClass)
		{
			UAL_CommandUtils::SendError(RequestId, 412, TEXT("MRQ 的渲染通道模块没有加载（MovieRenderPipelineRenderPasses）"));
			return;
		}
		if (bPathTracer)
		{
			IConsoleVariable* RayTracing = IConsoleManager::Get().FindConsoleVariable(TEXT("r.RayTracing"));
			if (!RayTracing || RayTracing->GetInt() == 0)
			{
				UAL_CommandUtils::SendError(RequestId, 400,
					TEXT("项目没开硬件光追，路径追踪用不了。项目设置 → 渲染 → 勾 Support Hardware Ray Tracing（要重启编辑器），或者改用 lumen"));
				return;
			}
		}
	}

	// ---- 帧范围 ----
	int32 PlayStart = 0, PlayEnd = 0;
	UALR::PlaybackInDisplayFrames(Sequence->GetMovieScene(), PlayStart, PlayEnd);
	double Tmp = 0.0;
	const bool bStartGiven = Payload->TryGetNumberField(TEXT("frame_start"), Tmp);
	const int32 FrameStart = bStartGiven ? static_cast<int32>(Tmp) : PlayStart;
	const bool bEndGiven = Payload->TryGetNumberField(TEXT("frame_end"), Tmp);
	const int32 FrameEnd = bEndGiven ? static_cast<int32>(Tmp) : PlayEnd;
	if ((bStartGiven || bEndGiven) && FrameEnd <= FrameStart)
	{
		UAL_CommandUtils::SendError(RequestId, 400,
			FString::Printf(TEXT("帧范围 [%d, %d) 是空的（结束帧不含）"), FrameStart, FrameEnd));
		return;
	}

	// ---- 输出目录：默认每次一个新目录，渲完数文件才不会把上一次的算进来 ----
	FString OutputDir;
	if (Payload->TryGetStringField(TEXT("output_dir"), OutputDir) && !OutputDir.IsEmpty())
	{
		if (FPaths::IsRelative(OutputDir))
		{
			UAL_CommandUtils::SendError(RequestId, 400, FString::Printf(TEXT("output_dir 要给绝对路径：%s"), *OutputDir));
			return;
		}
	}
	else
	{
		OutputDir = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("MovieRenders"), SequenceName,
			FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S")));
	}
	OutputDir = FPaths::ConvertRelativePathToFull(OutputDir);
	FPaths::NormalizeDirectoryName(OutputDir);
	if (!IFileManager::Get().MakeDirectory(*OutputDir, /*Tree=*/true))
	{
		UAL_CommandUtils::SendError(RequestId, 500, FString::Printf(TEXT("建不了输出目录：%s"), *OutputDir));
		return;
	}

	// ---- 建队列和任务 ----
	UObject* Queue = NewObject<UObject>(GetTransientPackage(), QueueClass, NAME_None, RF_Transient);
	UObject* Job = nullptr;
	{
		UALReflect::FCall Call(Queue, TEXT("AllocateNewJob"));
		Call.Cls(TEXT("InJobType"), JobClass);
		if (Call.Invoke())
		{
			Job = Call.OutObject(TEXT("ReturnValue"));
		}
		if (!Job)
		{
			UAL_CommandUtils::SendError(RequestId, 500, FString::Printf(TEXT("MRQ 建不出渲染任务：%s"), *Call.GetError()));
			return;
		}
	}
	{
		// 用 SetSequence 不直接写属性：它顺带载入序列、重建镜头列表
		UALReflect::FCall Call(Job, TEXT("SetSequence"));
		Call.SoftPath(TEXT("InSequence"), SequenceSoftPath);
		Call.Invoke();
	}
	UALR::SetSoftPath(Job, TEXT("Map"), MapSoftPath);
	UALReflect::SetStringProp(Job, TEXT("JobName"), SequenceName);

	if (Preset)
	{
		UALReflect::FCall Call(Job, TEXT("SetConfiguration"));
		Call.Obj(TEXT("InPreset"), Preset);
		Call.Invoke();
	}
	UObject* Config = nullptr;
	{
		UALReflect::FCall Call(Job, TEXT("GetConfiguration"));
		if (Call.Invoke())
		{
			Config = Call.OutObject(TEXT("ReturnValue"));
		}
	}
	if (!Config)
	{
		UAL_CommandUtils::SendError(RequestId, 500, TEXT("拿不到渲染任务的配置"));
		return;
	}

	// ---- 渲染通道与画质 ----
	if (!Preset)
	{
		if (!UALR::FindOrAddSetting(Config, PassClass))
		{
			UAL_CommandUtils::SendError(RequestId, 500, TEXT("加不上渲染通道"));
			return;
		}
		UObject* AA = UALR::FindOrAddSetting(Config, AAClass);
		if (AA)
		{
			UALReflect::SetIntProp(AA, TEXT("SpatialSampleCount"), QualityPreset.Spatial);
			UALReflect::SetIntProp(AA, TEXT("TemporalSampleCount"), QualityPreset.Temporal);
			UALR::SetBool(AA, TEXT("bOverrideAntiAliasing"), QualityPreset.bOverrideAAToNone);
			if (QualityPreset.bOverrideAAToNone)
			{
				UALR::SetByte(AA, TEXT("AntiAliasingMethod"), 0 /* AAM_None */);
			}
			UALReflect::SetIntProp(AA, TEXT("EngineWarmUpCount"), QualityPreset.EngineWarmUp);
			UALR::SetBool(AA, TEXT("bRenderWarmUpFrames"), QualityPreset.RenderWarmUp > 0);
			UALReflect::SetIntProp(AA, TEXT("RenderWarmUpCount"), QualityPreset.RenderWarmUp);
			UALR::SetBool(AA, TEXT("bUseCameraCutForWarmUp"), false);
		}
	}

	// ---- 输出格式：预设上换格式时，先把预设原有的输出都摘掉 ----
	if (OutputClass)
	{
		if (Preset)
		{
			for (UObject* Existing : UALR::SettingsOfClass(Config, UALReflect::FindScriptClass(UALR::OUTPUT_BASE_CLASS)))
			{
				UALR::RemoveSetting(Config, Existing);
			}
		}
		if (!UALR::FindOrAddSetting(Config, OutputClass))
		{
			UAL_CommandUtils::SendError(RequestId, 500, FString::Printf(TEXT("加不上 %s 输出"), *Format));
			return;
		}
	}

	// ---- 输出设置 ----
	UObject* Output = UALR::FindOrAddSetting(Config, OutputSettingClass);
	if (!Output)
	{
		UAL_CommandUtils::SendError(RequestId, 500, TEXT("拿不到输出设置"));
		return;
	}
	UALR::SetDirectoryPath(Output, TEXT("OutputDirectory"), OutputDir);
	UALR::SetBool(Output, TEXT("bOverrideExistingOutput"), true);
	const TArray<TSharedPtr<FJsonValue>>* ResArray = nullptr;
	if (Payload->TryGetArrayField(TEXT("resolution"), ResArray) && ResArray && ResArray->Num() == 2)
	{
		UALR::SetIntPoint(Output, TEXT("OutputResolution"),
			FIntPoint(static_cast<int32>((*ResArray)[0]->AsNumber()), static_cast<int32>((*ResArray)[1]->AsNumber())));
	}
	if (bStartGiven || bEndGiven)
	{
		UALR::SetBool(Output, TEXT("bUseCustomPlaybackRange"), true);
		UALReflect::SetIntProp(Output, TEXT("CustomStartFrame"), FrameStart);
		UALReflect::SetIntProp(Output, TEXT("CustomEndFrame"), FrameEnd);
	}

	// ---- 执行器 ----
	UObject* Executor = NewObject<UObject>(GetTransientPackage(), ExecutorClass, NAME_None, RF_Transient);
	UUAL_RenderListener* Listener = NewObject<UUAL_RenderListener>(GetTransientPackage(), NAME_None, RF_Transient);
	if (!UALR::BindExecutorDelegates(Executor, Listener))
	{
		UAL_CommandUtils::SendError(RequestId, 500, TEXT("挂不上 MRQ 执行器的完成回调"));
		return;
	}

	UALR::GJob = MakeUnique<UALR::FRenderJob>();
	UALR::GJob->JobId = FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphens).ToLower();
	UALR::GJob->OutputDir = OutputDir;
	UALR::GJob->StartedAtUtc = FDateTime::UtcNow();
	UALR::GJob->StartSeconds = FPlatformTime::Seconds();
	UALR::GJob->Queue.Reset(Queue);
	UALR::GJob->Executor.Reset(Executor);
	UALR::GJob->Listener.Reset(Listener);

	UALR::RaiseUnattended();

	// 5.6+ 走子系统：用我们的私有队列，同时让 MRQ 窗口知道有渲染在跑
	bool bSubmitted = false;
	if (Subsystem && Subsystem->FindFunction(TEXT("RenderQueueInstanceWithExecutorInstance")))
	{
		UALReflect::FCall Call(Subsystem, TEXT("RenderQueueInstanceWithExecutorInstance"));
		Call.Obj(TEXT("InQueue"), Queue).Obj(TEXT("InExecutor"), Executor);
		bSubmitted = Call.Invoke();
	}
	if (!bSubmitted)
	{
		UALReflect::FCall Call(Executor, TEXT("Execute"));
		Call.Obj(TEXT("InPipelineQueue"), Queue);
		bSubmitted = Call.Invoke();
		if (!bSubmitted)
		{
			UALR::RestoreUnattended();
			const FString Err = Call.GetError();
			UALR::GJob.Reset();
			UAL_CommandUtils::SendError(RequestId, 500, FString::Printf(TEXT("MRQ 没能开始渲染：%s"), *Err));
			return;
		}
	}

	// 地图 / 序列有问题时执行器在 Execute 里就同步广播了完成
	if (UALR::GJob->State != UALR::ERenderState::Rendering)
	{
		UAL_CommandUtils::SendError(RequestId, 500,
			FString::Printf(TEXT("MRQ 没能开始渲染：%s"), UALR::GJob->Error.IsEmpty() ? TEXT("没有给出原因，看输出日志") : *UALR::GJob->Error),
			UALR::StatusJson(*UALR::GJob));
		return;
	}

	// ---- 回包：从配置里读回来，不回显入参 ----
	const FIntPoint Resolution = UALR::GetIntPoint(Output, TEXT("OutputResolution"), FIntPoint(1920, 1080));
	int32 RangeStart = PlayStart, RangeEnd = PlayEnd;
	if (UALR::GetBool(Output, TEXT("bUseCustomPlaybackRange")))
	{
		RangeStart = UALR::GetInt(Output, TEXT("CustomStartFrame"), PlayStart);
		RangeEnd = UALR::GetInt(Output, TEXT("CustomEndFrame"), PlayEnd);
	}

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("job_id"), UALR::GJob->JobId);
	Data->SetStringField(TEXT("sequence_path"), SequenceSoftPath.GetLongPackageName());
	Data->SetStringField(TEXT("map_path"), MapPackage);
	Data->SetStringField(TEXT("output_dir"), OutputDir);
	{
		// 格式按配置里实际的输出类报，预设没换格式时也对
		TArray<FString> Formats;
		for (UObject* Out : UALR::SettingsOfClass(Config, UALReflect::FindScriptClass(UALR::OUTPUT_BASE_CLASS)))
		{
			for (const TCHAR* Candidate : { TEXT("png"), TEXT("jpg"), TEXT("bmp"), TEXT("exr"), TEXT("mp4") })
			{
				UClass* Cls = UALR::FindOutputClass(Candidate);
				if (Cls && Out->GetClass() == Cls)
				{
					Formats.AddUnique(FString(Candidate));
				}
			}
		}
		Data->SetStringField(TEXT("format"), Formats.Num() > 0 ? FString::Join(Formats, TEXT("+")) : Format);
	}
	TArray<TSharedPtr<FJsonValue>> Res = { MakeShared<FJsonValueNumber>(Resolution.X), MakeShared<FJsonValueNumber>(Resolution.Y) };
	Data->SetArrayField(TEXT("resolution"), Res);
	Data->SetStringField(TEXT("renderer"), Preset ? TEXT("preset") : *Renderer);
	Data->SetStringField(TEXT("quality"), Preset ? TEXT("preset") : *Quality);
	TArray<TSharedPtr<FJsonValue>> Range = { MakeShared<FJsonValueNumber>(RangeStart), MakeShared<FJsonValueNumber>(RangeEnd) };
	Data->SetArrayField(TEXT("frame_range"), Range);
	if (Preset)
	{
		Data->SetStringField(TEXT("preset_path"), Preset->GetPathName());
	}
	if (Warnings.Num() > 0)
	{
		TArray<TSharedPtr<FJsonValue>> W;
		for (const FString& S : Warnings)
		{
			W.Add(MakeShared<FJsonValueString>(S));
		}
		Data->SetArrayField(TEXT("warnings"), W);
	}

	UE_LOG(LogUALRender, Log, TEXT("Render job %s started: %s -> %s"), *UALR::GJob->JobId, *SequencePath, *OutputDir);
	UAL_CommandUtils::SendResponse(RequestId, 200, Data);
}

// ============================================================================
// sequence.render_status
// ============================================================================

void FUAL_RenderCommands::Handle_Status(const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
{
	FString JobId;
	Payload->TryGetStringField(TEXT("job_id"), JobId);

	if (!UALR::GJob.IsValid() || (!JobId.IsEmpty() && JobId != UALR::GJob->JobId))
	{
		TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
		Data->SetStringField(TEXT("job_id"), JobId);
		Data->SetStringField(TEXT("state"), TEXT("none"));
		Data->SetNumberField(TEXT("progress"), 0);
		Data->SetNumberField(TEXT("output_frame"), 0);
		Data->SetNumberField(TEXT("total_frames"), 0);
		Data->SetNumberField(TEXT("elapsed_seconds"), 0);
		Data->SetStringField(TEXT("output_dir"), TEXT(""));
		// 编辑器重启过、或者盒子拿着别的 job_id —— 这次任务的记录已经不在了
		Data->SetStringField(TEXT("error"), TEXT("编辑器里没有这个渲染任务（编辑器可能重启过）"));
		UAL_CommandUtils::SendResponse(RequestId, 200, Data);
		return;
	}

	UAL_CommandUtils::SendResponse(RequestId, 200, UALR::StatusJson(*UALR::GJob));
}

// ============================================================================
// sequence.render_cancel
// ============================================================================

void FUAL_RenderCommands::Handle_Cancel(const TSharedPtr<FJsonObject>& Payload, const FString RequestId)
{
	FString JobId;
	Payload->TryGetStringField(TEXT("job_id"), JobId);

	TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
	if (!UALR::GJob.IsValid() || (!JobId.IsEmpty() && JobId != UALR::GJob->JobId) || UALR::GJob->State != UALR::ERenderState::Rendering)
	{
		Data->SetBoolField(TEXT("canceled"), false);
		Data->SetStringField(TEXT("state"), UALR::GJob.IsValid() ? UALR::StateName(UALR::GJob->State) : TEXT("none"));
		UAL_CommandUtils::SendResponse(RequestId, 200, Data);
		return;
	}

	UALR::GJob->bCancelRequested = true;
	if (UObject* Executor = UALR::GJob->Executor.Get())
	{
		UALReflect::FCall Call(Executor, TEXT("CancelAllJobs"));
		Call.Invoke();
	}
	// 完成回调会把状态改成 canceled；这里回的是「请求已发出」时的样子
	Data->SetBoolField(TEXT("canceled"), true);
	Data->SetStringField(TEXT("state"), UALR::StateName(UALR::GJob->State));
	UAL_CommandUtils::SendResponse(RequestId, 200, Data);
}
