#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "AnomalyScanTarget.h"
#include "AnomalyScannerComponent.generated.h"

class UAnomalyScanWidget;
class UAudioComponent;

UCLASS(Blueprintable, ClassGroup=(Anomaly), meta=(BlueprintSpawnableComponent))
class ANOMALYLAB_API UAnomalyScannerComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UAnomalyScannerComponent();
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Scan") float ScanRange = 300.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Scan") float ScanDuration = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Scan") TSubclassOf<UAnomalyScanWidget> PanelClass;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Scan") float Progress = 0.f;
    /** Per new run, Metal/Bio/Matter respectively. Legacy scans remain unlimited. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Scan|Resources") TArray<int32> MaxCharges = {3, 3, 3};
    UFUNCTION(BlueprintPure, Category="Scan|Resources") int32 GetRemaining(EAnomalyEquipment Instrument) const;
    UFUNCTION(BlueprintPure, Category="Scan|Resources") int32 GetMaximum(EAnomalyEquipment Instrument) const;
    bool UsesCharges() const;
    float GetPrecisionReduction() const { return PrecisionReduction; }
    UFUNCTION(BlueprintCallable, Category="Scan") void CancelScan();
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTick) override;
private:
    friend class AAnomalyBoxActor;
    friend class AAnomalyRoundCoordinator;
    friend struct FAnomalyV04Probe;
    TArray<int32> Remaining = {3, 3, 3};
    float PrecisionReduction=0.f;
    void InitializeRunResources(int32 CapacityBonus = 0);
    bool CommitCharge(EAnomalyEquipment Instrument);
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> ScanAudio;
    UAudioComponent* Feedback(FName Event);
    UPROPERTY(Transient) TObjectPtr<UAnomalyScanWidget> Panel;
    TWeakObjectPtr<AActor> Focus;
    TWeakObjectPtr<AActor> ScanningTarget;
    EAnomalyEquipment ScanningInstrument = EAnomalyEquipment::Gun;
    bool bRequireRelease = false;
    float Elapsed = 0.f;
    float ActiveScanSeconds=1.f;
    FString LastPresentation;
    AActor* FindTarget() const;
    void Present(EAnomalyEquipment Instrument, bool bEnabled);
};
