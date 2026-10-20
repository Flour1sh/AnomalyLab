#include "AnomalyObserverCharacter.h"
#include "AnomalyEnvironment.h"
#include "AnomalyObserverConfig.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "AIController.h"
#include "UObject/ConstructorHelpers.h"
#include "Engine/World.h"

AAnomalyObserverCharacter::AAnomalyObserverCharacter()
{
    PrimaryActorTick.TickGroup=TG_PostUpdateWork;
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    Body=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ObserverBody")); Body->SetupAttachment(GetRootComponent());
    Body->SetStaticMesh(Cube.Object); Body->SetRelativeLocation(FVector(0,0,38)); Body->SetRelativeScale3D(FVector(.5,.35,1.4));
    Head=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ObserverHead")); Head->SetupAttachment(GetRootComponent());
    Head->SetStaticMesh(Sphere.Object); Head->SetRelativeLocation(FVector(0,0,115)); Head->SetRelativeScale3D(FVector(.72));
    Eye=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ObserverEye")); Eye->SetupAttachment(GetRootComponent());
    Eye->SetStaticMesh(Cube.Object); Eye->SetRelativeLocation(FVector(42,0,115)); Eye->SetRelativeScale3D(FVector(.12,.6,.22));
    for (auto Part:{Body,Head,Eye}) { Part->SetCollisionEnabled(ECollisionEnabled::NoCollision); Part->SetCanEverAffectNavigation(false); }
    Glow=CreateDefaultSubobject<UPointLightComponent>(TEXT("ObserverEyeGlow")); Glow->SetupAttachment(Eye);
    Glow->SetIntensity(700.f); Glow->SetAttenuationRadius(300.f); Glow->SetCastShadows(false);
}
void AAnomalyObserverCharacter::BeginPlay()
{
    Super::BeginPlay(); FString Why;
    bValidConfig=IsValid(Config) && Config->Validate(Why);
    if (!bValidConfig) { UE_LOG(LogTemp,Error,TEXT("[Observer] Invalid configuration %s"),*Why); return; }
    Config=DuplicateObject<UAnomalyObserverConfig>(Config,this);
    if (Config->BodyMaterial) { Body->SetMaterial(0,Config->BodyMaterial); Head->SetMaterial(0,Config->BodyMaterial); }
    SetObserverState(EAnomalyObserverState::Dormant);
}
FVector AAnomalyObserverCharacter::GetObservationPoint() const { return Eye->GetComponentLocation(); }
bool AAnomalyObserverCharacter::IsEffectivelyObserved(bool bExitThreshold) const
{
    if (!bValidConfig || !IsValid(TargetPlayer) || !GetWorld()) return false;
    const auto Camera=TargetPlayer->FindComponentByClass<UCameraComponent>(); if (!Camera) return false;
    const FVector Start=Camera->GetComponentLocation(), Delta=GetObservationPoint()-Start;
    if (Delta.SizeSquared()>FMath::Square(Config->ObserveDistance)) return false;
    if (!Delta.IsNearlyZero() && FVector::DotProduct(Camera->GetForwardVector(),Delta.GetSafeNormal())<(bExitThreshold?Config->ExitDot:Config->EnterDot)) return false;
    FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(ObserverSight),false,this); Query.AddIgnoredActor(TargetPlayer);
    return !GetWorld()->LineTraceSingleByChannel(Hit,Start,GetObservationPoint(),ECC_Visibility,Query);
}
void AAnomalyObserverCharacter::SetObserverState(EAnomalyObserverState State)
{
    ObserverState=State;
    const bool Red=State==EAnomalyObserverState::Unobservable;
    Glow->SetLightColor(Red?FLinearColor(1.f,.005f,.001f):FLinearColor(.05f,.8f,1.f));
    if (Config && (Red?Config->RedEyeMaterial:Config->EyeMaterial)) Eye->SetMaterial(0,Red?Config->RedEyeMaterial:Config->EyeMaterial);
    UE_LOG(LogTemp,Display,TEXT("[Observer] State=%d Actor=%s"),int32(State),*GetName());
}
void AAnomalyObserverCharacter::BeginWarning()
{ if (ObserverState==EAnomalyObserverState::Dormant) SetObserverState(EAnomalyObserverState::Warning); }
void AAnomalyObserverCharacter::ActivateThreat()
{
    if (!bValidConfig || bResolved || bThreatActive || !IsValid(TargetPlayer)) return;
    ActivatedAt=LastSeen=ChangedAt=GetWorld()->GetTimeSeconds(); bObserved=true; ObservedBudget=0;
    SetObserverState(EAnomalyObserverState::Observed); Super::ActivateThreat();
}
bool AAnomalyObserverCharacter::CanDealContactDamage() const
{ return bValidConfig && GetWorld()->GetTimeSeconds()>=ActivatedAt+Config->ContactGrace; }
void AAnomalyObserverCharacter::StartChase()
{
    if (!bThreatActive || bResolved || !GetController()) return;
    if (bObserved)
    {
        if (auto AI=Cast<AAIController>(GetController())) AI->StopMovement();
        GetCharacterMovement()->StopMovementImmediately(); return;
    }
    Super::StartChase();
}
void AAnomalyObserverCharacter::Tick(float Seconds)
{
    Super::Tick(Seconds);
    if (!bThreatActive || bResolved || !bValidConfig) return;
    const float Now=GetWorld()->GetTimeSeconds();
    if (IsValid(TargetPlayer)) SetActorRotation(FRotator(0,(TargetPlayer->GetActorLocation()-GetActorLocation()).Rotation().Yaw,0));
    if (ObserverState==EAnomalyObserverState::Unobservable && Now<UnobservableUntil) { StartChase(); return; }
    if (ObserverState==EAnomalyObserverState::Unobservable) { ChangedAt=Now; bAcquiring=false; SetObserverState(EAnomalyObserverState::Unobserved); }
    const bool Seen=IsEffectivelyObserved(bObserved);
    if (Seen) { LastSeen=Now; if (!bAcquiring) { bAcquiring=true; AcquireAt=Now; } }
    else bAcquiring=false;
    const bool Desired=Seen?(bObserved || Now-AcquireAt>=Config->AcquireSeconds):(bObserved && Now-LastSeen<Config->LostSightGrace);
    if (Desired!=bObserved && Now-ChangedAt>=Config->MinimumDwell)
    { bObserved=Desired; ChangedAt=Now; SetObserverState(bObserved?EAnomalyObserverState::Observed:EAnomalyObserverState::Unobserved); }
    if (bObserved)
    {
        ObservedBudget+=Seconds;
        if (ObservedBudget>=GetEffectiveObservationTolerance())
        {
            ObservedBudget=0; bObserved=false; UnobservableUntil=Now+Config->UnobservableSeconds; ChangedAt=Now;
            SetObserverState(EAnomalyObserverState::Unobservable);
        }
    }
    StartChase();
}
void AAnomalyObserverCharacter::ResolveThreat()
{
    if (bResolved || !bThreatActive) return;
    SetObserverState(EAnomalyObserverState::Resolved); Super::ResolveThreat();
}
void AAnomalyObserverCharacter::EndPlay(const EEndPlayReason::Type Reason)
{ ObserverState=EAnomalyObserverState::Resolved; Super::EndPlay(Reason); }
FString AAnomalyObserverCharacter::DescribeState() const
{
    if (ObserverState==EAnomalyObserverState::Unobservable)
        return FString::Printf(TEXT("观察者 · 红眼 %.1f 秒无法抑制！保持距离"),FMath::Max(0.f,UnobservableUntil-GetWorld()->GetTimeSeconds()));
    return ObserverState==EAnomalyObserverState::Observed?FString::Printf(TEXT("观察者 · 正视停步 · %.1f 秒后红眼"),FMath::Max(0.f,GetEffectiveObservationTolerance()-ObservedBudget))
        :TEXT("观察者 · 背对/遮挡会接近 · 正视抑制");
}

float AAnomalyObserverCharacter::GetEffectiveObservationTolerance() const
{
    auto Environment=AAnomalyEnvironmentController::Find(GetWorld());
    return Config?Config->ObservationTolerance*(Environment?Environment->ObserveMultiplier(this):1.f):0.f;
}
