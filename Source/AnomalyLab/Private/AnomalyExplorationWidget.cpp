#include "AnomalyExplorationWidget.h"
#include "Components/TextBlock.h"
#include "Components/Image.h"
#include "Blueprint/WidgetTree.h"

void UAnomalyExplorationWidget::PresentShop(const FString& Text,bool bOpen)
{
    if (ShopText)
    {
        ShopText->SetVisibility(bOpen?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
        if (ShopText->GetText().ToString()!=Text) ShopText->SetText(FText::FromString(Text));
    }
    if (WidgetTree)
    {
        if (auto Backing=WidgetTree->FindWidget<UImage>(TEXT("ShopBacking")))
            Backing->SetVisibility(bOpen?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
        for (const FName Name:{FName(TEXT("RegionText")),FName(TEXT("RegionBacking")),FName(TEXT("InventoryText")),FName(TEXT("ExplorationObjective")),FName(TEXT("MetaText"))})
            if (auto Widget=WidgetTree->FindWidget(Name)) Widget->SetVisibility(bOpen?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
    }
}
void UAnomalyExplorationWidget::PresentMeta(const FString& Text)
{ if (MetaText && MetaText->GetText().ToString()!=Text) MetaText->SetText(FText::FromString(Text)); }

void UAnomalyExplorationWidget::PresentRegion(const FString& Hint)
{
    if (RegionText && RegionText->GetText().ToString() != Hint) RegionText->SetText(FText::FromString(Hint));
}

void UAnomalyExplorationWidget::Present(const FString& Focus, const FString& Objective, bool bEnabled)
{
    if (WidgetTree)
        if (UImage* Backing = WidgetTree->FindWidget<UImage>(TEXT("PromptBacking")))
            Backing->SetVisibility(Focus.IsEmpty() ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
    SetVisibility(bEnabled ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
    if (InteractionPrompt && LastFocus != Focus)
    {
        LastFocus = Focus;
        InteractionPrompt->SetText(FText::FromString(Focus));
    }
    if (ExplorationObjective && LastObjective != Objective)
    {
        LastObjective = Objective;
        ExplorationObjective->SetText(FText::FromString(Objective));
    }
}

void UAnomalyExplorationWidget::PresentInventory(const FString& Items, const FString& Notice)
{
    if (InventoryText && InventoryText->GetText().ToString() != Items) InventoryText->SetText(FText::FromString(Items));
    if (WidgetTree)
        if (UImage* Backing = WidgetTree->FindWidget<UImage>(TEXT("NoticeBacking")))
            Backing->SetVisibility(Notice.IsEmpty() ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
    if (NoticeText && NoticeText->GetText().ToString() != Notice) NoticeText->SetText(FText::FromString(Notice));
}

void UAnomalyExplorationWidget::PresentDamage(bool bDamaged)
{ if (DamageVeil) DamageVeil->SetRenderOpacity(bDamaged ? .16f : 0.f); }
