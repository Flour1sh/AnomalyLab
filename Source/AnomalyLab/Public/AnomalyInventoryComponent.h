#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "AnomalyItemDefinition.h"
#include "AnomalyInventoryComponent.generated.h"
class AAnomalyWorldPickup;
class AAnomalyRoundCoordinator;

/** Player-owned four-slot authority. UI only reads snapshots. No stacking or persistence. */
UCLASS(ClassGroup=(Anomaly), meta=(BlueprintSpawnableComponent))
class ANOMALYLAB_API UAnomalyInventoryComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    static constexpr int32 Capacity = 4;
    UFUNCTION(BlueprintPure) int32 GetCapacity() const { return CurrentCapacity; }
    UFUNCTION(BlueprintPure) int32 GetCarryValue() const;
    UFUNCTION(BlueprintPure) int32 GetCount() const { return Items.Num(); }
    const TArray<FAnomalyItemInstance>& GetItems() const { return Items; }
    FString Describe() const;
    bool Contains(const FGuid& Id) const;
private:
    friend struct FAnomalyV05Probe;
    friend class AAnomalyRoundCoordinator;
    friend struct FAnomalyV04Probe;
    int32 CurrentCapacity=Capacity;
    UPROPERTY(Transient) TArray<FAnomalyItemInstance> Items;
    TSet<FGuid> ClaimedIds;
    bool bSealed = false;
    bool TryStore(AAnomalyWorldPickup* Pickup);
    void SealAndClear();
};
