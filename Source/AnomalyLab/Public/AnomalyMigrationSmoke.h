#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AnomalyMigrationSmoke.generated.h"

class AAnomalyRoundCoordinator;
class AAnomalyBoxActor;
class UAnomalyWalletComponent;

/** Explicit development-only command-line smoke harness. Never spawned during normal gameplay. */
UCLASS(NotBlueprintable, Transient)
class ANOMALYLAB_API AAnomalyMigrationSmoke : public AActor
{
    GENERATED_BODY()
public:
    AAnomalyMigrationSmoke();
    virtual void Tick(float DeltaSeconds) override;
private:
    UPROPERTY() TObjectPtr<AAnomalyRoundCoordinator> Coordinator;
    UPROPERTY() TObjectPtr<AAnomalyBoxActor> SelectedBox;
    UPROPERTY() TObjectPtr<UAnomalyWalletComponent> Wallet;
    UPROPERTY() TObjectPtr<AActor> Player;
    int32 Stage = 0;
    int32 StartingMoney = 0;
    int32 ExpectedMoney = 0;
    bool bSawOutcome = false;
    bool bCheckedThreatMovement = false;
    bool bCheckedThreatContact = false;
    float ThreatStartedAt = 0.0f;
    FVector ThreatStartLocation = FVector::ZeroVector;
    float Elapsed = 0.0f;
    bool Check(const FString& Name, bool bPassed);
    void Finish(bool bPassed);
    bool ValidateDefinitions();
};
