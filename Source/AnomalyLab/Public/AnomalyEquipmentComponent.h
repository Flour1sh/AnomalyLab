#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "AnomalyEquipmentComponent.generated.h"

class UCameraComponent;
class UInputComponent;
class UStaticMesh;
class UStaticMeshComponent;

UENUM(BlueprintType)
enum class EAnomalyEquipment : uint8
{
    MetalDetector,
    BioDetector,
    MatterAnalyzer,
    Gun
};

/** Fixed T11E starter equipment. Scanner use/readings are implemented in T12. */
UCLASS(ClassGroup=(Anomaly), meta=(BlueprintSpawnableComponent))
class ANOMALYLAB_API UAnomalyEquipmentComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UAnomalyEquipmentComponent();

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="T11E|Meshes") TObjectPtr<UStaticMesh> MetalDetectorMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="T11E|Meshes") TObjectPtr<UStaticMesh> BioDetectorMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="T11E|Meshes") TObjectPtr<UStaticMesh> MatterAnalyzerMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="T11E|Meshes") TObjectPtr<UStaticMesh> GunMesh;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="T11E") EAnomalyEquipment CurrentEquipment = EAnomalyEquipment::MetalDetector;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="T11E") EAnomalyEquipment LastScanner = EAnomalyEquipment::MetalDetector;

    UFUNCTION(BlueprintCallable, Category="T11E") void EquipScanner();
    UFUNCTION(BlueprintCallable, Category="T11E") void EquipGun();
    UFUNCTION(BlueprintCallable, Category="T11E") void CancelUse();
    UFUNCTION(BlueprintPure, Category="T11E") bool IsScannerEquipped() const { return CurrentEquipment != EAnomalyEquipment::Gun; }
    UFUNCTION(BlueprintPure, Category="T11E") EAnomalyEquipment GetEffectiveEquipment() const { return CurrentEquipment; }

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
    FTimerHandle InputRetryTimer;
    FTimerHandle EquipTransitionTimer;
    TWeakObjectPtr<UInputComponent> BoundInput;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> HeldMesh;
    void TryBindInput();
    void UpdateHeldMesh();
    void BeginEquipTransition();
    void FinishEquipTransition();
    void ShowFeedback() const;
    bool CanEquip() const;
    bool RouteDecisionInput(bool bContinue);
};
