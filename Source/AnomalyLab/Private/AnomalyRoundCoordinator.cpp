#include "AnomalyRoundCoordinator.h"
#include "AnomalyBoxActor.h"
#include "AnomalyRegionDefinition.h"
#include "AnomalyWorldPickup.h"
#include "AnomalyInventoryComponent.h"
#include "AnomalyProgressionSubsystem.h"
#include "AnomalyProgressionConfig.h"
#include "AnomalyTransitionSubsystem.h"
#include "AnomalyPlacementConfig.h"
#include "AnomalyEnvironment.h"
#include "AnomalyLoadingWidget.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InputComponent.h"
#include "InputCoreTypes.h"
#include "Components/AudioComponent.h"
#include "Components/PointLightComponent.h"
#include "Sound/SoundBase.h"
#include "AssetCompilingManager.h"
#include "AnomalyThreatCharacter.h"
#include "AnomalyObserverCharacter.h"
#include "AnomalyBalanceConfig.h"
#include "Engine/World.h"
#include "TimerManager.h"
#include "AnomalyMigrationSmoke.h"
#include "AnomalyT14Smoke.h"
#include "AnomalyT15Smoke.h"
#include "AnomalyV03Smoke.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Components/SceneComponent.h"
#include "AnomalyDecisionWidget.h"
#include "AnomalyWalletComponent.h"
#include "AnomalyScannerComponent.h"
#include "AnomalyHealthComponent.h"
#include "AnomalyStatusWidget.h"
#include "Blueprint/UserWidget.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Blueprint/WidgetTree.h"
#include "Components/TextBlock.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Camera/CameraComponent.h"
#include "AnomalyExplorationWidget.h"
#include "NavigationSystem.h"
#include "NavMesh/RecastNavMesh.h"
#include "UObject/UObjectGlobals.h"

AAnomalyRoundCoordinator::AAnomalyRoundCoordinator()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickInterval = .05f;
    PrimaryActorTick.TickGroup = TG_PostUpdateWork;
    SpawnRoot = CreateDefaultSubobject<USceneComponent>(TEXT("T13SpawnRoot"));
    SetRootComponent(SpawnRoot);
    BoxPointLeft = CreateDefaultSubobject<USceneComponent>(TEXT("T13BoxPointLeft"));
    BoxPointMiddle = CreateDefaultSubobject<USceneComponent>(TEXT("T13BoxPointMiddle"));
    BoxPointRight = CreateDefaultSubobject<USceneComponent>(TEXT("T13BoxPointRight"));
    BoxPointLeft->SetupAttachment(SpawnRoot);
    BoxPointMiddle->SetupAttachment(SpawnRoot);
    BoxPointRight->SetupAttachment(SpawnRoot);
    BoxPointLeft->SetRelativeLocation(FVector(0., -220., 0.));
    BoxPointMiddle->SetRelativeLocation(FVector::ZeroVector);
    BoxPointRight->SetRelativeLocation(FVector(0., 220., 0.));
}
void AAnomalyRoundCoordinator::BeginPlay()
{
    Super::BeginPlay();
    RunId=FGuid::NewGuid();
    if (PlayMode == EAnomalyPlayMode::Exploration && bUseRegionRules)
    {
        RegionStream.Initialize(bUseFixedRegionSeed ? RegionSeed : FMath::Rand());
        for (TObjectPtr<UAnomalyRegionDefinition>& Region : RegionRules)
            if (IsValid(Region)) Region = DuplicateObject<UAnomalyRegionDefinition>(Region, this);
    }
    if (DecisionWidgetClass && IsValid(GetWorld()->GetFirstPlayerController()))
    {
        DecisionWidget = CreateWidget<UAnomalyDecisionWidget>(GetWorld()->GetFirstPlayerController(), DecisionWidgetClass);
        if (IsValid(DecisionWidget))
        {
            DecisionWidget->AddToViewport(100);
            DecisionWidget->SetVisibility(ESlateVisibility::Collapsed);
        }
    }
    BindPlayerHealth();
    SetActorTickEnabled(PlayMode == EAnomalyPlayMode::Exploration);
    if (PlayMode == EAnomalyPlayMode::Exploration)
    {
        ACharacter* Player = UGameplayStatics::GetPlayerCharacter(this, 0);
        if (IsValid(Player))
        {
            Inventory = NewObject<UAnomalyInventoryComponent>(Player, TEXT("V03Inventory"));
            Player->AddInstanceComponent(Inventory);
            Inventory->RegisterComponent();
        }
        InputPriority = 10;
        EnableInput(GetWorld()->GetFirstPlayerController());
        if (InputComponent)
        {
            InputComponent->BindKey(EKeys::E, IE_Pressed, this, &AAnomalyRoundCoordinator::HandleExploreInteract).bConsumeInput = false;
            InputComponent->BindKey(EKeys::Up, IE_Pressed, this, &AAnomalyRoundCoordinator::ShopUp);
            InputComponent->BindKey(EKeys::Down, IE_Pressed, this, &AAnomalyRoundCoordinator::ShopDown);
            InputComponent->BindKey(EKeys::Enter, IE_Pressed, this, &AAnomalyRoundCoordinator::ShopBuy);
            InputComponent->BindKey(EKeys::F, IE_Pressed, this, &AAnomalyRoundCoordinator::HandleDecoyInput);
            if(bAwaitLevelLaunch) InputComponent->BindKey(EKeys::R,IE_Pressed,this,&AAnomalyRoundCoordinator::BlockV05Restart);
        }
    }
    SetPhase(EAnomalyRoundPhase::Initializing);
    SetState(0);
    if (bAwaitLevelLaunch)
    {
        RunId.Invalidate();
        Progression=GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>();
        FString Reason;
        auto Travel=GetGameInstance()->GetSubsystem<UAnomalyTransitionSubsystem>(); FAnomalyLaunchContext Launch;
        if(!Progression || !Progression->Configure(ProgressionConfig,Reason) || !Travel->ClaimLab(this,Launch,Reason))
        {
            // Explicit map-inspection fixture is read-only; normal direct loading returns safely.
            if(!FParse::Param(FCommandLine::Get(),TEXT("AnomalyV05InspectLevel"))) Travel->RejectLab(GetWorld(),Reason);
            UE_LOG(LogTemp,Warning,TEXT("[Lab] %s"),*Reason);
        }
        else
        {
            bV05Lab=true; bAwaitLevelLaunch=false; RunId=Launch.Run; RegionSeed=Launch.Seed; RegionStream.Initialize(RegionSeed);
            const auto Config=Progression->GetConfig();
            if(!Inventory || !PlayerHealth || !Config) { FailWithError(); }
            else
            {
                V05Capacity=Launch.Equipment.BackpackLevel>0?5:4;
                V05ChargeBonus=Launch.Equipment.BatteryLevel*Config->ChargesPerLevel;
                V05Precision=FMath::Min(Config->PrecisionCap,Launch.Equipment.PrecisionLevel*Config->PrecisionPerLevel);
                DecoysRemaining=Launch.Decoys;
                // Coordinator can BeginPlay before the pawn scanner: apply after all components initialize.
                V05StartTimer=GetWorldTimerManager().SetTimerForNextTick(this,&AAnomalyRoundCoordinator::InitializeV05Run);
            }
        }
    }
    else if (PlayMode==EAnomalyPlayMode::Exploration && bUsePreparation)
    {
        Progression=GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>();
        FString Reason;
        if (!Progression || !Progression->Configure(ProgressionConfig,Reason)) { Notify(Reason); FailWithError(); }
        else { ShopMessage=Progression->GetLoadMessage(); SetPhase(EAnomalyRoundPhase::Preparation); FreezePlayer(true); }
    }
    else SpawnInitialBox();
#if !UE_BUILD_SHIPPING
    if (FParse::Param(FCommandLine::Get(), TEXT("AnomalyV03Smoke")))
        GetWorld()->SpawnActor<AAnomalyV03Smoke>();
    if (FParse::Param(FCommandLine::Get(), TEXT("AnomalyMigrationSmoke")))
        GetWorld()->SpawnActor<AAnomalyMigrationSmoke>();
    if (FParse::Param(FCommandLine::Get(), TEXT("AnomalyT14Smoke")))
        GetWorld()->SpawnActor<AAnomalyT14Smoke>();
    if (FParse::Param(FCommandLine::Get(), TEXT("AnomalyT15Smoke")))
        GetWorld()->SpawnActor<AAnomalyT15Smoke>();
#endif
}
AActor* AAnomalyRoundCoordinator::TraceExplorationTarget(const AActor* Interactor) const
{
    if (!IsValid(Interactor) || !GetWorld()) return nullptr;
    const UCameraComponent* Camera = Interactor->FindComponentByClass<UCameraComponent>();
    if (!IsValid(Camera)) return nullptr;
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(T20Interaction), false, Interactor);
    const FVector Start = Camera->GetComponentLocation();
    const float Range = FMath::Clamp(InteractionRange, 1.f, 300.f);
    if (!GetWorld()->LineTraceSingleByChannel(Hit, Start, Start + Camera->GetForwardVector() * Range, ECC_Visibility, Params)) return nullptr;
    return Hit.GetActor();
}
AAnomalyBoxActor* AAnomalyRoundCoordinator::TraceExplorationBox(const AActor* Interactor) const
{ return Cast<AAnomalyBoxActor>(TraceExplorationTarget(Interactor)); }
void AAnomalyRoundCoordinator::Notify(const FString& Message)
{ FeedbackMessage = Message; FeedbackUntil = GetWorld()->GetTimeSeconds() + 2.5f; UE_LOG(LogTemp, Display, TEXT("[V03] %s"), *Message); }
void AAnomalyRoundCoordinator::RecordRegionEvent(const AAnomalyBoxActor* Box, FName Event, int32 Value)
{
    if (PlayMode != EAnomalyPlayMode::Exploration || !bUseRegionRules || !IsValid(Box)
        || !IsValid(Box->RegionDefinition) || Box->RoundId != RoundId || !CandidateBoxes.Contains(Box)) return;
    FAnomalyRegionStats& Stats = RegionStats.FindOrAdd(Box->RegionDefinition->RegionID);
    if (Event == TEXT("open")) ++Stats.OpenCount;
    else if (Event == TEXT("scan")) ++Stats.ScanCount;
    else if (Event == TEXT("reward")) Stats.Reward += FMath::Max(0, Value);
    else if (Event == TEXT("threat")) ++Stats.Threat;
    else if (Event == TEXT("survive")) ++Stats.Survive;
    else return;
    RecordTelemetry(Event.ToString(),FString::Printf(TEXT("%s:%d"),*Box->RegionDefinition->RegionID.ToString(),Value));
    // Reward is generated face value, not inventory/payout; this never writes Wallet.
    UE_LOG(LogTemp, Display, TEXT("[Region] id=%s round=%d event=%s open_count=%d scan_count=%d reward=%lld threat=%d survive=%d"),
        *Box->RegionDefinition->RegionID.ToString(), RoundId, *Event.ToString(), Stats.OpenCount, Stats.ScanCount,
        Stats.Reward, Stats.Threat, Stats.Survive);
}
bool AAnomalyRoundCoordinator::TryPickup(AActor* Interactor, AAnomalyWorldPickup* Pickup)
{
    if (PlayMode != EAnomalyPlayMode::Exploration || NativeState == 3 || bExtractionPending || bPrototypeError || !IsValid(Inventory)
        || Interactor != UGameplayStatics::GetPlayerCharacter(this, 0) || !IsValid(Pickup) || !WorldLoot.Contains(Pickup)
        || TraceExplorationTarget(Interactor) != Pickup || !IsValid(PlayerHealth) || PlayerHealth->bDead) return false;
    LastInteractionFrame = GFrameCounter;
    if (Inventory->GetCount() >= Inventory->GetCapacity()) { Notify(TEXT("背包已满 · 物品仍留在原地")); return false; }
    const FAnomalyItemInstance Item = Pickup->Item;
    if (!Inventory->TryStore(Pickup)) return false;
    WorldLoot.Remove(Pickup);
    EmitFeedback(TEXT("Pickup"));
    Notify(FString::Printf(TEXT("已拾取 %s  +携带 $%d"), *Item.DisplayName.ToString(), Item.Value));
    return true;
}
void AAnomalyRoundCoordinator::HandleExploreInteract()
{
    if (bAwaitLevelLaunch || PlayMode != EAnomalyPlayMode::Exploration || NativeState == 3) return;
    if (IsPreparing()) { StartPreparedRun(); return; }
    ACharacter* Player = UGameplayStatics::GetPlayerCharacter(this, 0);
    if (AAnomalyWorldPickup* Pickup = Cast<AAnomalyWorldPickup>(TraceExplorationTarget(Player)))
    { TryPickup(Player, Pickup); return; }
    if(auto Terminal=Cast<AAnomalyEnvironmentTerminal>(TraceExplorationTarget(Player))) { Terminal->Interact(Player); return; }
    if (AtEntrance(Player)) ConfirmExtraction(Player);
}
int32 AAnomalyRoundCoordinator::BuildExplorationNavigation(UObject* WorldContextObject)
{
#if WITH_EDITOR
    UWorld* World = IsValid(WorldContextObject) ? WorldContextObject->GetWorld() : nullptr;
    if (!World || World->IsGameWorld()) return -1;
    FlushAsyncLoading();
    World->FlushLevelStreaming(EFlushLevelStreamingType::Full);
    UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    if (!Nav) return -1;
    const bool bRestoreEditorLock = !Nav->GetIsAutoUpdateEnabled();
    // Python map loading can leave the async-load lock until the next editor tick.
    // All loading is now flushed; release it before collecting the generated geometry.
    Nav->RemoveNavigationBuildLock(ENavigationBuildLock::NoUpdateInEditor | ENavigationBuildLock::AsyncLoadLock,
        UNavigationSystemV1::ELockRemovalRebuildAction::NoRebuild);
    Nav->Tick(0.f);
    Nav->Build(); // Synchronously finishes tile generation in editor worlds.
    if (bRestoreEditorLock) Nav->AddNavigationBuildLock(ENavigationBuildLock::NoUpdateInEditor);
    ARecastNavMesh* Recast = Cast<ARecastNavMesh>(Nav->GetDefaultNavDataInstance(FNavigationSystem::DontCreate));
    if (!Recast || Nav->IsNavigationBuildInProgress()) return -1;
    const int32 ValidTiles = Recast->GetNumActiveTiles();
    UE_LOG(LogTemp, Display, TEXT("[T20] Navigation built: %d valid tiles"), ValidTiles);
    return ValidTiles;
#else
    return -1;
#endif
}
bool AAnomalyRoundCoordinator::ValidateBoxInteraction(const AActor* Interactor, const AAnomalyBoxActor* Box) const
{
    // Legacy automation and accepted Blueprint routing retain their original semantics.
    if (PlayMode == EAnomalyPlayMode::LegacyPrototype) return true;
    const ACharacter* Player = UGameplayStatics::GetPlayerCharacter(this, 0);
    return IsValid(Player) && Interactor == Player && LastInteractionFrame != GFrameCounter && IsSelectableBox(Box) && TraceExplorationBox(Interactor) == Box;
}
void AAnomalyRoundCoordinator::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(bV05Lab) Telemetry.Tick(this);
    if (PlayMode != EAnomalyPlayMode::Exploration) return;
    ACharacter* Player = UGameplayStatics::GetPlayerCharacter(this, 0);
    APlayerController* PC = IsValid(Player) ? Cast<APlayerController>(Player->GetController()) : nullptr;
    if (!IsValid(PC)) return;
    if (!IsValid(ExplorationWidget) && ExplorationWidgetClass)
    {
        ExplorationWidget = CreateWidget<UAnomalyExplorationWidget>(PC, ExplorationWidgetClass);
        if (IsValid(ExplorationWidget)) ExplorationWidget->AddToViewport(7);
    }
    if (!IsValid(ExplorationWidget)) return;
    // The old HUD includes legacy income instructions. Keep it alive for Blueprint adapters, hide its presentation in this mode.
    TArray<UUserWidget*> HUDs;
    UWidgetBlueprintLibrary::GetAllWidgetsOfClass(this, HUDs, UUserWidget::StaticClass(), false);
    for (UUserWidget* HUD : HUDs)
        if (IsValid(HUD) && HUD->GetClass()->GetName() == TEXT("WBP_PrototypeHUD_C")) HUD->SetVisibility(ESlateVisibility::Collapsed);
    ExplorationWidget->PresentDamage(GetWorld()->GetTimeSeconds() < DamageVeilUntil);
    if (IsPreparing())
    {
        ExplorationWidget->Present(TEXT(""),TEXT(""),true);
        ExplorationWidget->PresentShop(Progression->DescribeShop(ShopSelection,ShopMessage),true);
        return;
    }
    ExplorationWidget->PresentShop(TEXT(""),false);
    if (bAwaitLevelLaunch)
    {
        ExplorationWidget->Present(TEXT(""),TEXT("实验室气闸 · 等待整备出发\nA 分析区 / B 动力区 / C 收容区"),true);
        ExplorationWidget->PresentMeta(TEXT("")); ExplorationWidget->PresentRegion(TEXT(""));
        ExplorationWidget->PresentInventory(TEXT(""),TEXT(""));
        if(ExplorationWidget->WidgetTree)
            if(auto Backing=ExplorationWidget->WidgetTree->FindWidget(TEXT("RegionBacking"))) Backing->SetVisibility(ESlateVisibility::Collapsed);
        return;
    }
    ExplorationWidget->PresentMeta(Progression ? FString::Printf(TEXT("永久余额 $%lld  |  诱饵 %d · F 使用"),Progression->GetProgress().Currency,DecoysRemaining) : TEXT(""));
    FString Focus;
    FString RegionHint;
    if (const AAnomalyBoxActor* Box = TraceExplorationBox(Player))
        if (IsSelectableBox(Box) && Box->CanScan())
        {
            Focus = FString::Printf(TEXT("%s  ·  E 打开  /  按住 Q 扫描"), *Box->DefinitionAsset->DisplayName.ToString());
            if (IsValid(Box->RegionDefinition)) RegionHint = Box->RegionDefinition->DisplayName.ToString()
                + TEXT("\n") + Box->RegionDefinition->Description.ToString();
        }
    if (const AAnomalyWorldPickup* Loot = Cast<AAnomalyWorldPickup>(TraceExplorationTarget(Player)))
        Focus = FString::Printf(TEXT("%s  $%d  ·  E 拾取"), *Loot->Item.DisplayName.ToString(), Loot->Item.Value);
    if(auto Terminal=Cast<AAnomalyEnvironmentTerminal>(TraceExplorationTarget(Player))) Focus=Terminal->Describe();
    const bool bAtEntrance = AtEntrance(Player);
    FString Objective = TEXT("探索 A / B / C 区 · 每轮只能打开一个箱子\n绿色引导线通往入口");
    if (RoundPhase == EAnomalyRoundPhase::PostRoundDecision)
        Objective = TEXT("本轮已结束 · 可沿绿色引导线返回入口\n按 1 继续 / 按 2 选择返回入口");
    if (RoundPhase == EAnomalyRoundPhase::PostRoundDecision && ThreatsResolved >= MaxThreats)
        Objective = TEXT("收容已达上限 · 沿绿色引导线返回入口\n到达入口后按 E 确认撤离");
    if (RoundPhase == EAnomalyRoundPhase::ReturningToExtraction)
        Objective = TEXT("返回入口 · 携带价值尚未兑现\n沿绿色引导线前往入口，按 E 确认撤离");
    if (IsValid(CurrentSpider) && (RoundPhase == EAnomalyRoundPhase::ThreatWarning || RoundPhase == EAnomalyRoundPhase::ThreatActive))
    {
        const FVector ToThreat = CurrentSpider->GetActorLocation() - Player->GetActorLocation();
        const float Bearing = FRotator::NormalizeAxis(ToThreat.Rotation().Yaw - PC->GetControlRotation().Yaw);
        const TCHAR* Direction = FMath::Abs(Bearing) < 45.f ? TEXT("前方") : FMath::Abs(Bearing) > 135.f ? TEXT("后方") : Bearing > 0 ? TEXT("右侧") : TEXT("左侧");
        Objective = FString::Printf(TEXT("危险 · %s %.0f 米\n保持移动直到自动收容\n绿色引导线通往入口"), Direction, ToThreat.Size2D() / 100.f);
        if (Cast<AAnomalyObserverCharacter>(CurrentSpider))
            Objective=FString::Printf(TEXT("观察者 · %s %.0f 米\n正视眼部停步；红眼时保持距离\n背对/遮挡会接近 · 诱饵无效"),Direction,ToThreat.Size2D()/100.f);
    }
    if (bAtEntrance)
    {
        Objective += TEXT("\n当前位置：入口 / 撤离区");
        if (RoundPhase == EAnomalyRoundPhase::AwaitingSelection || RoundPhase == EAnomalyRoundPhase::PostRoundDecision
            || RoundPhase == EAnomalyRoundPhase::ReturningToExtraction)
            if (Focus.IsEmpty()) Focus = TEXT("E 确认撤离 · 兑现携带物品");
    }
    if(auto Env=AAnomalyEnvironmentController::Find(GetWorld())) { const FString Event=Env->DescribeEvent(); if(!Event.IsEmpty()) Objective+=TEXT("\n")+Event; }
    ExplorationWidget->Present(Focus, Objective, NativeState != 3);
    if (RegionHint.IsEmpty() && bUseRegionRules)
        RegionHint = TEXT("区域选择 · 每轮仍只能开一箱\nA 低风险 / 较低收益    B 中风险 / 中高收益\nC 高风险 / 高收益 · 未知箱不保证安全");
    if (BalanceConfig && RegionHint.StartsWith(TEXT("区域选择")))
        RegionHint=FString::Printf(TEXT("第 %d 轮 · 风险权重 ×%.2f / 高值 ×%.2f\nA 低风险 / 较低收益    B 中风险 / 中高收益\nC 高风险 / 高收益 · 未知箱不保证安全"),RoundId,
            BalanceConfig->ThreatMultiplier(RoundId),BalanceConfig->RewardMultiplier(RoundId));
    ExplorationWidget->PresentRegion(RegionHint);
    ExplorationWidget->PresentInventory(IsValid(Inventory) ? Inventory->Describe() : TEXT(""),
        GetWorld()->GetTimeSeconds() < FeedbackUntil ? FeedbackMessage : TEXT(""));
}
void AAnomalyRoundCoordinator::SetState(int32 State)
{
    NativeState = State;
    PresentRoundState(State);
    UE_LOG(LogTemp, Display, TEXT("[Round] State=%d Generation=%llu"), State, RoundGeneration);
}
void AAnomalyRoundCoordinator::SetPhase(EAnomalyRoundPhase Phase)
{
    RoundPhase = Phase;
    UE_LOG(LogTemp, Display, TEXT("[Round] Phase=%d Generation=%llu"), static_cast<int32>(Phase), RoundGeneration);
}
void AAnomalyRoundCoordinator::SpawnInitialBox() { CurrentSpawnRetryCount = 0; SpawnNextBox(); }

void AAnomalyRoundCoordinator::SpawnNextBox()
{
    if (bAwaitLevelLaunch || NativeState != 0 || RoundPhase==EAnomalyRoundPhase::Preparation || bSpawningChoices || CandidateBoxes.Num() != 0 || IsValid(SelectedBox)) return;
    bSpawningChoices = true;
    SetPhase(EAnomalyRoundPhase::SpawningChoices);
    const USceneComponent* Points[] = {BoxPointLeft, BoxPointMiddle, BoxPointRight};
    // Draw each type independently, then repair the only invalid combination.
    static const FName PublicTypes[] = {TEXT("Safe"), TEXT("Risky"), TEXT("Unknown")};
    TArray<FName> Types;
    const bool bRegional = PlayMode == EAnomalyPlayMode::Exploration && bUseRegionRules;
    FString RegionError;
    if (bRegional && !UAnomalyRegionDefinition::DrawChoices(RegionRules, RegionStream, Types, RegionError))
    { bSpawningChoices = false; UE_LOG(LogTemp, Error, TEXT("[Region] %s"), *RegionError); FailWithError(); return; }
    if (!bRegional) for (int32 Index = 0; Index < 3; ++Index) Types.Add(PublicTypes[FMath::RandRange(0, 2)]);
    if (!bRegional && Types[0] == Types[1] && Types[1] == Types[2])
    {
        const int32 Slot = FMath::RandRange(0, 2);
        int32 Other = FMath::RandRange(0, 1);
        if (PublicTypes[Other] == Types[Slot]) Other = 2;
        Types[Slot] = PublicTypes[Other];
    }
    const int32 NextRoundId = RoundId + 1;
    TArray<AAnomalyBoxActor*> Spawned;
    TArray<FTransform> PlacementTransforms; LastSpawnPointIds.Empty();
    if(bV05Lab)
    {
        if(!PlacementConfig) { bSpawningChoices=false; Notify(TEXT("箱位配置缺失")); FailWithError(); return; }
        for(int32 Index=0;Index<3;++Index)
        {
            FTransform Transform; int32 Id=INDEX_NONE;
            if(!PlacementConfig->Choose(this,Index,RegionSeed,NextRoundId,Transform,Id))
            { bSpawningChoices=false; Notify(TEXT("无合法箱位，安全结束，不兑现")); FailWithError(); return; }
            PlacementTransforms.Add(Transform); LastSpawnPointIds.Add(Id);
            UE_LOG(LogTemp,Display,TEXT("[Placement] Run=%s Seed=%d Round=%d Region=%d Point=%d XYZ=%s"),*RunId.ToString(),RegionSeed,NextRoundId,Index,Id,*Transform.GetLocation().ToString());
        }
    }
    FActorSpawnParameters Parameters;
    Parameters.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    for (int32 Index = 0; Index < 3; ++Index)
    {
        const FTransform Transform=bV05Lab?PlacementTransforms[Index]:(IsValid(Points[Index])?Points[Index]->GetComponentTransform():FTransform::Identity);
        AAnomalyBoxActor* Box = BoxClass && IsValid(Points[Index])
            ? GetWorld()->SpawnActorDeferred<AAnomalyBoxActor>(BoxClass, Transform, this, nullptr,
                ESpawnActorCollisionHandlingMethod::AlwaysSpawn) : nullptr;
        if (!IsValid(Box)) break;
        Box->DefinitionID = Types[Index];
        if (bRegional)
        {
            Box->RegionDefinition = RegionRules[Index];
            if (bUseFixedRegionSeed)
            {
                Box->bUseFixedSeeds = true;
                Box->ConfigurationSeed = static_cast<int32>(RegionStream.GetUnsignedInt());
                Box->OutcomeSeed = static_cast<int32>(RegionStream.GetUnsignedInt());
            }
        }
        if(bV05Lab)
        {
            // Stable run-seeded configuration/outcome, independent of chosen point.
            Box->bUseFixedSeeds=true;
            Box->ConfigurationSeed=int32(uint32(RegionSeed)^uint32(NextRoundId)*0x27d4eb2du^uint32(Index+1)*0x165667b1u);
            Box->OutcomeSeed=Box->ConfigurationSeed^int32(0xc2b2ae35u);
        }
        Box->RoundId = NextRoundId;
        Box->SetCoordinator(this);
        Box->bExplorationSpawn = PlayMode == EAnomalyPlayMode::Exploration;
        Box->bUseObserverPool=Box->bExplorationSpawn && bEnableObserverPool;
        Box->ObserverClass=ObserverClass; Box->ObserverConfig=ObserverConfig;
        Box->BalanceConfig=Box->bExplorationSpawn?BalanceConfig:nullptr;
        Box->ExplorationThreatOffset = ExplorationThreatOffset;
        Box->FinishSpawning(Transform);
        if (!IsValid(Box) || !Box->bDefinitionValid)
        { if (IsValid(Box)) Box->Destroy(); break; }
        Spawned.Add(Box);
    }
    if (Spawned.Num() != 3)
    {
        for (AAnomalyBoxActor* Box : Spawned) if (IsValid(Box)) Box->Destroy();
        bSpawningChoices = false;
        UE_LOG(LogTemp, Warning, TEXT("[Round] Box spawn failed Retry=%d/%d"), CurrentSpawnRetryCount, MaxSpawnRetries);
        if (CurrentSpawnRetryCount >= MaxSpawnRetries) { FailWithError(); return; }
        GetWorldTimerManager().SetTimer(RetryTimer, this, &AAnomalyRoundCoordinator::RetryBoxSpawn, FMath::Max(0.001, SpawnRetryDelay), false);
        return;
    }
    ++RoundGeneration;
    RoundId = NextRoundId;
    CurrentSpawnRetryCount = 0; CurrentThreatSpawnRetryCount = 0;
    bCompleting = false; bAttackNotified = false; bContainmentConfirmed = false;
    for (AAnomalyBoxActor* Box : Spawned)
    {
        CandidateBoxes.Add(Box);
        Box->OnNativeOutcomeResolved.AddDynamic(this, &AAnomalyRoundCoordinator::HandleNativeOutcome);
    }
    CurrentBox = Spawned[0]; // Legacy read-only alias used by migration diagnostics.
    bSpawningChoices = false;
    SetPhase(EAnomalyRoundPhase::AwaitingSelection);
    if (!bRunClockStarted) { RunStartTime = GetWorld()->GetTimeSeconds(); bRunClockStarted = true; }
    UE_LOG(LogTemp, Display, TEXT("[Round] Round %d spawned three boxes"), RoundId);
}

void AAnomalyRoundCoordinator::RetryBoxSpawn()
{ if (NativeState == 0 && CandidateBoxes.IsEmpty()) { ++CurrentSpawnRetryCount; SpawnNextBox(); } }
bool AAnomalyRoundCoordinator::IsSelectableBox(const AAnomalyBoxActor* Box) const
{
    return NativeState == 0 && RoundPhase == EAnomalyRoundPhase::AwaitingSelection && !bSpawningChoices && IsValid(Box) && Box->RoundId == RoundId
        && !IsValid(SelectedBox) && CandidateBoxes.Num() == 3 && CandidateBoxes.Contains(Box);
}
bool AAnomalyRoundCoordinator::TryLockSelection(AAnomalyBoxActor* Box)
{
    if (!IsSelectableBox(Box)) return false;
    SelectedBox = Box;
    SetPhase(EAnomalyRoundPhase::ResolvingOutcome);
    CurrentBox = Box;
    for (AAnomalyBoxActor* Candidate : CandidateBoxes)
        if (IsValid(Candidate) && Candidate != Box) Candidate->LockUnselected();
    SetState(1); return true;
}
bool AAnomalyRoundCoordinator::CanResolveBox(const AAnomalyBoxActor* Box) const
{ return NativeState == 1 && RoundPhase == EAnomalyRoundPhase::ResolvingOutcome && IsValid(Box) && Box == SelectedBox && Box->RoundId == RoundId; }

void AAnomalyRoundCoordinator::HandleNativeOutcome(AActor* Box, int32 OutcomeIndex, AActor* SpawnedActor, bool bSpawnSucceeded)
{
    if (RoundPhase != EAnomalyRoundPhase::ResolvingOutcome || !CanResolveBox(Cast<AAnomalyBoxActor>(Box)) || bCompleting) return;
    CurrentOutcomeActor = SpawnedActor; NativeOutcome = OutcomeIndex; SetState(2);
    if (PlayMode == EAnomalyPlayMode::LegacyPrototype) PresentRoundOutcome(OutcomeIndex, SpawnedActor, bSpawnSucceeded);
    if (OutcomeIndex != 2)
    {
        OutcomeReadyTime = GetWorld()->GetTimeSeconds() + FMath::Max(0.001, NextRoundDelay);
        GetWorldTimerManager().SetTimer(RewardTimer, this, &AAnomalyRoundCoordinator::CompleteCurrentOutcome, FMath::Max(0.001, NextRoundDelay), false);
        return;
    }
    CurrentSpider = Cast<AAnomalyThreatCharacter>(SpawnedActor);
    if (bSpawnSucceeded && IsValid(CurrentSpider))
    {
        BeginThreatWarning();
        return;
    }
    if (IsValid(SpawnedActor)) SpawnedActor->Destroy();
    CurrentOutcomeActor = nullptr;
    UE_LOG(LogTemp, Warning, TEXT("[Round] Threat spawn failed; starting limited retries"));
    GetWorldTimerManager().SetTimer(ThreatRetryTimer, this, &AAnomalyRoundCoordinator::RetryThreatSpawn,
        FMath::Max(.001f, ThreatSpawnRetryDelay), false);
}

void AAnomalyRoundCoordinator::HandleNativeThreatResolved(AActor* Spider)
{
    if (NativeState != 2 || RoundPhase != EAnomalyRoundPhase::ThreatActive || NativeOutcome != 2 || !bThreatPursuitActive || !IsValid(Spider)
        || Spider != CurrentSpider || !IsValid(PlayerHealth) || PlayerHealth->bDead) return;
    bThreatPursuitActive = false;
    bContainmentConfirmed = true;
    RecordRegionEvent(SelectedBox, TEXT("survive"));
    EmitFeedback(TEXT("Containment"));
    SetPhase(EAnomalyRoundPhase::ThreatContainment);
    OutcomeReadyTime = GetWorld()->GetTimeSeconds() + FMath::Max(.001f, ContainmentMessageSeconds);
    PlayerHealth->SetDamageEnabled(false);
    GetWorldTimerManager().ClearTimer(ThreatDisplayTimer);
    if (UAnomalyStatusWidget* Status = PlayerHealth->GetStatusWidget()) Status->PresentThreat(TEXT("收容完成"));
    GetWorldTimerManager().SetTimer(ContainmentTimer, this, &AAnomalyRoundCoordinator::CompleteCurrentOutcome,
        FMath::Max(.001f, ContainmentMessageSeconds), false);
}
void AAnomalyRoundCoordinator::HandleNativePlayerAttacked(AActor* Spider)
{
    if (NativeState != 2 || RoundPhase != EAnomalyRoundPhase::ThreatActive || NativeOutcome != 2 || !bThreatPursuitActive || !IsValid(Spider)
        || Spider != CurrentSpider || bAttackNotified) return;
    bAttackNotified = true; PresentRoundAttack();
}

bool AAnomalyRoundCoordinator::BindPlayerHealth()
{
    if (IsValid(PlayerHealth)) return true;
    ACharacter* Player = UGameplayStatics::GetPlayerCharacter(this, 0);
    PlayerHealth = IsValid(Player) ? Player->FindComponentByClass<UAnomalyHealthComponent>() : nullptr;
    if (IsValid(PlayerHealth))
    {
        PlayerHealth->OnNativeDeath.AddUniqueDynamic(this, &AAnomalyRoundCoordinator::HandlePlayerDeath);
        PlayerHealth->OnNativeHealthChanged.AddUniqueDynamic(this, &AAnomalyRoundCoordinator::HandleHealthChanged);
    }
    return IsValid(PlayerHealth);
}

void AAnomalyRoundCoordinator::BeginThreatWarning()
{
    if (NativeState != 2 || !IsValid(CurrentSpider) || !BindPlayerHealth() || PlayerHealth->bDead)
    { FailWithError(); return; }
    SetPhase(EAnomalyRoundPhase::ThreatWarning);
    auto Observer=Cast<AAnomalyObserverCharacter>(CurrentSpider);
    if (Observer) Observer->BeginWarning();
    if (PlayMode == EAnomalyPlayMode::Exploration)
    {
        EmitFeedback(TEXT("Warning"));
        Notify(Observer?TEXT("观察者预警 · 正视眼部可停步；红眼时保持距离，诱饵无效"):TEXT("收容失效 · 红色应急光标记威胁来源"));
        UPointLightComponent* Light = NewObject<UPointLightComponent>(CurrentSpider, TEXT("EmergencyLight"));
        Light->SetupAttachment(CurrentSpider->GetRootComponent());
        Light->SetRelativeLocation(FVector(0,0,110));
        Light->SetMobility(EComponentMobility::Movable);
        Light->SetLightColor(Observer?FLinearColor(.02f,.55f,1.f):FLinearColor(1.f,.005f,.001f));
        Light->SetIntensityUnits(ELightUnits::Candelas);
        Light->SetIntensity(5000.f); Light->SetAttenuationRadius(650.f); Light->SetCastShadows(false); Light->RegisterComponent();
        if (USoundBase* Sound = FeedbackSounds.FindRef(TEXT("Threat")))
        {
            UAudioComponent* Audio = NewObject<UAudioComponent>(CurrentSpider);
            Audio->bAutoActivate = false; Audio->SetupAttachment(CurrentSpider->GetRootComponent());
            Audio->SetSound(Sound); Audio->bAutoDestroy = false;
            FSoundAttenuationSettings Attenuation; Attenuation.bAttenuate = true;
            Attenuation.bSpatialize = true; Attenuation.AttenuationShapeExtents = FVector(120.f);
            Attenuation.FalloffDistance = 1800.f;
            Audio->AdjustAttenuation(Attenuation); Audio->RegisterComponent(); Audio->Play();
        }
    }
    PlayerHealth->SetDamageEnabled(false);
    CurrentSpider->OnNativeThreatResolved.AddUniqueDynamic(this, &AAnomalyRoundCoordinator::HandleNativeThreatResolved);
    CurrentSpider->OnNativePlayerAttacked.AddUniqueDynamic(this, &AAnomalyRoundCoordinator::HandleNativePlayerAttacked);
    if (UAnomalyStatusWidget* Status = PlayerHealth->GetStatusWidget()) Status->PresentThreat(Observer?TEXT("观察者预警 · 正视停步，红眼时保持距离"):TEXT("危险：收容失效"));
    GetWorldTimerManager().SetTimer(WarningTimer, this, &AAnomalyRoundCoordinator::ActivateCurrentThreat,
        FMath::Max(.001f, ThreatWarningSeconds), false);
}

void AAnomalyRoundCoordinator::ActivateCurrentThreat()
{
    if (NativeState != 2 || RoundPhase != EAnomalyRoundPhase::ThreatWarning || NativeOutcome != 2 || !IsValid(CurrentSpider) || !IsValid(PlayerHealth)
        || PlayerHealth->bDead) return;
    CurrentSpider->AutoResolveDelay = FMath::Max(.001f, ThreatSurvivalSeconds);
    CurrentSpider->ActivateThreat();
    if (!CurrentSpider->bThreatActive) { FailWithError(); return; }
    bThreatPursuitActive = true;
    SetPhase(EAnomalyRoundPhase::ThreatActive);
    ThreatEndTime = GetWorld()->GetTimeSeconds() + CurrentSpider->AutoResolveDelay;
    PlayerHealth->SetDamageEnabled(true);
    UpdateThreatDisplay();
    GetWorldTimerManager().SetTimer(ThreatDisplayTimer, this, &AAnomalyRoundCoordinator::UpdateThreatDisplay, .2f, true);
}

void AAnomalyRoundCoordinator::UpdateThreatDisplay()
{
    if (!bThreatPursuitActive || !IsValid(PlayerHealth)) return;
    if (UAnomalyStatusWidget* Status = PlayerHealth->GetStatusWidget())
    {
        auto Observer=Cast<AAnomalyObserverCharacter>(CurrentSpider);
        Status->PresentThreat((Observer?Observer->DescribeState()+TEXT("\n"):TEXT(""))+FString::Printf(TEXT("收容倒计时  %d 秒"),
            FMath::Max(0, FMath::CeilToInt(ThreatEndTime - GetWorld()->GetTimeSeconds()))));
    }
}

void AAnomalyRoundCoordinator::RetryThreatSpawn()
{
    if (NativeState != 2 || NativeOutcome != 2 || !IsValid(SelectedBox) || IsValid(CurrentSpider)) return;
    ++CurrentThreatSpawnRetryCount;
    FActorSpawnParameters Parameters;
    Parameters.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    AActor* Result = SelectedBox->SpawnThreatActor();
    CurrentSpider = Cast<AAnomalyThreatCharacter>(Result);
    if (IsValid(CurrentSpider))
    {
        CurrentOutcomeActor = CurrentSpider;
        PresentRoundOutcome(2, CurrentSpider, true);
        BeginThreatWarning();
        return;
    }
    if (IsValid(Result)) Result->Destroy();
    UE_LOG(LogTemp, Warning, TEXT("[Round] Threat retry failed %d/%d"), CurrentThreatSpawnRetryCount, MaxThreatSpawnRetries);
    if (CurrentThreatSpawnRetryCount >= MaxThreatSpawnRetries) { FailWithError(); return; }
    GetWorldTimerManager().SetTimer(ThreatRetryTimer, this, &AAnomalyRoundCoordinator::RetryThreatSpawn,
        FMath::Max(.001f, ThreatSpawnRetryDelay), false);
}

void AAnomalyRoundCoordinator::HandlePlayerDeath()
{
    if (NativeState == 3 || !IsValid(PlayerHealth) || !PlayerHealth->bDead) return;
    RunEndReason = EAnomalyRunEndReason::Failed;
    EndRun();
}

void AAnomalyRoundCoordinator::CompleteCurrentOutcome()
{
    if (NativeState != 2 || bCompleting || GetWorld()->GetTimeSeconds() + KINDA_SMALL_NUMBER < OutcomeReadyTime || (NativeOutcome == 2 &&
        (RoundPhase != EAnomalyRoundPhase::ThreatContainment || !bContainmentConfirmed || !IsValid(PlayerHealth) || PlayerHealth->bDead))
        || (NativeOutcome != 2 && RoundPhase != EAnomalyRoundPhase::ResolvingOutcome)) return;
    bCompleting = true;
    if (NativeOutcome == 2) { ++ThreatsResolved; PresentThreatCount(ThreatsResolved, MaxThreats); }
    ++CompletedRounds;
    CleanupCurrentRound();
    SetPhase(EAnomalyRoundPhase::PostRoundDecision);
    SetState(4);
    ShowDecision();
    if (PlayMode == EAnomalyPlayMode::Exploration && ThreatsResolved >= MaxThreats) CashOut();
}

void AAnomalyRoundCoordinator::FreezePlayer(bool bFreeze)
{
    ACharacter* Player = UGameplayStatics::GetPlayerCharacter(this, 0);
    if (!IsValid(Player)) return;
    if (UAnomalyScannerComponent* Scanner = Player->FindComponentByClass<UAnomalyScannerComponent>()) Scanner->CancelScan();
    if (UCharacterMovementComponent* Movement = Player->GetCharacterMovement())
    {
        if (bFreeze) Movement->DisableMovement();
        else Movement->SetMovementMode(MOVE_Walking);
    }
}

void AAnomalyRoundCoordinator::ShowDecision()
{
    FreezePlayer(PlayMode == EAnomalyPlayMode::LegacyPrototype);
    ACharacter* Player = UGameplayStatics::GetPlayerCharacter(this, 0);
    UAnomalyWalletComponent* Wallet = IsValid(Player) ? Player->FindComponentByClass<UAnomalyWalletComponent>() : nullptr;
    if (PlayMode == EAnomalyPlayMode::Exploration)
    {
        if (IsValid(DecisionWidget)) DecisionWidget->SetVisibility(ESlateVisibility::Collapsed);
        Notify(TEXT("本轮已结束 · E 拾取物品，1 继续，2 返回入口"));
        return;
    }
    if (IsValid(DecisionWidget))
        DecisionWidget->PresentDecision(IsValid(Wallet) ? Wallet->NativeGetMoney() : 0,
            CompletedRounds, ThreatsResolved, ThreatsResolved < MaxThreats);
}

void AAnomalyRoundCoordinator::ContinueRun()
{
    if (NativeState != 4 || RoundPhase != EAnomalyRoundPhase::PostRoundDecision || ThreatsResolved >= MaxThreats || bPrototypeError) return;
    if (IsValid(DecisionWidget)) DecisionWidget->SetVisibility(ESlateVisibility::Collapsed);
    FreezePlayer(false);
    SetState(0);
    SetPhase(EAnomalyRoundPhase::Initializing);
    SpawnNextBox();
}

void AAnomalyRoundCoordinator::CashOut()
{
    if (NativeState != 4 || RoundPhase != EAnomalyRoundPhase::PostRoundDecision || bPrototypeError) return;
    if (PlayMode == EAnomalyPlayMode::Exploration)
    {
        if(bV05Lab) Telemetry.BeginReturn(this);
        SetPhase(EAnomalyRoundPhase::ReturningToExtraction);
        if (IsValid(DecisionWidget)) DecisionWidget->SetVisibility(ESlateVisibility::Collapsed);
        Notify(TEXT("撤离意图已确认 · 返回入口后按 E，尚未兑现"));
        return;
    }
    RunEndReason = EAnomalyRunEndReason::CashedOut;
    EndRun();
}

void AAnomalyRoundCoordinator::CleanupCurrentRound()
{
    GetWorldTimerManager().ClearTimer(RewardTimer);
    GetWorldTimerManager().ClearTimer(RetryTimer);
    GetWorldTimerManager().ClearTimer(FallbackTimer);
    GetWorldTimerManager().ClearTimer(WarningTimer);
    GetWorldTimerManager().ClearTimer(ThreatDisplayTimer);
    GetWorldTimerManager().ClearTimer(ContainmentTimer);
    GetWorldTimerManager().ClearTimer(ThreatRetryTimer);
    bThreatPursuitActive = false;
    bContainmentConfirmed = false;
    if (IsValid(PlayerHealth))
    {
        PlayerHealth->SetDamageEnabled(false);
        if (UAnomalyStatusWidget* Status = PlayerHealth->GetStatusWidget()) Status->PresentThreat(TEXT(""));
    }
    AActor* Result = CurrentOutcomeActor;
    if (IsValid(CurrentSpider))
    {
        CurrentSpider->OnNativeThreatResolved.RemoveDynamic(this, &AAnomalyRoundCoordinator::HandleNativeThreatResolved);
        CurrentSpider->OnNativePlayerAttacked.RemoveDynamic(this, &AAnomalyRoundCoordinator::HandleNativePlayerAttacked);
    }
    for (AAnomalyBoxActor* Box : CandidateBoxes)
        if (IsValid(Box)) Box->OnNativeOutcomeResolved.RemoveDynamic(this, &AAnomalyRoundCoordinator::HandleNativeOutcome);
    CurrentSpider = nullptr; CurrentOutcomeActor = nullptr; CurrentBox = nullptr; SelectedBox = nullptr; bAttackNotified = false;
    if (IsValid(Result) && !Cast<AAnomalyWorldPickup>(Result)) Result->Destroy();
    for (AAnomalyBoxActor* Box : CandidateBoxes) if (IsValid(Box)) Box->Destroy();
    CandidateBoxes.Empty();
    bSpawningChoices = false;
    UE_LOG(LogTemp, Display, TEXT("[Round] Cleanup complete"));
}
void AAnomalyRoundCoordinator::EndRun()
{
    if (bAwaitLevelLaunch || NativeState == 3) return;
    NativeState = 3; // Seal all gameplay entry points before Wallet presentation can re-enter.
    if (PlayMode == EAnomalyPlayMode::Exploration && RunEndReason != EAnomalyRunEndReason::Failed)
    {
        if (!bExtractionAuthorized || bPrototypeError) { bPrototypeError = true; RunEndReason = EAnomalyRunEndReason::Error; }
        else RunEndReason = EAnomalyRunEndReason::CashedOut;
    }
    if (RunEndReason == EAnomalyRunEndReason::None)
        RunEndReason = bPrototypeError ? EAnomalyRunEndReason::Error : EAnomalyRunEndReason::CashedOut;
    SetPhase(RunEndReason == EAnomalyRunEndReason::Failed ? EAnomalyRoundPhase::RunFailed
        : RunEndReason == EAnomalyRunEndReason::Error ? EAnomalyRoundPhase::Error : EAnomalyRoundPhase::RunCashedOut);
    ACharacter* Player = UGameplayStatics::GetPlayerCharacter(this, 0);
    UAnomalyWalletComponent* Wallet = IsValid(Player) ? Player->FindComponentByClass<UAnomalyWalletComponent>() : nullptr;
    const int32 Balance = IsValid(Wallet) ? Wallet->NativeGetMoney() : 0;
    if (PlayMode == EAnomalyPlayMode::Exploration)
    {
        const int32 Carry = IsValid(Inventory) ? Inventory->GetCarryValue() : 0;
        TerminalItems.Empty();
        if (IsValid(Inventory))
            for (const FAnomalyItemInstance& Item : Inventory->GetItems())
                TerminalItems += FString::Printf(TEXT("%s $%d\n"), *Item.DisplayName.ToString(), Item.Value);
        LostRunValue = (RunEndReason == EAnomalyRunEndReason::Failed
            || (bV05Lab && RunEndReason == EAnomalyRunEndReason::Error)) ? Carry : 0;
        FinalRunValue = 0;
        if (RunEndReason == EAnomalyRunEndReason::CashedOut && !bSettlementDone && IsValid(Wallet))
        {
            FString Reason;
            if ((bV05Lab && !Progression) || (Progression && !Progression->CreditExtraction(this,RunId,Carry,Reason)))
            { bPrototypeError=true; RunEndReason=EAnomalyRunEndReason::Error; if(bV05Lab) LostRunValue=Carry; SetPhase(EAnomalyRoundPhase::Error); Notify(Reason); }
            else
            {
            bSettlementDone = true;
            ++SettlementCount;
            FinalRunValue = Carry;
            Wallet->NativeAddMoney(Carry);
            }
        }
        if (IsValid(Inventory)) Inventory->SealAndClear();
        for (AAnomalyWorldPickup* Loot : WorldLoot) if (IsValid(Loot)) Loot->Destroy();
        WorldLoot.Empty();
    }
    else
    {
    LostRunValue = RunEndReason == EAnomalyRunEndReason::Failed ? Balance : 0;
    FinalRunValue = RunEndReason == EAnomalyRunEndReason::Failed ? 0 : Balance;
    }
    GetWorldTimerManager().ClearTimer(ExtractionTimer);
    if (IsValid(DecoySource)) DecoySource->Destroy();
    DecoySource=nullptr; DecoysRemaining=0;
    bExtractionPending = false;
    FinalRunSeconds = bRunClockStarted ? FMath::Max(0.f, GetWorld()->GetTimeSeconds() - RunStartTime) : 0.f;
    EndSnapshot.Detail=RunEndReason==EAnomalyRunEndReason::Failed?TEXT("生命归零"):RunEndReason==EAnomalyRunEndReason::Error?FeedbackMessage:TEXT("已在气闸完成撤离");
    EndSnapshot.RunId=RunId; EndSnapshot.Reason=RunEndReason; EndSnapshot.CashedOut=FinalRunValue; EndSnapshot.Lost=LostRunValue;
    EndSnapshot.PermanentBalance=Progression?Progression->GetProgress().Currency:0;
    EndSnapshot.Rounds=CompletedRounds; EndSnapshot.Contained=ThreatsResolved; EndSnapshot.Seconds=FinalRunSeconds;
    EndSnapshot.Items=TerminalItems; EndSnapshot.bDurableCredit=Progression && bSettlementDone && RunEndReason==EAnomalyRunEndReason::CashedOut;
    FreezePlayer(true);
    if (IsValid(PlayerHealth)) PlayerHealth->SetDamageEnabled(false);
    SetState(3); CleanupCurrentRound();
    if (RunEndReason == EAnomalyRunEndReason::Failed && IsValid(Wallet)) Wallet->NativeResetMoney();
    PresentRunEnded(bPrototypeError);
    // The accepted decision widget owns the terminal screen; the legacy HUD terminal text overlaps it.
    TArray<UUserWidget*> VisibleWidgets;
    UWidgetBlueprintLibrary::GetAllWidgetsOfClass(this, VisibleWidgets, UUserWidget::StaticClass(), false);
    for (UUserWidget* Widget : VisibleWidgets)
        if (IsValid(Widget) && Widget->WidgetTree)
            if (UTextBlock* LegacyEnd = Widget->WidgetTree->FindWidget<UTextBlock>(TEXT("RunEndText")))
                LegacyEnd->SetVisibility(ESlateVisibility::Collapsed);
    const int32 DisplayMoney = EndSnapshot.Reason == EAnomalyRunEndReason::Failed ? EndSnapshot.Lost : EndSnapshot.CashedOut;
    if (IsValid(DecisionWidget)) DecisionWidget->PresentTerminal(DisplayMoney, EndSnapshot.Rounds, EndSnapshot.Contained,
        EndSnapshot.Seconds, EndSnapshot.Reason == EAnomalyRunEndReason::CashedOut, EndSnapshot.Reason==EAnomalyRunEndReason::Error);
    if (PlayMode == EAnomalyPlayMode::Exploration && IsValid(DecisionWidget))
        DecisionWidget->AppendItems(EndSnapshot.Items + (Progression ? FString::Printf(TEXT("永久余额 $%lld · %s\n"),EndSnapshot.PermanentBalance,
            EndSnapshot.bDurableCredit?TEXT("已保存"):TEXT("本局未新增永久收入")) : TEXT("")));
    UE_LOG(LogTemp, Display, TEXT("[Round] Run Ended Error=%d Threats=%d"), bPrototypeError, ThreatsResolved);
    if(bV05Lab)
    {
        LoadingWidget=CreateWidget<UAnomalyLoadingWidget>(GetWorld()->GetFirstPlayerController()); if(LoadingWidget) LoadingWidget->AddToViewport(1000);
        if(auto Env=AAnomalyEnvironmentController::Find(GetWorld())) Env->CancelEvents(TEXT("结算离场"));
        Telemetry.Finish(this,EndSnapshot);
        if(auto Scanner=Player->FindComponentByClass<UAnomalyScannerComponent>()) Scanner->CancelScan();
        for(TActorIterator<AActor> It(GetWorld());It;++It)
        { TArray<UAudioComponent*> Audio; It->GetComponents(Audio); for(auto Component:Audio) Component->Stop(); }
        if(!GetGameInstance()->GetSubsystem<UAnomalyTransitionSubsystem>()->CompleteRun(this))
            GetGameInstance()->GetSubsystem<UAnomalyTransitionSubsystem>()->RejectLab(GetWorld(),TEXT("结果协议拒绝：本局未兑现"));
    }
}
void AAnomalyRoundCoordinator::FailWithError() { bPrototypeError = true; EndRun(); }
void AAnomalyRoundCoordinator::EndPlay(const EEndPlayReason::Type Reason)
{
    if(bV05Lab) Telemetry.Finish(this,EndSnapshot,true);
    if(LoadingWidget) LoadingWidget->RemoveFromParent(); LoadingWidget=nullptr;
    NativeState = 3; GetWorldTimerManager().ClearTimer(V05StartTimer); GetWorldTimerManager().ClearTimer(ExtractionTimer); CleanupCurrentRound();
    if (IsValid(DecoySource)) DecoySource->Destroy();
    for (AAnomalyWorldPickup* Loot : WorldLoot) if (IsValid(Loot)) Loot->Destroy();
    WorldLoot.Empty();
    if (IsValid(PlayerHealth))
    {
        PlayerHealth->OnNativeDeath.RemoveDynamic(this, &AAnomalyRoundCoordinator::HandlePlayerDeath);
        PlayerHealth->OnNativeHealthChanged.RemoveDynamic(this, &AAnomalyRoundCoordinator::HandleHealthChanged);
    }
    if (IsValid(DecisionWidget)) DecisionWidget->RemoveFromParent();
    if (IsValid(ExplorationWidget)) ExplorationWidget->RemoveFromParent();
    Super::EndPlay(Reason);
}

AAnomalyWorldPickup* AAnomalyRoundCoordinator::SpawnLoot(int32 Outcome, int32 Value, const FTransform& Transform, int32 SourceRound)
{
    if (PlayMode != EAnomalyPlayMode::Exploration || SourceRound != RoundId || !IsValid(SelectedBox) || !CanResolveBox(SelectedBox) || GeneratedRewardRounds.Contains(SourceRound)) return nullptr;
    // Cosmetic identity uses an existing visual seed, never consumes the outcome RNG.
    TArray<UAnomalyItemDefinition*> Pool;
    for (UAnomalyItemDefinition* Def : LootDefinitions)
        if (IsValid(Def) && Def->bTrash == (Outcome == 1)) Pool.Add(Def);
    if (Pool.IsEmpty()) return nullptr;
    const int32 Index = uint32(GetTypeHash(SelectedBox->GetName())) % Pool.Num();
    FTransform LootTransform=Transform;
    if(bV05Lab)
    {
        FVector Location;
        if(!PlacementConfig || !PlacementConfig->FindPickupSpot(this,SelectedBox->GetActorLocation(),Location)) return nullptr;
        LootTransform.SetLocation(Location);
    }
    AAnomalyWorldPickup* Loot = GetWorld()->SpawnActor<AAnomalyWorldPickup>(AAnomalyWorldPickup::StaticClass(), LootTransform);
    if (!IsValid(Loot) || !Loot->InitializeItem(Pool[Index], Value, SourceRound))
    { if (IsValid(Loot)) Loot->Destroy(); return nullptr; }
    GeneratedRewardRounds.Add(SourceRound);
    WorldLoot.Add(Loot);
    EmitFeedback(TEXT("Reveal"));
    Notify(TEXT("物品已出现 · 对准实体按 E 拾取，未兑现"));
    return Loot;
}

bool AAnomalyRoundCoordinator::AtEntrance(const AActor* Player) const
{
    if (!IsValid(Player) || FVector::DistSquared2D(Player->GetActorLocation(), EntranceLocation) > FMath::Square(325.f)
        || FMath::Abs(Player->GetActorLocation().Z - EntranceLocation.Z) > 180.f) return false;
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(ExtractionLOS), false, Player);
    return !GetWorld()->LineTraceSingleByChannel(Hit, Player->GetActorLocation(), EntranceLocation + FVector(0,0,95), ECC_Visibility, Params);
}
bool AAnomalyRoundCoordinator::ConfirmExtraction(AActor* Interactor)
{
    if (bAwaitLevelLaunch || PlayMode != EAnomalyPlayMode::Exploration || NativeState == 3 || bExtractionPending || bSettlementDone || bPrototypeError
        || Interactor != UGameplayStatics::GetPlayerCharacter(this, 0) || !AtEntrance(Interactor) || !IsValid(PlayerHealth) || PlayerHealth->bDead
        || !IsValid(Inventory) || (RoundPhase != EAnomalyRoundPhase::AwaitingSelection && RoundPhase != EAnomalyRoundPhase::PostRoundDecision
        && RoundPhase != EAnomalyRoundPhase::ReturningToExtraction)) return false;
    if(bV05Lab) Telemetry.BeginReturn(this);
    LastInteractionFrame = GFrameCounter;
    bExtractionPending = true;
    SetPhase(EAnomalyRoundPhase::ReturningToExtraction);
    // Defer the credit until the next frame, allowing this frame's death event to win.
    ExtractionTimer = GetWorldTimerManager().SetTimerForNextTick(this, &AAnomalyRoundCoordinator::CommitExtraction);
    return true;
}
void AAnomalyRoundCoordinator::CommitExtraction()
{
    if (!bExtractionPending || NativeState == 3 || RoundPhase != EAnomalyRoundPhase::ReturningToExtraction) return;
    if (GFrameCounter == LastInteractionFrame)
    {
        ExtractionTimer = GetWorldTimerManager().SetTimerForNextTick(this, &AAnomalyRoundCoordinator::CommitExtraction);
        return;
    }
    bExtractionPending = false;
    if (!IsValid(PlayerHealth) || PlayerHealth->bDead) { HandlePlayerDeath(); return; }
    if (!AtEntrance(UGameplayStatics::GetPlayerCharacter(this, 0))) { Notify(TEXT("已离开撤离区 · 请返回后确认")); return; }
    ACharacter* Player = UGameplayStatics::GetPlayerCharacter(this, 0);
    if (!IsValid(Inventory) || !IsValid(Player->FindComponentByClass<UAnomalyWalletComponent>())) { FailWithError(); return; }
    EmitFeedback(TEXT("Extract"));
    bExtractionAuthorized = true;
    RunEndReason = EAnomalyRunEndReason::CashedOut;
    EndRun();
}

UAudioComponent* AAnomalyRoundCoordinator::EmitFeedback(FName Event)
{
    if (PlayMode != EAnomalyPlayMode::Exploration) return nullptr;
    ++FeedbackCounts.FindOrAdd(Event);
    if (USoundBase* Sound = FeedbackSounds.FindRef(Event)) return UGameplayStatics::SpawnSound2D(this, Sound);
    return nullptr;
}
void AAnomalyRoundCoordinator::HandleHealthChanged(int32 NewHealth, int32 Delta)
{
    if(bV05Lab) { Telemetry.Damage(Delta); RecordTelemetry(TEXT("ThreatDamage"),FString::FromInt(Delta)); }
    if (PlayMode != EAnomalyPlayMode::Exploration || Delta >= 0 || NativeState == 3) return;
    DamageVeilUntil = GetWorld()->GetTimeSeconds() + .25f;
    EmitFeedback(TEXT("Damage"));
}

bool AAnomalyRoundCoordinator::IsPreparing() const
{
    return !bAwaitLevelLaunch && PlayMode==EAnomalyPlayMode::Exploration && bUsePreparation && NativeState==0
        && RoundPhase==EAnomalyRoundPhase::Preparation && IsValid(PlayerHealth) && !PlayerHealth->bDead
        && AtEntrance(UGameplayStatics::GetPlayerCharacter(this,0));
}
bool AAnomalyRoundCoordinator::StartPreparedRun()
{
    if (!IsPreparing() || !Progression || !IsValid(Inventory)) return false;
    FString Reason; int32 Decoys=0;
    if (!Progression->BeginRun(this,Decoys,Reason)) { ShopMessage=Reason; return false; }
    const auto& Meta=Progression->GetProgress();
    const auto Config=Progression->GetConfig();
    Inventory->CurrentCapacity=Meta.BackpackLevel>0 ? 5 : 4;
    if (auto Scanner=UGameplayStatics::GetPlayerCharacter(this,0)->FindComponentByClass<UAnomalyScannerComponent>())
    {
        Scanner->InitializeRunResources(Meta.BatteryLevel*Config->ChargesPerLevel);
        Scanner->PrecisionReduction=FMath::Min(Config->PrecisionCap,Meta.PrecisionLevel*Config->PrecisionPerLevel);
    }
    DecoysRemaining=Decoys;
    SetPhase(EAnomalyRoundPhase::Initializing); FreezePlayer(false); SpawnInitialBox();
    return NativeState!=3;
}
void AAnomalyRoundCoordinator::ShopUp() { if (IsPreparing()) ShopSelection=(ShopSelection+3)%4; }
void AAnomalyRoundCoordinator::ShopDown() { if (IsPreparing()) ShopSelection=(ShopSelection+1)%4; }
void AAnomalyRoundCoordinator::ShopBuy()
{ if (IsPreparing() && Progression) PurchaseProduct(ShopSelection,Progression->GetProgress().Revision,FGuid::NewGuid()); }
bool AAnomalyRoundCoordinator::PurchaseProduct(int32 Product,int32 ExpectedRevision,const FGuid& Request)
{
    if (!IsPreparing() || !Progression || LastPurchaseFrame==GFrameCounter) return false;
    const bool Bought=Progression->Purchase(this,Product,ExpectedRevision,Request,ShopMessage);
    if (Bought) LastPurchaseFrame=GFrameCounter;
    return Bought;
}
void AAnomalyRoundCoordinator::HandleDecoyInput() { UseDecoy(); }
bool AAnomalyRoundCoordinator::UseDecoy()
{
    if (!Progression || NativeState==3 || IsPreparing() || DecoysRemaining<=0
        || !IsValid(PlayerHealth) || PlayerHealth->bDead || GetWorld()->GetTimeSeconds()<DecoyReadyAt) return false;
    auto Player=UGameplayStatics::GetPlayerCharacter(this,0);
    const auto Config=Progression->GetConfig();
    AActor* Source=GetWorld()->SpawnActor<AActor>();
    if (!Source) return false;
    auto Mesh=NewObject<UStaticMeshComponent>(Source);
    Source->SetRootComponent(Mesh);
    Mesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cylinder.Cylinder")));
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision); Mesh->SetCanEverAffectNavigation(false); Mesh->RegisterComponent();
    Source->SetActorLocation(Player->GetActorLocation()-FVector(0,0,80)); Source->SetActorScale3D(FVector(.22,.22,.12));
    Source->SetLifeSpan(Config->DecoySeconds);
    DecoySource=Source; --DecoysRemaining; DecoyReadyAt=GetWorld()->GetTimeSeconds()+Config->DecoyCooldown;
    int32 Lured=0;
    for (TActorIterator<AAnomalyThreatCharacter> It(GetWorld());It;++It)
        if (FVector::DistSquared2D(It->GetActorLocation(),Source->GetActorLocation())<=FMath::Square(Config->DecoyRadius)
            && It->TryLure(Source,Config->DecoySeconds)) ++Lured;
    Notify(FString::Printf(TEXT("诱饵已落地 · %.0f 秒 · 引走 %d 个追逐者 · 观察者无效 · 剩余 %d"),Config->DecoySeconds,Lured,DecoysRemaining));
    return true;
}

void AAnomalyRoundCoordinator::FinishAssetCompilation()
{
#if WITH_EDITOR
    FAssetCompilingManager::Get().FinishAllCompilation();
#endif
}

void AAnomalyRoundCoordinator::BlockV05Restart() {} // Production terminal returns through the sealed result route.

void AAnomalyRoundCoordinator::InitializeV05Run()
{
    if(!bV05Lab || NativeState==3) return;
    auto Player=UGameplayStatics::GetPlayerCharacter(this,0);
    auto Scanner=Player?Player->FindComponentByClass<UAnomalyScannerComponent>():nullptr;
    if(!Scanner || !Inventory || !PlayerHealth) { FailWithError(); return; }
    Inventory->CurrentCapacity=V05Capacity;
    Scanner->InitializeRunResources(V05ChargeBonus); Scanner->PrecisionReduction=V05Precision;
    FreezePlayer(false); SpawnInitialBox();
    if(bV05Lab && NativeState!=3) Telemetry.Start(this);
}
