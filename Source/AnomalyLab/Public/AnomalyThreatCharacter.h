#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "AnomalyThreatCharacter.generated.h"

class AAIController;
class USphereComponent;
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FNativeThreatEvent, AActor*, Spider);

/** Native threat lifecycle; BP_Spider retains AlienVisual and the accepted T10 cosmetic graphs. */
UCLASS(Blueprintable)
class ANOMALYLAB_API AAnomalyThreatCharacter : public ACharacter
{
    GENERATED_BODY()
public:
    AAnomalyThreatCharacter();
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Threat") double MoveSpeed = 330.0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Threat") int32 MaxHealth = 100; // Future combat configuration only.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Threat") double AcceptanceRadius = 80.0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Threat") bool bAutoResolveThreat = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Threat") double AutoResolveDelay = 20.0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Threat") float AttackRadius = 80.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Debug") bool bDebugLogging = true;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Threat") bool bResolved = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Threat") bool bAttackTriggered = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Threat") bool bMoveRetryUsed = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Threat") bool bThreatActive = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Threat") TObjectPtr<ACharacter> TargetPlayer;
    UPROPERTY(BlueprintAssignable) FNativeThreatEvent OnNativeThreatResolved;
    UPROPERTY(BlueprintAssignable) FNativeThreatEvent OnNativePlayerAttacked;
    UFUNCTION(BlueprintCallable, Category="Threat") virtual void ResolveThreat();
    UFUNCTION(BlueprintCallable, Category="Threat") virtual void ActivateThreat();
    UFUNCTION(BlueprintCallable, Category="Threat") virtual void StartChase();
    virtual bool CanBeLured() const { return true; }
    bool TryLure(AActor* Source,float Seconds);
    AActor* GetPursuitTarget() const;
    void SetEnvironmentStasis(bool Enabled);
    bool IsEnvironmentStasis() const { return bEnvironmentStasis; }
    UFUNCTION(BlueprintImplementableEvent, Category="Presentation") void PresentThreatResolved(AActor* Spider);
    UFUNCTION(BlueprintImplementableEvent, Category="Presentation") void PresentPlayerAttacked(AActor* Spider);
protected:
    virtual bool CanDealContactDamage() const { return true; }
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
    TWeakObjectPtr<AActor> LureTarget;
    TWeakObjectPtr<AActor> LastMoveTarget;
    float LureUntil=0.f;
    FTimerHandle ResolveTimer;
    FTimerHandle ChaseTimer;
    FTimerHandle AttackTimer;
    void AttackTick();
    bool bEnvironmentStasis=false;
};
