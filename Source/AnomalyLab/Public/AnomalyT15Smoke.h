#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AnomalyT15Smoke.generated.h"

class AAnomalyRoundCoordinator;
class AAnomalyBoxActor;
class UAnomalyHealthComponent;
class UAnomalyWalletComponent;
class AAnomalyThreatCharacter;

/** Development-only real-map T15 runtime checks. */
UCLASS(NotBlueprintable, Transient)
class ANOMALYLAB_API AAnomalyT15Smoke : public AActor
{
    GENERATED_BODY()
public:
    AAnomalyT15Smoke();
    virtual void Tick(float DeltaSeconds) override;
private:
    UPROPERTY() TObjectPtr<AAnomalyRoundCoordinator> Coordinator;
    UPROPERTY() TObjectPtr<AAnomalyBoxActor> Box;
    UPROPERTY() TObjectPtr<UAnomalyHealthComponent> Health;
    UPROPERTY() TObjectPtr<UAnomalyWalletComponent> Wallet;
    UPROPERTY() TObjectPtr<AActor> Player;
    int32 Stage = 0;
    int32 LastHealth = 100;
    int32 Hits = 0;
    float LastHitAt = -1000.f;
    float Elapsed = 0.f;
    float PursuitStartedAt = 0.f;
    FVector ThreatStartLocation = FVector::ZeroVector;
    bool bCheckedMovement = false;
    bool bWarningChecked = false;
    bool Check(const FString& Name, bool bPassed);
    bool OpenThreat(bool bAllowSpawn);
    bool PanelContains(const FString& Token) const;
    void Finish(bool bPassed);
};
