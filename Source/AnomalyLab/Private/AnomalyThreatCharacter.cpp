#include "AnomalyThreatCharacter.h"
#include "AIController.h"
#include "Navigation/PathFollowingComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/CapsuleComponent.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"
#include "AnomalyHealthComponent.h"

AAnomalyThreatCharacter::AAnomalyThreatCharacter()
{
    PrimaryActorTick.bCanEverTick = true;
    AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
    AIControllerClass = AAIController::StaticClass();
    GetCapsuleComponent()->SetCapsuleSize(34.0f, 45.0f);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
    GetCapsuleComponent()->SetGenerateOverlapEvents(true);
    GetCapsuleComponent()->SetCanEverAffectNavigation(false);
    GetCharacterMovement()->bEnablePhysicsInteraction = false;
    GetCharacterMovement()->bOrientRotationToMovement = false;
    GetCharacterMovement()->bUseControllerDesiredRotation = false;
    bUseControllerRotationYaw = false;
}

void AAnomalyThreatCharacter::BeginPlay()
{
    Super::BeginPlay();
    GetCharacterMovement()->MaxWalkSpeed = static_cast<float>(MoveSpeed);
    TargetPlayer = UGameplayStatics::GetPlayerCharacter(this, 0);
    GetCharacterMovement()->DisableMovement();
    UE_LOG(LogTemp, Display, TEXT("[Threat] Spawned inactive %s"), *GetName());
}

void AAnomalyThreatCharacter::ActivateThreat()
{
    if (bResolved || bThreatActive || !IsValid(TargetPlayer)) return;
    bThreatActive = true;
    GetCharacterMovement()->MaxWalkSpeed = static_cast<float>(MoveSpeed);
    GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    if (bAutoResolveThreat)
        GetWorldTimerManager().SetTimer(ResolveTimer, this, &AAnomalyThreatCharacter::ResolveThreat,
            FMath::Max(0.001, AutoResolveDelay), false);
    GetWorldTimerManager().SetTimer(AttackTimer, this, &AAnomalyThreatCharacter::AttackTick, .1f, true, 0.f);
    StartChase();
    UE_LOG(LogTemp, Display, TEXT("[Threat] Started %s Speed=%.1f Duration=%.1f"), *GetName(), MoveSpeed, AutoResolveDelay);
}

void AAnomalyThreatCharacter::StartChase()
{
    if(bEnvironmentStasis)
    {
        if(auto AI=Cast<AAIController>(GetController())) AI->StopMovement();
        GetWorldTimerManager().SetTimer(ChaseTimer,this,&AAnomalyThreatCharacter::StartChase,.15f,false); return;
    }
    if (bResolved || !bThreatActive || !IsValid(TargetPlayer)) return;
    AAIController* AI = Cast<AAIController>(GetController());
    AActor* Pursuit=GetPursuitTarget();
    if (LastMoveTarget.Get()!=Pursuit)
    { if (AI) AI->StopMovement(); LastMoveTarget=Pursuit; bMoveRetryUsed=false; }
    if (AI && AI->GetMoveStatus() == EPathFollowingStatus::Moving)
    {
        GetWorldTimerManager().SetTimer(ChaseTimer, this, &AAnomalyThreatCharacter::StartChase, 0.15f, false);
        return;
    }
    const EPathFollowingRequestResult::Type Request = AI
        ? AI->MoveToActor(Pursuit, static_cast<float>(AcceptanceRadius), false)
        : EPathFollowingRequestResult::Failed;
    if (Request == EPathFollowingRequestResult::Failed)
    {
        if (bMoveRetryUsed) { UE_LOG(LogTemp, Warning, TEXT("[Threat] MoveTo failed twice; waiting for independent resolution")); return; }
        bMoveRetryUsed = true;
        UE_LOG(LogTemp, Warning, TEXT("[Threat] MoveTo failed; retry once in 0.5s"));
        GetWorldTimerManager().SetTimer(ChaseTimer, this, &AAnomalyThreatCharacter::StartChase, 0.5f, false);
        return;
    }
    GetWorldTimerManager().SetTimer(ChaseTimer, this, &AAnomalyThreatCharacter::StartChase, 0.15f, false);
}

AActor* AAnomalyThreatCharacter::GetPursuitTarget() const
{ return LureTarget.IsValid() && GetWorld()->GetTimeSeconds()<LureUntil ? LureTarget.Get() : TargetPlayer.Get(); }
bool AAnomalyThreatCharacter::TryLure(AActor* Source,float Seconds)
{
    if (!CanBeLured() || !bThreatActive || bResolved || !IsValid(Source) || Seconds<=0 || !FMath::IsFinite(Seconds)) return false;
    LureTarget=Source; LureUntil=GetWorld()->GetTimeSeconds()+Seconds;
    if (AAIController* AI=Cast<AAIController>(GetController())) AI->StopMovement();
    StartChase(); return true;
}

void AAnomalyThreatCharacter::AttackTick()
{
    if(bEnvironmentStasis) return;
    if (!bThreatActive || bResolved || !IsValid(TargetPlayer) || !CanDealContactDamage()) return;
    const FVector Delta = TargetPlayer->GetActorLocation() - GetActorLocation();
    if (FVector2D(Delta.X, Delta.Y).SizeSquared() > FMath::Square(AttackRadius) || FMath::Abs(Delta.Z) > 120.f) return;
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(ThreatAttackLOS), false, this);
    if (GetWorld()->LineTraceSingleByChannel(Hit, GetActorLocation(), TargetPlayer->GetActorLocation(), ECC_Visibility, Params)
        && Hit.GetActor() != TargetPlayer) return;
    UAnomalyHealthComponent* Health = TargetPlayer->FindComponentByClass<UAnomalyHealthComponent>();
    if (!IsValid(Health) || !Health->ApplyDamage(Health->ThreatDamage)) return;
    // ApplyDamage may end the run and destroy this actor through the death delegate.
    if (Health->bDead || IsActorBeingDestroyed()) return;
    if (!bAttackTriggered)
    {
        bAttackTriggered = true;
        UE_LOG(LogTemp, Display, TEXT("[Threat] SPIDER ATTACKED"));
        PresentPlayerAttacked(this);
        OnNativePlayerAttacked.Broadcast(this);
    }
}

void AAnomalyThreatCharacter::ResolveThreat()
{
    if (bResolved || !bThreatActive) return;
    bResolved = true;
    bThreatActive = false;
    GetWorldTimerManager().ClearTimer(ResolveTimer);
    GetWorldTimerManager().ClearTimer(ChaseTimer);
    GetWorldTimerManager().ClearTimer(AttackTimer);
    if (AAIController* AI = Cast<AAIController>(GetController())) AI->StopMovement();
    GetCharacterMovement()->DisableMovement();
    UE_LOG(LogTemp, Display, TEXT("[Threat] Resolved %s"), *GetName());
    PresentThreatResolved(this);
    OnNativeThreatResolved.Broadcast(this);
}

void AAnomalyThreatCharacter::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(ResolveTimer);
    GetWorldTimerManager().ClearTimer(ChaseTimer);
    GetWorldTimerManager().ClearTimer(AttackTimer);
    OnNativeThreatResolved.Clear(); OnNativePlayerAttacked.Clear();
    Super::EndPlay(Reason);
}

void AAnomalyThreatCharacter::SetEnvironmentStasis(bool Enabled)
{
    if(bEnvironmentStasis==Enabled) return; bEnvironmentStasis=Enabled;
    if(Enabled)
    { if(auto AI=Cast<AAIController>(GetController())) AI->StopMovement();
      GetCharacterMovement()->StopMovementImmediately(); GetCharacterMovement()->DisableMovement(); }
    else if(bThreatActive && !bResolved) { GetCharacterMovement()->SetMovementMode(MOVE_Walking); StartChase(); }
}
