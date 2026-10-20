#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "AnomalyProgressionConfig.generated.h"

UCLASS(BlueprintType)
class ANOMALYLAB_API UAnomalyProgressionConfig : public UPrimaryDataAsset
{
    GENERATED_BODY()
public:
    /** Battery / Precision / Backpack / next-run Decoy; fixed price per level. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<int32> Prices = {1000,1500,2500,600};
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<int32> MaxLevels = {2,2,1,1};
    UPROPERTY(EditAnywhere, BlueprintReadOnly) int32 ChargesPerLevel = 1;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float PrecisionPerLevel = .25f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float PrecisionCap = .5f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float DecoyRadius = 1200.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float DecoySeconds = 5.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float DecoyCooldown = 3.f;
    bool Validate(FString& Reason) const;
};
