#include "AnomalyBoxActor.h"
#include "AnomalyRoundCoordinator.h"
#include "AnomalyRegionDefinition.h"
#include "AnomalyObserverCharacter.h"
#include "AnomalyObserverConfig.h"
#include "AnomalyBalanceConfig.h"
#include "AnomalyWalletComponent.h"
#include "AnomalyWorldPickup.h"
#include "Components/BoxComponent.h"
#include "NavAreas/NavArea_Null.h"
#include "AnomalyScannerComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Components/PrimitiveComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/WidgetComponent.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"
#include "Engine/World.h"

AAnomalyBoxActor::AAnomalyBoxActor() { PrimaryActorTick.bCanEverTick = false; }
void AAnomalyBoxActor::BeginPlay()
{
    Super::BeginPlay();
    InitializeDefinition();
    InitializeVisualClues();
    if (bExplorationSpawn)
    {
        // Skeletal crates collide with characters but do not export a reliable runtime nav obstacle.
        UBoxComponent* Obstacle = NewObject<UBoxComponent>(this, TEXT("V03CrateNavObstacle"));
        Obstacle->SetupAttachment(GetRootComponent());
        Obstacle->SetBoxExtent(FVector(60,60,100));
        Obstacle->SetRelativeLocation(FVector(0,0,50));
        Obstacle->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Obstacle->bDynamicObstacle = true;
        Obstacle->SetAreaClassOverride(UNavArea_Null::StaticClass());
        Obstacle->SetCanEverAffectNavigation(true);
        Obstacle->RegisterComponent();
    }
}
void AAnomalyBoxActor::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(RevealTimer);
    OnNativeBoxOpened.Clear(); OnNativeOutcomeResolved.Clear();
    Super::EndPlay(Reason);
}
void AAnomalyBoxActor::SetCoordinator(AAnomalyRoundCoordinator* Coordinator) { RoundCoordinator = Coordinator; }
void AAnomalyBoxActor::LockUnselected()
{
    if (bSelectionLocked || bOpened) return;
    bSelectionLocked = true;
    TInlineComponentArray<UPrimitiveComponent*> Primitives(this);
    for (UPrimitiveComponent* Primitive : Primitives)
        Primitive->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
    if (LockedWidgetClass)
    {
        UWidgetComponent* Label = NewObject<UWidgetComponent>(this, TEXT("T13LockedLabel"));
        Label->SetupAttachment(GetRootComponent());
        Label->SetWidgetSpace(EWidgetSpace::Screen);
        Label->SetDrawSize(FVector2D(160., 64.));
        Label->SetWidgetClass(LockedWidgetClass);
        Label->SetRelativeLocation(FVector(0., 0., 140.));
        Label->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Label->RegisterComponent();
    }
}

void AAnomalyBoxActor::InitializeDefinition()
{
    if (bDefinitionInitialized) return;
    bDefinitionInitialized = true;
    FString Reason;
    if (RegionDefinition)
    {
        if (!RegionDefinition->Validate(Reason))
        { UE_LOG(LogTemp, Error, TEXT("[Region] Invalid box region: %s"), *Reason); return; }
        RegionDefinition = DuplicateObject<UAnomalyRegionDefinition>(RegionDefinition, this);
    }
    ConfigurationStream.Initialize(bUseFixedSeeds ? ConfigurationSeed : FMath::Rand());
    OutcomeStream.Initialize(bUseFixedSeeds ? OutcomeSeed : FMath::Rand());
    static const FName PublicIDs[] = {TEXT("Safe"), TEXT("Risky"), TEXT("Unknown")};
    static const FName HiddenIDs[] = {TEXT("UnknownSafe"), TEXT("UnknownMedium"), TEXT("UnknownRisky")};
    ResolvedDefinitionID = DefinitionID.IsNone()
        ? RegionDefinition ? RegionDefinition->DrawBoxType(ConfigurationStream) : PublicIDs[ConfigurationStream.RandRange(0, 2)]
        : DefinitionID;
    const TObjectPtr<UAnomalyBoxDefinition>* Asset = Definitions.Find(ResolvedDefinitionID);
    DefinitionAsset = Asset ? *Asset : nullptr;
    if (IsValid(DefinitionAsset) && DefinitionAsset->RandomHiddenProfile)
    {
        ResolvedDefinitionID = RegionDefinition ? RegionDefinition->DrawHiddenProfile(ConfigurationStream)
            : HiddenIDs[ConfigurationStream.RandRange(0, 2)];
        Asset = Definitions.Find(ResolvedDefinitionID);
        DefinitionAsset = Asset ? *Asset : nullptr;
    }
    bDefinitionValid = IsValid(DefinitionAsset) && DefinitionAsset->Validate(Reason);
    if (!bDefinitionValid)
    { UE_LOG(LogTemp, Error, TEXT("[Box] Invalid definition ID=%s Reason=%s"), *ResolvedDefinitionID.ToString(), *Reason); return; }
    // Duplicate into the actor so future config changes cannot mutate an initialized box.
    DefinitionAsset = DuplicateObject<UAnomalyBoxDefinition>(DefinitionAsset, this);
    if (RegionDefinition && !RegionDefinition->ApplyTo(*DefinitionAsset, Reason))
    { bDefinitionValid = false; UE_LOG(LogTemp, Error, TEXT("[Region] Invalid adjusted definition: %s"), *Reason); return; }
    if (bExplorationSpawn && BalanceConfig && !BalanceConfig->ApplyTo(*DefinitionAsset,RoundId,Reason))
    { bDefinitionValid=false; UE_LOG(LogTemp,Error,TEXT("[Balance] %s"),*Reason); return; }
    UE_LOG(LogTemp, Display, TEXT("[Box] Initialized %s Definition=%s"), *GetName(), *ResolvedDefinitionID.ToString());
}

void AAnomalyBoxActor::AddVisualClue(UStaticMesh* Mesh, USkeletalMeshComponent* Crate,
    const FVector& Scale, const FVector& Center, const TCHAR* ComponentName)
{
    if (!IsValid(Mesh) || !IsValid(Crate)) return;
    UStaticMeshComponent* Visual = NewObject<UStaticMeshComponent>(this, ComponentName);
    Visual->SetupAttachment(Crate);
    Visual->SetStaticMesh(Mesh);
    Visual->SetRelativeScale3D(Scale);
    Visual->SetRelativeLocation(Center);
    Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Visual->SetGenerateOverlapEvents(false);
    Visual->SetCanEverAffectNavigation(false);
    Visual->RegisterComponent();
}

void AAnomalyBoxActor::InitializeVisualClues()
{
    if (!bDefinitionValid || !IsValid(DefinitionAsset)) return;
    USkeletalMeshComponent* Crate = nullptr;
    TInlineComponentArray<USkeletalMeshComponent*> Meshes(this);
    for (USkeletalMeshComponent* Mesh : Meshes)
        if (Mesh->GetName().StartsWith(TEXT("CrateMesh"))) { Crate = Mesh; break; }
    if (!IsValid(Crate)) return;
    const FBoxSphereBounds Bounds = Crate->GetLocalBounds();
    const FVector Extent = Bounds.BoxExtent;
    if (Extent.GetMin() <= KINDA_SMALL_NUMBER) return;
    // Source attachments fit a 100 cm body. Scale with the existing animated crate.
    const FVector Fit(Extent.X / 50.0, Extent.Y / 50.0, Extent.Z / 50.0);
    const FVector Center = Bounds.Origin;
    VisualStream.Initialize(ConfigurationStream.GetInitialSeed() ^ 0x53564E1);
    if (VisualStream.FRand() < DefinitionAsset->MetalChance)
        AddVisualClue(MetalBraceMesh, Crate, Fit, Center, TEXT("T11EMetalBrace"));
    if (VisualStream.FRand() < DefinitionAsset->WarningChance)
        AddVisualClue(WarningMarkerMesh, Crate, Fit, Center, TEXT("T11EWarningMarker"));
    if (VisualStream.FRand() < DefinitionAsset->WearChance)
        AddVisualClue(WearPatchMesh, Crate, Fit, Center, TEXT("T11EWearPatch"));
}

int32 AAnomalyBoxActor::NativeSelectOutcome(double UnitRoll) const
{ return bDefinitionValid && DefinitionAsset ? DefinitionAsset->SelectOutcome(UnitRoll) : INDEX_NONE; }

bool AAnomalyBoxActor::NativeInteract(AActor* Interactor, int32 DebugOutcomeIndex)
{
    if (IsValid(Interactor))
        if (UAnomalyScannerComponent* Scanner = Interactor->FindComponentByClass<UAnomalyScannerComponent>()) Scanner->CancelScan();
    InitializeDefinition();
    if (!IsValid(Interactor) || bOpened || bSelectionLocked || !bDefinitionValid) return false;
    if (!RoundCoordinator.IsValid() || !RoundCoordinator->ValidateBoxInteraction(Interactor, this)
        || !RoundCoordinator->TryLockSelection(this)) return false;
    bOpened = true; OpeningInteractor = Interactor; PendingDebugOutcome = DebugOutcomeIndex;
    RoundCoordinator->RecordRegionEvent(this, TEXT("open"));
    TInlineComponentArray<UPrimitiveComponent*> Primitives(this);
    for (UPrimitiveComponent* P : Primitives) P->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
    OnNativeBoxOpened.Broadcast(this); PresentBoxOpened(this);
    TInlineComponentArray<USkeletalMeshComponent*> Meshes(this);
    for (USkeletalMeshComponent* Mesh : Meshes)
    {
        if (Mesh->GetName().StartsWith(TEXT("CrateMesh")) && Mesh->GetSkeletalMeshAsset() && OpeningAnimation)
        { Mesh->PlayAnimation(OpeningAnimation, false); break; }
    }
    if (OpeningSound) UGameplayStatics::PlaySoundAtLocation(this, OpeningSound, GetActorLocation());
    UE_LOG(LogTemp, Display, TEXT("[Box] Opened %s"), *GetName());
    GetWorldTimerManager().SetTimer(RevealTimer, this, &AAnomalyBoxActor::ResolveOutcome, FMath::Max(0.001, RevealDelay), false);
    return true;
}

bool AAnomalyBoxActor::CanScan() const
{
    return bDefinitionInitialized && bDefinitionValid && IsValid(DefinitionAsset) && !bOpened && !bResolved
        && !bSelectionLocked && RoundCoordinator.IsValid() && RoundCoordinator->IsSelectableBox(this);
}

FAnomalyScanReading AAnomalyBoxActor::GetCachedReading(EAnomalyEquipment Instrument) const
{
    const FAnomalyScanReading* Cached = ScanCache.Find(Instrument);
    return Cached ? *Cached : FAnomalyScanReading();
}

bool AAnomalyBoxActor::CompleteScan(EAnomalyEquipment Instrument, FAnomalyScanReading& Reading)
{
    Reading = FAnomalyScanReading();
    if (!CanScan() || static_cast<uint8>(Instrument) >= 3) return false;
    if (const FAnomalyScanReading* Cached = ScanCache.Find(Instrument)) { Reading = *Cached; return true; }
    const UAnomalyBoxDefinition& Data = *DefinitionAsset;
    const auto Player=UGameplayStatics::GetPlayerPawn(this,0);
    const auto Scanner=IsValid(Player)?Player->FindComponentByClass<UAnomalyScannerComponent>():nullptr;
    const double Precision=Scanner && bExplorationSpawn ? FMath::Clamp(double(Scanner->GetPrecisionReduction()),0.,.75) : 0.;
    const double Error=Data.ScanProbabilityError*(1.-Precision);
    Reading.bScanned = true;
    Reading.Reliability = FText::FromString(Data.HiddenProfile || Data.ScanProbabilityError > 0.0 ? TEXT("低") : TEXT("高"));
    if (Precision>0) Reading.Reliability=FText::FromString(TEXT("精度改善 · 仍不保证结果"));
    if (Instrument == EAnomalyEquipment::MetalDetector)
    {
        // int64 keeps outward rounding valid even at the largest legal int32 reward.
        const auto StableHundreds = [](double Value)
        {
            const double Rounded = FMath::RoundToDouble(Value);
            return FMath::Abs(Value - Rounded) < 1.e-8 ? Rounded : Value;
        };
        const double Low = StableHundreds(double(Data.ValueMin) * (1.-(1.-Data.ValueLowerScale)*(1.-Precision)) / 100.0);
        const double High = StableHundreds(double(Data.ValueMax) * (1.+(Data.ValueUpperScale-1.)*(1.-Precision)) / 100.0);
        if (!FMath::IsFinite(High) || High >= double(MAX_int64 / 100))
        { Reading = FAnomalyScanReading(); return false; }
        Reading.ValueMin = FMath::Max<int64>(0, FMath::FloorToInt64(Low) * 100);
        Reading.ValueMax = FMath::CeilToInt64(High) * 100;
    }
    else
    {
        const bool bBio = Instrument == EAnomalyEquipment::BioDetector;
        const double Probability = bBio ? Data.ThreatChance : Data.HighValueChance;
        const double LowerBoundary = bBio ? .15 : .35;
        const double UpperBoundary = bBio ? .30 : .50;
        const auto Level = [LowerBoundary, UpperBoundary](double Value)
        {
            // Decimal configuration boundaries may differ by a floating-point ULP.
            return Value + 1.e-9 < LowerBoundary ? 0 : Value + 1.e-9 < UpperBoundary ? 1 : 2;
        };
        const int32 Low = Level(FMath::Clamp(Probability - Error, 0.0, 1.0));
        const int32 High = Level(FMath::Clamp(Probability + Error, 0.0, 1.0));
        const TCHAR* Names[] = {TEXT("低"), TEXT("中"), TEXT("高")};
        Reading.Level = FText::FromString(Low == High ? FString(Names[Low]) : FString::Printf(TEXT("%s–%s"), Names[Low], Names[High]));
    }
    // Commit once on the game thread, after all fallible reading construction and before any event.
    // A repeated completion sees the cache above, including when the last charge was consumed.
    if (RoundCoordinator.IsValid() && RoundCoordinator->PlayMode == EAnomalyPlayMode::Exploration)
    {
        if (!Scanner || !Scanner->CommitCharge(Instrument)) { Reading = FAnomalyScanReading(); return false; }
    }
    ScanCache.Add(Instrument, Reading);
    if (RoundCoordinator.IsValid()) RoundCoordinator->RecordRegionEvent(this, TEXT("scan"));
    return true;
}

FTransform AAnomalyBoxActor::SpawnTransformFor(bool bThreat) const
{
    if (bThreat && bExplorationSpawn)
        return FTransform(GetActorQuat(), GetActorTransform().TransformPosition(ExplorationThreatOffset));
    TInlineComponentArray<USceneComponent*> Components(this);
    const FString Name = bThreat ? TEXT("CreatureSpawnPoint") : TEXT("LootSpawnPoint");
    for (USceneComponent* C : Components) if (C->GetName().StartsWith(Name)) return C->GetComponentTransform();
    return GetActorTransform();
}

void AAnomalyBoxActor::ResolveOutcome()
{
    if (bResolved || !bOpened || !bDefinitionValid) return;
    if (RoundCoordinator.IsValid() && !RoundCoordinator->CanResolveBox(this)) return;
    bResolved = true;
    OutcomeRoll = bForceOutcome ? PendingDebugOutcome : DefinitionAsset->SelectOutcome(OutcomeStream.FRand());
    if (OutcomeRoll < 0 || OutcomeRoll > 2)
    { UE_LOG(LogTemp, Error, TEXT("[Box] Invalid forced outcome %d"), OutcomeRoll); if (RoundCoordinator.IsValid()) RoundCoordinator->FailWithError(); return; }
    const bool bThreat = OutcomeRoll == 2;
    if (bThreat) ResolvedThreatClass=SelectThreatClass();
    const TSubclassOf<AActor> ResultClass = bThreat ? ResolvedThreatClass : OutcomeRoll == 0 ? HighValueClass : TrashClass;
    if (OutcomeRoll == 0) HighValueAmount = OutcomeStream.RandRange(DefinitionAsset->ValueMin, DefinitionAsset->ValueMax);
    FActorSpawnParameters Parameters;
    Parameters.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    AActor* Result = bExplorationSpawn && !bThreat && RoundCoordinator.IsValid()
        ? RoundCoordinator->SpawnLoot(OutcomeRoll, OutcomeRoll == 0 ? HighValueAmount : TrashAmount,
            FTransform(GetActorQuat(), GetActorLocation() + FVector(0., -130., 35.)), RoundId)
        : bThreat && bExplorationSpawn ? SpawnThreatActor()
        : ResultClass ? GetWorld()->SpawnActor<AActor>(ResultClass, SpawnTransformFor(bThreat), Parameters) : nullptr;
    if (!Result) UE_LOG(LogTemp, Warning, TEXT("[Box] Result actor spawn failed Outcome=%d"), OutcomeRoll);
    if (bExplorationSpawn && !bThreat && !IsValid(Result))
    { if (RoundCoordinator.IsValid()) RoundCoordinator->FailWithError(); return; }
    if (!bExplorationSpawn && !bThreat && IsValid(OpeningInteractor))
    {
        if (UAnomalyWalletComponent* Wallet = OpeningInteractor->FindComponentByClass<UAnomalyWalletComponent>())
            Wallet->NativeAddMoney(OutcomeRoll == 0 ? HighValueAmount : TrashAmount);
        else UE_LOG(LogTemp, Error, TEXT("[Wallet] Interactor has no native wallet component"));
    }
    UE_LOG(LogTemp, Display, TEXT("[Box] Outcome=%d Reward=%d"), OutcomeRoll, OutcomeRoll == 0 ? HighValueAmount : OutcomeRoll == 1 ? TrashAmount : 0);
    if (RoundCoordinator.IsValid()) RoundCoordinator->RecordRegionEvent(this,
        bThreat ? TEXT("threat") : TEXT("reward"), OutcomeRoll == 0 ? HighValueAmount : OutcomeRoll == 1 ? TrashAmount : 0);
    if (!bExplorationSpawn) PresentOutcome(OutcomeRoll, Result, IsValid(Result));
    OnNativeOutcomeResolved.Broadcast(this, OutcomeRoll, Result, IsValid(Result));
}

TSubclassOf<AActor> AAnomalyBoxActor::SelectThreatClass() const
{
    if (!bExplorationSpawn || !bUseObserverPool || !RegionDefinition) return ThreatClass;
    const bool Chaser=RegionDefinition->AllowedAnomalies.Contains(TEXT("Chaser"));
    const bool Observer=RegionDefinition->AllowedAnomalies.Contains(TEXT("Observer"));
    FString Why;
    if (Observer && (!ObserverClass || !ObserverConfig || !ObserverConfig->Validate(Why))) return nullptr;
    FRandomStream Encounter(ConfigurationStream.GetInitialSeed() ^ 0x4F425331);
    const bool PickObserver=Observer && (!Chaser || Encounter.FRand()<ObserverConfig->MixedPoolWeight);
    UE_LOG(LogTemp,Display,TEXT("[ObserverPool] Region=%s Type=%s Seed=%d"),*RegionDefinition->RegionID.ToString(),PickObserver?TEXT("Observer"):TEXT("Chaser"),Encounter.GetInitialSeed());
    return PickObserver?ObserverClass:ThreatClass;
}
AActor* AAnomalyBoxActor::SpawnThreatActor()
{
    if (!ResolvedThreatClass) return nullptr;
    const FTransform Transform=GetThreatSpawnTransform();
    if (!bExplorationSpawn)
    {
        FActorSpawnParameters P; P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        return GetWorld()->SpawnActor<AActor>(ResolvedThreatClass,Transform,P);
    }
    auto Actor=GetWorld()->SpawnActorDeferred<AActor>(ResolvedThreatClass,Transform,this,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    if (!Actor) return nullptr;
    if (auto Observer=Cast<AAnomalyObserverCharacter>(Actor)) Observer->Config=ObserverConfig;
    Actor->FinishSpawning(Transform); return Actor;
}
