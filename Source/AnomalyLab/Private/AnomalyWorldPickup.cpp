#include "AnomalyWorldPickup.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"

AAnomalyWorldPickup::AAnomalyWorldPickup()
{
    PrimaryActorTick.bCanEverTick = true;
    InteractionSphere = CreateDefaultSubobject<USphereComponent>(TEXT("PickupInteraction"));
    SetRootComponent(InteractionSphere);
    InteractionSphere->SetSphereRadius(32.f);
    InteractionSphere->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    InteractionSphere->SetCollisionResponseToAllChannels(ECR_Ignore);
    InteractionSphere->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    InteractionSphere->SetCanEverAffectNavigation(false);
    ItemMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ItemMesh"));
    ItemMesh->SetupAttachment(InteractionSphere);
    ItemMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    ItemMesh->SetCanEverAffectNavigation(false);
    Glow = CreateDefaultSubobject<UPointLightComponent>(TEXT("ItemGlow"));
    Glow->SetupAttachment(InteractionSphere);
    Glow->SetIntensity(90.f);
    Glow->SetAttenuationRadius(130.f);
    Glow->SetCastShadows(false);
}
bool AAnomalyWorldPickup::InitializeItem(const UAnomalyItemDefinition* Definition, int32 Value, int32 RoundId)
{
    if (bInitialized || !IsValid(Definition) || Definition->ItemId.IsNone() || !Definition->Mesh || Value < 0) return false;
    bInitialized = true;
    bPickable = Definition->bPickable;
    Item.InstanceId = FGuid::NewGuid();
    Item.ItemId = Definition->ItemId;
    Item.DisplayName = Definition->DisplayName;
    Item.Value = Definition->bTrash ? Definition->TrashValue : Value;
    Item.SourceRoundId = RoundId;
    ItemMesh->SetStaticMesh(Definition->Mesh);
    ItemMesh->SetMaterial(0, Definition->Material);
    ItemMesh->SetRelativeScale3D(Definition->MeshScale);
    Glow->SetLightColor(Definition->GlowColour);
    return true;
}
void AAnomalyWorldPickup::Tick(float Seconds)
{
    Super::Tick(Seconds);
    // Slow rotation only: no flashing, lifetime expiry, physics or reward callbacks.
    ItemMesh->AddLocalRotation(FRotator(0, 25.f * Seconds, 0));
}
