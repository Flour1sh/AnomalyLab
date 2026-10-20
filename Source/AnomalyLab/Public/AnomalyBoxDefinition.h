#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "AnomalyBoxDefinition.generated.h"

/** Editable box configuration. Runtime actors copy values; shared assets are never mutated. */
UCLASS(BlueprintType, Blueprintable)
class ANOMALYLAB_API UAnomalyBoxDefinition : public UPrimaryDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Box") FName BoxID;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Box") FText DisplayName;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Reward") int32 ValueMin = 0;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Reward") int32 ValueMax = 0;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Outcome") double HighValueChance = 0.0;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Outcome") double TrashChance = 1.0;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Outcome") double ThreatChance = 0.0;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Scan") double ValueLowerScale = 0.9;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Scan") double ValueUpperScale = 1.1;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Scan") double ScanProbabilityError = 0.0;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Box") bool RandomHiddenProfile = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Box") bool HiddenProfile = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Visual") double MetalChance = 0.3;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Visual") double WarningChance = 0.2;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Visual") double WearChance = 0.3;

    bool Validate(FString& Reason) const;
    int32 SelectOutcome(double UnitRoll) const;
};
