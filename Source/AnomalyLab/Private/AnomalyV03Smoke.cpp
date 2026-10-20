#include "AnomalyV03Smoke.h"
#include "AnomalyRoundCoordinator.h"
#include "AnomalyBoxActor.h"
#include "AnomalyWorldPickup.h"
#include "AnomalyInventoryComponent.h"
#include "AnomalyWalletComponent.h"
#include "AnomalyHealthComponent.h"
#include "AnomalyScannerComponent.h"
#include "AnomalyEquipmentComponent.h"
#include "AnomalyProgressionSubsystem.h"
#include "Engine/GameInstance.h"
#include "AnomalyThreatCharacter.h"
#include "AnomalyExplorationWidget.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "Components/TextBlock.h"
#include "Components/BoxComponent.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"
#include "InputKeyEventArgs.h"
#include "HAL/PlatformTime.h"

namespace V03Smoke
{
    int32 Scenario = 0;
    bool Finished = false;
    TArray<TSharedPtr<FJsonValue>> Checks;
    FString Output;
}
AAnomalyV03Smoke::AAnomalyV03Smoke()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickGroup = TG_PrePhysics;
    bRender = FParse::Param(FCommandLine::Get(), TEXT("V03Render"));
    FParse::Value(FCommandLine::Get(), TEXT("V03Evidence="), V03Smoke::Output);
    FParse::Value(FCommandLine::Get(), TEXT("V03Strategy="), Strategy);
}
bool AAnomalyV03Smoke::Check(const FString& Name, bool Passed)
{
    auto Item = MakeShared<FJsonObject>();
    Item->SetStringField(TEXT("check"), FString::Printf(TEXT("S%d: %s"), V03Smoke::Scenario, *Name));
    Item->SetBoolField(TEXT("passed"), Passed);
    V03Smoke::Checks.Add(MakeShared<FJsonValueObject>(Item));
    UE_LOG(LogTemp, Display, TEXT("[V03Smoke] %s S%d %s"), Passed ? TEXT("PASS") : TEXT("FAIL"), V03Smoke::Scenario, *Name);
    if (!Passed) Finish(false);
    return Passed;
}
void AAnomalyV03Smoke::Finish(bool Passed)
{
    if (V03Smoke::Finished) return;
    V03Smoke::Finished = true;
    auto Report = MakeShared<FJsonObject>();
    Report->SetStringField(TEXT("status"), Passed ? TEXT("PASS") : TEXT("FAIL"));
    Report->SetStringField(TEXT("scope"), TEXT("Actual game world, native authority, camera collision traces and synthetic PlayerController input. Forced instance outcomes exercise branches. Render mode walks first-room route; other branch setup teleports. No physical human input/audio listening."));
    if (!Strategy.IsEmpty())
    {
        Report->SetStringField(TEXT("scope"),TEXT("Single autonomous navigation/input bot, natural outcomes, finite scanner resources. No human input or audio listening; not a balance population."));
        Report->SetStringField(TEXT("strategy"), Strategy);
        Report->SetNumberField(TEXT("run_seconds"), GetWorld()->GetTimeSeconds() - Started);
        Report->SetNumberField(TEXT("extracted_value"), Coordinator->FinalRunValue);
        Report->SetNumberField(TEXT("lost_value"), Coordinator->LostRunValue);
        Report->SetBoolField(TEXT("died"), Coordinator->RunEndReason == EAnomalyRunEndReason::Failed);
        Report->SetNumberField(TEXT("scans"), ScanCount);
        Report->SetNumberField(TEXT("rounds"), Coordinator->CompletedRounds);
        TArray<TSharedPtr<FJsonValue>> Regions;
        for (const auto& Pair:Coordinator->RegionStats) { auto R=MakeShared<FJsonObject>(); R->SetStringField(TEXT("region"),Pair.Key.ToString()); R->SetNumberField(TEXT("opens"),Pair.Value.OpenCount); R->SetNumberField(TEXT("scans"),Pair.Value.ScanCount); Regions.Add(MakeShared<FJsonValueObject>(R)); }
        Report->SetArrayField(TEXT("regions"),Regions);
        Report->SetStringField(TEXT("limitations"), TEXT("Single autonomous bot sample; navigation movement, real scan, unforced outcomes; does not represent human pacing or establish 3-5 minute target."));
    }
    Report->SetNumberField(TEXT("scenario"), V03Smoke::Scenario);
    Report->SetNumberField(TEXT("stage"), Stage);
    Report->SetArrayField(TEXT("checks"), V03Smoke::Checks);
    FString Text;
    FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Text));
    IFileManager::Get().MakeDirectory(*V03Smoke::Output, true);
    const bool Saved = FFileHelper::SaveStringToFile(Text, *(V03Smoke::Output / TEXT("runtime_report.json")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    FPlatformMisc::RequestExitWithStatus(false, Passed && Saved ? 0 : 1);
}
void AAnomalyV03Smoke::Key(FKey KeyValue, bool Pressed)
{ Player->GetController<APlayerController>()->InputKey(FInputKeyEventArgs(nullptr, INPUTDEVICEID_NONE, KeyValue, Pressed ? IE_Pressed : IE_Released, Pressed ? 1.f : 0.f, false, FPlatformTime::Cycles64())); }
void AAnomalyV03Smoke::Shot(const FString& Name)
{
    if (bRender) FScreenshotRequest::RequestScreenshot(V03Smoke::Output / (Name + TEXT(".png")), true, false, false, FIntRect(), true);
}
void AAnomalyV03Smoke::AimAt(const FVector& Target)
{
    UCameraComponent* Camera = Player->FindComponentByClass<UCameraComponent>();
    Player->GetController()->SetControlRotation((Target - Camera->GetComponentLocation()).Rotation());
}
void AAnomalyV03Smoke::PlaceNear(AActor* Target, float Distance)
{
    Player->SetActorLocation(Target->GetActorLocation() + FVector(0,-Distance,98-Target->GetActorLocation().Z), false);
    Player->GetCharacterMovement()->StopMovementImmediately();
    AimAt(Target->GetActorLocation() + (Cast<AAnomalyBoxActor>(Target) ? FVector(0,0,35) : FVector::ZeroVector));
}
bool AAnomalyV03Smoke::WalkTo(const FVector& Target)
{
    if (!bRender && Strategy.IsEmpty()) { Player->SetActorLocation(FVector(Target.X, Target.Y, 98), false); return true; }
    if (WalkPath.IsEmpty())
    {
        UNavigationPath* Path = UNavigationSystemV1::FindPathToLocationSynchronously(this, Player->GetActorLocation(), Target);
        if (!Check(TEXT("Walking route exists and is complete"), Path && Path->IsValid() && !Path->IsPartial())) return false;
        WalkPath = Path->PathPoints; WalkIndex = 1;
    }
    while (WalkPath.IsValidIndex(WalkIndex) && FVector::DistSquared2D(Player->GetActorLocation(), WalkPath[WalkIndex]) < 15.f*15.f) ++WalkIndex;
    if (!WalkPath.IsValidIndex(WalkIndex)) { WalkPath.Empty(); Player->ConsumeMovementInputVector(); Player->GetCharacterMovement()->StopMovementImmediately(); return true; }
    const FVector Direction = (WalkPath[WalkIndex] - Player->GetActorLocation()).GetSafeNormal2D();
    Player->AddMovementInput(Direction, FMath::Clamp(float(FVector::Dist2D(Player->GetActorLocation(),WalkPath[WalkIndex]))/80.f,.15f,1.f));
    static double LastWalkLog=0.;
    if (FPlatformTime::Seconds()-LastWalkLog>3.)
    {
        LastWalkLog=FPlatformTime::Seconds();
        UE_LOG(LogTemp,Display,TEXT("[V03Walk] Position=%s Waypoint=%s Velocity=%s"),*Player->GetActorLocation().ToString(),*WalkPath[WalkIndex].ToString(),*Player->GetVelocity().ToString());
    }
    Player->GetController()->SetControlRotation(Direction.Rotation());
    return false;
}
bool AAnomalyV03Smoke::Open(int32 Outcome)
{
    if (!Check(TEXT("Three candidates before selection"), Coordinator->CandidateBoxes.Num() == 3)) return false;
    Box = Coordinator->CandidateBoxes[Iteration % 3];
    PlaceNear(Box);
    Box->bForceOutcome = true;
    if (Strategy.IsEmpty()) Box->bUseObserverPool=false; // Explicit original-Chaser regression; T30 has its own real-input Observer path.
    // Allow the current camera component transform to update before interaction.
    Next = GetWorld()->GetTimeSeconds() + .15f;
    Stage = 20 + Outcome;
    return true;
}
void AAnomalyV03Smoke::Restart()
{
    ++V03Smoke::Scenario;
    Key(EKeys::R, true);
    Next = GetWorld()->GetTimeSeconds() + 5.f;
    Stage = 99;
}
void AAnomalyV03Smoke::Tick(float Seconds)
{
    Super::Tick(Seconds);
    if (V03Smoke::Finished) return;
    const float Time = GetWorld()->GetTimeSeconds();
    if (Time > (Strategy.IsEmpty() ? 155.f : 360.f)) { Check(TEXT("Scenario completes before timeout"), false); return; }
    if (Time < Next) return;
    if (Stage==-1) { Key(EKeys::E,false); Stage=0; Next=Time+.3f; return; }
    if (Stage == 0)
    {
        for (TActorIterator<AAnomalyRoundCoordinator> It(GetWorld()); It; ++It) { Coordinator = *It; break; }
        Player = UGameplayStatics::GetPlayerCharacter(this, 0);
        if (Player && Coordinator && Coordinator->IsPreparing() && Time>=2.f)
        {
            if (!Check(TEXT("Preparation has no boxes or combat; synthetic E starts a new run"),Coordinator->CandidateBoxes.IsEmpty())) return;
            Shot(TEXT("00_preparation")); Key(EKeys::E,true); Stage=-1; Next=Time+.2f; return;
        }
        if (!Player || !Coordinator || Time < 2.f || Coordinator->CandidateBoxes.Num() != 3) return;
        Health = Player->FindComponentByClass<UAnomalyHealthComponent>();
        Wallet = Player->FindComponentByClass<UAnomalyWalletComponent>();
        Scanner = Player->FindComponentByClass<UAnomalyScannerComponent>();
        StartingPermanentBalance=GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>()->GetProgress().Currency;
        if (!Check(TEXT("Exploration assets and player authority exist"), Coordinator->PlayMode == EAnomalyPlayMode::Exploration && Coordinator->Inventory && Health && Wallet && Scanner)) return;
        if (!Check(TEXT("Restart clean: inventory/wallet/settlement/counters"), Coordinator->Inventory->GetCount() == 0 && Wallet->Money == 0 && Coordinator->SettlementCount == 0 && Coordinator->CompletedRounds == 0)) return;
        // Deliver synthetic events before controller input processing, as OS events normally arrive.
        Player->GetController<APlayerController>()->PrimaryActorTick.AddPrerequisite(this, PrimaryActorTick);
        Started = Time;
        if (!Strategy.IsEmpty()) { Stage = 200; Started = Time; }
        else if (V03Smoke::Scenario == 0) Stage = 1;
        else if (V03Smoke::Scenario == 1) { Coordinator->NextRoundDelay = .1; Stage = 10; }
        else if (V03Smoke::Scenario == 2 || V03Smoke::Scenario == 4) Stage = 10;
        else if (V03Smoke::Scenario == 3) Stage = 60;
        else if (V03Smoke::Scenario == 5) { Coordinator->LootDefinitions.Empty(); Stage = 10; }
        else if (V03Smoke::Scenario == 6) Stage = 70;
    }
    if (!Strategy.IsEmpty()) { TickStrategy(Seconds); return; }
    switch (Stage)
    {
    case 1:
        if (!Check(TEXT("Four valid item definitions and fixed trash value"), Coordinator->LootDefinitions.Num() == 4 && Coordinator->LootDefinitions[3]->bTrash && Coordinator->LootDefinitions[3]->TrashValue == 3)) return;
        for (AAnomalyBoxActor* Candidate : Coordinator->CandidateBoxes)
        {
            UNavigationPath* Path = UNavigationSystemV1::FindPathToLocationSynchronously(this, Player->GetActorLocation(), Candidate->GetActorLocation()+FVector(0,-180,48));
            if (!Check(TEXT("All rooms reachable by navigation"), Path && Path->IsValid() && !Path->IsPartial())) return;
            if (!Check(TEXT("Far interaction rejected"), !Candidate->NativeInteract(Player,0))) return;
        }
        Shot(TEXT("01_entry")); Stage = 2; Next = Time+1.f; break;
    case 2:
        Box = Coordinator->CandidateBoxes[0];
        if (!WalkTo(Box->GetActorLocation()+FVector(0,-180,48))) return;
        AimAt(Box->GetActorLocation()+FVector(0,0,35)); Stage = 3; Next = Time+.25f; break;
    case 3:
        if (Coordinator->TraceExplorationBox(Player) != Box)
        {
            UCameraComponent* Camera=Player->FindComponentByClass<UCameraComponent>();
            UE_LOG(LogTemp, Warning, TEXT("[V03Smoke] Aim debug Player=%s Box=%s Camera=%s Rotation=%s Hit=%s"),
                *Player->GetActorLocation().ToString(),*Box->GetActorLocation().ToString(),*Camera->GetComponentLocation().ToString(),
                *Camera->GetComponentRotation().ToString(),*GetNameSafe(Coordinator->TraceExplorationTarget(Player)));
            AimAt(Box->GetActorLocation()+FVector(0,0,35));
            if (!bShot) { Shot(TEXT("failure_aim")); bShot=true; Next=Time+1.f; return; }
        }
        if (!Check(TEXT("Camera trace finds room A box"), Coordinator->TraceExplorationBox(Player) == Box)) return;
        bShot=false;
        Key(EKeys::Q,true); Stage = 4; Next = Time+.45f; break;
    case 4:
        if (!Check(TEXT("Q press drives partial scan and one start sound"), Scanner->Progress > .1f && Scanner->Progress < 1.f && Coordinator->FeedbackCounts.FindRef(TEXT("ScanStart")) == 1)) return;
        Shot(TEXT("02_scan_progress")); Key(EKeys::Q,false); Stage = 5; Next = Time+.25f; break;
    case 5:
        if (!Check(TEXT("Q release cancels immediately without cached result or charge"), Scanner->Progress == 0 && !Box->GetCachedReading(EAnomalyEquipment::MetalDetector).bScanned && Scanner->GetRemaining(EAnomalyEquipment::MetalDetector)==3)) return;
        Key(EKeys::Q,true); Stage = 51; Next = Time+.35f; break;
    case 51:
        if (!Check(TEXT("Restarted scan in progress before equipment change"), Scanner->Progress > .05f)) return;
        Player->FindComponentByClass<UAnomalyEquipmentComponent>()->EquipGun(); Stage=52; Next=Time+.2f; break;
    case 52:
        if (!Check(TEXT("Equipment switch cancels scan without charge"), Scanner->Progress==0 && Scanner->GetRemaining(EAnomalyEquipment::MetalDetector)==3)) return;
        Player->FindComponentByClass<UAnomalyEquipmentComponent>()->EquipScanner(); Stage=53; Next=Time+.2f; break;
    case 53:
        if (!Check(TEXT("Holding Q cannot restart after cancellation"), Scanner->Progress==0)) return;
        Key(EKeys::Q,false); Stage=54; Next=Time+.1f; break;
    case 54: Key(EKeys::Q,true); Stage=55; Next=Time+.35f; break;
    case 55:
        if (!Check(TEXT("Scan partial before leaving range"),Scanner->Progress>.05f)) return;
        PlaceNear(Box,450.f); Stage=56; Next=Time+.2f; break;
    case 56:
        if (!Check(TEXT("Range loss cancels without charge or cache"),Scanner->Progress==0 && Scanner->GetRemaining(EAnomalyEquipment::MetalDetector)==3
            && !Box->GetCachedReading(EAnomalyEquipment::MetalDetector).bScanned)) return;
        Key(EKeys::Q,false); PlaceNear(Box,180.f); Stage=57; Next=Time+.2f; break;
    case 57: Key(EKeys::Q,true); Stage=58; Next=Time+.35f; break;
    case 58:
        if (!Check(TEXT("Scan partial before occlusion"),Scanner->Progress>.05f)) return;
        {
            auto Camera=Player->FindComponentByClass<UCameraComponent>();
            Occluder=GetWorld()->SpawnActor<AActor>();
            auto Wall=NewObject<UBoxComponent>(Occluder);
            Occluder->SetRootComponent(Wall); Wall->SetBoxExtent(FVector(35,35,35));
            Wall->SetCollisionEnabled(ECollisionEnabled::QueryOnly); Wall->SetCollisionResponseToAllChannels(ECR_Ignore);
            Wall->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block); Wall->RegisterComponent();
            Occluder->SetActorLocation(Camera->GetComponentLocation()+Camera->GetForwardVector()*70.f);
        }
        Stage=59; Next=Time+.2f; break;
    case 59:
        if (!Check(TEXT("Visibility occlusion cancels without charge or cache"),Scanner->Progress==0 && Scanner->GetRemaining(EAnomalyEquipment::MetalDetector)==3
            && !Box->GetCachedReading(EAnomalyEquipment::MetalDetector).bScanned)) return;
        Occluder->Destroy(); Occluder=nullptr; Key(EKeys::Q,false); Stage=590; Next=Time+.2f; break;
    case 590: Key(EKeys::Q,true); Stage=6; Next=Time+1.4f; break;
    case 6:
        Key(EKeys::Q,false);
        if (!Check(TEXT("One-second scan completes with reliability, cache and one charge"), Box->GetCachedReading(EAnomalyEquipment::MetalDetector).bScanned && Coordinator->FeedbackCounts.FindRef(TEXT("ScanComplete")) == 1 && Scanner->GetRemaining(EAnomalyEquipment::MetalDetector)==2)) return;
        Shot(TEXT("03_scan_result")); Stage = 10; Next = Time+.8f; break;
    case 10:
        if (V03Smoke::Scenario == 1 || (V03Smoke::Scenario==0 && FParse::Param(FCommandLine::Get(),TEXT("V03FromMenu")) && Coordinator->Inventory->GetCount()==4 && Coordinator->CompletedRounds>=5)) Open(2);
        else Open(Iteration == 1 ? 1 : 0);
        break;
    case 20: case 21: case 22:
        {
            const int32 Outcome = Stage-20;
            Box->bForceOutcome = true;
            if (!Check(TEXT("Valid camera E interaction opens one box"), Box->NativeInteract(Player,Outcome))) return;
            if (!Check(TEXT("Duplicate opening rejected and other two locked"), !Box->NativeInteract(Player,Outcome)
                && Coordinator->CandidateBoxes[(Iteration+1)%3]->bSelectionLocked && Coordinator->CandidateBoxes[(Iteration+2)%3]->bSelectionLocked)) return;
            if (Outcome == 2) { Stage = 40; Next=Time+1.25f; }
            else { Stage = 30; Next=Time+1.25f; }
            break;
        }
    case 30:
        if (Coordinator->GetNativeRoundState()==1) return; // Timers tick after this automation actor.
        if (V03Smoke::Scenario == 5)
        {
            if (!Check(TEXT("Missing loot definitions produce Error without income or permanent loss"), Coordinator->RunEndReason == EAnomalyRunEndReason::Error && Wallet->Money == 0 && !Coordinator->bSettlementDone
                && GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>()->GetProgress().Currency==StartingPermanentBalance)) return;
            Shot(TEXT("12_technical_error")); Stage=80; Next=Time+1.f; break;
        }
        if (!Check(TEXT("Opening spawned exactly one persistent visible pickup, wallet zero"), Coordinator->WorldLoot.Num() == Iteration+1-Coordinator->Inventory->GetCount() && Wallet->Money == 0)) return;
        {
            AAnomalyWorldPickup* Loot = Coordinator->WorldLoot.Last();
            if (!Check(TEXT("Pickup stores the once-generated amount"), Loot->Item.Value == (Iteration == 1 ? 3 : Box->HighValueAmount))) return;
            const int32 StableValue=Loot->Item.Value;
            if (!Check(TEXT("Initialized item rejects reinitialization and reroll"), !Loot->InitializeItem(Coordinator->LootDefinitions[0],999999,Coordinator->RoundId) && Loot->Item.Value==StableValue)) return;
            if (!Check(TEXT("Wrong interactor and out-of-range pickup rejected"), !Coordinator->TryPickup(this,Loot))) return;
            PlaceNear(Loot,650.f); Stage=31; Next=Time+.15f;
        }
        break;
    case 31:
        {
            AAnomalyWorldPickup* Loot=Coordinator->WorldLoot.Last();
            if (!Check(TEXT("Player beyond 300 cm cannot pick up"), !Coordinator->TryPickup(Player,Loot))) return;
            PlaceNear(Loot);
            if (V03Smoke::Scenario==0 && Iteration==0)
            {
                Occluder=GetWorld()->SpawnActor<AActor>();
                UBoxComponent* Wall=NewObject<UBoxComponent>(Occluder);
                Occluder->SetRootComponent(Wall); Wall->SetBoxExtent(FVector(60,5,100));
                Wall->SetCollisionEnabled(ECollisionEnabled::QueryOnly); Wall->SetCollisionResponseToAllChannels(ECR_Block);
                Wall->SetCanEverAffectNavigation(false); Wall->RegisterComponent();
                Occluder->SetActorLocation(Loot->GetActorLocation()+FVector(0,-80,0)); Stage=34;
            }
            else Stage=32;
            Next=Time+.2f;
        } break;
    case 34:
        if (!Check(TEXT("Occlusion rejects pickup, retaining its ownership and value"), !Coordinator->TryPickup(Player,Coordinator->WorldLoot.Last()) && !Coordinator->WorldLoot.Last()->bClaimed)) return;
        Occluder->Destroy(); Stage=32; Next=Time+.2f; break;
    case 32:
        {
            AAnomalyWorldPickup* Loot=Coordinator->WorldLoot.Last();
            const FGuid Id=Loot->Item.InstanceId;
            if (Iteration == 4)
            {
                if (!Check(TEXT("Fifth item rejected; full backpack preserves world proxy"), !Coordinator->TryPickup(Player,Loot) && IsValid(Loot) && !Loot->bClaimed && Coordinator->Inventory->GetCount()==4)) return;
                Shot(TEXT("06_inventory_full")); Stage=50; Next=Time+.8f;
            }
            else
            {
                const int32 Value=Loot->Item.Value;
                // Synthetic E traverses the actual input stack, including the old box adapter.
                Key(EKeys::E,true); Key(EKeys::E,false);
                ExpectedValue += Value;
                Stage=33; Next=Time+.2f;
                bShot=false;
            }
        } break;
    case 33:
        if (!bShot && !Check(TEXT("Synthetic E pickup changes exactly one slot and carry value only"), Coordinator->Inventory->GetCount()==Iteration+1 && Coordinator->Inventory->GetCarryValue()==ExpectedValue && Wallet->Money==0)) return;
        if (!bShot)
        {
            Shot(TEXT("04_pickup_")+FString::FromInt(Iteration)); bShot=true;
            for (int32 I=0; I<5; ++I) { Key(EKeys::E,true); Key(EKeys::E,false); }
            Stage=35; Next=Time+.2f; return;
        }
        if (Coordinator->GetRoundPhase()!=EAnomalyRoundPhase::PostRoundDecision) return;
        if (V03Smoke::Scenario==2 || V03Smoke::Scenario==4) { Stage=60; break; }
        ++Iteration; Key(EKeys::One,true); Key(EKeys::One,false); Stage=10; Next=Time+.2f; break;
    case 35:
        if (!Check(TEXT("Five repeated E events cannot duplicate the claimed instance"), Coordinator->Inventory->GetCount()==Iteration+1 && Coordinator->Inventory->GetCarryValue()==ExpectedValue && Wallet->Money==0)) return;
        Stage=33; Next=Time+.6f; break;
    case 40:
        if (Coordinator->RoundPhase==EAnomalyRoundPhase::ResolvingOutcome) return;
        if (!Check(TEXT("Threat spawns inactive with warning before pursuit"), Coordinator->RoundPhase==EAnomalyRoundPhase::ThreatWarning && Coordinator->CurrentSpider && !Coordinator->CurrentSpider->bThreatActive)) return;
        AimAt(Coordinator->CurrentSpider->GetActorLocation()+FVector(0,0,20));
        Shot(TEXT("07_warning")); Stage=43; Next=Time+.3f; break;
    case 43:
        Player->SetActorLocation(FVector(0,1750,98),false); Stage=41; Next=Time+1.f; break;
    case 41:
        if (Coordinator->RoundPhase==EAnomalyRoundPhase::ThreatWarning) return;
        if (!Check(TEXT("Default threat active, damage enabled and warning emitted once"), Coordinator->RoundPhase==EAnomalyRoundPhase::ThreatActive && Health->bDamageEnabled && Coordinator->FeedbackCounts.FindRef(TEXT("Warning"))==Iteration+1)) return;
        Shot(TEXT("08_pursuit")); Stage=42; break;
    case 42:
        if (Coordinator->RoundPhase==EAnomalyRoundPhase::ThreatActive)
        {
            // Survive through actual movement in the entrance area; no immunity or forced timer completion.
            const float Angle=(Time-Started)*.72f;
            const FVector Target(500.f*FMath::Cos(Angle), 1570.f+360.f*FMath::Sin(Angle),98);
            Player->AddMovementInput((Target-Player->GetActorLocation()).GetSafeNormal2D(),1.f);
            if (Health->bDead) { Check(TEXT("Survival route remains alive"),false); return; }
            return;
        }
        if (Coordinator->RoundPhase==EAnomalyRoundPhase::ThreatContainment) return;
        Player->GetCharacterMovement()->StopMovementImmediately();
        if (!Check(TEXT("Threat naturally resolves after twenty seconds"), Coordinator->ThreatsResolved==Iteration+1 && !Coordinator->bThreatPursuitActive)) return;
        if (V03Smoke::Scenario==0 && FParse::Param(FCommandLine::Get(),TEXT("V03FromMenu")))
        {
            if (!Check(TEXT("Continuous itinerary carries loot through live threat with zero wallet credit"),Coordinator->Inventory->GetCount()==4 && Wallet->Money==0 && Coordinator->ThreatsResolved==1)) return;
            Coordinator->CashOut(); Stage=60; Next=Time+.3f; break;
        }
        ++Iteration;
        if (Iteration==2)
        {
            const int32 Round=Coordinator->RoundId;
            Coordinator->ContinueRun();
            if (!Check(TEXT("Second containment requires physical extraction and forbids new boxes"), Coordinator->RoundPhase==EAnomalyRoundPhase::ReturningToExtraction && Coordinator->RoundId==Round && Coordinator->CandidateBoxes.IsEmpty() && Wallet->Money==0)) return;
            Shot(TEXT("09_forced_return")); Stage=60; Next=Time+.8f;
        }
        else { Coordinator->ContinueRun(); Stage=10; Next=Time+.2f; }
        break;
    case 50:
        if (Coordinator->RoundPhase!=EAnomalyRoundPhase::PostRoundDecision) return;
        if (V03Smoke::Scenario==0 && FParse::Param(FCommandLine::Get(),TEXT("V03FromMenu")))
        {
            Coordinator->ContinueRun(); Iteration=0; Stage=10; Next=Time+.2f; break;
        }
        Coordinator->CashOut();
        if (!Check(TEXT("Choosing extraction grants no money and keeps movement"), Coordinator->RoundPhase==EAnomalyRoundPhase::ReturningToExtraction && Wallet->Money==0 && Player->GetCharacterMovement()->MovementMode!=MOVE_None)) return;
        if (!Check(TEXT("Remote confirmation rejected"), !Coordinator->ConfirmExtraction(Player))) return;
        Stage=60; break;
    case 60:
        if (V03Smoke::Scenario==2)
        {
            Health->SetDamageEnabled(true); Health->ApplyDamage(Health->MaxHealth);
            Stage=62; Next=Time+.2f; break;
        }
        if (!WalkTo(Coordinator->EntranceLocation)) return;
        AimAt(FVector(0,2070,230));
        if (!Check(TEXT("Physical entrance accepts extraction once"), Coordinator->ConfirmExtraction(Player) && !Coordinator->ConfirmExtraction(Player))) return;
        if (!Check(TEXT("Confirmation frame cannot pay before next frame"),Wallet->Money==0 && Coordinator->SettlementCount==0)) return;
        if (V03Smoke::Scenario==4) { Health->SetDamageEnabled(true); Health->ApplyDamage(Health->MaxHealth); }
        Stage=62; Next=Time+.3f; break;
    case 62:
        if (Coordinator->GetNativeRoundState()!=3) return; // Commit timer runs after PrePhysics, possibly later in this frame.
        if (V03Smoke::Scenario==2 || V03Smoke::Scenario==4)
        {
            if (!Check(TEXT("Death wins, snapshots carry loss, no income or settlement"), Coordinator->RunEndReason==EAnomalyRunEndReason::Failed && Coordinator->LostRunValue==ExpectedValue && Coordinator->FinalRunValue==0 && Wallet->Money==0 && Coordinator->SettlementCount==0)) return;
            if (!Check(TEXT("Death preserves prior permanent currency and immutable zero-income snapshot"),GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>()->GetProgress().Currency==StartingPermanentBalance
                && Coordinator->GetEndSnapshot().PermanentBalance==StartingPermanentBalance && !Coordinator->GetEndSnapshot().bDurableCredit)) return;
            Shot(V03Smoke::Scenario==4 ? TEXT("11_same_frame_death") : TEXT("10_death_loss"));
        }
        else
        {
            if (!Check(TEXT("Successful extraction credits exact snapshot once, including empty exit"), Coordinator->RunEndReason==EAnomalyRunEndReason::CashedOut && Coordinator->FinalRunValue==ExpectedValue && Wallet->Money==ExpectedValue && Coordinator->SettlementCount==1)) return;
            if (!Check(TEXT("Physical delayed entrance durably credits only extracted carry"),GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>()->GetProgress().Currency==StartingPermanentBalance+ExpectedValue
                && Coordinator->GetEndSnapshot().PermanentBalance==StartingPermanentBalance+ExpectedValue && Coordinator->GetEndSnapshot().bDurableCredit)) return;
            Shot(TEXT("05_extraction_")+FString::FromInt(V03Smoke::Scenario));
        }
        if (!Check(TEXT("Terminal clears inventory/boxes/world loot and rejects late actions"), Coordinator->Inventory->GetCount()==0 && Coordinator->WorldLoot.IsEmpty() && Coordinator->CandidateBoxes.IsEmpty() && !Coordinator->ConfirmExtraction(Player))) return;
        {
        const auto Snapshot=Coordinator->GetEndSnapshot();
        Coordinator->CompleteCurrentOutcome(); Coordinator->CashOut(); Coordinator->ContinueRun(); Coordinator->EndRun();
        if (!Check(TEXT("Duplicate terminal calls cannot mutate immutable result or permanent currency"),Coordinator->GetEndSnapshot().RunId==Snapshot.RunId
            && Coordinator->GetEndSnapshot().PermanentBalance==Snapshot.PermanentBalance && Coordinator->GetEndSnapshot().CashedOut==Snapshot.CashedOut
            && GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>()->GetProgress().Currency==Snapshot.PermanentBalance)) return;
        }
        if (!Check(TEXT("Late callbacks cannot change terminal snapshot"), Coordinator->GetNativeRoundState()==3 && Coordinator->SettlementCount <= 1)) return;
        Stage=80; Next=Time+1.f; break;
    case 70:
        Coordinator->EndRun();
        if (!Check(TEXT("Unauthorised direct EndRun is Error, never free extraction"), Coordinator->RunEndReason==EAnomalyRunEndReason::Error && Coordinator->SettlementCount==0)) return;
        Finish(true); break;
    case 80: Restart(); break;
    case 99: Check(TEXT("R synthetic input reloads current map"),false); break;
    }
}



void AAnomalyV03Smoke::TickStrategy(float Seconds)
{
    const float Time = GetWorld()->GetTimeSeconds();
    if (Coordinator->GetNativeRoundState()==3)
    {
        Check(TEXT("Strategy ended as extraction or death; no technical error"), Coordinator->RunEndReason==EAnomalyRunEndReason::CashedOut || Coordinator->RunEndReason==EAnomalyRunEndReason::Failed);
        Finish(!V03Smoke::Finished); return;
    }
    switch (Stage)
    {
    case 200:
        if (Coordinator->CandidateBoxes.Num()!=3) return;
        {
            int32 Index = FMath::RandRange(0,2);
            if (Strategy!=TEXT("random"))
            {
                float Best=-1.e9f;
                for (int32 I=0; I<3; ++I)
                {
                    // Bot uses public box type only; Unknown is not given hidden information.
                    const FName Id=Coordinator->CandidateBoxes[I]->DefinitionID;
                    const float Score = Strategy==TEXT("conservative") ? (Id==TEXT("Safe")?3.f:Id==TEXT("Unknown")?2.f:1.f)
                        : (Id==TEXT("Risky")?3.f:Id==TEXT("Unknown")?2.f:1.f);
                    if (Score>Best) { Best=Score; Index=I; }
                }
            }
            Box=Coordinator->CandidateBoxes[Index]; ++ChosenRounds;
            Stage=201;
        } break;
    case 201:
        // Approach from the corridor side instead of walking through C's solid crate.
        if (!WalkTo(Box->GetActorLocation()+FVector(Box->GetActorLocation().X>100?-180:Box->GetActorLocation().X<-100?180:0,
            FMath::Abs(Box->GetActorLocation().X)<100?180:0,48))) return;
        AimAt(Box->GetActorLocation()+FVector(0,0,35)); Stage=202; Next=Time+.25f; break;
    case 202:
        if (Scanner->GetRemaining(Player->FindComponentByClass<UAnomalyEquipmentComponent>()->GetEffectiveEquipment())==0)
        { if (!Check(TEXT("Finite scanner exhausted; bot proceeds without a new reading"),!Box->bForceOutcome && Box->NativeInteract(Player))) return;
          Stage=204; Next=Time+1.2f; break; }
        Key(EKeys::Q,true); Stage=203; Next=Time+1.3f; break;
    case 203:
        Key(EKeys::Q,false);
        if (!Check(TEXT("Strategy completed actual scan before opening"), Box->GetCachedReading(Player->FindComponentByClass<UAnomalyEquipmentComponent>()->GetEffectiveEquipment()).bScanned)) return;
        ++ScanCount;
        if (!Check(TEXT("Strategy opens without forced outcome"), !Box->bForceOutcome && Box->NativeInteract(Player))) return;
        Stage=204; Next=Time+1.2f; break;
    case 204:
        if (Coordinator->RoundPhase==EAnomalyRoundPhase::ThreatWarning || Coordinator->RoundPhase==EAnomalyRoundPhase::ThreatActive)
        { Stage=207; WalkPath.Empty(); break; }
        if (!Coordinator->WorldLoot.IsEmpty())
        {
            AAnomalyWorldPickup* Loot=Coordinator->WorldLoot.Last();
            const float Side=Player->GetActorLocation().X<Loot->GetActorLocation().X?-250.f:250.f;
            if (!WalkTo(Loot->GetActorLocation()+FVector(Side,0,13))) return;
            AimAt(Loot->GetActorLocation()); Stage=205; Next=Time+.2f; break;
        }
        Stage=206; break;
    case 205:
        if (!Coordinator->WorldLoot.IsEmpty()) Coordinator->TryPickup(Player,Coordinator->WorldLoot.Last());
        Stage=206; break;
    case 206:
        if (Coordinator->RoundPhase!=EAnomalyRoundPhase::PostRoundDecision && Coordinator->RoundPhase!=EAnomalyRoundPhase::ReturningToExtraction) return;
        {
            const int32 Limit = Strategy==TEXT("conservative") ? 2 : Strategy==TEXT("greedy") ? 4 : 3;
            if (Coordinator->Inventory->GetCount()>=Limit || ChosenRounds>=7 || Coordinator->ThreatsResolved>=Coordinator->MaxThreats)
            { Coordinator->CashOut(); Stage=208; }
            else { Coordinator->ContinueRun(); Stage=200; }
        } break;
    case 207:
        if (Coordinator->RoundPhase==EAnomalyRoundPhase::ThreatWarning || Coordinator->RoundPhase==EAnomalyRoundPhase::ThreatActive)
        {
            // Navigate to the entrance, then keep moving through a broad loop. Damage and all threat defaults stay enabled.
            if (Player->GetActorLocation().Y<1150.f)
            { WalkTo(FVector(0,1550,98)); return; }
            WalkPath.Empty();
            const float Angle=(Time-Started)*.72f;
            const FVector Target(500.f*FMath::Cos(Angle),1570.f+360.f*FMath::Sin(Angle),98);
            Player->AddMovementInput((Target-Player->GetActorLocation()).GetSafeNormal2D(),1.f);
            return;
        }
        if (Coordinator->RoundPhase==EAnomalyRoundPhase::ThreatContainment) return;
        Player->GetCharacterMovement()->StopMovementImmediately(); Stage=206; break;
    case 208:
        if (!WalkTo(Coordinator->EntranceLocation)) return;
        if (!Check(TEXT("Strategy reaches physical extraction zone"),Coordinator->ConfirmExtraction(Player))) return;
        Stage=209; Next=Time+.3f; break;
    case 209: break;
    }
}
