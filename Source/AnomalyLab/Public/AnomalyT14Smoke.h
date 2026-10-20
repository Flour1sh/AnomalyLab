#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AnomalyT14Smoke.generated.h"

class AAnomalyRoundCoordinator;
class AAnomalyBoxActor;
class UAnomalyWalletComponent;
class UAnomalyEquipmentComponent;

/** Command-line-only T14 runtime checks in the real map. */
UCLASS(NotBlueprintable, Transient)
class ANOMALYLAB_API AAnomalyT14Smoke : public AActor
{
    GENERATED_BODY()
public:
    AAnomalyT14Smoke();
    virtual void Tick(float DeltaSeconds) override;
private:
    UPROPERTY() TObjectPtr<AAnomalyRoundCoordinator> Coordinator;
    UPROPERTY() TObjectPtr<AAnomalyBoxActor> Box;
    UPROPERTY() TObjectPtr<UAnomalyWalletComponent> Wallet;
    UPROPERTY() TObjectPtr<UAnomalyEquipmentComponent> Equipment;
    UPROPERTY() TObjectPtr<AActor> Player;
    int32 Stage = 0;
    int32 ExpectedMoney = 0;
    bool bCapturedOutcome = false;
    float Elapsed = 0.f;
    bool Check(const FString& Name, bool bPassed);
    bool OpenForced(int32 Outcome);
    bool PanelContains(const FString& Token) const;
    void Finish(bool bPassed);
};
