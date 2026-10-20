#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "AnomalyObserverConfig.generated.h"
class UMaterialInterface;
UCLASS(BlueprintType)
class ANOMALYLAB_API UAnomalyObserverConfig : public UPrimaryDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float ObserveDistance=2000.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float EnterDot=.80f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float ExitDot=.72f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float LostSightGrace=.18f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float MinimumDwell=.20f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float AcquireSeconds=.08f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float ContactGrace=.35f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float ObservationTolerance=4.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float UnobservableSeconds=1.25f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float MixedPoolWeight=.35f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UMaterialInterface> BodyMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UMaterialInterface> EyeMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UMaterialInterface> RedEyeMaterial;
    bool Validate(FString& Reason) const;
};
