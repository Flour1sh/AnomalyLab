#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "AnomalyBalanceConfig.generated.h"
class UAnomalyBoxDefinition;

/** Bounded round modifiers; applied only to a private, already regionalized box copy. */
UCLASS(BlueprintType)
class ANOMALYLAB_API UAnomalyBalanceConfig : public UPrimaryDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere,BlueprintReadOnly,Category="Curve") double ThreatPerRound=.03;
    UPROPERTY(EditAnywhere,BlueprintReadOnly,Category="Curve") double ThreatCap=1.15;
    UPROPERTY(EditAnywhere,BlueprintReadOnly,Category="Curve") double RewardPerRound=.05;
    UPROPERTY(EditAnywhere,BlueprintReadOnly,Category="Curve") double RewardCap=1.30;
    bool Validate(FString& Reason) const;
    double ThreatMultiplier(int32 Round) const;
    double RewardMultiplier(int32 Round) const;
    bool ApplyTo(UAnomalyBoxDefinition& Data,int32 Round,FString& Reason) const;
};
