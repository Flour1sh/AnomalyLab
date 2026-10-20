#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GameFramework/Actor.h"
#include "AnomalyEnvironment.generated.h"
class UBoxComponent;
class UStaticMeshComponent;
class UPointLightComponent;
class AAnomalyBoxActor;
class AAnomalyRoundCoordinator;
class AAnomalyThreatCharacter;
UENUM()
enum class EAnomalyDynamicEvent : uint8 { None, PowerFluctuation, ContainmentAlarm };
UENUM()
enum class EAnomalyEventPhase : uint8 { Quiet, Warning, Active };
USTRUCT()
struct FAnomalyEventSpec
{
    GENERATED_BODY()
    UPROPERTY() EAnomalyDynamicEvent Type=EAnomalyDynamicEvent::None;
    UPROPERTY() float At=0;
    UPROPERTY() float Duration=4;
};

UCLASS(BlueprintType)
class ANOMALYLAB_API UAnomalyEnvironmentConfig : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere) float PowerScanMultiplier=1.75f;
    UPROPERTY(EditAnywhere) float PowerObserveMultiplier=1.5f;
    UPROPERTY(EditAnywhere) float PowerLightMultiplier=.25f;
    UPROPERTY(EditAnywhere) float InteractCooldown=.35f;
    UPROPERTY(EditAnywhere) bool bEnableChamber=false;
    UPROPERTY(EditAnywhere) float ChamberSeconds=3.f;
    UPROPERTY(EditAnywhere) float ChamberRadius=300.f;
    UPROPERTY(EditAnywhere) FVector ChamberCenter=FVector(300,-1100,0);
    UPROPERTY(EditAnywhere) bool bEnableEvents=false;
    UPROPERTY(EditAnywhere) float EventChance=.5f;
    UPROPERTY(EditAnywhere) int32 MaxEvents=2;
    UPROPERTY(EditAnywhere) float EventFirstDelay=12.f;
    UPROPERTY(EditAnywhere) float EventSpacing=10.f;
    UPROPERTY(EditAnywhere) float EventWarningSeconds=2.f;
    UPROPERTY(EditAnywhere) float EventSeconds=4.f;
    UPROPERTY(EditAnywhere) float AlarmSpeedMultiplier=1.08f;
    TArray<FAnomalyEventSpec> BuildEventPlan(int32 Seed) const;
    bool Validate() const;
};
UENUM(BlueprintType)
enum class EAnomalyEnvironmentKind : uint8 { Power, Chamber };
UENUM()
enum class EAnomalyChamberPhase : uint8 { Idle, Armed, Triggered, Spent };

UCLASS()
class ANOMALYLAB_API AAnomalyEnvironmentTerminal : public AActor
{
    GENERATED_BODY()
public:
    AAnomalyEnvironmentTerminal();
    UPROPERTY(EditAnywhere) EAnomalyEnvironmentKind Kind=EAnomalyEnvironmentKind::Power;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UBoxComponent> Bounds;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Visual;
    bool Interact(AActor* Player);
    bool ValidatePlayer(AActor* Player) const;
    FString Describe() const;
};

/** World-owned environmental state, never a wallet, save or cross-level object. */
UCLASS()
class ANOMALYLAB_API AAnomalyEnvironmentController : public AActor
{
    GENERATED_BODY()
public:
    AAnomalyEnvironmentController();
    UPROPERTY(EditAnywhere) TObjectPtr<UAnomalyEnvironmentConfig> Config;
    static AAnomalyEnvironmentController* Find(const UWorld* World);
    bool Active() const;
    bool TogglePower(AAnomalyEnvironmentTerminal* Terminal,AActor* Player,FString& Reason);
    float ScanMultiplier(const AAnomalyBoxActor* Target) const;
    float ObserveMultiplier(const AActor* Observer) const;
    bool IsPowerOn() const { return bPowerOn && !bEventPowerOff; }
    bool TriggerChamber(AAnomalyEnvironmentTerminal* Terminal,AActor* Player,FString& Reason);
    EAnomalyChamberPhase GetChamberPhase() const { return ChamberPhase; }
    FString DescribeChamber() const;
    FString DescribeEvent() const;
    bool StartEvent(const FAnomalyEventSpec& Spec);
    void CancelEvents(const FString& Reason);
    EAnomalyDynamicEvent GetEvent() const { return CurrentEvent.Type; }
    EAnomalyEventPhase GetEventPhase() const { return EventPhase; }
    int32 GetEventCount() const { return EventCount; }
    float ThreatSpeedMultiplier(const AAnomalyThreatCharacter* Target) const;
    FString DescribePower() const;
    virtual void Tick(float Delta) override;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    friend struct FAnomalyV05Probe;
    bool bPowerOn=true;
    float PowerReadyAt=0;
    TArray<TWeakObjectPtr<UPointLightComponent>> Lights;
    TArray<float> InitialIntensities;
    void ApplyLights();
    AAnomalyRoundCoordinator* Coordinator() const;
    EAnomalyChamberPhase ChamberPhase=EAnomalyChamberPhase::Idle;
    TWeakObjectPtr<AAnomalyThreatCharacter> Held;
    float HoldUntil=0;
    AAnomalyThreatCharacter* ChamberTarget(bool& ObserverOnly) const;
    bool bPlanBuilt=false,bEventsCancelled=false,bEventPowerOff=false;
    UPROPERTY() TArray<FAnomalyEventSpec> EventPlan;
    FAnomalyEventSpec CurrentEvent;
    EAnomalyEventPhase EventPhase=EAnomalyEventPhase::Quiet;
    float EventDeadline=0,RunStarted=0,EventReadyAt=0;
    int32 NextEvent=0,EventCount=0;
    TArray<TWeakObjectPtr<UPointLightComponent>> AlarmLights;
    TArray<FLinearColor> InitialAlarmColours;
    void TickEvents();
    void EndEvent(const FString& Cause);
    void ApplyAlarmLights();
};
