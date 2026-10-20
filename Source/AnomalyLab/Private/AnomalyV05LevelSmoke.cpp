#if !UE_BUILD_SHIPPING
#include "AnomalyHub.h"
#include "AnomalyMenuGameMode.h"
#include "AnomalyMainMenuWidget.h"
#include "AnomalyRoundCoordinator.h"
#include "AnomalyProgressionSubsystem.h"
#include "AnomalyHealthComponent.h"
#include "AnomalyScannerComponent.h"
#include "AnomalyEquipmentComponent.h"
#include "AnomalyInventoryComponent.h"
#include "AnomalyThreatCharacter.h"
#include "AnomalyBoxActor.h"
#include "AnomalyWorldPickup.h"
#include "Camera/CameraComponent.h"
#include "Components/TextBlock.h"
#include "Components/Button.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CapsuleComponent.h"
#include "Components/BoxComponent.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "Engine/DamageEvents.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"
#include "InputKeyEventArgs.h"

namespace V05LevelSmoke
{
    FDelegateHandle Handle;
    FString Output,Mode;
    int32 Stage=0,Index=0;
    float Next=0;
    double Started=0;
    bool Finished=false;
    FVector Before;
    int32 InitialRevision=0;
    TArray<TSharedPtr<FJsonValue>> Checks;
    void Finish(bool Pass)
    {
        if(Finished) return; Finished=true;
        auto Report=MakeShared<FJsonObject>();
        Report->SetStringField(TEXT("status"),Pass?TEXT("PASS"):TEXT("FAIL"));
        Report->SetStringField(TEXT("mode"),Mode); Report->SetNumberField(TEXT("stage"),Stage);
        Report->SetStringField(TEXT("scope"),TEXT("T34 actual independent map worlds, native/synthetic input, collision/NavMesh, safe Hub and launch-gated Lab. Teleports set screenshot/interaction fixtures. No T35 economic travel, physical human input or packaged acceptance."));
        Report->SetArrayField(TEXT("checks"),Checks);
        FString Json; FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
        const bool Saved=FFileHelper::SaveStringToFile(Json,*(Output/TEXT("report.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
        FPlatformMisc::RequestExitWithStatus(false,Pass&&Saved?0:1);
    }
    bool Check(const FString& Name,bool Pass)
    {
        auto Item=MakeShared<FJsonObject>(); Item->SetStringField(TEXT("check"),Name); Item->SetBoolField(TEXT("passed"),Pass);
        Checks.Add(MakeShared<FJsonValueObject>(Item)); UE_LOG(LogTemp,Display,TEXT("[T34] %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),*Name);
        if(!Pass) Finish(false); return Pass;
    }
    void Key(APlayerController* PC,FKey Key,bool Press)
    { PC->InputKey(FInputKeyEventArgs(nullptr,INPUTDEVICEID_NONE,Key,Press?IE_Pressed:IE_Released,Press?1.f:0.f,false,FPlatformTime::Cycles64())); }
    void Shot(const FString& Name)
    { FScreenshotRequest::RequestScreenshot(Output/(Name+TEXT(".png")),true,false,false,FIntRect(),true); }
    bool Nav(UWorld* World,ACharacter* Player,const FVector& Target,const FString& Name)
    {
        auto Path=UNavigationSystemV1::FindPathToLocationSynchronously(World,Player->GetActorLocation(),Target);
        return Check(TEXT("Complete runtime NavMesh route: ")+Name,Path&&Path->IsValid()&&!Path->IsPartial());
    }
    bool SpawnSafe(UWorld* World,ACharacter* Player)
    {
        FCollisionQueryParams Params(SCENE_QUERY_STAT(T34Spawn),false,Player);
        auto Capsule=Player->GetCapsuleComponent();
        return Check(TEXT("Pawn spawn not inside blocking geometry"),!World->OverlapBlockingTestByChannel(Player->GetActorLocation(),FQuat::Identity,ECC_Pawn,
            FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius()-2,Capsule->GetScaledCapsuleHalfHeight()-2),Params));
    }
    bool Ground(UWorld* World,const FVector& Point,const FString& Name)
    {
        FHitResult Hit; FCollisionQueryParams Params;
        if(auto PC=World->GetFirstPlayerController()) Params.AddIgnoredActor(PC->GetPawn());
        return Check(TEXT("Walkable floor collision: ")+Name,World->LineTraceSingleByChannel(Hit,Point+FVector(0,0,200),Point-FVector(0,0,120),ECC_Visibility,Params)&&Hit.ImpactNormal.Z>.9f&&FMath::Abs(Hit.ImpactPoint.Z)<5.f);
    }
    AAnomalyHubTerminal* Terminal(UWorld* World,int32 Kind)
    { for(TActorIterator<AAnomalyHubTerminal> It(World);It;++It) if(int32(It->Kind)==Kind) return *It; return nullptr; }
    void Tick(UWorld* World,ELevelTick TickType,float DeltaSeconds)
    {
        if(Finished || !World || !World->IsGameWorld()) return;
        if(FPlatformTime::Seconds()-Started>150) { Check(TEXT("Runtime itinerary timeout"),false); return; }
        auto PC=World->GetFirstPlayerController(); if(!PC) return;
        const float Time=World->GetTimeSeconds();
        const FString Map=World->GetOutermost()->GetName();
        if(Mode==TEXT("Menu"))
        {
            if(Stage==0 && Time>4)
            {
                auto MenuPC=Cast<AAnomalyMenuPlayerController>(PC);
                if(!Check(TEXT("Normal default boot is menu with no pawn"),Map.EndsWith(TEXT("L_MainMenu"))&&MenuPC&&!PC->GetPawn())) return;
                if(!Check(TEXT("Production route has no legacy override"),!FParse::Param(FCommandLine::Get(),TEXT("AnomalyLegacyMenuRoute")))) return;
                Shot(TEXT("00_menu")); Stage=100; Next=Time+.4f; return;
            }
            if(Stage==100 && Time>Next)
            {
                auto MenuPC=Cast<AAnomalyMenuPlayerController>(PC);
                auto Button=Cast<UButton>(MenuPC->GetMenuWidget()->WidgetTree->FindWidget(TEXT("StartButton")));
                if(!Check(TEXT("Real menu Start button exists"),Button!=nullptr)) return;
                Button->OnClicked.Broadcast();
                MenuPC->StartLevel01();
                if(!Check(TEXT("Repeated menu start sealed while loading"),MenuPC->IsStartingGame())) return;
                Stage=1; return;
            }
            if(Stage==1 && Map.EndsWith(TEXT("L_Hub")) && Time>3)
            {
                auto Hub=Cast<AAnomalyHubPlayerController>(PC);
                if(!Check(TEXT("Normal menu route loads independent Hub package"),Hub&&Cast<AAnomalyHubGameMode>(World->GetAuthGameMode())&&Cast<AAnomalyHubCharacter>(PC->GetPawn()))) return;
                TArray<UUserWidget*> Menus; UWidgetBlueprintLibrary::GetAllWidgetsOfClass(World,Menus,UAnomalyMainMenuWidget::StaticClass(),true);
                if(!Check(TEXT("Travel removes menu widget and restores GameOnly input"),Menus.IsEmpty()&&!PC->bShowMouseCursor&&!PC->IsMoveInputIgnored()&&Hub->GetHubWidget()&&Hub->GetHubWidget()->IsInViewport())) return;
                Shot(TEXT("01_menu_to_hub")); Stage=2; Next=Time+1; return;
            }
            if(Stage==2 && Time>Next) Finish(true);
            return;
        }
        auto Player=Cast<ACharacter>(PC->GetPawn()); if(!Player) return;
        auto Meta=World->GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>();
        if(!Meta) { Check(TEXT("Existing meta authority exists"),false); return; }
        if(Stage==0 && Time>4)
        {
            if(!Check(TEXT("Separate requested map loaded"),Map==TEXT("/Game/Maps/L_")+Mode)) return;
            if(!SpawnSafe(World,Player)) return;
            if(!Check(TEXT("Player initially faces horizontally"),FMath::Abs(PC->GetControlRotation().Pitch)<.1f)) return;
            InitialRevision=Meta->GetProgress().Revision;
            if(Mode==TEXT("Hub"))
            {
                auto Hub=Cast<AAnomalyHubPlayerController>(PC);
                if(!Check(TEXT("Hub owns distinct safe Pawn/Controller/GameMode"),Hub&&Cast<AAnomalyHubCharacter>(Player)&&Cast<AAnomalyHubGameMode>(World->GetAuthGameMode()))) return;
                if(!Check(TEXT("Hub has no round, boxes, threats or loot"),!TActorIterator<AAnomalyRoundCoordinator>(World)&&!TActorIterator<AAnomalyBoxActor>(World)&&!TActorIterator<AAnomalyThreatCharacter>(World)&&!TActorIterator<AAnomalyWorldPickup>(World))) return;
                if(!Check(TEXT("Hub pawn has no scanner/equipment/health/inventory components"),!Player->FindComponentByClass<UAnomalyScannerComponent>()&&!Player->FindComponentByClass<UAnomalyEquipmentComponent>()&&!Player->FindComponentByClass<UAnomalyHealthComponent>()&&!Player->FindComponentByClass<UAnomalyInventoryComponent>())) return;
                FDamageEvent Event;
                if(!Check(TEXT("Hub rejects damage"),!Player->CanBeDamaged()&&Player->TakeDamage(1000,Event,nullptr,nullptr)==0)) return;
                if(!Check(TEXT("Hub passive UI present without threat HUD"),Hub->GetHubWidget()&&Hub->GetHubWidget()->IsInViewport())) return;
                for(FKey K:{EKeys::Q,EKeys::F,EKeys::One,EKeys::Two,EKeys::R,EKeys::Enter}) { Key(PC,K,true);Key(PC,K,false); }
                if(!Check(TEXT("Hub gameplay keys cannot start run or mutate permanent progress"),Meta->GetProgress().Revision==InitialRevision&&!TActorIterator<AAnomalyBoxActor>(World)&&Hub->GetOpenPanel()<0)) return;
                for(int32 I=0;I<4;++I) {
                    auto T=Terminal(World,I); if(!Check(TEXT("One terminal ID exists ")+FString::FromInt(I),T!=nullptr)) return;
                    FVector Approach=T->GetActorLocation(); Approach.X+=(Approach.X<0?200:Approach.X>0?-200:0); if(I==2) Approach.Y+=220; Approach.Z=96;
                    if(!Nav(World,Player,Approach,T->GetTitle())) return;
                }
                if(!Ground(World,FVector(0,500,0),TEXT("Hub start"))) return;
                Shot(TEXT("01_hub_panorama")); Before=Player->GetActorLocation();Key(PC,EKeys::W,true);Stage=1;Next=Time+.5f;
            }
            else
            {
                AAnomalyRoundCoordinator* C=nullptr; for(TActorIterator<AAnomalyRoundCoordinator> It(World);It;++It) { C=*It;break; }
                if(!Check(TEXT("Lab retains original gameplay Pawn/Controller and Coordinator"),C&&Player->GetClass()->GetPathName().Contains(TEXT("BP_FirstPersonCharacter"))&&PC->GetClass()->GetPathName().Contains(TEXT("BP_FirstPersonPlayerController")))) return;
                if(!Check(TEXT("Lab is launch-gated, not a second preparation shop"),C->bAwaitLevelLaunch&&!C->bUsePreparation&&!C->IsPreparing()&&!C->RunId.IsValid()&&C->CandidateBoxes.IsEmpty())) return;
                C->SpawnInitialBox(); C->EndRun();
                if(!Check(TEXT("Unauthorized Lab cannot launch, spawn, purchase or extract"),!C->StartPreparedRun()&&!C->PurchaseProduct(0,Meta->GetProgress().Revision,FGuid::NewGuid())&&!C->ConfirmExtraction(Player)&&C->CandidateBoxes.IsEmpty()&&!C->bSettlementDone&&Meta->GetProgress().Revision==InitialRevision)) return;
                if(!Check(TEXT("Lab retains scanner/equipment/healthy pawn"),Player->FindComponentByClass<UAnomalyScannerComponent>()&&Player->FindComponentByClass<UAnomalyEquipmentComponent>()&&Player->FindComponentByClass<UAnomalyHealthComponent>()->CurrentHealth==100)) return;
                for(const auto& P:TArray<FVector>{FVector(-500,200,96),FVector(500,200,96),FVector(0,-750,96),FVector(0,1600,96)}) if(!Nav(World,Player,P,P.ToString())) return;
                if(!Ground(World,FVector(0,1750,0),TEXT("Lab start"))) return;
                Shot(TEXT("01_lab_entry")); Stage=10;Index=0;Next=Time+1;
            }
            return;
        }
        if(Mode==TEXT("Hub"))
        {
            auto Hub=Cast<AAnomalyHubPlayerController>(PC);
            if(Stage==1 && Time>Next)
            {
                Key(PC,EKeys::W,false);
                if(!Check(TEXT("Real W key moves safe pawn at accepted speed"),FVector::Dist2D(Before,Player->GetActorLocation())>70.f&&FMath::IsNearlyEqual(Player->GetCharacterMovement()->MaxWalkSpeed,350.f))) return;
                Player->SetActorLocation(FVector(0,850,96)); Player->GetCharacterMovement()->StopMovementImmediately(); PC->SetControlRotation(FRotator(0,90,0)); Key(PC,EKeys::W,true);Stage=2;Next=Time+1;
            }
            else if(Stage==2 && Time>Next)
            {
                Key(PC,EKeys::W,false);
                FHitResult Wall; FCollisionQueryParams Params(SCENE_QUERY_STAT(T34Wall),false,Player);
                if(!Check(TEXT("Hub north wall trace at authored inner face"),World->LineTraceSingleByChannel(Wall,FVector(0,850,150),FVector(0,1200,150),ECC_Visibility,Params)&&FMath::IsNearlyEqual(Wall.ImpactPoint.Y,1000.f,.5f))) return;
                const float ExpectedY=Wall.ImpactPoint.Y-Player->GetCapsuleComponent()->GetScaledCapsuleRadius();
                if(!Check(FString::Printf(TEXT("Real movement stops at capsule/wall boundary actual=%.2f expected=%.2f"),Player->GetActorLocation().Y,ExpectedY),FMath::IsNearlyEqual(Player->GetActorLocation().Y,ExpectedY,2.f)&&FMath::Abs(Player->GetVelocity().Y)<1.f)) return;
                Player->GetCharacterMovement()->StopMovementImmediately();Stage=3;Next=Time+.3f;Index=0;
            }
            else if(Stage==3 && Time>Next)
            {
                auto T=Terminal(World,Index); FVector P=T->GetActorLocation(); P.X+=(P.X<0?200:P.X>0?-200:0); if(Index==2)P.Y+=220; P.Z=96;
                Player->SetActorLocation(P); Player->GetCharacterMovement()->StopMovementImmediately();
                auto Camera=Player->FindComponentByClass<UCameraComponent>(); PC->SetControlRotation((T->GetActorLocation()-Camera->GetComponentLocation()).Rotation());
                Stage=4;Next=Time+.4f;
            }
            else if(Stage==4 && Time>Next)
            {
                if(!Check(TEXT("Range/LOS focus resolves terminal ")+FString::FromInt(Index),Hub->TraceTerminal()==Terminal(World,Index))) return;
                auto Occluder=World->SpawnActor<AActor>();
                auto Bounds=NewObject<UBoxComponent>(Occluder);Occluder->SetRootComponent(Bounds);
                Bounds->InitBoxExtent(FVector(25,25,80));Bounds->SetCollisionProfileName(TEXT("BlockAll"));Bounds->SetCanEverAffectNavigation(false);Bounds->RegisterComponent();
                FVector Eye;FRotator EyeRotation;PC->GetPlayerViewPoint(Eye,EyeRotation);
                Occluder->SetActorLocation((Eye+Terminal(World,Index)->GetActorLocation())*.5f);
                const bool Blocked=Hub->TraceTerminal()==nullptr;
                Bounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);Occluder->Destroy();
                if(!Check(TEXT("Intervening collision blocks terminal interaction ")+FString::FromInt(Index),Blocked)) return;
                Key(PC,EKeys::E,true);Key(PC,EKeys::E,false);Key(PC,EKeys::E,true);Key(PC,EKeys::E,false);
                Stage=41;Next=Time+.3f;
            }
            else if(Stage==41 && Time>Next)
            {
                if(!Check(TEXT("Real E opens terminal once ")+FString::FromInt(Index),Hub->GetOpenPanel()==Index&&PC->IsMoveInputIgnored())) return;
                Stage=5;Next=Time+.5f;
            }
            else if(Stage==5 && Time>Next)
            {
                if(!Check(TEXT("Terminal panel text displayed ")+FString::FromInt(Index),Hub->GetHubWidget()->HubPanel&&!Hub->GetHubWidget()->HubPanel->GetText().IsEmpty())) return;
                const TCHAR* Names[]={TEXT("02_hub_shop"),TEXT("03_hub_loadout"),TEXT("04_hub_departure"),TEXT("05_hub_report")}; Shot(Names[Index]);Stage=6;Next=Time+.5f;
            }
            else if(Stage==6 && Time>Next)
            {
                Key(PC,EKeys::Escape,true);Key(PC,EKeys::Escape,false);
                Stage=61;Next=Time+.2f;
            }
            else if(Stage==61 && Time>Next)
            {
                if(!Check(TEXT("ESC closes panel and restores movement ")+FString::FromInt(Index),Hub->GetOpenPanel()<0&&!PC->IsMoveInputIgnored())) return;
                ++Index;Stage=Index<4?3:7;Next=Time+.4f;
            }
            else if(Stage==7 && Time>Next)
            {
                Player->SetActorLocation(FVector(0,500,96)); PC->SetControlRotation(FRotator(0,-90,0));
                Stage=71;Next=Time+.3f;
            }
            else if(Stage==71 && Time>Next)
            {
                if(!Check(TEXT("Distant terminals fail 300cm camera trace"),Hub->TraceTerminal()==nullptr)) return;
                if(!Check(TEXT("All Hub viewing and keys leave save revision unchanged"),Meta->GetProgress().Revision==InitialRevision)) return;
                Finish(true);
            }
        }
        else if(Stage==10 && Time>Next)
        {
            const FVector Positions[]={FVector(-410,-240,96),FVector(410,-240,96),FVector(370,-610,96),FVector(300,1150,96)};
            const FVector Targets[]={FVector(-1100,420,140),FVector(1090,420,140),FVector(-60,-1310,140),FVector(-60,1840,145)};
            const TCHAR* Names[]={TEXT("02_lab_A"),TEXT("03_lab_B"),TEXT("04_lab_C"),TEXT("05_lab_exit")};
            if(!Nav(World,Player,Positions[Index],Names[Index])) return;
            Player->SetActorLocation(Positions[Index]); Player->GetCharacterMovement()->StopMovementImmediately();
            PC->SetControlRotation((Targets[Index]-Player->FindComponentByClass<UCameraComponent>()->GetComponentLocation()).Rotation()); Stage=11;Next=Time+.6f;
        }
        else if(Stage==11 && Time>Next)
        {
            const TCHAR* Names[]={TEXT("02_lab_A"),TEXT("03_lab_B"),TEXT("04_lab_C"),TEXT("05_lab_exit")};
            if(!SpawnSafe(World,Player)) return;
            Shot(Names[Index]); Stage=12;Next=Time+.5f;
        }
        else if(Stage==12 && Time>Next) { ++Index;if(Index>=4) Finish(true);else {Stage=10;Next=Time+.2f;} }
    }
}
void RegisterAnomalyV05LevelSmoke()
{
    if(!FParse::Param(FCommandLine::Get(),TEXT("AnomalyV05LevelSmoke"))) return;
    FParse::Value(FCommandLine::Get(),TEXT("T34Evidence="),V05LevelSmoke::Output);
    FParse::Value(FCommandLine::Get(),TEXT("T34Mode="),V05LevelSmoke::Mode);
    if(V05LevelSmoke::Output.IsEmpty()) return;
    IFileManager::Get().MakeDirectory(*V05LevelSmoke::Output,true); V05LevelSmoke::Started=FPlatformTime::Seconds();
    V05LevelSmoke::Handle=FWorldDelegates::OnWorldTickStart.AddStatic(&V05LevelSmoke::Tick);
}
void UnregisterAnomalyV05LevelSmoke() { FWorldDelegates::OnWorldTickStart.Remove(V05LevelSmoke::Handle); }
#endif
