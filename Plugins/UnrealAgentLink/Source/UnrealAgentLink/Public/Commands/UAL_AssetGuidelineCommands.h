#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

/**
 * 资产指南（UAssetGuideline）命令
 *
 * 有的资产自带一张「使用说明」：要求工程开某些设置、某些插件（CitySample 的车、人群
 * 就要虚拟纹理、16 位骨骼索引……）。编辑器每加载到一张，就拿它和工程设置比一遍，
 * 对不上弹「缺失项目设置！」。这组命令把同一件事做成能查、能改、能读回的：
 *
 * - project.check_asset_guidelines：找出说明并逐项比对（可先扫给定目录里的包）
 * - project.apply_asset_guidelines：把没满足的工程设置写进工程的 Default*.ini 并读回
 *
 * 插件那一项不在这里改：盒子侧调已有的 system.manage_plugin（带落盘回读）。
 */
class FUAL_AssetGuidelineCommands
{
public:
	using FHandlerFunc = TFunction<void(const TSharedPtr<FJsonObject>&, const FString)>;

	static void RegisterCommands(TMap<FString, FHandlerFunc>& CommandMap);

	static void Handle_Check(const TSharedPtr<FJsonObject>& Payload, const FString RequestId);
	static void Handle_Apply(const TSharedPtr<FJsonObject>& Payload, const FString RequestId);
};
