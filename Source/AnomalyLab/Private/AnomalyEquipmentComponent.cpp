#include "AnomalyEquipmentComponent.h"
#include "AnomalyScannerComponent.h"
#include "AnomalyRoundCoordinator.h"
#include "Camera/CameraComponent.h"
#include "Components/InputComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "InputCoreTypes.h"
#include "EngineUtils.h"
#include "TimerManager.h"

UAnomalyEquipmentComponent::UAnomalyEquipmentComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
}

void UAnomalyEquipmentComponent::BeginPlay()
{
    Super::BeginPlay();
    ACharacter* Character = Cast<ACharacter>(GetOwner());
    if (!IsValid(Character) || !Character->IsLocallyControlled()) return;
    UCameraComponent* Camera = Character->FindComponentByClass<UCameraComponent>();
    if (!IsValid(Camera))
    {
        UE_LOG(LogTemp, Error, TEXT("[T11E] Player has no camera for held equipment"));
        return;
    }
    HeldMesh = NewObject<UStaticMeshComponent>(Character, TEXT("T11EHeldEquipment"));
    HeldMesh->SetupAttachment(Camera);
    HeldMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    HeldMesh->SetGenerateOverlapEvents(false);
    HeldMesh->SetCanEverAffectNavigation(false);
    HeldMesh->SetOnlyOwnerSee(true);
    HeldMesh->RegisterComponent();
    HeldMesh->SetRelativeLocation(FVector(43.0, 24.0, -24.0));
    HeldMesh->SetRelativeRotation(FRotator(0.0, 0.0, -7.0));
    UpdateHeldMesh();
    TryBindInput();
    if (!BoundInput.IsValid())
        GetWorld()->GetTimerManager().SetTimer(InputRetryTimer, this, &UAnomalyEquipmentComponent::TryBindInput, 0.1f, true);
}

void UAnomalyEquipmentComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if (GetWorld())
    {
        GetWorld()->GetTimerManager().ClearTimer(InputRetryTimer);
        GetWorld()->GetTimerManager().ClearTimer(EquipTransitionTimer);
    }
    BoundInput.Reset();
    if (IsValid(HeldMesh)) HeldMesh->DestroyComponent();
    Super::EndPlay(Reason);
}

void UAnomalyEquipmentComponent::TryBindInput()
{
    ACharacter* Character = Cast<ACharacter>(GetOwner());
    if (!IsValid(Character) || !Character->IsLocallyControlled()) return;
    UInputComponent* Input = Character->InputComponent;
    if (!IsValid(Input)) return;
    if (BoundInput.Get() == Input) return;
    Input->BindKey(EKeys::One, IE_Pressed, this, &UAnomalyEquipmentComponent::EquipScanner).bConsumeInput = true;
    Input->BindKey(EKeys::Two, IE_Pressed, this, &UAnomalyEquipmentComponent::EquipGun).bConsumeInput = true;
    BoundInput = Input;
    GetWorld()->GetTimerManager().ClearTimer(InputRetryTimer);
}

bool UAnomalyEquipmentComponent::CanEquip() const
{
    const ACharacter* Character = Cast<ACharacter>(GetOwner());
    return IsValid(Character) && Character->IsLocallyControlled()
        && IsValid(Character->GetCharacterMovement())
        && Character->GetCharacterMovement()->MovementMode != MOVE_None;
}

void UAnomalyEquipmentComponent::EquipScanner()
{
    if (RouteDecisionInput(true)) return;
    if (!CanEquip()) return;
    CancelUse();
    if (CurrentEquipment == EAnomalyEquipment::Gun) CurrentEquipment = LastScanner;
    else CurrentEquipment = static_cast<EAnomalyEquipment>((static_cast<uint8>(CurrentEquipment) + 1) % 3);
    LastScanner = CurrentEquipment;
    BeginEquipTransition();
    ShowFeedback();
}

void UAnomalyEquipmentComponent::EquipGun()
{
    if (RouteDecisionInput(false)) return;
    if (!CanEquip() || CurrentEquipment == EAnomalyEquipment::Gun) return;
    CancelUse();
    LastScanner = CurrentEquipment;
    CurrentEquipment = EAnomalyEquipment::Gun;
    BeginEquipTransition();
    ShowFeedback();
}

bool UAnomalyEquipmentComponent::RouteDecisionInput(bool bContinue)
{
    if (!GetWorld()) return false;
    for (TActorIterator<AAnomalyRoundCoordinator> It(GetWorld()); It; ++It)
    {
        AAnomalyRoundCoordinator* Coordinator = *It;
        if (IsValid(Coordinator) && Coordinator->IsDecisionActive())
        {
            if (bContinue) Coordinator->ContinueRun();
            else Coordinator->CashOut();
            return true;
        }
    }
    return false;
}

void UAnomalyEquipmentComponent::BeginEquipTransition()
{
    if (!IsValid(HeldMesh) || !GetWorld()) return;
    GetWorld()->GetTimerManager().ClearTimer(EquipTransitionTimer);
    HeldMesh->SetRelativeLocation(FVector(43.0, 24.0, -42.0));
    GetWorld()->GetTimerManager().SetTimer(EquipTransitionTimer, this,
        &UAnomalyEquipmentComponent::FinishEquipTransition, 0.12f, false);
}

void UAnomalyEquipmentComponent::FinishEquipTransition()
{
    UpdateHeldMesh();
    if (IsValid(HeldMesh)) HeldMesh->SetRelativeLocation(FVector(43.0, 24.0, -24.0));
}

void UAnomalyEquipmentComponent::CancelUse()
{
    if (IsValid(GetOwner()))
        if (UAnomalyScannerComponent* Scanner = GetOwner()->FindComponentByClass<UAnomalyScannerComponent>()) Scanner->CancelScan();
}

void UAnomalyEquipmentComponent::UpdateHeldMesh()
{
    if (!IsValid(HeldMesh)) return;
    UStaticMesh* Mesh = CurrentEquipment == EAnomalyEquipment::MetalDetector ? MetalDetectorMesh
        : CurrentEquipment == EAnomalyEquipment::BioDetector ? BioDetectorMesh
        : CurrentEquipment == EAnomalyEquipment::MatterAnalyzer ? MatterAnalyzerMesh : GunMesh;
    HeldMesh->SetStaticMesh(Mesh);
    HeldMesh->SetVisibility(IsValid(Mesh));
}

void UAnomalyEquipmentComponent::ShowFeedback() const
{
    if (!GEngine) return;
    const TCHAR* Name = CurrentEquipment == EAnomalyEquipment::MetalDetector ? TEXT("金属价值探测仪")
        : CurrentEquipment == EAnomalyEquipment::BioDetector ? TEXT("生物探测仪")
        : CurrentEquipment == EAnomalyEquipment::MatterAnalyzer ? TEXT("物质分析仪") : TEXT("武器功能尚未启用");
    GEngine->AddOnScreenDebugMessage(11011, 2.0f, FColor::Cyan, FString::Printf(TEXT("装备: %s"), Name));
}
