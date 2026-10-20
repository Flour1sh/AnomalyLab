#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "AnomalyStatusWidget.generated.h"

class UTextBlock;

/** Passive HP, warning, countdown and hit feedback display. */
UCLASS()
class ANOMALYLAB_API UAnomalyStatusWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void PresentHealth(int32 Current, int32 Maximum);
    void PresentThreat(const FString& Message);
    void PresentDamage(const FString& Message);
protected:
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UTextBlock> HPText;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UTextBlock> ThreatText;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UTextBlock> DamageText;
};
