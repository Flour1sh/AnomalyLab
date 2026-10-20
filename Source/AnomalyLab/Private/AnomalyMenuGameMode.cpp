#include "AnomalyMenuGameMode.h"
#include "AnomalyMainMenuWidget.h"
#include "Camera/CameraActor.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/PackageName.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "TimerManager.h"

namespace
{
    FName GetStartPackage()
    {
#if !UE_BUILD_SHIPPING
        // Explicit compatibility fixture only; normal menu always uses the Hub.
        if (FParse::Param(FCommandLine::Get(),TEXT("AnomalyLegacyMenuRoute")))
            return FName(TEXT("/Game/Prototype/Maps/L_Prototype"));
#endif
        return FName(TEXT("/Game/Maps/L_Hub"));
    }
}

AAnomalyMenuGameMode::AAnomalyMenuGameMode()
{
    PlayerControllerClass = AAnomalyMenuPlayerController::StaticClass();
    DefaultPawnClass = nullptr;
    HUDClass = nullptr;
    bStartPlayersAsSpectators = true;
}

AAnomalyMenuPlayerController::AAnomalyMenuPlayerController()
{
    MenuWidgetClass = TSoftClassPtr<UAnomalyMainMenuWidget>(FSoftObjectPath(GetStartPackage().ToString().EndsWith(TEXT("L_Prototype"))
        ?TEXT("/Game/UI/Menu/WBP_MainMenu.WBP_MainMenu_C")
        :TEXT("/Game/Prototype/V05/UI/WBP_MainMenu_V05.WBP_MainMenu_V05_C")));
}

void AAnomalyMenuPlayerController::BeginPlay()
{
    Super::BeginPlay();
    if (!IsLocalController()) return;
    for (TActorIterator<ACameraActor> It(GetWorld()); It; ++It)
        if (It->ActorHasTag(TEXT("MenuCamera"))) { SetViewTarget(*It); break; }
    MenuWidget = CreateWidget<UAnomalyMainMenuWidget>(this, MenuWidgetClass.LoadSynchronous());
    if (!IsValid(MenuWidget))
    {
        UE_LOG(LogTemp, Error, TEXT("[MainMenu] WBP_MainMenu missing; rebuild T19 menu assets"));
        return;
    }
    MenuWidget->AddToViewport(100);
    bShowMouseCursor = true;
    FInputModeUIOnly InputMode;
    InputMode.SetWidgetToFocus(MenuWidget->TakeWidget());
    InputMode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    SetInputMode(InputMode);
    MenuWidget->SetKeyboardFocus();
    UE_LOG(LogTemp, Display, TEXT("[MainMenu] Ready; Target=%s"), *GetStartPackage().ToString());
}

void AAnomalyMenuPlayerController::StartLevel01()
{
    if (bStartingGame || !IsValid(MenuWidget) || !Cast<AAnomalyMenuGameMode>(GetWorld()->GetAuthGameMode())) return;
    const FName Level01Package=GetStartPackage();
    if (!FPackageName::DoesPackageExist(Level01Package.ToString()))
    {
        MenuWidget->ShowLaunchError();
        UE_LOG(LogTemp, Error, TEXT("[MainMenu] Level01 package missing: %s"), *Level01Package.ToString());
        return;
    }
    bStartingGame = true;
    MenuWidget->PresentLoading();
    // Give Slate a rendered frame for the loading card before synchronous map travel.
    GetWorldTimerManager().SetTimer(StartTimer, this, &AAnomalyMenuPlayerController::TravelToLevel01, .25f, false);
}

void AAnomalyMenuPlayerController::TravelToLevel01()
{
    if (!bStartingGame) return;
    bShowMouseCursor = false;
    SetInputMode(FInputModeGameOnly());
    UGameplayStatics::OpenLevel(this, GetStartPackage());
}

void AAnomalyMenuPlayerController::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    GetWorldTimerManager().ClearTimer(StartTimer);
    if (IsValid(MenuWidget)) MenuWidget->RemoveFromParent();
    MenuWidget = nullptr;
    Super::EndPlay(EndPlayReason);
}
