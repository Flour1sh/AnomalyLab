#include "UAL_AnimGraphNames.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUALAnimGraphNamesTest,
    "UnrealAgentLink.Blueprint.AnimGraphNames",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUALAnimGraphNamesTest::RunTest(const FString& Parameters)
{
    // 图路径切段：空段丢掉，`->` 两边的空格不算数
    {
        const TArray<FString> Segments = UAL_AnimGraphNames::SplitPath(TEXT("AnimGraph/ Locomotion /Idle -> Walk/"));
        TestEqual(TEXT("segment count"), Segments.Num(), 3);
        if (Segments.Num() == 3)
        {
            TestEqual(TEXT("top"), Segments[0], FString(TEXT("AnimGraph")));
            TestEqual(TEXT("state machine"), Segments[1], FString(TEXT("Locomotion")));
            TestEqual(TEXT("transition spacing"), Segments[2], FString(TEXT("Idle->Walk")));
        }
    }

    // 转换段：两端状态名 + 第几条
    {
        FString From, To;
        int32 Ordinal = 0;
        TestTrue(TEXT("plain transition"), UAL_AnimGraphNames::ParseTransitionSegment(TEXT("Idle->Walk"), From, To, Ordinal));
        TestEqual(TEXT("from"), From, FString(TEXT("Idle")));
        TestEqual(TEXT("to"), To, FString(TEXT("Walk")));
        TestEqual(TEXT("first by default"), Ordinal, 1);

        TestTrue(TEXT("second transition"), UAL_AnimGraphNames::ParseTransitionSegment(TEXT("Idle->Walk#2"), From, To, Ordinal));
        TestEqual(TEXT("ordinal"), Ordinal, 2);
        TestEqual(TEXT("to without ordinal"), To, FString(TEXT("Walk")));

        TestFalse(TEXT("state name is not a transition"), UAL_AnimGraphNames::ParseTransitionSegment(TEXT("Idle"), From, To, Ordinal));
        TestFalse(TEXT("missing target"), UAL_AnimGraphNames::ParseTransitionSegment(TEXT("Idle->"), From, To, Ordinal));
        TestFalse(TEXT("non-numeric ordinal"), UAL_AnimGraphNames::ParseTransitionSegment(TEXT("Idle->Walk#x"), From, To, Ordinal));

        TestEqual(TEXT("round trip first"), UAL_AnimGraphNames::MakeTransitionSegment(TEXT("Idle"), TEXT("Walk"), 1), FString(TEXT("Idle->Walk")));
        TestEqual(TEXT("round trip second"), UAL_AnimGraphNames::MakeTransitionSegment(TEXT("Idle"), TEXT("Walk"), 2), FString(TEXT("Idle->Walk#2")));
    }

    // 引脚序号：多输入节点靠它判断要补到第几个
    {
        FString Base;
        int32 Index = -1;
        TestTrue(TEXT("indexed pin"), UAL_AnimGraphNames::ParseIndexedPinName(TEXT("BlendPose_2"), Base, Index));
        TestEqual(TEXT("base"), Base, FString(TEXT("BlendPose")));
        TestEqual(TEXT("index"), Index, 2);
        TestFalse(TEXT("plain pin"), UAL_AnimGraphNames::ParseIndexedPinName(TEXT("Pose"), Base, Index));
        TestFalse(TEXT("non-numeric suffix"), UAL_AnimGraphNames::ParseIndexedPinName(TEXT("Blend_Pose"), Base, Index));
    }

    // 别名两头都认，读回的 write_as 能原样写回去
    {
        TestEqual(TEXT("alias to class"), UAL_AnimGraphNames::ClassNameForAlias(TEXT("blend_poses_by_bool")), FString(TEXT("AnimGraphNode_BlendListByBool")));
        TestEqual(TEXT("unknown alias"), UAL_AnimGraphNames::ClassNameForAlias(TEXT("SequencePlayer")), FString());
        TestEqual(TEXT("class to alias"), UAL_AnimGraphNames::WriteAsForClassName(TEXT("AnimGraphNode_LayeredBoneBlend")), FString(TEXT("LayeredBlendPerBone")));
        TestEqual(TEXT("class without alias drops prefix"), UAL_AnimGraphNames::WriteAsForClassName(TEXT("AnimGraphNode_SequencePlayer")), FString(TEXT("SequencePlayer")));
    }

    // 转换取值节点
    {
        FString Target;
        const UAL_AnimGraphNames::FGetter* Getter = UAL_AnimGraphNames::ParseGetter(TEXT("TimeRemainingRatio"), Target);
        TestNotNull(TEXT("getter by name"), Getter);
        if (Getter)
        {
            TestEqual(TEXT("engine index"), Getter->Index, 4);
            TestTrue(TEXT("needs a player"), Getter->bNeedsAssetPlayer);
        }
        TestTrue(TEXT("no target"), Target.IsEmpty());

        Getter = UAL_AnimGraphNames::ParseGetter(TEXT("blend_weight: Walk"), Target);
        TestNotNull(TEXT("getter with target"), Getter);
        TestEqual(TEXT("target"), Target, FString(TEXT("Walk")));
        TestNull(TEXT("unknown getter"), UAL_AnimGraphNames::ParseGetter(TEXT("Speed"), Target));
        TestEqual(TEXT("by index"), FString(UAL_AnimGraphNames::GetterByIndex(7)->Name), FString(TEXT("TransitionDuration")));
    }

    return true;
}

#endif
