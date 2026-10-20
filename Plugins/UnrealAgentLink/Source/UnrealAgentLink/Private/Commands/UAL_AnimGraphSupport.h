#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "UObject/WeakObjectPtr.h"

class UBlueprint;
class UClass;
class UEdGraph;
class UEdGraphNode;
class UEdGraphPin;
class UPackage;

/**
 * 动画蓝图编辑：图路径、动画节点、状态机。
 *
 * 不另起一套工具 —— 读图、写图、新建蓝图三条现有命令认识动画蓝图就够了。
 * 这里是它们调进来的那部分：
 *
 *   - **图路径**：`AnimGraph/Locomotion/Idle->Walk` 定位到状态机里任意一页。
 *     转换规则图的对象名是引擎自动起的（Transition_3），只能按两端状态名认。
 *   - **动画节点**：姿势图、状态内部、转换规则都是 K2 图（动画的 schema 派生自 K2），
 *     现有的整图写入照常走，只是节点由这里建、设置由这里写。
 *   - **状态机那一页**不是 K2 图：节点是状态，一根线是一个转换。单独一个写入入口。
 *
 * 设计见 docs/动画蓝图编辑设计-2026-10-08.md。
 */
namespace UALAnimGraph
{
	/**
	 * 一次写入里对**已有对象**的改动记录，整批失败时照它写回去。
	 *
	 * 新建的节点不用记 —— 回滚把它删掉就干净了。要记的是复用的节点（同名状态、
	 * 同名状态机、图里自带的输出节点）和连线时顺手暴露了引脚的已有节点：
	 * 它们留在图里，改过的值不写回去就是「回执说没动，其实动了」。
	 */
	class FMutationLog
	{
	public:
		/** 改之前调。同一个对象的同一个属性只记第一次（那才是改动前的值） */
		void Backup(UObject* Object, FName PropertyName);
		/** 写回之后要重建引脚的节点（引脚显隐、输入个数这类改动） */
		void NoteReconstruct(UEdGraphNode* Node);
		/** 属性快照装不下的改动（入口连线、别名指向）自己带一个撤销函数，倒序执行 */
		void AddUndo(TFunction<void()> Undo);
		void Rollback();

	private:
		struct FEntry
		{
			TWeakObjectPtr<UObject> Object;
			FName Property;
			FString Text;
		};
		TArray<FEntry> Entries;
		TArray<TWeakObjectPtr<UEdGraphNode>> ToReconstruct;
		TArray<TFunction<void()>> Undos;
	};

	// ---- 图 ----

	/**
	 * 按路径找子图。路径只有一段（顶层图名）时返回 nullptr、不填错误 ——
	 * 那是调用方自己的老路径。多段但走不通时填 OutError，并列出走到的那一层有哪些子图。
	 */
	UEdGraph* FindGraphByPath(UBlueprint* Blueprint, const FString& Path, FString& OutError);

	/** 图 → 路径。顶层图就是图名；读写回执里的 graph_name 一律用它，调用方抄回来就能用 */
	FString GetGraphPath(const UEdGraph* Graph);

	/** 动画图的种类：anim_graph / state_machine / state / conduit / transition / custom_blend；不是动画图返回 nullptr */
	const TCHAR* GetGraphKind(const UEdGraph* Graph);

	bool IsStateMachineGraph(const UEdGraph* Graph);
	bool IsAnimBlueprint(const UBlueprint* Blueprint);

	/** 所有嵌套子图（状态机、状态、转换规则、折叠图），深度优先。Type 同 GetGraphKind，折叠图是 sub_graph */
	void ForEachNestedGraph(UBlueprint* Blueprint, TFunctionRef<void(UEdGraph* Graph, const FString& Path, const TCHAR* Type)> Visit);

	// ---- 姿势图 / 状态内部 / 转换规则里的节点 ----

	/**
	 * 动画这边认不认这个节点类型。返回 false 表示不归这里管，调用方接着走自己的报错；
	 * 返回 true 时 OutNode 和 OutError 二选一有值。
	 *
	 * 这里只**建**节点和找复用（输出节点、同名状态机、同名缓存姿势）。
	 * member_name 的含义（播哪段动画、缓存叫什么）在 FinishNode 里落 ——
	 * 那一步要等这一批的节点都建完，「用缓存姿势」才找得到同一批里的「存缓存姿势」。
	 */
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
		FString& OutError);

	/** 新建的动画节点按 member_name 配好。不是动画节点直接返回 true */
	bool FinishNode(UBlueprint* Blueprint, UEdGraphNode* Node, const FString& MemberName, FString& OutError);

	/**
	 * 写 `settings`：动画节点写进它的 `Node` 结构体（引脚露在外面的写到引脚上），
	 * 状态和转换写到节点自己身上。每条失败单独进 OutErrors（已带 `settings.键名` 前缀）。
	 */
	void ApplySettings(UEdGraphNode* Node, const TSharedPtr<FJsonObject>& Settings, bool bNodeIsNew, FMutationLog& Log, TArray<FString>& OutErrors);

	/**
	 * 引脚不在时，按需把它变出来：可选引脚（播放速率这类默认藏着的）就暴露，
	 * 「加一个输入」那类节点（按整数混合、分层混合）就补到那个序号。变不出来返回 nullptr。
	 */
	UEdGraphPin* RevealPin(UEdGraphNode* Node, const FString& PinName, bool bNodeIsNew, FMutationLog& Log);

	/** 「这张图是空的」判定里算骨架的节点：各类输出节点 */
	bool IsSkeletonNode(const UEdGraphNode* Node);

	/**
	 * 删掉这个节点会让哪些转换取值节点（剩余时间之类）读不到东西。
	 * clear_existing 删播放节点或状态之前问一句：引擎事后的编译报错是一句
	 * 「ICE: Player node ... was not processed」，看不出是哪条规则、为什么。没有返回空串。
	 */
	FString DescribeGetterDependents(UBlueprint* Blueprint, const UEdGraphNode* Node);

	/** 读图：write_as / member_name / settings / sub_graph。不是动画相关的节点什么都不加 */
	void AnnotateNode(UEdGraphNode* Node, const TSharedPtr<FJsonObject>& NodeObj);

	/** 报错时追加的一句：动画图里能写哪些节点类型 */
	FString DescribeNodeTypesForError(const UEdGraph* Graph);

	// ---- 状态机那一页 ----

	/** 读：状态（不带引脚）、转换、入口状态 */
	void AppendStateMachineJson(UEdGraph* Graph, const TSharedPtr<FJsonObject>& Result);

	/** 写：blueprint.create_graph 打到状态机图上时整条命令转到这里 */
	void HandleApplyStateMachine(UBlueprint* Blueprint, UEdGraph* Graph, const FString& ResolvedPath, const TSharedPtr<FJsonObject>& Payload, const FString& RequestId);

	// ---- 资产 ----

	/** 父类是不是 AnimInstance（是的话新建要走动画蓝图那条路） */
	bool IsAnimInstanceClass(const UClass* Class);

	/** 新建动画蓝图。Skeleton 可以是骨架，也可以是骨骼网格体（顺带当预览网格） */
	UBlueprint* CreateAnimBlueprint(UClass* ParentClass, UPackage* Package, FName Name, const FString& Skeleton, FString& OutError);

	/** describe 里补一段：骨架、预览网格 */
	void AppendBlueprintInfo(UBlueprint* Blueprint, const TSharedPtr<FJsonObject>& Result);

	/** search_nodes：按名字搜动画节点类，带上能写的 settings 字段 */
	void SearchAnimNodes(const FString& Query, int32 Limit, TArray<TSharedPtr<FJsonValue>>& OutResults, int32& OutTotal);
}
