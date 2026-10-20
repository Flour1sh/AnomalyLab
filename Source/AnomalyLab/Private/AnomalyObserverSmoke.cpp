#include "CoreMinimal.h"
#if !UE_BUILD_SHIPPING
#include "AnomalyObserverCharacter.h"
#include "AnomalyObserverConfig.h"
#include "AnomalyRoundCoordinator.h"
#include "AnomalyRegionDefinition.h"
#include "AnomalyBoxActor.h"
#include "AnomalyHealthComponent.h"
#include "AnomalyProgressionSubsystem.h"
#include "Engine/GameInstance.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "AIController.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"
#include "InputKeyEventArgs.h"
#include "HAL/PlatformTime.h"

struct FAnomalyObserverProbe
{
    static void Seed(AAnomalyRoundCoordinator* C,int32 N) { C->bUseFixedRegionSeed=true; C->RegionSeed=N; C->RegionStream.Initialize(N); }
};
namespace ObserverSmoke
{
    FDelegateHandle Handle;
    FString Output,SavePath;
    bool Finished=false;
    int32 Stage=0,Scenario=0,ChosenSeed=0,Slot=0,Rotations=0,Flips=0,ContactHealth=0;
    float Next=2,Activated=0,Deadline=0;
    FVector FrozenPosition;
    EAnomalyObserverState LastState=EAnomalyObserverState::Dormant;
    TWeakObjectPtr<AAnomalyBoxActor> Box;
    TWeakObjectPtr<AAnomalyObserverCharacter> Observer;
    TWeakObjectPtr<AActor> Wall;
    TArray<TSharedPtr<FJsonValue>> Checks;
    void Finish(bool Pass)
    {
        Finished=true;
        auto R=MakeShared<FJsonObject>(); R->SetStringField(TEXT("status"),Pass?TEXT("PASS"):TEXT("FAIL"));
        R->SetStringField(TEXT("scope"),TEXT("Fixed-seed natural outcome, synthetic E/R and camera/movement fixtures, real rendered frames. Not human play, audio or fairness acceptance."));
        R->SetNumberField(TEXT("seed"),ChosenSeed); R->SetNumberField(TEXT("human_samples"),0);
        R->SetStringField(TEXT("save_path"),SavePath); R->SetArrayField(TEXT("checks"),Checks);
        FString Json; FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Json)); IFileManager::Get().MakeDirectory(*Output,true);
        const bool Saved=FFileHelper::SaveStringToFile(Json,*(Output/TEXT("report.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
        FPlatformMisc::RequestExitWithStatus(false,Pass&&Saved?0:1);
    }
    bool Check(const TCHAR* Name,bool Pass)
    {
        auto R=MakeShared<FJsonObject>(); R->SetStringField(TEXT("check"),Name); R->SetBoolField(TEXT("passed"),Pass);
        Checks.Add(MakeShared<FJsonValueObject>(R)); UE_LOG(LogTemp,Display,TEXT("[ObserverSmoke] %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Name);
        if (!Pass) Finish(false); return Pass;
    }
    void Key(ACharacter* P,FKey K,bool Down)
    { P->GetController<APlayerController>()->InputKey(FInputKeyEventArgs(nullptr,INPUTDEVICEID_NONE,K,Down?IE_Pressed:IE_Released,Down?1.f:0.f,false,FPlatformTime::Cycles64())); }
    void Aim(ACharacter* P,const FVector& Point,float YawOffset=0)
    {
        auto Camera=P->FindComponentByClass<UCameraComponent>(); FRotator R=(Point-Camera->GetComponentLocation()).Rotation(); R.Yaw+=YawOffset;
        P->GetController()->SetControlRotation(R);
    }
    void Place(ACharacter* P,const FVector& Position)
    { P->SetActorLocation(Position,false); P->GetCharacterMovement()->StopMovementImmediately(); }
    void Shot(const TCHAR* Name)
    { if (!FParse::Param(FCommandLine::Get(),TEXT("nullrhi"))) FScreenshotRequest::RequestScreenshot(Output/(FString(Name)+TEXT(".png")),true,false,false,FIntRect(),true); }
    bool NoObservers(UWorld* W)
    { for (TActorIterator<AAnomalyObserverCharacter> It(W);It;++It) if (IsValid(*It) && !It->IsActorBeingDestroyed()) return false; return true; }
    bool Prepare(AAnomalyRoundCoordinator* C,ACharacter* P)
    {
        FString Why;
        if (!Check(TEXT("Production Observer references and thresholds valid"),C->bEnableObserverPool && C->ObserverClass && C->ObserverConfig && C->ObserverConfig->Validate(Why))) return false;
        auto Bad=DuplicateObject<UAnomalyObserverConfig>(C->ObserverConfig,C); Bad->EnterDot=Bad->ExitDot-.01f;
        if (!Check(TEXT("Invalid hysteresis configuration rejected"),!Bad->Validate(Why))) return false;
        const auto Defaults=C->BoxClass->GetDefaultObject<AAnomalyBoxActor>();
        bool Found=false;
        for (int32 Seed=30001;Seed<31001 && !Found;++Seed)
        {
            FRandomStream S(Seed); TArray<FName> Types;
            if (!UAnomalyRegionDefinition::DrawChoices(C->RegionRules,S,Types,Why)) return Check(TEXT("Region sample valid"),false);
            for (int32 I=0;I<3;++I)
            {
                FRandomStream Config(static_cast<int32>(S.GetUnsignedInt())); FRandomStream Outcome(static_cast<int32>(S.GetUnsignedInt()));
                const FName ID=Types[I]==TEXT("Unknown")?C->RegionRules[I]->DrawHiddenProfile(Config):Types[I];
                auto D=DuplicateObject<UAnomalyBoxDefinition>(Defaults->Definitions[ID],C);
                if (!C->RegionRules[I]->ApplyTo(*D,Why)) return Check(TEXT("Adjusted fixture data valid"),false);
                if (!Found && D->SelectOutcome(Outcome.FRand())==2) { ChosenSeed=Seed; Slot=I; Found=true; }
            }
        }
        if (!Check(TEXT("Fixed seed with natural threat found without forcing outcomes"),Found)) return false;
        for (auto R:C->RegionRules) R->AllowedAnomalies={FName(TEXT("Observer"))}; // Runtime fixture only; no saved data changes.
        FAnomalyObserverProbe::Seed(C,ChosenSeed);
        if (!Check(TEXT("Prepared run starts and still has exactly three candidates"),C->StartPreparedRun() && C->CandidateBoxes.Num()==3)) return false;
        Box=C->CandidateBoxes[Slot]; FRandomStream Outcome(Box->OutcomeSeed);
        if (!Check(TEXT("Chosen live box reproduces natural threat seed; no force flag"),!Box->bForceOutcome && Box->NativeSelectOutcome(Outcome.FRand())==2)) return false;
        Place(P,Box->GetActorLocation()+FVector(0,-180,48)); Aim(P,Box->GetActorLocation()+FVector(0,0,35));
        return true;
    }
    void Tick(UWorld* W,ELevelTick,float)
    {
        if (Finished || !W || !W->IsGameWorld() || !W->HasBegunPlay()) return;
        const float Time=W->GetTimeSeconds(); if (Time<Next) return;
        if (Time>90) { Check(TEXT("Observer fixture finishes within bounded time"),false); return; }
        AAnomalyRoundCoordinator* C=nullptr; for (TActorIterator<AAnomalyRoundCoordinator> It(W);It;++It) { C=*It; break; }
        auto P=UGameplayStatics::GetPlayerCharacter(W,0); if (!C || !P) return;
        auto H=P->FindComponentByClass<UAnomalyHealthComponent>();
        auto Meta=C->GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>(); SavePath=Meta->GetSavePath();
        if (Stage==100)
        { if (!C->IsPreparing() || Time<2) return; Stage=0; Next=2; }
        if (Stage==0)
        { if (!Prepare(C,P)) return; Stage=1; Next=Time+.3f; return; }
        if (Stage==1) { Key(P,EKeys::E,true); Stage=2; Next=Time+.25f; return; }
        if (Stage==2)
        {
            Key(P,EKeys::E,false);
            if (!Check(TEXT("Real E opens exactly the selected box and locks both others"),Box.IsValid() && Box->bOpened && C->SelectedBox==Box.Get()
                && C->CandidateBoxes.FilterByPredicate([](const auto B){return B->bSelectionLocked;}).Num()==2)) return;
            Stage=3; Next=Time+.8f; return;
        }
        if (Stage==3)
        {
            Observer=Cast<AAnomalyObserverCharacter>(C->CurrentSpider);
            if (!Check(TEXT("Natural threat spawns Observer in readable inactive Warning"),Observer.IsValid() && C->RoundPhase==EAnomalyRoundPhase::ThreatWarning
                && Observer->ObserverState==EAnomalyObserverState::Warning && !Observer->bThreatActive && !H->bDamageEnabled)) return;
            Aim(P,Observer->GetObservationPoint()); Stage=31; Next=Time+.2f; return;
        }
        if (Stage==31) { Shot(TEXT("01_warning")); Stage=32; Next=Time+.15f; return; }
        if (Stage==32)
        {
            Observer->SetActorLocation(FVector(0,0,47),false); Place(P,FVector(0,650,98)); Aim(P,Observer->GetObservationPoint());
            Stage=4; Next=Time+.8f; return;
        }
        if (Stage==4)
        {
            if (!Check(TEXT("Unobstructed front camera observes active threat with existing damage gate"),Observer.IsValid() && Observer->bThreatActive && H->bDamageEnabled
                && Observer->IsEffectivelyObserved() && Observer->ObserverState==EAnomalyObserverState::Observed)) return;
            if (Scenario==1)
            { H->ApplyDamage(H->MaxHealth); Stage=200; Next=Time+.5f; return; }
            Activated=Time-.3f; FrozenPosition=Observer->GetActorLocation(); Shot(TEXT("02_observed")); Stage=5; Next=Time+.6f; return;
        }
        if (Stage==5)
        {
            if (!Check(TEXT("Effective observation freezes actual position and rejects decoy"),FVector::DistSquared2D(FrozenPosition,Observer->GetActorLocation())<4
                && !Observer->CanBeLured() && !Observer->TryLure(C,5))) return;
            Aim(P,Observer->GetObservationPoint(),180); Stage=6; Next=Time+.5f; return;
        }
        if (Stage==6)
        {
            if (!Check(TEXT("Back camera ends observation after grace and actual AI moves"),Observer->ObserverState==EAnomalyObserverState::Unobserved
                && FVector::DistSquared2D(FrozenPosition,Observer->GetActorLocation())>400)) return;
            Observer->SetActorLocation(FVector(0,0,47),false); Place(P,FVector(0,650,98)); Aim(P,Observer->GetObservationPoint(),40.5f);
            Stage=7; Next=Time+.2f; return;
        }
        if (Stage==7)
        {
            if (!Check(TEXT("Angle boundary has separate enter and exit thresholds"),!Observer->IsEffectivelyObserved(false) && Observer->IsEffectivelyObserved(true))) return;
            Aim(P,Observer->GetObservationPoint()); Stage=8; Next=Time+.3f; return;
        }
        if (Stage==8)
        {
            auto Actor=W->SpawnActor<AActor>(); auto Block=NewObject<UBoxComponent>(Actor); Actor->SetRootComponent(Block);
            Block->SetBoxExtent(FVector(90,10,160)); Block->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
            Block->SetCollisionResponseToAllChannels(ECR_Ignore); Block->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block); Block->RegisterComponent();
            Actor->SetActorLocation((P->FindComponentByClass<UCameraComponent>()->GetComponentLocation()+Observer->GetObservationPoint())*.5);
            auto Visual=NewObject<UStaticMeshComponent>(Actor); Visual->SetupAttachment(Block);
            Visual->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"))); Visual->SetRelativeScale3D(FVector(1.8,.2,3.2));
            Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision); Visual->SetCanEverAffectNavigation(false); Visual->RegisterComponent();
            Wall=Actor; Stage=9; Next=Time+.3f; return;
        }
        if (Stage==9)
        {
            if (!Check(TEXT("Visibility wall prevents through-wall freeze"),!Observer->IsEffectivelyObserved(true) && Observer->ObserverState==EAnomalyObserverState::Unobserved)) return;
            Shot(TEXT("03_occluded")); Stage=91; Next=Time+.15f; return;
        }
        if (Stage==91)
        {
            Wall->Destroy(); Wall.Reset(); Observer->SetActorLocation(FVector(0,0,47),false); Place(P,FVector(0,2300,98)); Aim(P,Observer->GetObservationPoint());
            Stage=10; Next=Time+.25f; return;
        }
        if (Stage==10)
        {
            if (!Check(TEXT("Out-of-range camera cannot freeze"),!Observer->IsEffectivelyObserved(true))) return;
            Observer->SetActorLocation(FVector(0,0,47),false); Place(P,FVector(0,650,98)); Aim(P,Observer->GetObservationPoint());
            Stage=11; Next=Time+.35f; return;
        }
        if (Stage==11)
        {
            if (!Check(TEXT("Front view reacquires after obstruction/range loss"),Observer->ObserverState==EAnomalyObserverState::Observed)) return;
            LastState=Observer->ObserverState; Rotations=Flips=0; Stage=12; Next=Time+.03f; return;
        }
        if (Stage==12)
        {
            if (Observer->ObserverState!=LastState) { ++Flips; LastState=Observer->ObserverState; }
            Aim(P,Observer->GetObservationPoint(),(++Rotations%2)?180:0);
            if (Rotations<10) { Next=Time+.03f; return; }
            if (!Check(TEXT("Rapid camera rotations do not produce frame-by-frame state jitter"),Flips<=1)) return;
            Observer->SetActorLocation(FVector(0,-500,47),false); Aim(P,Observer->GetObservationPoint());
            Deadline=Time+Observer->Config->ObservationTolerance+.5f; Stage=13; Next=Time+.05f; return;
        }
        if (Stage==13)
        {
            if (Observer->ObserverState!=EAnomalyObserverState::Unobservable)
            { if (Time>Deadline) Check(TEXT("Tolerance enters red-eye within configured bound"),false); else Next=Time+.05f; return; }
            FrozenPosition=Observer->GetActorLocation(); Stage=131; Next=Time+.25f; return;
        }
        if (Stage==131)
        {
            if (!Check(TEXT("Predictable red-eye ignores gaze briefly and approaches"),Observer->ObserverState==EAnomalyObserverState::Unobservable
                && Observer->DescribeState().Contains(TEXT("红眼")) && FVector::DistSquared2D(FrozenPosition,Observer->GetActorLocation())>25)) return;
            Shot(TEXT("04_red_eye")); Stage=14; Next=Time+1.3f; return;
        }
        if (Stage==14)
        {
            if (!Check(TEXT("Red-eye ends and effective gaze suppresses again"),Observer->ObserverState==EAnomalyObserverState::Observed)) return;
            ContactHealth=H->CurrentHealth; Observer->SetActorLocation(P->GetActorLocation()+FVector(0,-50,-51),false); Aim(P,Observer->GetObservationPoint());
            Stage=15; Next=Time+.3f; return;
        }
        if (Stage==15)
        {
            if (!Check(TEXT("Overlap uses existing single contact damage"),H->CurrentHealth==ContactHealth-H->ThreatDamage && !H->bDead)) return;
            ContactHealth=H->CurrentHealth; Stage=16; Next=Time+.4f; return;
        }
        if (Stage==16)
        {
            if (!Check(TEXT("Existing 1.5-second damage cooldown prevents duplicate overlap hits"),H->CurrentHealth==ContactHealth)) return;
            Observer->SetActorLocation(FVector(0,-500,47),false); if (auto AI=Cast<AAIController>(Observer->GetController())) { AI->StopMovement(); AI->UnPossess(); }
            Observer->GetCharacterMovement()->StopMovementImmediately(); Aim(P,Observer->GetObservationPoint(),180);
            Stage=17; Next=Time+.3f; return;
        }
        if (Stage==17)
        {
            if (!Check(TEXT("Navigation/controller loss stays safe and independent expiry remains active"),Observer.IsValid() && !Observer->GetController()
                && Observer->bThreatActive && H->CurrentHealth==ContactHealth)) return;
            Stage=18; Next=Time+.1f; return;
        }
        if (Stage==18)
        {
            if (C->RoundPhase!=EAnomalyRoundPhase::PostRoundDecision) { Next=Time+.1f; return; }
            if (!Check(TEXT("Observer naturally contains once after 20 seconds; no remaining attack actor"),C->ThreatsResolved==1 && C->CompletedRounds==1
                && NoObservers(W) && !H->bDamageEnabled && Time-Activated>=19.5f)) return;
            Shot(TEXT("05_contained")); Place(P,C->EntranceLocation+FVector(0,0,98)); Stage=19; Next=Time+.25f; return;
        }
        if (Stage==19)
        {
            if (!Check(TEXT("Post-Observer physical extraction queues once"),C->ConfirmExtraction(P) && !C->ConfirmExtraction(P))) return;
            H->SetDamageEnabled(true); H->ApplyDamage(H->MaxHealth); Stage=20; Next=Time+.3f; return;
        }
        if (Stage==20)
        {
            if (!Check(TEXT("Death beats queued extraction, Meta unchanged, Observer/timers cleaned"),C->RunEndReason==EAnomalyRunEndReason::Failed
                && !C->bSettlementDone && Meta->GetProgress().Currency==0 && NoObservers(W))) return;
            Shot(TEXT("06_death_race")); Stage=21; Next=Time+.2f; return;
        }
        if (Stage==21) { Scenario=1; Key(P,EKeys::R,true); Stage=100; Next=2; return; }
        if (Stage==200)
        {
            Finish(Check(TEXT("Death during active Observer destroys actor and all damage work"),H->bDead && C->RunEndReason==EAnomalyRunEndReason::Failed
                && NoObservers(W) && C->CandidateBoxes.IsEmpty() && Meta->GetProgress().Currency==0)); return;
        }
    }
}
void RegisterAnomalyObserverSmoke()
{
    if (!FParse::Param(FCommandLine::Get(),TEXT("AnomalyObserverSmoke"))) return;
    FParse::Value(FCommandLine::Get(),TEXT("T30Evidence="),ObserverSmoke::Output);
    if (ObserverSmoke::Output.IsEmpty()) ObserverSmoke::Output=FPaths::ProjectSavedDir()/TEXT("V04/T30/Runtime");
    ObserverSmoke::Handle=FWorldDelegates::OnWorldTickStart.AddStatic(&ObserverSmoke::Tick);
}
void UnregisterAnomalyObserverSmoke() { FWorldDelegates::OnWorldTickStart.Remove(ObserverSmoke::Handle); }
#endif
