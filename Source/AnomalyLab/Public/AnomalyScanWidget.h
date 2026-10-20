#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "AnomalyScanWidget.generated.h"

class UTextBlock;
class UProgressBar;

/** Passive HUD extension. The Python-built widget owns layout; scanner owns state. */
UCLASS()
class ANOMALYLAB_API UAnomalyScanWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Present(const FString& Summary, const FString& Hint, float Progress, bool bFocused, bool bEnabled);
protected:
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UTextBlock> ScanSummary;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UTextBlock> ScanHint;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UProgressBar> ScanProgress;
};
