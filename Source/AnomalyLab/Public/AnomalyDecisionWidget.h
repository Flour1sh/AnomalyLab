#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "AnomalyDecisionWidget.generated.h"

class UTextBlock;

/** Passive T14 panel. The coordinator owns decisions and snapshots. */
UCLASS()
class ANOMALYLAB_API UAnomalyDecisionWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void AppendItems(const FString& Items);
    void PresentDecision(int32 Money, int32 Rounds, int32 Threats, bool bCanContinue);
    void PresentTerminal(int32 Money, int32 Rounds, int32 Threats, float Seconds, bool bCashedOut, bool bError);
protected:
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UTextBlock> StatusText;
};
