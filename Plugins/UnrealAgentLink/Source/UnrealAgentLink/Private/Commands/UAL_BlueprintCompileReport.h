#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

class UBlueprint;
class UEdGraphNode;

/**
 * 完整编译一次蓝图，把结果写进回执：`compiled` / `compile_error_count` /
 * `compile_warning_count` / `diagnostics`。
 *
 * 诊断按**调用方给的 id** 回（`node`），同时带引擎 GUID（`node_id`）和节点所在的
 * 图路径（`graph`）—— 动画蓝图的报错常常落在状态机里某一层的子图上，
 * 不说在哪一页，调用方拿着 id 也找不到地方改。
 *
 * 必须在事务**之外**调，理由见 Handle_CreateGraphDeclarative 里「编译必须在事务之外」那段。
 * 实现在 UAL_BlueprintCommands.cpp。
 */
void UAL_CompileAndReport(
	UBlueprint* Blueprint,
	const TMap<UEdGraphNode*, FString>& NodeToCallerId,
	const TSharedPtr<FJsonObject>& Result);
