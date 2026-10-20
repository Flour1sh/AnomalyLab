// Opt-in Development check of the real menu, Slate keyboard routing and map travel.
#include "CoreMinimal.h"
#if !UE_BUILD_SHIPPING
#include "AnomalyMenuGameMode.h"
#include "AnomalyMainMenuWidget.h"
#include "AnomalyRoundCoordinator.h"
#include "AnomalyHealthComponent.h"
#include "AnomalyEquipmentComponent.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Components/Button.h"
#include "Components/TextBlock.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"
#include "InputKeyEventArgs.h"

namespace MenuSmoke
{
    FDelegateHandle TickHandle;
    int32 Stage = 0;
    double Started = 0.;
    float NextTime = 0.f;
    bool bFinished = false;
    FString Output;
    TArray<TSharedPtr<FJsonValue>> Checks;

    void Finish(bool bPassed)
    {
        if (bFinished) return;
        bFinished = true;
        TSharedRef<FJsonObject> Report = MakeShared<FJsonObject>();
        Report->SetStringField(TEXT("status"), bPassed ? TEXT("PASS") : TEXT("FAIL"));
        Report->SetStringField(TEXT("scope"), TEXT("Real rendered menu, synthetic Slate keyboard and button events, menu/Level01/menu travel. Physical human input and audio listening remain PENDING_MANUAL."));
        Report->SetNumberField(TEXT("stage"), Stage);
        Report->SetArrayField(TEXT("checks"), Checks);
        FString Json;
        FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json));
        const bool bSaved = FFileHelper::SaveStringToFile(Json, *(Output / TEXT("runtime_report.json")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
        UE_LOG(LogTemp, Display, TEXT("[MenuSmoke] RESULT %s Saved=%d"), bPassed ? TEXT("PASS") : TEXT("FAIL"), bSaved);
        FPlatformMisc::RequestExitWithStatus(false, bPassed && bSaved ? 0 : 1);
    }

    bool Check(const FString& Name, bool bPassed)
    {
        TSharedRef<FJsonObject> Item = MakeShared<FJsonObject>();
        Item->SetStringField(TEXT("check"), Name);
        Item->SetBoolField(TEXT("passed"), bPassed);
        Checks.Add(MakeShared<FJsonValueObject>(Item));
        UE_LOG(LogTemp, Display, TEXT("[MenuSmoke] %s %s"), bPassed ? TEXT("PASS") : TEXT("FAIL"), *Name);
        if (!bPassed) Finish(false);
        return bPassed;
    }

    template<class T> T* Find(UAnomalyMainMenuWidget* Menu, const TCHAR* Name)
    { return Cast<T>(Menu->WidgetTree->FindWidget(FName(Name))); }

    void Click(UAnomalyMainMenuWidget* Menu, const TCHAR* Name)
    {
        if (UButton* Button = Find<UButton>(Menu, Name)) Button->OnClicked.Broadcast();
        else Check(FString(TEXT("Button exists: ")) + Name, false);
    }

    void Key(FKey Key)
    {
        FSlateApplication::Get().ProcessKeyDownEvent(FKeyEvent(Key, FModifierKeysState(), 0, false, 0, 0));
        FSlateApplication::Get().ProcessKeyUpEvent(FKeyEvent(Key, FModifierKeysState(), 0, false, 0, 0));
    }

    void Screenshot(const TCHAR* Name)
    {
        if (!FParse::Param(FCommandLine::Get(), TEXT("nullrhi")))
            FScreenshotRequest::RequestScreenshot(Output / (FString(Name) + TEXT(".png")), true, false, false, FIntRect(), true);
    }

    void Tick(UWorld* World, ELevelTick TickType, float Delta)
    {
        if (bFinished || !World || !World->IsGameWorld() || !World->HasBegunPlay()) return;
        if (FPlatformTime::Seconds() - Started > 150.) { Check(TEXT("Completes before timeout"), false); return; }
        const float Time = World->GetTimeSeconds();
        APlayerController* PC = World->GetFirstPlayerController();
        if (!IsValid(PC) || Time < NextTime) return;
        AAnomalyMenuPlayerController* Controller = Cast<AAnomalyMenuPlayerController>(PC);
        UAnomalyMainMenuWidget* Menu = Controller ? Controller->GetMenuWidget() : nullptr;
        if (FParse::Param(FCommandLine::Get(), TEXT("V03FromMenu")))
        {
            if (Stage==0 && Menu && Time>=2.f)
            {
                if (!Check(TEXT("Continuous flow boots default main menu without pawn"), !PC->GetPawn() && World->GetOutermost()->GetName().EndsWith(TEXT("L_MainMenu")))) return;
                Screenshot(TEXT("00_boot_menu")); Stage=49; NextTime=Time+1.f;
            }
            else if (Stage==49 && Menu)
            {
                Click(Menu,TEXT("StartButton")); Stage=50; NextTime=0.f;
            }
            else if (Stage==50 && !Controller && PC->GetPawn())
            {
                AAnomalyRoundCoordinator* Round=nullptr;
                for (TActorIterator<AAnomalyRoundCoordinator> It(World); It; ++It) { Round=*It; break; }
                if (!Round || Round->CandidateBoxes.Num()!=3) return;
                if (!Check(TEXT("Continuous Start button enters Level01 Exploration"), World->GetOutermost()->GetName().EndsWith(TEXT("L_Prototype")) && Round->PlayMode==EAnomalyPlayMode::Exploration)) return;
                if (!Check(TEXT("Continuous travel restores gameplay input and removes menu"), !PC->bShowMouseCursor && !PC->IsMoveInputIgnored())) return;
                TSharedRef<FJsonObject> Boot=MakeShared<FJsonObject>();
                Boot->SetStringField(TEXT("status"),TEXT("PASS")); Boot->SetArrayField(TEXT("checks"),Checks);
                FString Json; FJsonSerializer::Serialize(Boot,TJsonWriterFactory<>::Create(&Json));
                FFileHelper::SaveStringToFile(Json,*(Output/TEXT("menu_boot_report.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
                FWorldDelegates::OnWorldTickStart.Remove(TickHandle);
            }
            return; // The exploration driver owns the subsequent loot/threat/extraction/restart itinerary.
        }

        if (Stage < 8 && !IsValid(Menu)) return;
        switch (Stage)
        {
        case 0:
            if (Time < 4.f) return;
            if (!Check(TEXT("Default boot is L_MainMenu"), World->GetOutermost()->GetName().EndsWith(TEXT("L_MainMenu")))) return;
            if (!Check(TEXT("Menu GameMode and no gameplay pawn"), Cast<AAnomalyMenuGameMode>(World->GetAuthGameMode()) && !PC->GetPawn())) return;
            if (!Check(TEXT("Menu does not own a round coordinator"), !TActorIterator<AAnomalyRoundCoordinator>(World))) return;
            if (!Check(TEXT("Main widget visible; cursor shown"), Menu->IsInViewport() && Menu->GetActivePanel() == 0 && PC->bShowMouseCursor)) return;
            if (!Check(TEXT("Menu receives keyboard focus"), Menu->HasKeyboardFocus())) return;
            {
                const FGeometry& Frame = Find<UWidget>(Menu, TEXT("MenuDesign"))->GetCachedGeometry();
                const FGeometry& Root = Menu->GetCachedGeometry();
                const FVector2D FrameMin = Root.AbsoluteToLocal(Frame.LocalToAbsolute(FVector2D::ZeroVector));
                const FVector2D FrameMax = Root.AbsoluteToLocal(Frame.LocalToAbsolute(Frame.GetLocalSize()));
                if (!Check(TEXT("Responsive frame fits viewport"), FrameMin.X >= -.5 && FrameMin.Y >= -.5 &&
                    FrameMax.X <= Root.GetLocalSize().X + .5 && FrameMax.Y <= Root.GetLocalSize().Y + .5)) return;
            }
            Screenshot(TEXT("01_main_menu"));
            ++Stage; NextTime = Time + 1.f; break;
        case 1:
            Key(EKeys::Down); Key(EKeys::Enter);
            if (!Check(TEXT("Slate Down/Enter opens settings"), Menu->GetActivePanel() == 1)) return;
            {
                UTextBlock* Label = Find<UTextBlock>(Menu, TEXT("ResolutionButtonLabel"));
                const FText Before = Label->GetText();
                Click(Menu, TEXT("ResolutionButton"));
                if (!Check(TEXT("Resolution option changes draft"), !Before.EqualTo(Label->GetText()))) return;
                Click(Menu, TEXT("QualityButton"));
                Click(Menu, TEXT("WindowModeButton"));
            }
            ++Stage; NextTime = Time + .6f; break;
        case 2:
            Screenshot(TEXT("02_settings"));
            ++Stage; NextTime = Time + .6f; break;
        case 3:
            Key(EKeys::Escape);
            if (!Check(TEXT("Escape dismisses settings without starting"), Menu->GetActivePanel() == 0 && !Controller->IsStartingGame())) return;
            Click(Menu, TEXT("GuideButton"));
            if (!Check(TEXT("Guide opens with current interaction and finite scanner hints"), Menu->GetActivePanel() == 2 &&
                Find<UTextBlock>(Menu, TEXT("GuideAction2"))->GetText().ToString().Contains(TEXT("开箱")) &&
                Find<UTextBlock>(Menu, TEXT("GuideAction3"))->GetText().ToString().Contains(TEXT("默认3次/种")) &&
                Find<UTextBlock>(Menu, TEXT("Version"))->GetText().ToString().Contains(TEXT("v0.4 RC")))) return;
            ++Stage; NextTime = Time + .6f; break;
        case 4:
            Screenshot(TEXT("03_field_guide"));
            ++Stage; NextTime = Time + .6f; break;
        case 5:
            Key(EKeys::Escape); Key(EKeys::Escape);
            if (!Check(TEXT("Main Escape opens quit confirmation"), Menu->GetActivePanel() == 3)) return;
            Key(EKeys::Enter);
            if (!Check(TEXT("Quit confirmation defaults to cancel"), Menu->GetActivePanel() == 0)) return;
            Click(Menu, TEXT("QuitButton"));
            ++Stage; NextTime = Time + .6f; break;
        case 6:
            Screenshot(TEXT("04_quit_confirmation"));
            ++Stage; NextTime = Time + .6f; break;
        case 7:
            if (!Menu) return;
            Key(EKeys::Escape);
            Click(Menu, TEXT("StartButton"));
            Click(Menu, TEXT("StartButton"));
            if (!Check(TEXT("Repeated Start creates one loading/travel request"), Menu->GetActivePanel() == 4 && Controller->IsStartingGame())) return;
            Screenshot(TEXT("04b_loading"));
            ++Stage; NextTime = 4.f; break;
        case 8:
            // Waiting for the new gameplay controller; the menu pointer is no longer valid.
            break;
        case 9:
            if (!Check(TEXT("Returned menu is clean and ready"), Menu && Menu->GetActivePanel() == 0 && !Controller->IsStartingGame() && !PC->GetPawn())) return;
            Finish(true); break;
        }
        if (Stage == 8 && !Controller && Time >= 4.f)
        {
            if (!Check(TEXT("Start loads existing Level01 package"), World->GetOutermost()->GetName().EndsWith(TEXT("L_Prototype")))) return;
            if (!Check(TEXT("Level01 retains Blueprint GameMode"), World->GetAuthGameMode()->GetClass()->GetPathName().Contains(TEXT("BP_FirstPersonGameMode")))) return;
            ACharacter* Player = Cast<ACharacter>(PC->GetPawn());
            UE_LOG(LogTemp, Display, TEXT("[MenuSmoke] Level01 initial ControlRotation=%s ActorRotation=%s"), *PC->GetControlRotation().ToString(), Player ? *Player->GetActorRotation().ToString() : TEXT("NoPawn"));
            if (!Check(TEXT("Gameplay pawn restored without menu mouse cursor"), Player && !PC->bShowMouseCursor)) return;
            if (!Check(TEXT("Level01 begins with a horizontal view"), FMath::Abs(PC->GetControlRotation().Pitch) < .1f)) return;
            const UAnomalyHealthComponent* Health = Player->FindComponentByClass<UAnomalyHealthComponent>();
            if (!Check(TEXT("Gameplay Health and Equipment retained"), Health && !Health->bDead && Player->FindComponentByClass<UAnomalyEquipmentComponent>())) return;
            AAnomalyRoundCoordinator* Coordinator = nullptr;
            for (TActorIterator<AAnomalyRoundCoordinator> It(World); It; ++It) { Coordinator = *It; break; }
            if (!Check(TEXT("Level01 starts in safe preparation without candidates"), Coordinator && Coordinator->IsPreparing() && Coordinator->CandidateBoxes.IsEmpty()
                && Player->GetCharacterMovement()->MovementMode==MOVE_None)) return;
            TArray<UUserWidget*> MenuWidgets;
            UWidgetBlueprintLibrary::GetAllWidgetsOfClass(World, MenuWidgets, UAnomalyMainMenuWidget::StaticClass(), true);
            if (!Check(TEXT("Menu removed from gameplay viewport"), MenuWidgets.IsEmpty())) return;
            Screenshot(TEXT("05_preparation"));
            PC->InputKey(FInputKeyEventArgs(nullptr,INPUTDEVICEID_NONE,EKeys::E,IE_Pressed,1.f,false,FPlatformTime::Cycles64()));
            Stage = 80; NextTime = Time + .3f;
        }
        else if (Stage == 80 && Time >= NextTime)
        {
            PC->InputKey(FInputKeyEventArgs(nullptr,INPUTDEVICEID_NONE,EKeys::E,IE_Released,0.f,false,FPlatformTime::Cycles64()));
            AAnomalyRoundCoordinator* Coordinator=nullptr;
            for (TActorIterator<AAnomalyRoundCoordinator> It(World);It;++It) { Coordinator=*It;break; }
            auto Player=Cast<ACharacter>(PC->GetPawn());
            if (!Check(TEXT("Preparation E starts original three boxes and restores walking"),Coordinator && Coordinator->CandidateBoxes.Num()==3
                && Coordinator->GetRoundPhase()==EAnomalyRoundPhase::AwaitingSelection && Player
                && Player->GetCharacterMovement()->MovementMode==MOVE_Walking && !PC->IsMoveInputIgnored())) return;
            Screenshot(TEXT("05_level01"));Stage=10;NextTime=Time+1.f;
        }
        else if (Stage == 10 && Time >= NextTime)
        {
            Stage = 9; NextTime = 3.f;
            UGameplayStatics::OpenLevel(World, FName(TEXT("/Game/Prototype/Maps/L_MainMenu")));
        }
    }
}

void RegisterAnomalyMenuSmoke()
{
    if (!FParse::Param(FCommandLine::Get(), TEXT("AnomalyMenuSmoke")) && !FParse::Param(FCommandLine::Get(), TEXT("V03FromMenu"))) return;
    FParse::Value(FCommandLine::Get(), TEXT("MenuEvidence="), MenuSmoke::Output);
    if (MenuSmoke::Output.IsEmpty()) MenuSmoke::Output = FPaths::ProjectSavedDir() / TEXT("T19Menu/Rendered");
    IFileManager::Get().MakeDirectory(*MenuSmoke::Output, true);
    MenuSmoke::Started = FPlatformTime::Seconds();
    MenuSmoke::TickHandle = FWorldDelegates::OnWorldTickStart.AddStatic(&MenuSmoke::Tick);
}

void UnregisterAnomalyMenuSmoke()
{
    FWorldDelegates::OnWorldTickStart.Remove(MenuSmoke::TickHandle);
}
#endif
