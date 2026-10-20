#include "AnomalyScanWidget.h"
#include "Components/TextBlock.h"
#include "Components/ProgressBar.h"

void UAnomalyScanWidget::Present(const FString& Summary, const FString& Hint, float Progress, bool bFocused, bool bEnabled)
{
    SetVisibility(bEnabled ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
    if (ScanSummary)
    {
        ScanSummary->SetText(FText::FromString(Summary));
        ScanSummary->SetVisibility(bFocused ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
    }
    if (ScanHint) ScanHint->SetText(FText::FromString(Hint));
    if (ScanProgress)
    {
        ScanProgress->SetPercent(Progress);
        ScanProgress->SetVisibility(Progress > 0.f ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
    }
}
