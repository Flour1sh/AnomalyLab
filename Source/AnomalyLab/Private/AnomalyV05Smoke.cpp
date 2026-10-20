#if !UE_BUILD_SHIPPING
#include "AnomalyTransitionSubsystem.h"
#include "AnomalyHub.h"
#include "AnomalyProgressionConfig.h"
#include "AnomalyMetaSaveGame.h"
#include "AnomalyInventoryComponent.h"
#include "AnomalyWorldPickup.h"
#include "AnomalyScannerComponent.h"
#include "AnomalyHealthComponent.h"
#include "AnomalyBoxActor.h"
#include "AnomalyPlacementConfig.h"
#include "AnomalyEnvironment.h"
#include "AnomalyObserverCharacter.h"
#include "Components/BoxComponent.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "AnomalyThreatCharacter.h"
#include "Camera/CameraComponent.h"
#include "Components/BoxComponent.h"
#include "Components/TextBlock.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"

struct FAnomalyV05Probe
{
    static bool Seed(UAnomalyProgressionSubsystem* P)
    { auto M=P->Progress; M.Currency=10000; M.BatteryLevel=1; M.PrecisionLevel=1; M.BackpackLevel=1; M.StoredDecoys=1;
      FString Why; return P->Commit(M,Why); }
    static void EventSchedule(AAnomalyEnvironmentController* E)
    {
        E->bPlanBuilt=true; E->RunStarted=E->GetWorld()->GetTimeSeconds(); E->EventPlan.Empty(); E->NextEvent=0;
        FAnomalyEventSpec A; A.Type=EAnomalyDynamicEvent::PowerFluctuation; A.At=.2f; A.Duration=4;
        auto B=A; B.Type=EAnomalyDynamicEvent::ContainmentAlarm; B.At=16.2f; E->EventPlan={A,B};
    }
    static void QuietSeed(UAnomalyTransitionSubsystem* T,UAnomalyEnvironmentConfig* C)
    { for(int32 Seed=0;Seed<1000;++Seed) if(C->BuildEventPlan(Seed).IsEmpty()) { T->Launch.Seed=Seed; return; } }
    static void Budget(AAnomalyObserverCharacter* O,float N) { O->ObservedBudget=N; }
    static int32 RegionState(AAnomalyRoundCoordinator* C) { return C->RegionStream.GetCurrentSeed(); }
    static void Currency(UAnomalyProgressionSubsystem* P,int64 Value) { P->Progress.Currency=Value; }
    static bool SeedShop(UAnomalyProgressionSubsystem* P)
    { auto M=P->Progress; M.Currency=10000; M.BatteryLevel=0; M.PrecisionLevel=0; M.BackpackLevel=0; M.StoredDecoys=0;
      FString Why; return P->Commit(M,Why); }
    static bool Import(UAnomalyProgressionSubsystem* P,const FString& Source,FString& Why) { return P->ImportSave(Source,Why); }
    static void Fault(UAnomalyProgressionSubsystem* P,int32 N) { P->SaveFault=N; }
    static void Carry(AAnomalyRoundCoordinator* C,int32 N)
    { FAnomalyItemInstance Item; Item.InstanceId=FGuid::NewGuid(); Item.Value=N; Item.DisplayName=FText::FromString(TEXT("自动测试样本")); C->Inventory->Items.Add(Item); }
};
namespace V05Smoke
{
    FDelegateHandle Handle;
    FString Output,Mode;
    int32 Stage=0,Run=0,StartRevision=0,PickupValue=0;
    int64 Balance=0;
    double Started=0,Next=0;
    bool Finished=false;
    FGuid RunID;
    TWeakObjectPtr<AAnomalyRoundCoordinator> Departed;
    TWeakObjectPtr<AAnomalyThreatCharacter> ChamberThreat;
    TArray<TSharedPtr<FJsonValue>> Checks;
    void Finish(bool Pass)
    {
        if(Finished) return; Finished=true;
        auto R=MakeShared<FJsonObject>(); R->SetStringField(TEXT("status"),Pass?TEXT("PASS"):TEXT("FAIL"));
        R->SetStringField(TEXT("mode"),Mode); R->SetNumberField(TEXT("stage"),Stage); R->SetNumberField(TEXT("completed_trips"),Run);
        R->SetStringField(TEXT("scope"),TEXT("Real travel, physical extraction validation and durable account. Test-only initial upgrades/carry/damage/save faults are explicit fixtures; no human input claim."));
        R->SetArrayField(TEXT("checks"),Checks); FString Json; FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Json));
        bool Saved=FFileHelper::SaveStringToFile(Json,*(Output/TEXT("report.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
        FPlatformMisc::RequestExitWithStatus(false,Pass&&Saved?0:1);
    }
    bool Check(const FString& Name,bool Pass)
    {
        auto R=MakeShared<FJsonObject>(); R->SetStringField(TEXT("check"),Name); R->SetBoolField(TEXT("passed"),Pass);
        Checks.Add(MakeShared<FJsonValueObject>(R)); UE_LOG(LogTemp,Display,TEXT("[V05] %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),*Name);
        if(!Pass) Finish(false); return Pass;
    }
    void Hold(APlayerController* PC,FKey K,bool Down)
    { PC->InputKey(FInputKeyEventArgs(nullptr,INPUTDEVICEID_NONE,K,Down?IE_Pressed:IE_Released,Down?1.f:0.f,false,FPlatformTime::Cycles64())); }
    AAnomalyEnvironmentTerminal* Power(UWorld* W)
    { for(TActorIterator<AAnomalyEnvironmentTerminal> It(W);It;++It) if(It->Kind==EAnomalyEnvironmentKind::Power) return *It; return nullptr; }
    void Key(APlayerController* PC,FKey K)
    { PC->InputKey(FInputKeyEventArgs(nullptr,INPUTDEVICEID_NONE,K,IE_Pressed,1.f,false,FPlatformTime::Cycles64()));
      PC->InputKey(FInputKeyEventArgs(nullptr,INPUTDEVICEID_NONE,K,IE_Released,0.f,false,FPlatformTime::Cycles64())); }
    void Shot(const FString& Name)
    { if(!FParse::Param(FCommandLine::Get(),TEXT("nullrhi"))) FScreenshotRequest::RequestScreenshot(Output/(Name+TEXT(".png")),true,false,false,FIntRect(),true); }
    void Tick(UWorld* W,ELevelTick,float)
    {
        if(Finished || !W || !W->IsGameWorld()) return;
        const double Time=FPlatformTime::Seconds();
        if(Time-Started>240) { Check(TEXT("Timed itinerary"),false); return; }
        if(Time<Next || W->GetTimeSeconds()<1) return;
        auto PC=W->GetFirstPlayerController(); if(!PC || !PC->GetPawn()) return;
        auto P=W->GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>();
        auto T=W->GetGameInstance()->GetSubsystem<UAnomalyTransitionSubsystem>();
        auto Hub=Cast<AAnomalyHubPlayerController>(PC);
        AAnomalyRoundCoordinator* C=nullptr; for(TActorIterator<AAnomalyRoundCoordinator> It(W);It;++It) { C=*It; break; }
        if(Mode==TEXT("Direct") && Hub)
        { Check(TEXT("Unauthorized direct Lab safely returned Hub"),T->GetResult().Reason==EAnomalyRunEndReason::Error && T->GetPhase()==EAnomalyTravelPhase::HubReady && P->GetProgress().Revision==0); Finish(!Finished); return; }
        if(Mode==TEXT("Import") && Hub)
        {
            FAnomalyMetaProgress Old; Old.SchemaVersion=1; Old.Currency=12345; Old.BatteryLevel=2; Old.PrecisionLevel=1;
            Old.BackpackLevel=1; Old.StoredDecoys=1; Old.Revision=17; Old.RecentSettlements.Add(FGuid::NewGuid());
            TArray<uint8> Bytes,After; FString Why; const FString Source=Output/TEXT("Automation_v04_fixture.sav");
            if(!Check(TEXT("Representative old Schema1 serialized"),FAnomalyMetaPersistence::Encode(Old,Bytes) && FFileHelper::SaveArrayToFile(Bytes,*Source))) return;
            if(!Check(TEXT("Explicit old save import uses validated existing authority"),FAnomalyV05Probe::Import(P,Source,Why))) return;
            const auto& Imported=P->GetProgress();
            if(!Check(TEXT("Imported nonzero currency upgrades decoy GUIDs migrate to Schema2"),Imported.SchemaVersion==2 && Imported.Currency==12345 && Imported.BatteryLevel==2 && Imported.PrecisionLevel==1 && Imported.BackpackLevel==1 && Imported.StoredDecoys==1 && Imported.Revision==17 && Imported.RecentSettlements==Old.RecentSettlements)) return;
            if(!Check(TEXT("Source bytes unchanged and second import cannot overwrite"),FFileHelper::LoadFileToArray(After,*Source) && After==Bytes && !FAnomalyV05Probe::Import(P,Source,Why))) return;
            FAnomalyMetaProgress Reload; bool Future=false;
            if(!Check(TEXT("Imported file readback preserves all values"),FAnomalyMetaPersistence::Load(P->GetSavePath(),Reload,Future,Why) && Reload.Currency==12345 && Reload.SchemaVersion==2 && Reload.Revision==17)) return;
            Finish(true); return;
        }
        if(Mode==TEXT("RestartRead") && Hub)
        {
            Check(TEXT("Process restart retains durable equipment/currency and consumed decoy"),P->GetProgress().Currency==10000 && P->GetProgress().BatteryLevel==1 && P->GetProgress().StoredDecoys==0);
            Check(TEXT("Process restart does not restore carry/run or replay settlement"),!T->GetLaunch().Run.IsValid() && !T->GetResult().RunId.IsValid() && P->GetProgress().Extractions==0);
            Finish(!Finished); return;
        }
        if(Mode==TEXT("Shop") && Hub)
        {
            if(Stage==0)
            {
                if(!Check(TEXT("Explicit shop fixture starts with currency but no upgrades"),FAnomalyV05Probe::SeedShop(P))) return;
                FString Why;
                if(!Check(TEXT("Hub purchases require an actual physical shop panel"),!P->PurchaseHub(Hub,0,P->GetProgress().Revision,FGuid::NewGuid(),Why))) return;
                AAnomalyHubTerminal* Shop=nullptr; for(TActorIterator<AAnomalyHubTerminal> It(W);It;++It) if(It->Kind==EAnomalyHubTerminalKind::Shop) Shop=*It;
                PC->GetPawn()->SetActorLocation(Shop->GetActorLocation()+FVector(180,0,20)); PC->SetControlRotation(FRotator(0,180,0));
                Stage=100; Next=Time+.3; return;
            }
            if(Stage==100) { Key(PC,EKeys::E); Stage=101; Next=Time+.3; return; }
            if(Stage==101)
            {
                if(!Check(TEXT("Shop input opens usable terminal"),Hub->CanPurchase())) return;
                FString Why; auto Request=FGuid::NewGuid(); const int32 Revision=P->GetProgress().Revision;
                FAnomalyV05Probe::Currency(P,0);
                if(!Check(TEXT("Insufficient balance cannot buy"),!P->PurchaseHub(Hub,0,Revision,Request,Why))) return;
                FAnomalyV05Probe::Currency(P,10000);
                if(!Check(TEXT("Existing battery price and durable Hub purchase"),P->PurchaseHub(Hub,0,Revision,Request,Why) && P->GetProgress().Currency==9000 && P->GetProgress().BatteryLevel==1)) return;
                if(!Check(TEXT("Duplicate GUID and stale revision cannot debit"),!P->PurchaseHub(Hub,0,Revision+1,Request,Why) && !P->PurchaseHub(Hub,1,Revision,FGuid::NewGuid(),Why) && P->GetProgress().Currency==9000)) return;
                FAnomalyV05Probe::Fault(P,1);
                if(!Check(TEXT("Purchase save fault changes neither money nor level"),!P->PurchaseHub(Hub,1,Revision+1,FGuid::NewGuid(),Why) && P->GetProgress().Currency==9000 && P->GetProgress().PrecisionLevel==0)) return;
                FAnomalyV05Probe::Fault(P,0); Key(PC,EKeys::Down); Stage=102; Next=Time+.3; return;
            }
            if(Stage==102 || Stage==104 || Stage==106)
            {
                const int32 Product=(Stage-102)/2+1;
                if(!Check(TEXT("Direction input selects intended product"),Hub->GetShopSelection()==Product)) return;
                Key(PC,EKeys::Enter); Stage++; Next=Time+.3; return;
            }
            if(Stage==103 || Stage==105)
            { Key(PC,EKeys::Down); Stage++; Next=Time+.3; return; }
            if(Stage==107)
            {
                const auto& M=P->GetProgress(); FString Why;
                if(!Check(TEXT("Actual ENTER buys all original equipment once at original prices"),M.Currency==4400 && M.BatteryLevel==1 && M.PrecisionLevel==1 && M.BackpackLevel==1 && M.StoredDecoys==1)) return;
                if(!Check(TEXT("Backpack and decoy cap cannot debit again"),!P->PurchaseHub(Hub,2,M.Revision,FGuid::NewGuid(),Why) && !P->PurchaseHub(Hub,3,M.Revision,FGuid::NewGuid(),Why) && P->GetProgress().Currency==4400)) return;
                if(!Check(TEXT("Hub remains safe with no scanner or health"),!PC->GetPawn()->FindComponentByClass<UAnomalyScannerComponent>() && !PC->GetPawn()->FindComponentByClass<UAnomalyHealthComponent>())) return;
                Shot(TEXT("shop_bought")); Stage=108; Next=Time+.5; return;
            }
            if(Stage==108)
            { Hub->ClosePanel(); if(!Check(TEXT("Closing shop restores game input without financial effect"),!Hub->IsMoveInputIgnored() && !Hub->IsLookInputIgnored() && P->GetProgress().Currency==4400)) return;
              Balance=4400; Mode=TEXT("ShopCarry"); Stage=0; Next=Time+.3; return; }
        }
        if(Stage==0 && Hub)
        {
            if(Run==0 && Mode!=TEXT("Corrupt") && Mode!=TEXT("ShopCarry")) { if(!Check(TEXT("Explicit fixture persists initial upgrades and decoy"),FAnomalyV05Probe::Seed(P))) return; Balance=P->GetProgress().Currency; }
            if(!Check(TEXT("Returned old coordinator destroyed"),!Departed.IsValid())) return;
            Hub->ClosePanel();
            AAnomalyHubTerminal* Gate=nullptr; for(TActorIterator<AAnomalyHubTerminal> It(W);It;++It) if(It->Kind==EAnomalyHubTerminalKind::Departure) Gate=*It;
            if(!Check(TEXT("Physical departure terminal exists"),Gate!=nullptr)) return;
            PC->GetPawn()->SetActorLocation(Gate->GetActorLocation()+FVector(0,180,20)); PC->SetControlRotation(FRotator(0,-90,0));
            Stage=1; Next=Time+.3; return;
        }
        if(Stage==1 && Hub) { Key(PC,EKeys::E); Stage=2; Next=Time+.3; return; }
        if(Stage==2 && Hub)
        {
            if(!Check(TEXT("E input opens physical departure panel"),Hub->CanConfirmDeparture())) return;
            StartRevision=P->GetProgress().Revision;
            if(Mode==TEXT("Corrupt"))
            {
                if(!Check(TEXT("Unreadable existing save visibly blocks launch without zero overwrite"),!Hub->ConfirmDeparture() && P->GetLoadMessage().Contains(TEXT("禁止")) && P->GetProgress().Revision==StartRevision && T->GetPhase()==EAnomalyTravelPhase::HubReady)) return;
                Finish(true); return;
            }
            if(Run==0)
            {
                FAnomalyV05Probe::Fault(P,1);
                if(!Check(TEXT("Failed launch persistence leaves account and phase unchanged"),!Hub->ConfirmDeparture() && P->GetProgress().Revision==StartRevision && T->GetPhase()==EAnomalyTravelPhase::HubReady)) return;
                FAnomalyV05Probe::Fault(P,0);
            }
            if(!Check(TEXT("Hub commits authorized departure"),Hub->ConfirmDeparture())) return;
            if(Mode==TEXT("Quiet")) FAnomalyV05Probe::QuietSeed(T,LoadObject<UAnomalyEnvironmentConfig>(nullptr,TEXT("/Game/Prototype/V05/Data/DA_Environment.DA_Environment")));
            RunID=T->GetLaunch().Run;
            if(!Check(TEXT("Repeated launch cannot consume again"),!Hub->ConfirmDeparture() && P->GetProgress().Revision==StartRevision+1)) return;
            Stage=3; Next=Time+1; return;
        }
        if(Stage==3 && C && C->IsV05Lab())
        {
            Departed=C;
            if(!Check(TEXT("Actual Lab receives same RunId and exactly three choices"),C->RunId==RunID && C->CandidateBoxes.Num()==3 && T->GetPhase()==EAnomalyTravelPhase::InRun)) return;
            FAnomalyLaunchContext Duplicate; FString Why;
            if(!Check(TEXT("Repeated Lab claim rejected"),!T->ClaimLab(C,Duplicate,Why))) return;
            auto S=PC->GetPawn()->FindComponentByClass<UAnomalyScannerComponent>();
            if(!Check(TEXT("Frozen upgrades apply after level load"),S && S->GetMaximum(EAnomalyEquipment::MetalDetector)==3 && S->GetRemaining(EAnomalyEquipment::MetalDetector)==4 && FMath::IsNearlyEqual(S->GetPrecisionReduction(),.25f) && C->Inventory->GetCapacity()==5)) return;
            if(!Check(TEXT("Decoy consumed only once before Lab"),P->GetProgress().StoredDecoys==0 && C->DecoysRemaining==(Run==0?1:0) && P->GetProgress().Revision==StartRevision+1)) return;
            if(!Check(TEXT("Lab purchase entry is denied"),!C->PurchaseProduct(0,P->GetProgress().Revision,FGuid::NewGuid()))) return;
            if(Mode==TEXT("Quiet")) { Stage=590; Next=Time+14; return; }
            if(Mode==TEXT("Events"))
            {
                auto Env=AAnomalyEnvironmentController::Find(W); if(!Check(TEXT("Event configuration enabled and bounded"),Env && Env->Config->bEnableEvents && Env->Config->Validate())) return;
                const int32 State=FAnomalyV05Probe::RegionState(C); int32 Quiet=0; TSet<int32> Types;
                if(Run==0) for(int32 Seed=0;Seed<100;++Seed)
                {
                    auto A=Env->Config->BuildEventPlan(Seed),B=Env->Config->BuildEventPlan(Seed);
                    bool Same=A.Num()==B.Num() && A.Num()<=2;
                    for(int32 I=0;I<A.Num();++I) { Same &= A[I].Type==B[I].Type && A[I].At==B[I].At && A[I].Duration==B[I].Duration; Types.Add(int32(A[I].Type)); }
                    if(A.IsEmpty()) ++Quiet;
                    if(A.Num()==2) Same &= A[1].At>=A[0].At+A[0].Duration+Env->Config->EventWarningSeconds+Env->Config->EventSpacing;
                    if(!Check(TEXT("Seeded event IDs/times reproducible, bounded and separated"),Same)) return;
                }
                if(Run==0 && !Check(TEXT("Seed corpus includes quiet runs and both real events without touching region RNG"),Quiet>0 && Quiet<100 && Types.Num()==2 && FAnomalyV05Probe::RegionState(C)==State)) return;
                FAnomalyV05Probe::EventSchedule(Env);
                auto Terminal=Power(W); PC->GetPawn()->SetActorLocation(Terminal->GetActorLocation()+FVector(180,0,20));
                auto Eye=PC->GetPawn()->FindComponentByClass<UCameraComponent>()->GetComponentLocation(); PC->SetControlRotation((Terminal->GetActorLocation()+FVector(0,0,35)-Eye).Rotation());
                Stage=600; Next=Time+.5; return;
            }
            if(Mode==TEXT("Chamber"))
            {
                auto Env=AAnomalyEnvironmentController::Find(W); AAnomalyEnvironmentTerminal* Terminal=nullptr;
                for(TActorIterator<AAnomalyEnvironmentTerminal> It(W);It;++It) if(It->Kind==EAnomalyEnvironmentKind::Chamber) Terminal=*It;
                if(!Check(TEXT("Chamber starts unused each new Lab"),Env && Env->Config->bEnableChamber && Env->GetChamberPhase()==EAnomalyChamberPhase::Idle && Terminal)) return;
                if(!Check(TEXT("Remote chamber request rejected"),!Terminal->Interact(PC->GetPawn()))) return;
                PC->GetPawn()->SetActorLocation(Terminal->GetActorLocation()+FVector(-180,0,20));
                auto Eye=PC->GetPawn()->FindComponentByClass<UCameraComponent>()->GetComponentLocation(); PC->SetControlRotation((Terminal->GetActorLocation()+FVector(0,0,35)-Eye).Rotation());
                Stage=399; Next=Time+.3; return;
            }
            if(Mode==TEXT("Power"))
            {
                auto Env=AAnomalyEnvironmentController::Find(W); auto Terminal=Power(W);
                if(!Check(TEXT("New run has validated power service in ON state"),Env && Env->Config && Env->Config->Validate() && Env->IsPowerOn() && Terminal)) return;
                if(!Check(TEXT("Power terminal rejects remote player"),!Terminal->Interact(PC->GetPawn()) && Env->IsPowerOn())) return;
                PC->GetPawn()->SetActorLocation(Terminal->GetActorLocation()+FVector(180,0,20));
                auto Eye=PC->GetPawn()->FindComponentByClass<UCameraComponent>()->GetComponentLocation();
                PC->SetControlRotation((Terminal->GetActorLocation()+FVector(0,0,35)-Eye).Rotation());
                Stage=300; Next=Time+.3; return;
            }
            if(Mode==TEXT("Placement"))
            {
                auto Config=C->PlacementConfig; if(!Check(TEXT("Lab has placement data"),Config!=nullptr)) return;
                if(Run==0 && !Check(TEXT("Former A6 rack-occluded drop now has legal visible pickup space"),Config->APoints.IsValidIndex(6) && Config->Legal(C,Config->APoints[6]) && Config->PickupSpace(C,Config->APoints[6]))) return;
                for(int32 Region=0;Region<3;++Region)
                {
                    auto Legal=Config->LegalPoints(C,Region);
                    if(!Check(FString::Printf(TEXT("Region %d has at least three legal authored points (found %d)"),Region,Legal.Num()),Legal.Num()>=3)) return;
                    if(Run==0)
                    {
                        TSet<int32> Seen; const int32 State=FAnomalyV05Probe::RegionState(C);
                        for(int32 Seed=1;Seed<=40;++Seed)
                        {
                            FTransform A,B; int32 AId,BId;
                            if(!Check(TEXT("Fixed seed produces same legal placement"),Config->Choose(C,Region,Seed,1,A,AId) && Config->Choose(C,Region,Seed,1,B,BId) && AId==BId && A.Equals(B))) return;
                            Seen.Add(AId);
                        }
                        if(!Check(TEXT("Multiple seeds distribute across at least three points without consuming region RNG"),Seen.Num()>=3 && State==FAnomalyV05Probe::RegionState(C))) return;
                        auto Fallback=DuplicateObject<UAnomalyPlacementConfig>(Config,C);
                        auto& Candidate=Region==0?Fallback->APoints:Region==1?Fallback->BPoints:Fallback->CPoints;
                        Candidate={FVector(90000,90000,48),FVector(91000,90000,48),Config->Points(Region)[Legal[0]]};
                        FTransform V; int32 Id;
                        if(!Check(TEXT("Bounded invalid candidates fall back to valid point"),Fallback->Choose(C,Region,1,1,V,Id) && Id==2)) return;
                        Candidate[2]=FVector(92000,90000,48);
                        if(!Check(TEXT("All invalid points fail finitely"),!Fallback->Choose(C,Region,1,1,V,Id))) return;
                    }
                    const FVector Point=C->CandidateBoxes[Region]->GetActorLocation();
                    auto Route=UNavigationSystemV1::FindPathToLocationSynchronously(W,C->EntranceLocation+FVector(0,0,96),Point+FVector(165,0,96-Point.Z));
                    if(!Check(TEXT("Actual spawned candidate has complete approach route"),Route && Route->IsValid() && !Route->IsPartial())) return;
                }
                auto Box=C->CandidateBoxes[Run%3]; Box->bForceOutcome=true; Box->RevealDelay=.01; C->NextRoundDelay=.01;
                const FVector Point=Box->GetActorLocation(); PC->GetPawn()->SetActorLocation(Point+FVector(165,0,96-Point.Z));
                const FVector Eye=PC->GetPawn()->FindComponentByClass<UCameraComponent>()->GetComponentLocation();
                PC->SetControlRotation((Point+FVector(0,0,35)-Eye).Rotation());
                Stage=199; Next=Time+.3; return;
            }
            PC->GetPawn()->SetActorLocation(FVector(0,500,110));
            if(!Check(TEXT("Extraction outside physical entrance denied"),!C->ConfirmExtraction(PC->GetPawn()))) return;
            FAnomalyV05Probe::Carry(C,Run==0?123:456);
            if(Mode==TEXT("RestartWrite")) { Check(TEXT("Quit Lab leaves carry uncredited"),P->GetProgress().Currency==10000 && P->GetProgress().Extractions==0); Finish(!Finished); return; }
            PC->GetPawn()->SetActorLocation(FVector(0,1750,110));
            Stage=4; Next=Time+.3; return;
        }
        if(Stage==590 && C)
        {
            auto Env=AAnomalyEnvironmentController::Find(W);
            if(!Check(TEXT("Actual seeded quiet Lab remains event-free after first-event window"),Env->GetEventCount()==0 && Env->GetEventPhase()==EAnomalyEventPhase::Quiet && Env->IsPowerOn())) return;
            FAnomalyV05Probe::Carry(C,Run==0?123:456); PC->GetPawn()->SetActorLocation(FVector(0,1750,110)); Stage=4; Next=Time+.3; return;
        }
        if(Stage==600 && C)
        {
            auto Env=AAnomalyEnvironmentController::Find(W); FAnomalyEventSpec Duplicate; Duplicate.Type=EAnomalyDynamicEvent::PowerFluctuation;
            if(!Check(TEXT("Actual scheduled power event begins with warning before effects"),Env->GetEventPhase()==EAnomalyEventPhase::Warning && Env->GetEvent()==EAnomalyDynamicEvent::PowerFluctuation && Env->IsPowerOn())) return;
            if(!Check(TEXT("Repeated event callback rejected without stacking"),!Env->StartEvent(Duplicate) && Env->GetEventCount()==1)) return;
            Shot(TEXT("event_power_warning")); Stage=601; Next=Time+2.2; return;
        }
        if(Stage==601 && C)
        {
            auto Env=AAnomalyEnvironmentController::Find(W);
            if(!Check(TEXT("Power fluctuation actually dims supply and increases B scan cost"),Env->GetEventPhase()==EAnomalyEventPhase::Active && !Env->IsPowerOn() && FMath::IsNearlyEqual(Env->ScanMultiplier(C->CandidateBoxes[1]),1.75f))) return;
            Shot(TEXT("event_power_active")); Stage=6011; Next=Time+.3; return;
        }
        if(Stage==6011 && C) { Key(PC,EKeys::E); Stage=602; Next=Time+.3; return; }
        if(Stage==602 && C)
        {
            auto Env=AAnomalyEnvironmentController::Find(W);
            if(!Check(TEXT("Actual power terminal input counters event with no payout or reroll"),Env->GetEventPhase()==EAnomalyEventPhase::Quiet && Env->IsPowerOn() && P->GetProgress().Currency==Balance && C->CandidateBoxes.Num()==3)) return;
            Stage=603; Next=Time+.2; return;
        }
        if(Stage==603 && C)
        {
            auto Env=AAnomalyEnvironmentController::Find(W);
            if(Env->GetEventPhase()!=EAnomalyEventPhase::Warning || Env->GetEvent()!=EAnomalyDynamicEvent::ContainmentAlarm) { Next=Time+.1; return; }
            if(!Check(TEXT("Second scheduled event follows separated timeline"),Env->GetEventCount()==2)) return;
            AAnomalyEnvironmentTerminal* Terminal=nullptr; for(TActorIterator<AAnomalyEnvironmentTerminal> It(W);It;++It) if(It->Kind==EAnomalyEnvironmentKind::Chamber) Terminal=*It;
            PC->GetPawn()->SetActorLocation(Terminal->GetActorLocation()+FVector(-180,0,20));
            auto Eye=PC->GetPawn()->FindComponentByClass<UCameraComponent>()->GetComponentLocation(); PC->SetControlRotation((Terminal->GetActorLocation()+FVector(0,0,35)-Eye).Rotation());
            const FVector Position=Env->Config->ChamberCenter+FVector(0,0,48);
            auto Target=W->SpawnActorDeferred<AAnomalyThreatCharacter>(C->CandidateBoxes[0]->ThreatClass,FTransform(Position),C,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
            Target->bAutoResolveThreat=false; Target->FinishSpawning(FTransform(Position)); Target->ActivateThreat(); ChamberThreat=Target;
            Shot(TEXT("event_alarm_warning")); Stage=604; Next=Time+2.2; return;
        }
        if(Stage==604 && C)
        {
            auto Env=AAnomalyEnvironmentController::Find(W);
            if(!Check(TEXT("Alarm actually changes Chaser walking speed within bounded C scope"),Env->GetEventPhase()==EAnomalyEventPhase::Active && ChamberThreat.IsValid() && FMath::IsNearlyEqual(ChamberThreat->GetCharacterMovement()->MaxWalkSpeed,float(ChamberThreat->MoveSpeed)*1.08f,.1f))) return;
            Shot(TEXT("event_alarm_active")); Key(PC,EKeys::E); Stage=605; Next=Time+.3; return;
        }
        if(Stage==605 && C)
        {
            auto Env=AAnomalyEnvironmentController::Find(W);
            if(!Check(TEXT("Chamber remains a real counter during alarm, without extra containment reward"),ChamberThreat.IsValid() && ChamberThreat->IsEnvironmentStasis() && C->ThreatsResolved==0 && P->GetProgress().Currency==Balance)) return;
            Stage=606; Next=Time+4.1; return;
        }
        if(Stage==606 && C)
        {
            auto Env=AAnomalyEnvironmentController::Find(W); FAnomalyEventSpec Extra; Extra.Type=EAnomalyDynamicEvent::ContainmentAlarm;
            if(!Check(TEXT("Alarm expires, speed restored and event cap prevents third"),Env->GetEventPhase()==EAnomalyEventPhase::Quiet && ChamberThreat.IsValid() && FMath::IsNearlyEqual(ChamberThreat->GetCharacterMovement()->MaxWalkSpeed,float(ChamberThreat->MoveSpeed),.1f) && !Env->StartEvent(Extra) && Env->GetEventCount()==2)) return;
            Env->CancelEvents(TEXT("explicit cancellation fixture"));
            if(!Check(TEXT("Cancelled callback cannot restart environmental effects"),!Env->StartEvent(Extra) && Env->IsPowerOn())) return;
            ChamberThreat->Destroy(); ChamberThreat.Reset(); FAnomalyV05Probe::Carry(C,Run==0?123:456);
            PC->GetPawn()->SetActorLocation(FVector(0,1750,110)); Stage=4; Next=Time+.3; return;
        }
        if(Stage==399 && C)
        {
            auto Camera=PC->GetPawn()->FindComponentByClass<UCameraComponent>();
            UE_LOG(LogTemp,Display,TEXT("[V05] ChamberFixture Player=%s Eye=%s Direction=%s Hit=%s"),*PC->GetPawn()->GetActorLocation().ToString(),*Camera->GetComponentLocation().ToString(),*Camera->GetForwardVector().ToString(),*GetNameSafe(C->TraceExplorationTarget(PC->GetPawn())));
            Shot(TEXT("chamber_fixture")); Stage=400; Next=Time+.3; return;
        }
        if(Stage==400 && C)
        {
            auto Env=AAnomalyEnvironmentController::Find(W); AAnomalyEnvironmentTerminal* Terminal=nullptr;
            for(TActorIterator<AAnomalyEnvironmentTerminal> It(W);It;++It) if(It->Kind==EAnomalyEnvironmentKind::Chamber) Terminal=*It;
            if(!Check(TEXT("Actual chamber station is unobstructed and within range"),Terminal->ValidatePlayer(PC->GetPawn()))) return;
            if(!Check(TEXT("Empty chamber rejects without spending use"),!Terminal->Interact(PC->GetPawn()) && Env->GetChamberPhase()==EAnomalyChamberPhase::Idle)) return;
            auto Position=Env->Config->ChamberCenter+FVector(0,0,48);
            auto Observer=W->SpawnActorDeferred<AAnomalyObserverCharacter>(C->ObserverClass,FTransform(Position),C,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
            Observer->Config=C->ObserverConfig; Observer->bAutoResolveThreat=false; Observer->FinishSpawning(FTransform(Position)); Observer->ActivateThreat();
            if(!Check(TEXT("Observer subtype explicitly immune and use remains unspent"),!Terminal->Interact(PC->GetPawn()) && !Observer->IsEnvironmentStasis() && Env->GetChamberPhase()!=EAnomalyChamberPhase::Triggered && Terminal->Describe().Contains(TEXT("观察者免疫")))) return;
            Observer->Destroy();
            Position=PC->GetPawn()->GetActorLocation()+FVector(0,70,48-PC->GetPawn()->GetActorLocation().Z);
            auto Target=W->SpawnActorDeferred<AAnomalyThreatCharacter>(C->CandidateBoxes[0]->ThreatClass,FTransform(Position),C,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
            if(!Check(TEXT("Actual Chaser class spawns inside marked zone"),Target && !Cast<AAnomalyObserverCharacter>(Target))) return;
            Target->bAutoResolveThreat=false; Target->FinishSpawning(FTransform(Position)); Target->ActivateThreat(); ChamberThreat=Target;
            Key(PC,EKeys::E); Stage=401; Next=Time+.3; return;
        }
        if(Stage==401 && C)
        {
            auto Env=AAnomalyEnvironmentController::Find(W);
            if(!Check(TEXT("Actual E triggers one-use stasis on real Chaser"),ChamberThreat.IsValid() && ChamberThreat->IsEnvironmentStasis() && Env->GetChamberPhase()==EAnomalyChamberPhase::Triggered)) return;
            auto H=PC->GetPawn()->FindComponentByClass<UAnomalyHealthComponent>(); H->SetDamageEnabled(true);
            Key(PC,EKeys::E); Stage=402; Next=Time+.7; return;
        }
        if(Stage==402 && C)
        {
            auto H=PC->GetPawn()->FindComponentByClass<UAnomalyHealthComponent>(); auto Env=AAnomalyEnvironmentController::Find(W);
            if(!Check(TEXT("Captured Chaser cannot move/contact-damage; no direct kill, money or count"),ChamberThreat.IsValid() && ChamberThreat->IsEnvironmentStasis() && !ChamberThreat->bResolved && ChamberThreat->GetCharacterMovement()->MovementMode==MOVE_None && H->CurrentHealth==100 && C->ThreatsResolved==0 && P->GetProgress().Currency==Balance)) return;
            if(!Check(TEXT("Repeated E neither extends nor duplicates use"),Env->GetChamberPhase()==EAnomalyChamberPhase::Triggered)) return;
            Shot(TEXT("chamber_stasis")); Stage=403; Next=Time+2.4; return;
        }
        if(Stage==403 && C)
        {
            auto H=PC->GetPawn()->FindComponentByClass<UAnomalyHealthComponent>(); auto Env=AAnomalyEnvironmentController::Find(W);
            if(!Check(TEXT("Stasis expires, chase/contact resumes and chamber is spent"),ChamberThreat.IsValid() && !ChamberThreat->IsEnvironmentStasis() && !ChamberThreat->bResolved && H->CurrentHealth<100 && !H->bDead && Env->GetChamberPhase()==EAnomalyChamberPhase::Spent)) return;
            AAnomalyEnvironmentTerminal* Terminal=nullptr; for(TActorIterator<AAnomalyEnvironmentTerminal> It(W);It;++It) if(It->Kind==EAnomalyEnvironmentKind::Chamber) Terminal=*It;
            if(!Check(TEXT("Spent chamber cannot trigger again"),!Terminal->Interact(PC->GetPawn()) && C->ThreatsResolved==0)) return;
            H->SetDamageEnabled(false); H->CurrentHealth=100; ChamberThreat->Destroy(); ChamberThreat.Reset();
            FAnomalyV05Probe::Carry(C,Run==0?123:456); PC->GetPawn()->SetActorLocation(FVector(0,1750,110)); Stage=4; Next=Time+.3; return;
        }
        if(Stage==300 && C) { Key(PC,EKeys::E); Stage=301; Next=Time+.4; return; }
        if(Stage==301 && C)
        {
            auto Env=AAnomalyEnvironmentController::Find(W); auto Terminal=Power(W);
            if(!Check(TEXT("Actual E input switches B lights and power OFF"),!Env->IsPowerOn())) return;
            if(!Check(TEXT("B scan cost rises while A is unchanged"),FMath::IsNearlyEqual(Env->ScanMultiplier(C->CandidateBoxes[1]),1.75f) && Env->ScanMultiplier(C->CandidateBoxes[0])==1.f)) return;
            if(!Check(TEXT("Rapid repeated physical toggle cannot apply twice"),Terminal->Interact(PC->GetPawn()) && Env->IsPowerOn() && !Terminal->Interact(PC->GetPawn()) && Env->IsPowerOn())) return;
            Stage=302; Next=Time+.4; return;
        }
        if(Stage==302 && C) { Key(PC,EKeys::E); Stage=303; Next=Time+.4; return; }
        if(Stage==303 && C)
        {
            auto Env=AAnomalyEnvironmentController::Find(W); auto Terminal=Power(W);
            if(!Check(TEXT("Second real E restores OFF state after cooldown"),!Env->IsPowerOn())) return;
            auto Player=PC->GetPawn(); auto Camera=Player->FindComponentByClass<UCameraComponent>();
            auto Block=W->SpawnActor<AActor>(); auto Collision=NewObject<UBoxComponent>(Block); Block->SetRootComponent(Collision);
            Collision->SetBoxExtent(FVector(25,25,90)); Collision->SetCollisionProfileName(TEXT("BlockAll")); Collision->RegisterComponent();
            Block->SetActorLocation(Camera->GetComponentLocation()+Camera->GetForwardVector()*70);
            if(!Check(TEXT("Real occluder prevents power interaction"),!Terminal->Interact(Player) && !Env->IsPowerOn())) return; Block->Destroy();
            auto Observer=W->SpawnActorDeferred<AAnomalyObserverCharacter>(C->ObserverClass,FTransform(FVector(1000,780,48)),C,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
            if(!Check(TEXT("Actual observer class is available"),Observer!=nullptr)) return;
            Observer->Config=C->ObserverConfig; Observer->bAutoResolveThreat=false; Observer->FinishSpawning(FTransform(FVector(1000,780,48))); Observer->ActivateThreat();
            FAnomalyV05Probe::Budget(Observer,4.2f); Observer->Tick(.01f);
            if(!Check(TEXT("Power OFF keeps actual observer suppression beyond old four-second limit"),FMath::IsNearlyEqual(Observer->GetEffectiveObservationTolerance(),6.f) && Observer->ObserverState!=EAnomalyObserverState::Unobservable)) return;
            Player->SetActorLocation(FVector(0,1750,110)); Observer->Tick(.01f);
            if(!Check(TEXT("Leaving B removes benefit and actual red-eye threshold remains active"),FMath::IsNearlyEqual(Observer->GetEffectiveObservationTolerance(),4.f) && Observer->ObserverState==EAnomalyObserverState::Unobservable)) return;
            Observer->Destroy();
            auto Box=C->CandidateBoxes[1]; auto Point=Box->GetActorLocation(); Player->SetActorLocation(Point+FVector(165,0,96-Point.Z));
            auto Eye=Camera->GetComponentLocation(); PC->SetControlRotation((Point+FVector(0,0,35)-Eye).Rotation());
            Stage=304; Next=Time+.3; return;
        }
        if(Stage==304 && C) { Shot(TEXT("power_off_B")); Hold(PC,EKeys::Q,true); Stage=305; Next=Time+1.1; return; }
        if(Stage==305 && C)
        {
            auto Scanner=PC->GetPawn()->FindComponentByClass<UAnomalyScannerComponent>();
            if(!Check(TEXT("Real Q scan not complete at normal one second under power cost"),!C->CandidateBoxes[1]->GetCachedReading(EAnomalyEquipment::MetalDetector).bScanned && Scanner->GetRemaining(EAnomalyEquipment::MetalDetector)==4 && Scanner->Progress>0)) return;
            Stage=306; Next=Time+.9; return;
        }
        if(Stage==306 && C)
        {
            auto Scanner=PC->GetPawn()->FindComponentByClass<UAnomalyScannerComponent>(); Hold(PC,EKeys::Q,false);
            if(!Check(TEXT("Extended real Q scan completes and charges exactly once"),C->CandidateBoxes[1]->GetCachedReading(EAnomalyEquipment::MetalDetector).bScanned && Scanner->GetRemaining(EAnomalyEquipment::MetalDetector)==3)) return;
            Shot(TEXT("power_B_scan_complete")); FAnomalyV05Probe::Carry(C,Run==0?123:456);
            PC->GetPawn()->SetActorLocation(FVector(0,1750,110)); Stage=4; Next=Time+.3; return;
        }
        if(Stage==199 && C)
        {
            auto Box=C->CandidateBoxes[Run%3]; auto Camera=PC->GetPawn()->FindComponentByClass<UCameraComponent>();
            UE_LOG(LogTemp,Display,TEXT("[V05] OpenFixture Player=%s Box=%s Camera=%s Direction=%s Hit=%s Selectable=%d"),
                *PC->GetPawn()->GetActorLocation().ToString(),*Box->GetActorLocation().ToString(),*Camera->GetComponentLocation().ToString(),*Camera->GetForwardVector().ToString(),*GetNameSafe(C->TraceExplorationTarget(PC->GetPawn())),C->IsSelectableBox(Box));
            Shot(FString::Printf(TEXT("placement_%d_candidate"),Run)); Stage=200; Next=Time+.3; return;
        }
        if(Stage==200 && C)
        {
            auto Box=C->CandidateBoxes[Run%3];
            if(!Check(TEXT("Actual camera-range interaction opens one generated box"),Box->NativeInteract(PC->GetPawn(),0))) return;
            for(auto Other:C->CandidateBoxes) if(Other!=Box && !Check(TEXT("Selecting one locks the other two"),Other->bSelectionLocked && !Other->NativeInteract(PC->GetPawn(),0))) return;
            Stage=201; Next=Time+.3; return;
        }
        if(Stage==201 && C)
        {
            if(!C->IsDecisionActive()) return;
            if(!Check(TEXT("Generated outcome completes and can request physical return"),C->CompletedRounds==1 && !C->WorldLoot.IsEmpty())) return;
            PickupValue=C->WorldLoot[0]->Item.Value;
            const auto Eye=PC->GetPawn()->FindComponentByClass<UCameraComponent>()->GetComponentLocation();
            PC->SetControlRotation((C->WorldLoot[0]->GetActorLocation()-Eye).Rotation());
            Stage=202; Next=Time+.3; return;
        }
        if(Stage==202 && C)
        {
            if(!Check(TEXT("Real pickup is visible from validated crate approach"),!C->WorldLoot.IsEmpty() && C->TraceExplorationTarget(PC->GetPawn())==C->WorldLoot[0].Get())) return;
            Key(PC,EKeys::E); Stage=203; Next=Time+.3; return;
        }
        if(Stage==203 && C)
        {
            if(!Check(TEXT("Actual E stores generated value without credit in each placement trip"),PickupValue>0 && C->Inventory->GetCarryValue()==PickupValue && C->WorldLoot.IsEmpty() && P->GetProgress().Currency==Balance)) return;
            C->CashOut();
            PC->GetPawn()->SetActorLocation(FVector(0,1750,110)); Stage=4; Next=Time+.3; return;
        }
        if(Stage==3 && Hub) { Check(TEXT("Lab failed to initialize: ")+T->GetMessage(),false); return; }
        if(Stage==4 && C)
        {
            if(Run==2 && Mode==TEXT("Error"))
            { C->FailWithError(); Stage=5; Next=Time+1; return; }
            if(Run==2) FAnomalyV05Probe::Fault(P,1);
            if(!Check(TEXT("Physical extraction request accepted"),C->ConfirmExtraction(PC->GetPawn()))) return;
            if(!Check(TEXT("Repeated E sealed pending extraction"),!C->ConfirmExtraction(PC->GetPawn()))) return;
            if(Run==1)
            { auto H=PC->GetPawn()->FindComponentByClass<UAnomalyHealthComponent>(); H->SetDamageEnabled(true); H->DamageCooldown=0.f; H->ApplyDamage(100); }
            Stage=5; Next=Time+1; return;
        }
        if(Stage==5 && Hub)
        {
            const auto& R=T->GetResult(); FAnomalyV05Probe::Fault(P,0);
            const int32 Expected=Mode==TEXT("Placement")?PickupValue:Run==0?123:456;
            if(Run==0 || Run>=3)
            { Balance+=Expected; if(!Check(TEXT("Success snapshot and permanent credit exactly once"),R.RunId==RunID && R.CashedOut==Expected && R.bDurableCredit && P->GetProgress().Extractions==(Run==0?1:Run-1) && P->GetProgress().Revision==StartRevision+2)) return; }
            if(Run==1 && !Check(TEXT("Same-frame death wins, zero payout, permanent upgrades preserved"),R.Reason==EAnomalyRunEndReason::Failed && R.CashedOut==0 && R.Lost==Expected && P->GetProgress().BatteryLevel==1 && P->GetProgress().Revision==StartRevision+1)) return;
            if(Run==2 && !Check(Mode==TEXT("Error")?TEXT("Technical run error reports actual lost carry without credit"):TEXT("Save fault returns Error with actual lost carry and no false durable credit"),R.Reason==EAnomalyRunEndReason::Error && !R.bDurableCredit && R.CashedOut==0 && R.Lost==Expected && P->GetProgress().Revision==StartRevision+1)) return;
            if(!Check(TEXT("Hub balance unchanged by report or repeat callback"),P->GetProgress().Currency==Balance && !T->CompleteRun(nullptr))) return;
            if(!Check(TEXT("Fresh safe Hub pawn after result"),Cast<AAnomalyHubCharacter>(PC->GetPawn()) && !PC->GetPawn()->FindComponentByClass<UAnomalyHealthComponent>() && !Departed.IsValid())) return;
            if(!Check(TEXT("Returning Hub auto-shows immutable actual result"),Hub->GetOpenPanel()==int32(EAnomalyHubTerminalKind::Report) && Hub->GetHubWidget()->HubPanel->GetText().ToString().Contains(TEXT("永久余额")))) return;
            Shot(FString::Printf(TEXT("trip_%d_hub"),Run)); ++Run;
            if(Run>=(Mode==TEXT("Placement")?20:3)) { Check(TEXT("All real roundtrips have unique results"),T->GetLaunchCount()==Run && T->GetResultCount()==Run); Stage=6; Next=Time+.5; }
            else { Stage=0; Next=Time+.5; } return;
        }
        if(Stage==6) Finish(true);
    }
}
void RegisterAnomalyV05Smoke()
{
    if(!FParse::Param(FCommandLine::Get(),TEXT("AnomalyV05Smoke"))) return;
    FParse::Value(FCommandLine::Get(),TEXT("V05Evidence="),V05Smoke::Output);
    FParse::Value(FCommandLine::Get(),TEXT("V05Mode="),V05Smoke::Mode);
    if(V05Smoke::Output.IsEmpty() || V05Smoke::Mode==TEXT("Journey")) return;
    V05Smoke::Started=FPlatformTime::Seconds();
    V05Smoke::Handle=FWorldDelegates::OnWorldTickStart.AddStatic(&V05Smoke::Tick);
}
void UnregisterAnomalyV05Smoke() { FWorldDelegates::OnWorldTickStart.Remove(V05Smoke::Handle); }
#endif

