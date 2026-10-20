#include "CoreMinimal.h"
#if !UE_BUILD_SHIPPING
#include "AnomalyHub.h"
#include "AnomalyMainMenuWidget.h"
#include "AnomalyMenuGameMode.h"
#include "AnomalyRoundCoordinator.h"
#include "AnomalyTransitionSubsystem.h"
#include "AnomalyBoxActor.h"
#include "AnomalyInventoryComponent.h"
#include "AnomalyWorldPickup.h"
#include "AnomalyScannerComponent.h"
#include "AnomalyHealthComponent.h"
#include "AnomalyTelemetry.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Button.h"
#include "Camera/CameraComponent.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"

struct FAnomalyJourneyProbe
{
    static bool InitialFunds(UAnomalyProgressionSubsystem* P)
    { auto M=P->Progress; M.Currency=10000; FString Why; return P->Commit(M,Why); }
};
namespace Journey
{
    FDelegateHandle Handle;
    FString Output;
    int32 Stage=0,Trip=0,Product=0,Point=0;
    double Started=0,Next=0,ProgressAt=0;
    float Best=MAX_flt;
    int64 ExpectedBalance=4400;
    int32 ExpectedCarry=0;
    FGuid RunId;
    bool Finished=false;
    TArray<FVector> Route;
    TArray<TSharedPtr<FJsonValue>> Checks;
    void End(bool Pass)
    {
        if(Finished) return; Finished=true;
        auto R=MakeShared<FJsonObject>(); R->SetStringField(TEXT("status"),Pass?TEXT("PASS"):TEXT("FAIL"));
        R->SetStringField(TEXT("mode"),TEXT("Journey")); R->SetNumberField(TEXT("stage"),Stage); R->SetNumberField(TEXT("completed_trips"),Trip);
        R->SetStringField(TEXT("scope"),TEXT("Default menu button, real synthetic W walking/collision along NavMesh, Q/E shop/scan/open/pickup/extraction; no teleports. Initial10000 currency and deterministic safe reward/lethal death are declared fixtures. Not human input."));
        R->SetArrayField(TEXT("checks"),Checks); FString Json; FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Json));
        const bool Saved=FFileHelper::SaveStringToFile(Json,*(Output/TEXT("report.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
        FPlatformMisc::RequestExitWithStatus(false,Pass&&Saved?0:1);
    }
    bool Check(const FString& Name,bool Pass)
    {
        auto R=MakeShared<FJsonObject>(); R->SetStringField(TEXT("check"),Name); R->SetBoolField(TEXT("passed"),Pass); Checks.Add(MakeShared<FJsonValueObject>(R));
        UE_LOG(LogTemp,Display,TEXT("[Journey] %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),*Name); if(!Pass) End(false); return Pass;
    }
    void Hold(APlayerController* P,FKey K,bool Down)
    { P->InputKey(FInputKeyEventArgs(nullptr,INPUTDEVICEID_NONE,K,Down?IE_Pressed:IE_Released,Down?1.f:0.f,false,FPlatformTime::Cycles64())); }
    void Key(APlayerController* P,FKey K) { Hold(P,K,true); Hold(P,K,false); }
    void Shot(const FString& Name)
    { if(!FParse::Param(FCommandLine::Get(),TEXT("nullrhi"))) FScreenshotRequest::RequestScreenshot(Output/(Name+TEXT(".png")),true,false,false,FIntRect(),true); }
    bool Walk(UWorld* W,APlayerController* P,const FVector& Target)
    {
        auto Path=UNavigationSystemV1::FindPathToLocationSynchronously(W,P->GetPawn()->GetActorLocation(),Target);
        if(!Check(TEXT("Real walking route has complete NavMesh path"),Path && Path->IsValid() && !Path->IsPartial())) return false;
        Route=Path->PathPoints; Point=0; Best=MAX_flt; ProgressAt=FPlatformTime::Seconds(); return true;
    }
    bool StepWalk(APlayerController* P)
    {
        while(Route.IsValidIndex(Point) && FVector::DistSquared2D(P->GetPawn()->GetActorLocation(),Route[Point])<FMath::Square(Point==Route.Num()-1?38.f:22.f))
        { ++Point; Best=MAX_flt; ProgressAt=FPlatformTime::Seconds(); }
        if(!Route.IsValidIndex(Point)) { Hold(P,EKeys::W,false); return true; }
        const auto Delta=Route[Point]-P->GetPawn()->GetActorLocation(); const float Distance=Delta.Size2D();
        if(Distance<Best-5) { Best=Distance; ProgressAt=FPlatformTime::Seconds(); }
        if(FPlatformTime::Seconds()-ProgressAt>6) { Hold(P,EKeys::W,false); Check(TEXT("Physical walking not stuck on blocking geometry"),false); return false; }
        P->SetControlRotation(FRotator(0,Delta.Rotation().Yaw,0)); Hold(P,EKeys::W,true); return false;
    }
    AAnomalyHubTerminal* Station(UWorld* W,EAnomalyHubTerminalKind Kind)
    { for(TActorIterator<AAnomalyHubTerminal> It(W);It;++It) if(It->Kind==Kind) return *It; return nullptr; }
    void Aim(APlayerController* P,const FVector& Target)
    { auto Camera=P->GetPawn()->FindComponentByClass<UCameraComponent>(); P->SetControlRotation((Target-Camera->GetComponentLocation()).Rotation()); }
    void Tick(UWorld* W,ELevelTick,float)
    {
        if(Finished || !W || !W->IsGameWorld()) return;
        const double Now=FPlatformTime::Seconds(); if(Now-Started>300) { Check(TEXT("Journey time bounded"),false); return; }
        if(Now<Next || W->GetTimeSeconds()<1) return;
        auto P=W->GetFirstPlayerController(); if(!P) return;
        if(Stage==0)
        {
            auto Menu=Cast<AAnomalyMenuPlayerController>(P); if(!Menu || !Menu->GetMenuWidget()) return;
            auto Button=Cast<UButton>(Menu->GetMenuWidget()->WidgetTree->FindWidget(TEXT("StartButton")));
            if(!Check(TEXT("Production default menu Start button exists"),Button && !P->GetPawn())) return;
            Shot(TEXT("00_default_menu")); Stage=1; Next=Now+.3; return;
        }
        if(Stage==1) { auto Menu=Cast<AAnomalyMenuPlayerController>(P); Cast<UButton>(Menu->GetMenuWidget()->WidgetTree->FindWidget(TEXT("StartButton")))->OnClicked.Broadcast(); Stage=2; return; }
        if(!P->GetPawn()) return;
        auto Hub=Cast<AAnomalyHubPlayerController>(P); auto Meta=W->GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>();
        auto T=W->GetGameInstance()->GetSubsystem<UAnomalyTransitionSubsystem>();
        AAnomalyRoundCoordinator* C=nullptr; for(TActorIterator<AAnomalyRoundCoordinator> It(W);It;++It) { C=*It; break; }
        if(Stage==2 && Hub)
        {
            if(!Check(TEXT("Menu reached independent safe Hub; explicit currency fixture"),FAnomalyJourneyProbe::InitialFunds(Meta))) return;
            if(!Walk(W,P,FVector(-370,100,96))) return; Stage=3; return;
        }
        if(Stage==3 && Hub) { if(!StepWalk(P)) return; Aim(P,Station(W,EAnomalyHubTerminalKind::Shop)->GetActorLocation()+FVector(0,0,35)); Stage=4; Next=Now+.3; return; }
        if(Stage==4 && Hub) { Key(P,EKeys::E); Stage=5; Next=Now+.3; return; }
        if(Stage==5 && Hub)
        { if(!Check(TEXT("Physical W walk reaches shop and E opens it"),Hub->CanPurchase())) return;
          Key(P,EKeys::Enter); Stage=6; Next=Now+.25; return; }
        if(Stage==6 && Hub)
        {
            if(++Product<4) { Key(P,EKeys::Down); Stage=7; Next=Now+.2; return; }
            if(!Check(TEXT("Actual shop keys buy original four products"),Meta->GetProgress().Currency==4400 && Meta->GetProgress().BackpackLevel==1)) return;
            Shot(TEXT("01_shop_purchased")); Stage=61; Next=Now+.3; return;
        }
        if(Stage==61 && Hub) { Key(P,EKeys::Escape); Stage=8; Next=Now+.3; return; }
        if(Stage==7 && Hub) { Key(P,EKeys::Enter); Stage=6; Next=Now+.25; return; }
        if(Stage==8 && Hub) { if(!Walk(W,P,FVector(0,-570,96))) return; Stage=9; return; }
        if(Stage==9 && Hub) { if(!StepWalk(P)) return; Aim(P,Station(W,EAnomalyHubTerminalKind::Departure)->GetActorLocation()+FVector(0,0,35)); Stage=10; Next=Now+.3; return; }
        if(Stage==10 && Hub) { Key(P,EKeys::E); Stage=11; Next=Now+.3; return; }
        if(Stage==11 && Hub) { if(!Check(TEXT("Physical departure terminal opens"),Hub->CanConfirmDeparture())) return; Key(P,EKeys::Enter); Stage=12; Next=Now+.08; return; }
        if(Stage==12 && Hub)
        { if(!Check(TEXT("Travel input freezes and opaque loading cover is present"),T->GetPhase()==EAnomalyTravelPhase::LoadingLab && Hub->IsLoadingVisible() && Hub->IsMoveInputIgnored())) return;
          RunId=T->GetLaunch().Run; Shot(TEXT("02_loading_lab")); Stage=13; Next=Now+.5; return; }
        if(Stage==13 && C && C->IsV05Lab())
        {
            if(!Check(TEXT("Walked into fresh Lab with frozen bought equipment"),C->RunId==RunId && C->CandidateBoxes.Num()==3 && C->Inventory->GetCapacity()==5 && P->GetPawn()->FindComponentByClass<UAnomalyScannerComponent>()->GetRemaining(EAnomalyEquipment::MetalDetector)==4)) return;
            auto Box=C->CandidateBoxes[Trip%3]; Box->bForceOutcome=true; Box->RevealDelay=.35; C->NextRoundDelay=.1;
            auto Target=Box->GetActorLocation()+FVector(165,0,96-Box->GetActorLocation().Z);
            if(!Walk(W,P,Target)) return; Stage=14; return;
        }
        if(Stage==14 && C) { if(!StepWalk(P)) return; Aim(P,C->CandidateBoxes[Trip%3]->GetActorLocation()+FVector(0,0,35)); Stage=15; Next=Now+.3; return; }
        if(Stage==15 && C) { Hold(P,EKeys::Q,true); Stage=16; Next=Now+2.1; return; }
        if(Stage==16 && C)
        {
            Hold(P,EKeys::Q,false); auto Box=C->CandidateBoxes[Trip%3];
            if(!Check(TEXT("Actual W route then held Q completes scan and consumes once"),Box->GetCachedReading(EAnomalyEquipment::MetalDetector).bScanned && P->GetPawn()->FindComponentByClass<UAnomalyScannerComponent>()->GetRemaining(EAnomalyEquipment::MetalDetector)==3)) return;
            Shot(FString::Printf(TEXT("trip_%d_scan"),Trip)); Hold(P,EKeys::E,true); Stage=17; Next=Now+.12; return;
        }
        if(Stage==17 && C)
        {
            Hold(P,EKeys::E,false);
            if(!Check(TEXT("Actual E opens the selected physical box before outcome"),C->SelectedBox && C->SelectedBox->bOpened)) return;
            Stage=171; Next=Now+.6; return;
        }
        if(Stage==171 && C)
        {
            if(!Check(TEXT("Opened box resolves into real world loot"),!C->WorldLoot.IsEmpty())) return;
            ExpectedCarry=C->WorldLoot[0]->Item.Value; Aim(P,C->WorldLoot[0]->GetActorLocation()); Stage=18; Next=Now+.25; return;
        }
        if(Stage==18 && C) { Key(P,EKeys::E); Stage=19; Next=Now+.3; return; }
        if(Stage==19 && C)
        {
            if(!Check(TEXT("Actual E pickup carries real generated value without credit"),C->Inventory->GetCarryValue()==ExpectedCarry && ExpectedCarry>0 && Meta->GetProgress().Currency==ExpectedBalance)) return;
            if(C->IsDecisionActive()) Key(P,EKeys::Two);
            if(!Walk(W,P,FVector(0,1700,96))) return; Stage=20; return;
        }
        if(Stage==20 && C) { if(!StepWalk(P)) return; Hold(P,EKeys::W,false); Stage=21; Next=Now+.2; return; }
        if(Stage==21 && C)
        {
            Key(P,EKeys::E);
            if(Trip==1) { auto H=P->GetPawn()->FindComponentByClass<UAnomalyHealthComponent>(); H->SetDamageEnabled(true); H->DamageCooldown=0; H->ApplyDamage(100); }
            Stage=22; Next=Now+.5; return;
        }
        if(Stage==22 && Hub)
        {
            const auto& R=T->GetResult(); if(Trip!=1) ExpectedBalance+=ExpectedCarry;
            if(!Check(TEXT("Real walked trip returns one matching result and exact permanent balance"),R.RunId==RunId && Meta->GetProgress().Currency==ExpectedBalance && R.CashedOut==(Trip==1?0:ExpectedCarry) && (Trip!=1 || R.Reason==EAnomalyRunEndReason::Failed))) return;
            if(!Check(TEXT("Telemetry contains actual engine frames and acknowledged Hub load"),T->GetHubLoadSeconds()>=.25f && T->GetLabLoadSeconds()>=.25f)) return;
            Shot(FString::Printf(TEXT("trip_%d_report"),Trip)); ++Trip;
            if(Trip==3) { Stage=23; Next=Now+.3; return; }
            Stage=24; Next=Now+.3; return;
        }
        if(Stage==24 && Hub) { Key(P,EKeys::Escape); Stage=8; Next=Now+.3; return; }
        if(Stage==23) End(true);
    }
}
void RegisterAnomalyJourneySmoke()
{
    FString Mode; FParse::Value(FCommandLine::Get(),TEXT("V05Mode="),Mode);
    if(!FParse::Param(FCommandLine::Get(),TEXT("AnomalyV05Smoke")) || Mode!=TEXT("Journey")) return;
    FParse::Value(FCommandLine::Get(),TEXT("V05Evidence="),Journey::Output); if(Journey::Output.IsEmpty()) return;
    Journey::Started=FPlatformTime::Seconds(); Journey::Handle=FWorldDelegates::OnWorldTickStart.AddStatic(&Journey::Tick);
}
void UnregisterAnomalyJourneySmoke() { FWorldDelegates::OnWorldTickStart.Remove(Journey::Handle); }
#endif
