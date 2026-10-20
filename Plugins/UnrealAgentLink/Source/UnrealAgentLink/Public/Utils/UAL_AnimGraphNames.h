#pragma once

#include "CoreMinimal.h"

/**
 * 动画蓝图里那几处「名字 ↔ 意思」的翻译，纯字符串，不碰引擎对象。
 *
 * 单独拆出来是为了能被自动化测试跑到（Tests/UAL_AnimGraphNamesTests.cpp）——
 * 图路径怎么切、转换那一段怎么认、引脚名末尾的序号怎么解，这些一旦写错，
 * 表现是「找不到图」「找不到引脚」，离真正的原因隔着好几层。
 *
 * 设计见 docs/动画蓝图编辑设计-2026-10-08.md。
 */
namespace UAL_AnimGraphNames
{
	/** 转换规则图下面那张自定义混合图的路径段：`Locomotion/Idle->Walk/CustomBlend` */
	inline const TCHAR* CustomBlendSegment() { return TEXT("CustomBlend"); }

	/**
	 * 图路径切段。`AnimGraph/Locomotion/Idle->Walk` → [AnimGraph, Locomotion, Idle->Walk]。
	 * 每段去掉首尾空白；`->` 两边的空格也去掉（`Idle -> Walk` 和 `Idle->Walk` 是同一条）。
	 */
	inline TArray<FString> SplitPath(const FString& Path)
	{
		TArray<FString> Raw;
		Path.ParseIntoArray(Raw, TEXT("/"), /*InCullEmpty=*/true);
		TArray<FString> Out;
		for (FString Segment : Raw)
		{
			Segment.TrimStartAndEndInline();
			while (Segment.Contains(TEXT(" ->")))
			{
				Segment.ReplaceInline(TEXT(" ->"), TEXT("->"));
			}
			while (Segment.Contains(TEXT("-> ")))
			{
				Segment.ReplaceInline(TEXT("-> "), TEXT("->"));
			}
			if (!Segment.IsEmpty())
			{
				Out.Add(Segment);
			}
		}
		return Out;
	}

	/** 一段路径是不是转换（`A->B` 或 `A->B#2`）。拆出两端状态名和第几条 */
	inline bool ParseTransitionSegment(const FString& Segment, FString& OutFrom, FString& OutTo, int32& OutOrdinal)
	{
		FString From, Rest;
		if (!Segment.Split(TEXT("->"), &From, &Rest))
		{
			return false;
		}
		OutOrdinal = 1;
		FString To = Rest;
		FString OrdinalText;
		if (Rest.Split(TEXT("#"), &To, &OrdinalText, ESearchCase::CaseSensitive, ESearchDir::FromEnd))
		{
			if (!OrdinalText.IsNumeric())
			{
				return false;
			}
			OutOrdinal = FMath::Max(1, FCString::Atoi(*OrdinalText));
		}
		OutFrom = From.TrimStartAndEnd();
		OutTo = To.TrimStartAndEnd();
		return !OutFrom.IsEmpty() && !OutTo.IsEmpty();
	}

	/** 反过来拼。第一条不带序号，第二条起 `#2` */
	inline FString MakeTransitionSegment(const FString& From, const FString& To, int32 Ordinal)
	{
		return Ordinal > 1
			? FString::Printf(TEXT("%s->%s#%d"), *From, *To, Ordinal)
			: FString::Printf(TEXT("%s->%s"), *From, *To);
	}

	/**
	 * 引脚名末尾的数组序号：`BlendPose_2` → (BlendPose, 2)。
	 * 「多加一个输入」那类节点（按整数混合、分层混合）靠它判断要补到第几个。
	 */
	inline bool ParseIndexedPinName(const FString& PinName, FString& OutBase, int32& OutIndex)
	{
		FString Base, IndexText;
		if (!PinName.Split(TEXT("_"), &Base, &IndexText, ESearchCase::CaseSensitive, ESearchDir::FromEnd))
		{
			return false;
		}
		if (Base.IsEmpty() || IndexText.IsEmpty() || !IndexText.IsNumeric())
		{
			return false;
		}
		OutBase = Base;
		OutIndex = FCString::Atoi(*IndexText);
		return OutIndex >= 0;
	}

	/** 节点类型名的比较形式：去下划线、空格，转小写（`blend_poses_by_bool` = `BlendPosesByBool`） */
	inline FString NormalizeTypeName(const FString& Raw)
	{
		return Raw.Replace(TEXT("_"), TEXT("")).Replace(TEXT(" "), TEXT("")).ToLower();
	}

	/**
	 * 编辑器菜单里的叫法 ↔ 引擎类名，只收**两边对不上**的那几个。
	 * 名字本来就一致的（SequencePlayer、Slot、TwoBoneIK…）不用登记，
	 * 解析时直接补 `AnimGraphNode_` 前缀去找。
	 */
	struct FAlias
	{
		const TCHAR* WriteAs;
		const TCHAR* ClassName;
	};

	inline TArrayView<const FAlias> Aliases()
	{
		static const FAlias Table[] = {
			{ TEXT("BlendPosesByBool"), TEXT("AnimGraphNode_BlendListByBool") },
			{ TEXT("BlendPosesByInt"), TEXT("AnimGraphNode_BlendListByInt") },
			{ TEXT("BlendPosesByEnum"), TEXT("AnimGraphNode_BlendListByEnum") },
			{ TEXT("LayeredBlendPerBone"), TEXT("AnimGraphNode_LayeredBoneBlend") },
			{ TEXT("AimOffset"), TEXT("AnimGraphNode_RotationOffsetBlendSpace") },
			{ TEXT("AimOffsetGraph"), TEXT("AnimGraphNode_RotationOffsetBlendSpaceGraph") },
			{ TEXT("BlendMulti"), TEXT("AnimGraphNode_MultiWayBlend") },
			{ TEXT("InputPose"), TEXT("AnimGraphNode_LinkedInputPose") },
		};
		return MakeArrayView(Table);
	}

	/** 写法 → 类名。不在表里返回空串 */
	inline FString ClassNameForAlias(const FString& Type)
	{
		const FString Wanted = NormalizeTypeName(Type);
		for (const FAlias& Alias : Aliases())
		{
			if (NormalizeTypeName(Alias.WriteAs) == Wanted)
			{
				return Alias.ClassName;
			}
		}
		return FString();
	}

	/**
	 * 类名 → 写回去用的名字：有别名用别名，没有就去掉 `AnimGraphNode_` 前缀。
	 * 读图回的 `write_as` 就是它，原样填回 `class` 能重建出同一个节点。
	 */
	inline FString WriteAsForClassName(const FString& ClassName)
	{
		for (const FAlias& Alias : Aliases())
		{
			if (ClassName.Equals(Alias.ClassName, ESearchCase::IgnoreCase))
			{
				return Alias.WriteAs;
			}
		}
		static const FString Prefix = TEXT("AnimGraphNode_");
		return ClassName.StartsWith(Prefix) ? ClassName.Mid(Prefix.Len()) : ClassName;
	}

	/**
	 * 转换规则里「播放进度」那类取值节点（编辑器里叫 Time Remaining (ratio) 那些）。
	 * `Index` 对应引擎 ETransitionGetter::Type 的取值 —— 九个版本都是这个顺序。
	 */
	struct FGetter
	{
		const TCHAR* Name;
		int32 Index;
		/** 要不要绑一个动画播放节点（剩余时间、进度这几个） */
		bool bNeedsAssetPlayer;
		/** 要不要指定一个状态（任意状态的混合权重） */
		bool bNeedsState;
	};

	inline TArrayView<const FGetter> Getters()
	{
		static const FGetter Table[] = {
			{ TEXT("CurrentTime"), 0, true, false },
			{ TEXT("Length"), 1, true, false },
			{ TEXT("CurrentTimeRatio"), 2, true, false },
			{ TEXT("TimeRemaining"), 3, true, false },
			{ TEXT("TimeRemainingRatio"), 4, true, false },
			{ TEXT("ElapsedStateTime"), 5, false, false },
			{ TEXT("StateWeight"), 6, false, false },
			{ TEXT("TransitionDuration"), 7, false, false },
			{ TEXT("BlendWeight"), 8, false, true },
		};
		return MakeArrayView(Table);
	}

	/**
	 * `TimeRemainingRatio` / `TimeRemainingRatio:Run_Fwd` / `BlendWeight:Walk` 拆成取值种类和它绑的对象。
	 * 冒号后面那半可以省（这个状态里只有一个动画播放节点时）。
	 */
	inline const FGetter* ParseGetter(const FString& MemberName, FString& OutTarget)
	{
		FString Kind = MemberName;
		OutTarget.Reset();
		FString Left, Right;
		if (MemberName.Split(TEXT(":"), &Left, &Right))
		{
			Kind = Left;
			OutTarget = Right.TrimStartAndEnd();
		}
		const FString Wanted = NormalizeTypeName(Kind);
		for (const FGetter& Getter : Getters())
		{
			if (NormalizeTypeName(Getter.Name) == Wanted)
			{
				return &Getter;
			}
		}
		return nullptr;
	}

	inline const FGetter* GetterByIndex(int32 Index)
	{
		for (const FGetter& Getter : Getters())
		{
			if (Getter.Index == Index)
			{
				return &Getter;
			}
		}
		return nullptr;
	}

	inline FString GetterNameList()
	{
		TArray<FString> Names;
		for (const FGetter& Getter : Getters())
		{
			Names.Add(Getter.Name);
		}
		return FString::Join(Names, TEXT(", "));
	}
}
