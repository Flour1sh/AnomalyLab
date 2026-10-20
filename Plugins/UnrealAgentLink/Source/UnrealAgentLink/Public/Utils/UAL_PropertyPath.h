#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonValue.h"

/**
 * 按**路径**读写属性，穿透嵌套结构体、数组和 Instanced 子对象。
 *
 * ## 为什么需要它
 *
 * 我们原来的属性设置只能改对象顶层的标量。可 UE 里真正要配的东西经常埋在好几层下面，
 * 比如 PCG 静态网格生成器上的树种列表：
 *
 *   MeshSelectorParameters          Instanced 子对象（UPCGMeshSelectorWeighted）
 *     .MeshEntries[0]               结构体数组
 *       .Descriptor                 结构体
 *         .StaticMesh               TSoftObjectPtr<UStaticMesh>
 *       .Weight                     int
 *
 * 够不到这一层的后果不是「少个功能」，是**整件事做不成** —— 生成器没有网格就
 * 生成不出任何东西，而工具会一路报成功，直到最后一步发现产出是 0。
 *
 * 有了路径就能一句话写完：
 *   "MeshSelectorParameters.MeshEntries[0].Descriptor.StaticMesh": "/Game/Trees/SM_Oak"
 *   "MeshSelectorParameters.MeshEntries[0].Weight": 5
 *
 * ## 数组会自动扩容
 *
 * 写 `MeshEntries[3]` 时数组只有 1 个元素，会补到 4 个（新元素是默认值）。
 * 不这么做的话调用方得先想办法把数组撑大，而「撑大数组」本身没有接口。
 *
 * ## 叶子值统一走 ImportText
 *
 * 不为每种属性类型写一遍转换，而是把 JSON 值转成 UE 的文本表示再交给
 * `FProperty::ImportText` —— 引擎自己认得所有类型，包括枚举、软引用、FVector
 * 这类结构体字面量。少写几百行，也不会漏类型。
 */
namespace UALPropertyPath
{
	/**
	 * 按路径写一个值。
	 *
	 * @param Root  起点对象
	 * @param Path  形如 `A`、`A.B`、`A.B[2].C`。段名必须和 C++ 里的 UPROPERTY 名逐字一致
	 * @param Value JSON 值。数字/布尔/字符串直接用；对象和数组会序列化成 UE 的文本字面量
	 * @param OutError 失败原因，已经是给模型看的完整句子（含"你是不是想写 XXX"）
	 */
	bool SetByPath(UObject* Root, const FString& Path, const TSharedPtr<FJsonValue>& Value, FString& OutError);

	/** 按路径读一个值。路径不存在时返回 nullptr 并填 OutError */
	TSharedPtr<FJsonValue> GetByPath(const UObject* Root, const FString& Path, FString& OutError);

	/**
	 * 同 SetByPath，但起点是一块结构体内存而不是对象。
	 *
	 * DataTable 的一行就是这样一块内存（`FindRowUnchecked` 拿到的 uint8*），
	 * 不是 UObject，走不了 SetByPath。
	 *
	 * @param RootOwner 这块内存归哪个对象管。写之前对它 Modify（进撤销），
	 *                  也作为 ImportText 解析对象引用时的外层。可以为空
	 */
	bool SetInStruct(
		const UStruct* RootStruct,
		void* RootData,
		UObject* RootOwner,
		const FString& Path,
		const TSharedPtr<FJsonValue>& Value,
		FString& OutError);

	/** 同 GetByPath，起点是一块结构体内存 */
	TSharedPtr<FJsonValue> GetInStruct(const UStruct* RootStruct, const void* RootData, const FString& Path, FString& OutError);

	/**
	 * 列出某个容器下所有可写字段的名字，用来拼「你是不是想写 XXX」。
	 * Path 为空表示列 Root 自己的顶层字段。
	 */
	void ListWritableFields(const UObject* Root, const FString& Path, TArray<FString>& OutNames);

	/**
	 * 把一个对象的可编辑属性**连同嵌套结构、数组、Instanced 子对象**一起铺平成
	 * 「路径 → 值」的映射。返回的键可以直接喂回 SetByPath。
	 *
	 * ## 为什么必须能读全
	 *
	 * 写得进去、读不出来，等于不敢重写。实测里就发生过：生成器上配了 12 个树种，
	 * 但工具只报得出 weight、报不出 mesh 路径，于是不敢用整图重建，只能绕路
	 * 「加节点 + 断旧边 + 重连」，多花好几轮。
	 * 能完整读出来，「读回来 → 改两个字段 → 整图写回去」才是安全的。
	 *
	 * @param MaxDepth 递归深度上限。UE 的对象图能绕回去，没有上限会走不完
	 * @param MaxEntries 条目上限。一个 settings 对象铺平后可能上百条，全塞给模型是浪费
	 */
	void FlattenProperties(
		const UObject* Root,
		TMap<FString, TSharedPtr<FJsonValue>>& OutValues,
		int32 MaxDepth = 4,
		int32 MaxEntries = 200);

	/**
	 * 同上，但起点是一块结构体内存而不是对象。
	 *
	 * 动画节点的设置全在节点对象上那个 `Node` 结构体里；从对象铺的话会连
	 * 引脚显隐表之类的编辑器字段一起铺出来，把真正的设置淹掉。
	 */
	void FlattenStruct(
		const UStruct* Struct,
		const void* Data,
		TMap<FString, TSharedPtr<FJsonValue>>& OutValues,
		int32 MaxDepth = 4,
		int32 MaxEntries = 200);
}
