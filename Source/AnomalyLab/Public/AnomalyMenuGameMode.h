#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "AnomalyMenuGameMode.generated.h"

class UAnomalyMainMenuWidget;

/** Menu-only controller; the existing Level01 controller remains the gameplay owner. */
UCLASS()
class ANOMALYLAB_API AAnomalyMenuPlayerController : public APlayerController
{
    GENERATED_BODY()
public:
    AAnomalyMenuPlayerController();
    UFUNCTION(BlueprintCallable, Category="Menu") void StartLevel01();
    UFUNCTION(BlueprintPure, Category="Menu") bool IsStartingGame() const { return bStartingGame; }
    UAnomalyMainMenuWidget* GetMenuWidget() const { return MenuWidget; }
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
    UPROPERTY(Transient) TObjectPtr<UAnomalyMainMenuWidget> MenuWidget;
    UPROPERTY() TSoftClassPtr<UAnomalyMainMenuWidget> MenuWidgetClass;
    FTimerHandle StartTimer;
    bool bStartingGame = false;
    void TravelToLevel01();
};

/** An empty menu map never spawns a first person pawn or starts a round. */
UCLASS()
class ANOMALYLAB_API AAnomalyMenuGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AAnomalyMenuGameMode();
};
