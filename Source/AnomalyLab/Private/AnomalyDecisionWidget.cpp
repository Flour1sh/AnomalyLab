#include "AnomalyDecisionWidget.h"
#include "Components/TextBlock.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/CanvasPanel.h"
#include "Components/Image.h"
#include "Blueprint/WidgetTree.h"

void UAnomalyDecisionWidget::PresentDecision(int32 Money, int32 Rounds, int32 Threats, bool bCanContinue)
{
    if (!StatusText) return;
    const FString Prompt = bCanContinue ? TEXT("[1] 继续    [2] 撤离") : TEXT("已完成第二次收容\n[2] 撤离");
    StatusText->SetText(FText::FromString(FString::Printf(
        TEXT("当前收益  $%d\n完成回合  %d    成功收容  %d\n\n%s"), Money, Rounds, Threats, *Prompt)));
    SetVisibility(ESlateVisibility::HitTestInvisible);
}

void UAnomalyDecisionWidget::PresentTerminal(int32 Money, int32 Rounds, int32 Threats, float Seconds,
    bool bCashedOut, bool bError)
{
    if (!StatusText) return;
    const TCHAR* Title = bError ? TEXT("原型运行异常") : bCashedOut ? TEXT("撤离成功") : TEXT("行动失败");
    const FString MoneyLine = bError ? FString::Printf(TEXT("当前金额  $%d\n本次带出  $0"), Money)
        : bCashedOut ? FString::Printf(TEXT("本次带出  $%d"), Money)
        : FString::Printf(TEXT("损失金额  $%d\n本次带出  $0"), Money);
    StatusText->SetText(FText::FromString(FString::Printf(
        TEXT("%s\n%s\n完成回合  %d    成功收容  %d\n本局用时  %.0f 秒\n\n[R] 重新开始"),
        Title, *MoneyLine, Rounds, Threats, Seconds)));
    SetVisibility(ESlateVisibility::HitTestInvisible);
}

void UAnomalyDecisionWidget::AppendItems(const FString& Items)
{
    if (!StatusText) return;
    if (WidgetTree && !WidgetTree->FindWidget(TEXT("ExplorationTerminalBacking")))
    {
        if (UCanvasPanel* Canvas = Cast<UCanvasPanel>(WidgetTree->RootWidget))
        {
            UImage* Backing = WidgetTree->ConstructWidget<UImage>(UImage::StaticClass(), TEXT("ExplorationTerminalBacking"));
            Backing->SetColorAndOpacity(FLinearColor(.006f,.012f,.014f,.96f));
            UCanvasPanelSlot* BackingSlot = Canvas->AddChildToCanvas(Backing);
            BackingSlot->SetAnchors(FAnchors(.5f,.5f)); BackingSlot->SetAlignment(FVector2D(.5,.5));
            BackingSlot->SetPosition(FVector2D::ZeroVector); BackingSlot->SetSize(FVector2D(1100,620)); BackingSlot->SetZOrder(-1);
        }
    }
    FSlateFontInfo Font = StatusText->GetFont(); Font.Size = 26; StatusText->SetFont(Font);
    StatusText->SetAutoWrapText(true);
    if (UCanvasPanelSlot* CanvasSlot = Cast<UCanvasPanelSlot>(StatusText->Slot)) CanvasSlot->SetSize(FVector2D(900,450));
    if (!Items.IsEmpty()) StatusText->SetText(FText::FromString(StatusText->GetText().ToString() + TEXT("\n物品快照：\n") + Items));
}

