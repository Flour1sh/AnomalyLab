#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"

#include "UAL_RenderListener.generated.h"

/**
 * 接 MRQ 执行器的两条动态多播：渲完、出错。
 *
 * ## 为什么要一个 UCLASS
 *
 * 我们不链接 MRQ（见 `UAL_ReflectCall.h` 开头），所以只能在运行时往执行器的
 * `OnExecutorFinishedDelegate` / `OnExecutorErroredDelegate` 上挂一个
 * `FScriptDelegate`，而它只认「某个 UObject 上的某个 UFUNCTION」。
 *
 * 不挂、改成轮询 `IsRendering()` 不行：它在 PIE 真正起来之前一直是 false
 * （`bIsRendering` 在 `OnPIEStartupFinished` 里才置位），刚开始就查会以为已经渲完；
 * 而地图 / 序列无效时执行器在 `Execute` 里**同步**广播完成，轮询根本看不到那一下。
 *
 * ## 形参为什么写 UObject*
 *
 * 引擎声明的是 `UMoviePipelineExecutorBase*` / `UMoviePipeline*`，那两个类型我们
 * 不能 include。广播时引擎按委托签名排好参数缓冲，再按名字找到这里的函数
 * `ProcessEvent` —— 只要逐个形参的大小和对齐一样就能对上，而指针都是 8 字节。
 * 顺序和个数必须和引擎的委托逐个对应（5.0–5.8 没变过）：
 *   FOnMoviePipelineExecutorFinished(PipelineExecutor, bSuccess)
 *   FOnMoviePipelineExecutorErrored(PipelineExecutor, PipelineWithError, bIsFatal, ErrorText)
 */
UCLASS(Transient)
class UUAL_RenderListener : public UObject
{
	GENERATED_BODY()

public:
	UFUNCTION()
	void HandleExecutorFinished(UObject* PipelineExecutor, bool bSuccess);

	UFUNCTION()
	void HandleExecutorErrored(UObject* PipelineExecutor, UObject* PipelineWithError, bool bIsFatal, FText ErrorText);
};
