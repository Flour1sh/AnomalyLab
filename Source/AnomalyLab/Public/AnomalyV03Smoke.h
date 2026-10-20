#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AnomalyV03Smoke.generated.h"
class AAnomalyRoundCoordinator;
class AAnomalyBoxActor;
class ACharacter;
class UAnomalyHealthComponent;
class UAnomalyWalletComponent;
class UAnomalyScannerComponent;
UCLASS(Transient, NotBlueprintable)
class ANOMALYLAB_API AAnomalyV03Smoke : public AActor
{
    GENERATED_BODY()
public:
    AAnomalyV03Smoke();
    virtual void Tick(float Seconds) override;
private:
    UPROPERTY() TObjectPtr<AAnomalyRoundCoordinator> Coordinator;
    UPROPERTY() TObjectPtr<ACharacter> Player;
    UPROPERTY() TObjectPtr<AAnomalyBoxActor> Box;
    UPROPERTY() TObjectPtr<UAnomalyHealthComponent> Health;
    UPROPERTY() TObjectPtr<UAnomalyWalletComponent> Wallet;
    UPROPERTY() TObjectPtr<UAnomalyScannerComponent> Scanner;
    FString Strategy;
    void TickStrategy(float Seconds);
    int32 ScanCount = 0;
    int32 ChosenRounds = 0;
    UPROPERTY() TObjectPtr<AActor> Occluder;
    int32 Stage = 0;
    int32 Iteration = 0;
    int32 ExpectedValue = 0;
    int64 StartingPermanentBalance=0;
    float Next = 0.f;
    float Started = 0.f;
    bool bRender = false;
    bool bShot = false;
    TArray<FVector> WalkPath;
    int32 WalkIndex = 0;
    bool Check(const FString& Name, bool Passed);
    void Finish(bool Passed);
    void Restart();
    void AimAt(const FVector& Target);
    void PlaceNear(AActor* Target, float Distance = 160.f);
    bool WalkTo(const FVector& Target);
    void Key(FKey Key, bool Pressed);
    void Shot(const FString& Name);
    bool Open(int32 Outcome);
};
