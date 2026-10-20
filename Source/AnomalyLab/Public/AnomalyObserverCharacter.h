#pragma once
#include "CoreMinimal.h"
#include "AnomalyThreatCharacter.h"
#include "AnomalyObserverCharacter.generated.h"
class UAnomalyObserverConfig;
class UStaticMeshComponent;
class UPointLightComponent;
UENUM(BlueprintType)
enum class EAnomalyObserverState:uint8 { Dormant, Warning, Observed, Unobserved, Unobservable, Resolved };
UCLASS(Blueprintable)
class ANOMALYLAB_API AAnomalyObserverCharacter : public AAnomalyThreatCharacter
{
    GENERATED_BODY()
public:
    AAnomalyObserverCharacter();
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UAnomalyObserverConfig> Config;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) EAnomalyObserverState ObserverState=EAnomalyObserverState::Dormant;
    virtual void ActivateThreat() override;
    virtual void ResolveThreat() override;
    virtual void StartChase() override;
    virtual bool CanBeLured() const override { return false; }
    virtual void Tick(float Seconds) override;
    void BeginWarning();
    bool IsEffectivelyObserved(bool bExitThreshold=false) const;
    FVector GetObservationPoint() const;
    FString DescribeState() const;
    float GetEffectiveObservationTolerance() const;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual bool CanDealContactDamage() const override;
private:
    friend struct FAnomalyV05Probe;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Body;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Head;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Eye;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UPointLightComponent> Glow;
    bool bValidConfig=false;
    bool bObserved=false;
    bool bAcquiring=false;
    float ActivatedAt=0,LastSeen=0,ChangedAt=0,AcquireAt=0,ObservedBudget=0,UnobservableUntil=0;
    void SetObserverState(EAnomalyObserverState State);
};
