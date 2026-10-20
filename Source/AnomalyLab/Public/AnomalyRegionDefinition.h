#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "AnomalyRegionDefinition.generated.h"

class UAnomalyBoxDefinition;

/** T26 region rules. Arrays use Safe/Risky/Unknown and UnknownSafe/Medium/Risky order. */
UCLASS(BlueprintType)
class ANOMALYLAB_API UAnomalyRegionDefinition : public UPrimaryDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName RegionID;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText DisplayName;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText Description;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<double> BoxTypeWeights = {1., 1., 1.};
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<double> HiddenProfileWeights = {1., 1., 1.};
    UPROPERTY(EditAnywhere, BlueprintReadOnly) double HighValueWeight = 1.;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) double TrashWeight = 1.;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) double ThreatWeight = 1.;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) double RewardScale = 1.;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) double ScanErrorAdd = 0.;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<FName> AllowedAnomalies = {FName(TEXT("Chaser"))};

    bool Validate(FString& Reason) const;
    /** Mutates only an actor-owned copy; caller validates the original definition first. */
    bool ApplyTo(UAnomalyBoxDefinition& Data, FString& Reason) const;
    FName DrawBoxType(FRandomStream& Stream, FName Exclude = NAME_None) const;
    FName DrawHiddenProfile(FRandomStream& Stream) const;
    /** Same sampling/repair used by runtime and the fixed-seed statistics suite. */
    static bool DrawChoices(const TArray<TObjectPtr<UAnomalyRegionDefinition>>& Regions,
                            FRandomStream& Stream, TArray<FName>& Types, FString& Reason);
private:
    static int32 DrawIndex(const TArray<double>& Weights, FRandomStream& Stream, int32 Exclude = INDEX_NONE);
};
