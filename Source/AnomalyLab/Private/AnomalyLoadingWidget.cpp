#include "AnomalyLoadingWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/Image.h"
#include "Components/TextBlock.h"
#include "Styling/CoreStyle.h"

TSharedRef<SWidget> UAnomalyLoadingWidget::RebuildWidget()
{
    if(!WidgetTree) WidgetTree=NewObject<UWidgetTree>(this,TEXT("LoadingTree"));
    if(!WidgetTree->RootWidget)
    {
        auto Root=WidgetTree->ConstructWidget<UCanvasPanel>(); WidgetTree->RootWidget=Root;
        auto Cover=WidgetTree->ConstructWidget<UImage>(); Cover->SetColorAndOpacity(FLinearColor(.006f,.016f,.022f,1));
        auto Back=Root->AddChildToCanvas(Cover); Back->SetAnchors(FAnchors(0,0,1,1)); Back->SetOffsets(FMargin(0));
        auto Label=WidgetTree->ConstructWidget<UTextBlock>(); Label->SetText(FText::FromString(TEXT("正在加载…\n请稍候")));
        Label->SetFont(FCoreStyle::GetDefaultFontStyle(TEXT("Regular"),28)); Label->SetJustification(ETextJustify::Center);
        Label->SetColorAndOpacity(FSlateColor(FLinearColor(.84f,.95f,.88f,1)));
        auto LabelSlot=Root->AddChildToCanvas(Label); LabelSlot->SetAnchors(FAnchors(.5f,.5f)); LabelSlot->SetAlignment(FVector2D(.5f,.5f));
        LabelSlot->SetPosition(FVector2D::ZeroVector); LabelSlot->SetSize(FVector2D(800,140));
    }
    return Super::RebuildWidget();
}
