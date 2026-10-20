#include "AnomalyT15Smoke.h"
#include "AnomalyRoundCoordinator.h"
#include "AnomalyBoxActor.h"
#include "AnomalyThreatCharacter.h"
#include "AnomalyHealthComponent.h"
#include "AnomalyWalletComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Blueprint/UserWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Components/TextBlock.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/PlatformFileManager.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

namespace
{
    int32 RunPhase = 0;
    bool bFinished = false;
    TArray<TSharedPtr<FJsonValue>> Checks;
}

AAnomalyT15Smoke::AAnomalyT15Smoke() { PrimaryActorTick.bCanEverTick = true; }

bool AAnomalyT15Smoke::Check(const FString& Name, bool bPassed)
{
    TSharedRef<FJsonObject> Item = MakeShared<FJsonObject>();
    Item->SetStringField(TEXT("check"), Name); Item->SetBoolField(TEXT("passed"), bPassed);
    Checks.Add(MakeShared<FJsonValueObject>(Item));
    UE_LOG(LogTemp, Display, TEXT("[T15Smoke] %s %s"), bPassed ? TEXT("PASS") : TEXT("FAIL"), *Name);
    if (!bPassed) Finish(false);
    return bPassed;
}

void AAnomalyT15Smoke::Finish(bool bPassed)
{
    if (bFinished) return;
    bFinished = true;
    FString Path;
    FParse::Value(FCommandLine::Get(), TEXT("T15Report="), Path);
    if (Path.IsEmpty()) Path = FPaths::ProjectSavedDir() / TEXT("T15/runtime_report.json");
    TSharedRef<FJsonObject> Report = MakeShared<FJsonObject>();
    Report->SetStringField(TEXT("status"), bPassed ? TEXT("PASS") : TEXT("FAIL"));
    Report->SetStringField(TEXT("scope"), TEXT("Real map hidden NullRHI native flow; temporary forced outcomes; no physical keyboard or rendered visual check"));
    Report->SetNumberField(TEXT("run_phase"), RunPhase);
    Report->SetArrayField(TEXT("checks"), Checks);
    FString Text;
    FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Text));
    FPlatformFileManager::Get().GetPlatformFile().CreateDirectoryTree(*FPaths::GetPath(Path));
    const bool bSaved = FFileHelper::SaveStringToFile(Text, *Path, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    UE_LOG(LogTemp, Display, TEXT("[T15Smoke] RESULT %s Saved=%d"), bPassed ? TEXT("PASS") : TEXT("FAIL"), bSaved);
    FPlatformMisc::RequestExitWithStatus(false, bPassed && bSaved ? 0 : 1);
}

bool AAnomalyT15Smoke::PanelContains(const FString& Token) const
{
    TArray<UUserWidget*> Widgets;
    UWidgetBlueprintLibrary::GetAllWidgetsOfClass(this, Widgets, UUserWidget::StaticClass(), false);
    for (UUserWidget* Widget : Widgets)
        if (IsValid(Widget) && Widget->WidgetTree)
            for (const TCHAR* Name : {TEXT("HPText"), TEXT("ThreatText"), TEXT("DamageText"), TEXT("StatusText"), TEXT("MoneyText"), TEXT("ThreatText")})
                if (UTextBlock* Text = Widget->WidgetTree->FindWidget<UTextBlock>(Name))
                    if (Text->GetText().ToString().Contains(Token)) return true;
    return false;
}

bool AAnomalyT15Smoke::OpenThreat(bool bAllowSpawn)
{
    if (!Check(TEXT("Three candidates ready"), Coordinator->GetNativeRoundState() == 0 && Coordinator->CandidateBoxes.Num() == 3)) return false;
    Box = Coordinator->CandidateBoxes[0];
    if (!Check(TEXT("Candidate valid"), IsValid(Box))) return false;
    Box->bForceOutcome = true;
    if (!bAllowSpawn) Box->ThreatClass = nullptr; // Temporary instance only.
    if (!Check(TEXT("Threat box opens"), Box->NativeInteract(Player, 2))) return false;
    return Check(TEXT("Duplicate threat opening rejected"), !Box->NativeInteract(Player, 2));
}

void AAnomalyT15Smoke::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (bFinished) return;
    Elapsed += DeltaSeconds;
    if (Elapsed > 55.f) { Check(TEXT("Phase finished within 55 seconds"), false); return; }
    if (Stage == 0)
    {
        for (TActorIterator<AAnomalyRoundCoordinator> It(GetWorld()); It; ++It) { Coordinator = *It; break; }
        Player = UGameplayStatics::GetPlayerCharacter(this, 0);
        if (!IsValid(Coordinator) || !IsValid(Player) || Coordinator->CandidateBoxes.Num() != 3) return;
        Health = Player->FindComponentByClass<UAnomalyHealthComponent>();
        Wallet = Player->FindComponentByClass<UAnomalyWalletComponent>();
        if (!Check(TEXT("Health and wallet attached"), IsValid(Health) && IsValid(Wallet))) return;
        if (!Check(TEXT("Fresh run HP and money reset"), Health->CurrentHealth == 100 && Wallet->Money == 0
            && Coordinator->CompletedRounds == 0 && Coordinator->ThreatsResolved == 0)) return;
        if (!Check(TEXT("Round explicitly awaits selection"), Coordinator->RoundPhase == EAnomalyRoundPhase::AwaitingSelection)) return;
        if (!Check(TEXT("HP widget initialized"), PanelContains(TEXT("HP  100 / 100")))) return;
        if (!Check(TEXT("Localized money HUD initialized"), PanelContains(TEXT("收益")))) return;
        if (RunPhase == 2)
        {
            if (!OpenThreat(false)) return;
            Stage = 30;
            return;
        }
        if (RunPhase == 0) Health->ThreatDamage = 0;
        else Wallet->NativeAddMoney(123);
        if (!OpenThreat(true)) return;
        if (!Check(TEXT("Early completion rejected before result"), Coordinator->GetNativeRoundState() == 1
            && Coordinator->RoundPhase == EAnomalyRoundPhase::ResolvingOutcome)) return;
        Coordinator->CompleteCurrentOutcome();
        if (!Check(TEXT("Premature completion cannot advance"), Coordinator->CompletedRounds == 0
            && Coordinator->GetNativeRoundState() == 1)) return;
        Stage = RunPhase == 0 ? 10 : 20;
        return;
    }
    if (Stage == 10 || Stage == 20)
    {
        if (Stage == 10 && Coordinator->GetNativeRoundState() == 4)
        {
            if (!Check(TEXT("Explicit decision phase"), Coordinator->RoundPhase == EAnomalyRoundPhase::PostRoundDecision)) return;
            if (!Check(TEXT("Timed survival resolves once"), Coordinator->ThreatsResolved == 1
                && Coordinator->CompletedRounds == 1 && Health->CurrentHealth == 100)) return;
            if (!Check(TEXT("Survival ends after twenty seconds"), Elapsed - PursuitStartedAt >= 19.8f)) return;
            if (!Check(TEXT("Post-threat damage disabled"), !Health->bDamageEnabled)) return;
            Coordinator->ContinueRun();
            if (!Check(TEXT("HP persists into next round"), Coordinator->CandidateBoxes.Num() == 3 && Health->CurrentHealth == 100)) return;
            RunPhase = 1; Stage = 99;
            UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this, true)));
            return;
        }
        if (Stage == 20 && Health->CurrentHealth < LastHealth)
        {
            ++Hits;
            if (!Check(TEXT("Each hit deals twenty-five"), LastHealth - Health->CurrentHealth == 25)) return;
            if (Hits > 1 && !Check(TEXT("Damage cooldown at least 1.5 seconds"), Elapsed - LastHitAt >= 1.48f)) return;
            LastHitAt = Elapsed;
            LastHealth = Health->CurrentHealth;
        }
        if (Stage == 20 && Coordinator->GetNativeRoundState() == 3)
        {
            if (!Check(TEXT("Explicit failed phase"), Coordinator->RoundPhase == EAnomalyRoundPhase::RunFailed)) return;
            if (!Check(TEXT("Four hits cause failed run"), Hits == 4 && Health->bDead && Health->CurrentHealth == 0
                && Coordinator->RunEndReason == EAnomalyRunEndReason::Failed)) return;
            if (!Check(TEXT("Death excludes successful containment"), Coordinator->ThreatsResolved == 0
                && Coordinator->CompletedRounds == 0 && Coordinator->CandidateBoxes.IsEmpty())) return;
            if (!Check(TEXT("Death snapshots loss and clears wallet"), Coordinator->LostRunValue == 123
                && Coordinator->FinalRunValue == 0 && Wallet->Money == 0)) return;
            if (!Check(TEXT("Failure panel shows loss"), PanelContains(TEXT("损失金额  $123")))) return;
            TArray<UUserWidget*> Widgets;
            UWidgetBlueprintLibrary::GetAllWidgetsOfClass(this, Widgets, UUserWidget::StaticClass(), false);
            bool bLegacyHidden = false;
            for (UUserWidget* Widget : Widgets)
                if (IsValid(Widget) && Widget->WidgetTree)
                    if (UTextBlock* Legacy = Widget->WidgetTree->FindWidget<UTextBlock>(TEXT("RunEndText")))
                        bLegacyHidden = Legacy->GetVisibility() == ESlateVisibility::Collapsed;
            if (!Check(TEXT("Legacy terminal overlay hidden"), bLegacyHidden)) return;
            RunPhase = 2; Stage = 99;
            UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this, true)));
            return;
        }
        if (!IsValid(Coordinator->CurrentSpider)) return;
        AAnomalyThreatCharacter* Threat = Coordinator->CurrentSpider;
        if (!Threat->bThreatActive)
        {
            if (PursuitStartedAt > 0.f) return; // One-second containment message after survival.
            if (!bWarningChecked)
            {
                bWarningChecked = true;
                if (!Check(TEXT("Explicit warning phase"), Coordinator->RoundPhase == EAnomalyRoundPhase::ThreatWarning)) return;
                if (!Check(TEXT("Warning has no damage or pursuit"), !Health->bDamageEnabled && Health->CurrentHealth == 100)) return;
                if (!Check(TEXT("Warning text shown"), PanelContains(TEXT("危险：收容失效")))) return;
            }
            return;
        }
        if (PursuitStartedAt <= 0.f)
        {
            PursuitStartedAt = Elapsed;
            ThreatStartLocation = Threat->GetActorLocation();
            if (!Check(TEXT("Explicit pursuit phase"), Coordinator->RoundPhase == EAnomalyRoundPhase::ThreatActive)) return;
            if (!Check(TEXT("Pursuit activates after warning"), Elapsed >= 1.f && Health->bDamageEnabled)) return;
            if (!Check(TEXT("Twenty-second threat timer configured"), FMath::Abs(Threat->AutoResolveDelay - 20.) < .001)) return;
            if (!Check(TEXT("Countdown text shown"), PanelContains(TEXT("收容倒计时")))) return;
            if (Stage == 20)
            {
                Threat->MoveSpeed = 0.;
                Threat->GetCharacterMovement()->MaxWalkSpeed = 0.f;
                LastHealth = Health->CurrentHealth;
            }
        }
        if (Stage == 10)
        {
            if (!bCheckedMovement && Elapsed - PursuitStartedAt >= .7f)
            {
                bCheckedMovement = true;
                if (!Check(TEXT("Threat moves during pursuit"), FVector::Dist2D(ThreatStartLocation, Threat->GetActorLocation()) > 1.f)) return;
            }
            return;
        }
        Threat->SetActorLocation(Player->GetActorLocation(), false, nullptr, ETeleportType::TeleportPhysics);
        return;
    }
    if (Stage == 30 && Coordinator->GetNativeRoundState() == 3)
    {
        if (!Check(TEXT("Explicit error phase"), Coordinator->RoundPhase == EAnomalyRoundPhase::Error)) return;
        if (!Check(TEXT("Threat spawn retries exhaust into Error"), Coordinator->RunEndReason == EAnomalyRunEndReason::Error
            && Coordinator->CurrentThreatSpawnRetryCount == 3 && Coordinator->ThreatsResolved == 0)) return;
        Finish(true);
    }
}
