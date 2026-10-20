#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "AnomalyHealthComponent.generated.h"

class UAnomalyStatusWidget;
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FAnomalyHealthChanged, int32, NewHealth, int32, Delta);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FAnomalyPlayerDied);

/** Authoritative player HP and damage cooldown; a round enables damage only during pursuit. */
UCLASS(Blueprintable, ClassGroup=(Anomaly), meta=(BlueprintSpawnableComponent))
class ANOMALYLAB_API UAnomalyHealthComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UAnomalyHealthComponent();
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="T15|Health") int32 MaxHealth = 100;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="T15|Health") int32 CurrentHealth = 100;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="T15|Health") int32 ThreatDamage = 25;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="T15|Health") float DamageCooldown = 1.5f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="T15|UI") TSubclassOf<UAnomalyStatusWidget> StatusWidgetClass;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="T15|Health") bool bDamageEnabled = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="T15|Health") bool bDead = false;
    UPROPERTY(BlueprintAssignable, Category="T15|Health") FAnomalyHealthChanged OnNativeHealthChanged;
    UPROPERTY(BlueprintAssignable, Category="T15|Health") FAnomalyPlayerDied OnNativeDeath;
    UFUNCTION(BlueprintCallable, Category="T15|Health") bool ApplyDamage(int32 Amount);
    UFUNCTION(BlueprintCallable, Category="T15|Health") void SetDamageEnabled(bool bEnabled);
    UFUNCTION(BlueprintPure, Category="T15|Health") UAnomalyStatusWidget* GetStatusWidget() const { return StatusWidget; }
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
    float LastDamageTime = -1000000.f;
    UPROPERTY(Transient) TObjectPtr<UAnomalyStatusWidget> StatusWidget;
    FTimerHandle DamageFeedbackTimer;
    void ClearDamageFeedback();
};
