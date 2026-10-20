#include "AnomalyHealthComponent.h"
#include "AnomalyStatusWidget.h"
#include "GameFramework/Character.h"
#include "Blueprint/UserWidget.h"
#include "Engine/World.h"
#include "TimerManager.h"

UAnomalyHealthComponent::UAnomalyHealthComponent() { PrimaryComponentTick.bCanEverTick = false; }

void UAnomalyHealthComponent::BeginPlay()
{
    Super::BeginPlay();
    CurrentHealth = FMath::Max(1, MaxHealth);
    ACharacter* Player = Cast<ACharacter>(GetOwner());
    if (StatusWidgetClass && IsValid(Player) && Player->IsLocallyControlled())
    {
        StatusWidget = CreateWidget<UAnomalyStatusWidget>(Player->GetController<APlayerController>(), StatusWidgetClass);
        if (IsValid(StatusWidget))
        {
            StatusWidget->AddToViewport(50);
            StatusWidget->PresentHealth(CurrentHealth, MaxHealth);
            StatusWidget->PresentThreat(TEXT(""));
            StatusWidget->PresentDamage(TEXT(""));
        }
    }
}

bool UAnomalyHealthComponent::ApplyDamage(int32 Amount)
{
    if (!bDamageEnabled || bDead || Amount <= 0 || !GetWorld()) return false;
    const float Now = GetWorld()->GetTimeSeconds();
    if (Now - LastDamageTime + KINDA_SMALL_NUMBER < FMath::Max(0.f, DamageCooldown)) return false;
    LastDamageTime = Now;
    const int32 Damage = FMath::Min(Amount, CurrentHealth);
    CurrentHealth -= Damage;
    bDead = CurrentHealth <= 0;
    if (IsValid(StatusWidget))
    {
        StatusWidget->PresentHealth(CurrentHealth, MaxHealth);
        StatusWidget->PresentDamage(FString::Printf(TEXT("受伤  -%d"), Damage));
        GetWorld()->GetTimerManager().ClearTimer(DamageFeedbackTimer);
        GetWorld()->GetTimerManager().SetTimer(DamageFeedbackTimer, this,
            &UAnomalyHealthComponent::ClearDamageFeedback, .35f, false);
    }
    OnNativeHealthChanged.Broadcast(CurrentHealth, -Damage);
    if (bDead)
    {
        bDamageEnabled = false;
        OnNativeDeath.Broadcast();
    }
    return true;
}

void UAnomalyHealthComponent::SetDamageEnabled(bool bEnabled)
{ bDamageEnabled = bEnabled && !bDead; }

void UAnomalyHealthComponent::ClearDamageFeedback()
{ if (IsValid(StatusWidget)) StatusWidget->PresentDamage(TEXT("")); }

void UAnomalyHealthComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if (GetWorld()) GetWorld()->GetTimerManager().ClearTimer(DamageFeedbackTimer);
    if (IsValid(StatusWidget)) StatusWidget->RemoveFromParent();
    Super::EndPlay(Reason);
}
