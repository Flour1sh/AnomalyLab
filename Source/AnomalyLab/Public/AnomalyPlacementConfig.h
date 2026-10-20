#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "AnomalyPlacementConfig.generated.h"
class AAnomalyRoundCoordinator;

UCLASS(BlueprintType)
class ANOMALYLAB_API UAnomalyPlacementConfig : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere) TArray<FVector> APoints;
    UPROPERTY(EditAnywhere) TArray<FVector> BPoints;
    UPROPERTY(EditAnywhere) TArray<FVector> CPoints;
    UPROPERTY(EditAnywhere) FVector LootOffset = FVector(100,0,35);
    FVector LootLocation(const FVector& BoxPoint) const { return BoxPoint+LootOffset; }
    bool FindPickupSpot(AAnomalyRoundCoordinator* Owner,const FVector& BoxPoint,FVector& Location) const;
    bool PickupSpace(AAnomalyRoundCoordinator* Owner,const FVector& BoxPoint) const
    { FVector Location; return FindPickupSpot(Owner,BoxPoint,Location); }
    bool Choose(AAnomalyRoundCoordinator* Owner,int32 Region,int32 Seed,int32 Round,FTransform& Transform,int32& PointId) const;
    TArray<int32> LegalPoints(AAnomalyRoundCoordinator* Owner,int32 Region) const;
    const TArray<FVector>& Points(int32 Region) const;
    bool Legal(AAnomalyRoundCoordinator* Owner,const FVector& Point) const;
};
