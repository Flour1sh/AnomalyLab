#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

/**
 * 渲染出片：用 Movie Render Queue 把一条 Level Sequence 渲成文件。
 *
 * ## 三条命令
 *
 *   - `sequence.render`         开始。参数校验、建任务、起 PIE 渲染，立刻回包
 *   - `sequence.render_status`  查进度；渲完之后扫盘数出写了几个文件
 *   - `sequence.render_cancel`  取消
 *
 * 一次只允许一个任务。盒子那边的 `sequence_render`（`ue-sequencer/render.ts`）
 * 把三条收成一个工具：开始、轮询、按停止时取消。JSON 形状与那个文件的
 * `RenderStartOutput` / `RenderStatusOutput` 逐字对应。
 *
 * ## 全程反射，不链接 MRQ
 *
 * MRQ 是可选插件，链接它会让用户工程没开 MRQ 时整个 UnrealAgentLink 加载失败
 * （理由见 `UAL_ReflectCall.h`）。每个用到的函数和属性都在 5.0–5.8 的引擎源码里
 * 逐版本核过，只有三处随版本变：
 *
 *   1. 配置类 5.2 从 `MoviePipelineMasterConfig` 改名 `MoviePipelinePrimaryConfig`。
 *      我们不按名字找它 —— 每个新任务自带一份配置，`GetConfiguration()` 拿来改就行；
 *      只有用户给了预设资产时才要认这个类，两个名字都试
 *   2. `FindOrAddSettingByClass` 5.2 多了 `bExactMatch` 形参 —— 有就传
 *   3. MP4 输出只有 5.6+ 有（`MovieRenderPipelineMP4Encoder` 模块）
 *
 * ## 用 PIE 执行器，和 MRQ 窗口的 Render (Local) 一样
 *
 * 渲的是编辑器内存里的样子，**未保存的改动也会进画面**；从没存过盘的新关卡渲不了。
 * 5.6+ 走 `MoviePipelineQueueSubsystem::RenderQueueInstanceWithExecutorInstance`，
 * 用我们自己的私有队列，又能让 MRQ 窗口知道有渲染在跑；更早的版本没有这个函数，
 * 直接 `Execute`，执行器由我们自己钉住防 GC。**不碰用户在 MRQ 窗口里排的队列。**
 *
 * ## 三个会把无人值守的渲染卡死的地方
 *
 *   - 地图或序列无效时 5.0 的 PIE 执行器会弹模态框 → 我们在开始前自己校验
 *   - 已经有 PIE 在跑时，引擎会**静默**把它结束掉再起渲染 → 我们直接拒绝
 *   - 起 PIE 前的「蓝图没编译，要编吗」「资产有编译错误，确定继续吗」模态框 →
 *     从提交到 PIE 起来这段时间置 `GIsRunningUnattendedScript`，弹框改成按默认值走
 */
class FUAL_RenderCommands
{
public:
	static void RegisterCommands(TMap<FString, TFunction<void(const TSharedPtr<FJsonObject>&, const FString)>>& CommandMap);

	static void Handle_Render(const TSharedPtr<FJsonObject>& Payload, const FString RequestId);
	static void Handle_Status(const TSharedPtr<FJsonObject>& Payload, const FString RequestId);
	static void Handle_Cancel(const TSharedPtr<FJsonObject>& Payload, const FString RequestId);

	/** `UUAL_RenderListener` 收到执行器广播后转进来 */
	static void OnExecutorFinished(bool bSuccess);
	static void OnExecutorErrored(const FString& ErrorText, bool bIsFatal);
};
