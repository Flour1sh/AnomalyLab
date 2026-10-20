#include "AnomalyStatusWidget.h"
#include "Components/TextBlock.h"

void UAnomalyStatusWidget::PresentHealth(int32 Current, int32 Maximum)
{ if (HPText) HPText->SetText(FText::FromString(FString::Printf(TEXT("HP  %d / %d"), Current, Maximum))); }

void UAnomalyStatusWidget::PresentThreat(const FString& Message)
{
    if (!ThreatText) return;
    ThreatText->SetText(FText::FromString(Message));
    ThreatText->SetVisibility(Message.IsEmpty() ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
}

void UAnomalyStatusWidget::PresentDamage(const FString& Message)
{
    if (!DamageText) return;
    DamageText->SetText(FText::FromString(Message));
    DamageText->SetVisibility(Message.IsEmpty() ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
}
