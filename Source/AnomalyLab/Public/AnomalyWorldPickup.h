#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AnomalyItemDefinition.h"
#include "AnomalyWorldPickup.generated.h"
class USphereComponent;
class UStaticMeshComponent;
class UPointLightComponent;
class UAnomalyInventoryComponent;

UCLASS(Blueprintable)
class ANOMALYLAB_API AAnomalyWorldPickup : public AActor
{
    GENERATED_BODY()
public:
    AAnomalyWorldPickup();
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USphereComponent> InteractionSphere;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> ItemMesh;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UPointLightComponent> Glow;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) FAnomalyItemInstance Item;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) bool bInitialized = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) bool bClaimed = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) bool bPickable = false;
    bool InitializeItem(const UAnomalyItemDefinition* Definition, int32 Value, int32 RoundId);
    virtual void Tick(float Seconds) override;
private:
    friend class UAnomalyInventoryComponent;
};
