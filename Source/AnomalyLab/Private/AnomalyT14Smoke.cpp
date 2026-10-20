#include "AnomalyT14Smoke.h"
#include "AnomalyRoundCoordinator.h"
#include "AnomalyBoxActor.h"
#include "AnomalyEquipmentComponent.h"
#include "AnomalyWalletComponent.h"
#include "AnomalyHealthComponent.h"
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
#include "UObject/UnrealType.h"

namespace
{
    int32 RunPhase = 0;
    bool bFinished = false;
    TArray<TSharedPtr<FJsonValue>> Checks;
}

AAnomalyT14Smoke::AAnomalyT14Smoke() { PrimaryActorTick.bCanEverTick = true; }

bool AAnomalyT14Smoke::Check(const FString& Name, bool bPassed)
{
    TSharedRef<FJsonObject> Item = MakeShared<FJsonObject>();
    Item->SetStringField(TEXT("check"), Name);
    Item->SetBoolField(TEXT("passed"), bPassed);
    Checks.Add(MakeShared<FJsonValueObject>(Item));
    UE_LOG(LogTemp, Display, TEXT("[T14Smoke] %s %s"), bPassed ? TEXT("PASS") : TEXT("FAIL"), *Name);
    if (!bPassed) Finish(false);
    return bPassed;
}

void AAnomalyT14Smoke::Finish(bool bPassed)
{
    if (bFinished) return;
    bFinished = true;
    FString Path;
    FParse::Value(FCommandLine::Get(), TEXT("T14Report="), Path);
    if (Path.IsEmpty()) Path = FPaths::ProjectSavedDir() / TEXT("T14/runtime_report.json");
    TSharedRef<FJsonObject> Report = MakeShared<FJsonObject>();
    Report->SetStringField(TEXT("status"), bPassed ? TEXT("PASS") : TEXT("FAIL"));
    Report->SetStringField(TEXT("scope"), TEXT("Real map, native state, Blueprint adapters and direct input handlers; NullRHI; no physical keys or visual check"));
    Report->SetNumberField(TEXT("run_phase"), RunPhase);
    Report->SetArrayField(TEXT("checks"), Checks);
    FString Text;
    FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Text));
    FPlatformFileManager::Get().GetPlatformFile().CreateDirectoryTree(*FPaths::GetPath(Path));
    const bool bSaved = FFileHelper::SaveStringToFile(Text, *Path, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    UE_LOG(LogTemp, Display, TEXT("[T14Smoke] RESULT %s Saved=%d"), bPassed ? TEXT("PASS") : TEXT("FAIL"), bSaved);
    FPlatformMisc::RequestExitWithStatus(false, bPassed && bSaved ? 0 : 1);
}

bool AAnomalyT14Smoke::PanelContains(const FString& Token) const
{
    TArray<UUserWidget*> Widgets;
    UWidgetBlueprintLibrary::GetAllWidgetsOfClass(this, Widgets, UUserWidget::StaticClass(), false);
    for (UUserWidget* Widget : Widgets)
        if (IsValid(Widget) && Widget->WidgetTree)
            if (UTextBlock* Text = Widget->WidgetTree->FindWidget<UTextBlock>(TEXT("StatusText")))
                if (Text->GetText().ToString().Contains(Token)) return true;
    return false;
}

bool AAnomalyT14Smoke::OpenForced(int32 Outcome)
{
    if (!Check(TEXT("Ready has three candidates"), Coordinator->GetNativeRoundState() == 0 && Coordinator->CandidateBoxes.Num() == 3)) return false;
    Box = Coordinator->CandidateBoxes[0];
    if (!Check(TEXT("Selected box valid"), IsValid(Box))) return false;
    Box->bForceOutcome = true; // Temporary instance only; asset defaults remain untouched.
    ExpectedMoney = Wallet->Money;
    bCapturedOutcome = false;
    if (!Check(TEXT("Box opens"), Box->NativeInteract(Player, Outcome))) return false;
    return Check(TEXT("Duplicate open rejected"), !Box->NativeInteract(Player, Outcome));
}

void AAnomalyT14Smoke::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (bFinished) return;
    Elapsed += DeltaSeconds;
    if (Elapsed > 45.f) { Check(TEXT("Phase completes within 45 seconds"), false); return; }
    if (Stage == 0)
    {
        for (TActorIterator<AAnomalyRoundCoordinator> It(GetWorld()); It; ++It) { Coordinator = *It; break; }
        Player = UGameplayStatics::GetPlayerCharacter(this, 0);
        if (!IsValid(Coordinator) || !IsValid(Player) || Coordinator->CandidateBoxes.Num() != 3) return;
        Wallet = Player->FindComponentByClass<UAnomalyWalletComponent>();
        Equipment = Player->FindComponentByClass<UAnomalyEquipmentComponent>();
        if (!Check(TEXT("Wallet and equipment exist"), IsValid(Wallet) && IsValid(Equipment))) return;
        if (!Check(TEXT("Fresh run resets money and statistics"), Wallet->Money == 0 && Coordinator->CompletedRounds == 0
            && Coordinator->ThreatsResolved == 0 && Coordinator->RunEndReason == EAnomalyRunEndReason::None)) return;
        if (RunPhase == 2)
        {
            Coordinator->FailWithError();
            if (!Check(TEXT("Technical error has distinct end reason"), Coordinator->GetNativeRoundState() == 3
                && Coordinator->RunEndReason == EAnomalyRunEndReason::Error)) return;
            if (!Check(TEXT("Technical error panel shown"), PanelContains(TEXT("原型运行异常")))) return;
            Coordinator->ContinueRun();
            if (!Check(TEXT("Terminal continue cannot spawn choices"), Coordinator->CandidateBoxes.IsEmpty())) return;
            Finish(true);
            return;
        }
        if (RunPhase == 1)
        {
            // Short deterministic threat fixtures keep this regression independent of the T15 20-second balance pass.
            Coordinator->ThreatSurvivalSeconds = 2.f;
            if (UAnomalyHealthComponent* Health = Player->FindComponentByClass<UAnomalyHealthComponent>())
                Health->ThreatDamage = 0;
        }
        if (!OpenForced(RunPhase == 0 ? 0 : 2)) return;
        Stage = RunPhase == 0 ? 1 : 10;
        return;
    }
    if (Stage == 1 || Stage == 3)
    {
        if (!bCapturedOutcome && IsValid(Box) && Box->bResolved)
        {
            ExpectedMoney += Stage == 1 ? Box->HighValueAmount : 3;
            bCapturedOutcome = true;
            if (!Check(TEXT("Exactly one reward payment"), Wallet->Money == ExpectedMoney)) return;
        }
        if (Coordinator->GetNativeRoundState() != 4) return;
        if (!Check(TEXT("Reward enters decision without auto spawn"), Coordinator->CandidateBoxes.IsEmpty()
            && !IsValid(Coordinator->SelectedBox) && Wallet->Money == ExpectedMoney)) return;
        if (!Check(TEXT("Decision freezes movement"), Cast<ACharacter>(Player)->GetCharacterMovement()->MovementMode == MOVE_None)) return;
        if (!Check(TEXT("Decision panel shows current money"), PanelContains(FString::Printf(TEXT("$%d"), ExpectedMoney)))) return;
        if (Stage == 1)
        {
            if (!Check(TEXT("First completed round counted"), Coordinator->CompletedRounds == 1)) return;
            Equipment->EquipScanner(); // Same handler as key 1; no physical keyboard is injected.
            if (!Check(TEXT("Continue preserves money and spawns three"), Coordinator->GetNativeRoundState() == 0
                && Coordinator->CandidateBoxes.Num() == 3 && Wallet->Money == ExpectedMoney)) return;
            if (!Check(TEXT("Continue restores movement"), Cast<ACharacter>(Player)->GetCharacterMovement()->MovementMode == MOVE_Walking)) return;
            if (!OpenForced(1)) return;
            Stage = 3;
            return;
        }
        if (!Check(TEXT("Second completed round counted"), Coordinator->CompletedRounds == 2)) return;
        Equipment->EquipGun(); // Same handler as key 2.
        if (!Check(TEXT("Cash out ends run with frozen snapshot"), Coordinator->GetNativeRoundState() == 3
            && Coordinator->RunEndReason == EAnomalyRunEndReason::CashedOut
            && Coordinator->FinalRunValue == ExpectedMoney && Coordinator->FinalRunSeconds > 0.f)) return;
        if (!Check(TEXT("Cash-out panel shown"), PanelContains(TEXT("撤离成功")))) return;
        FBoolProperty* Ended = FindFProperty<FBoolProperty>(Player->GetClass(), TEXT("bT06Ended"));
        if (!Check(TEXT("Blueprint received terminal event"), Ended && Ended->GetPropertyValue_InContainer(Player))) return;
        Coordinator->ContinueRun();
        if (!Check(TEXT("Terminal continue is rejected"), Coordinator->CandidateBoxes.IsEmpty())) return;
        RunPhase = 1; Stage = 99;
        UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this, true)));
        return;
    }
    if (Stage == 10 || Stage == 11)
    {
        if (Coordinator->GetNativeRoundState() != 4) return;
        const int32 ExpectedThreats = Stage == 10 ? 1 : 2;
        if (!Check(TEXT("Threat count and completed rounds advance once"), Coordinator->ThreatsResolved == ExpectedThreats
            && Coordinator->CompletedRounds == ExpectedThreats && Wallet->Money == 0)) return;
        if (Stage == 10)
        {
            Coordinator->ContinueRun();
            if (!Check(TEXT("First threat allows continue"), Coordinator->GetNativeRoundState() == 0
                && Coordinator->CandidateBoxes.Num() == 3)) return;
            if (!OpenForced(2)) return;
            Stage = 11;
            return;
        }
        Coordinator->ContinueRun();
        if (!Check(TEXT("Second threat rejects continue"), Coordinator->GetNativeRoundState() == 4
            && Coordinator->CandidateBoxes.IsEmpty())) return;
        if (!Check(TEXT("Second threat panel offers cash out"), PanelContains(TEXT("已完成第二次收容")))) return;
        Coordinator->CashOut();
        if (!Check(TEXT("Second threat can cash out"), Coordinator->GetNativeRoundState() == 3
            && Coordinator->RunEndReason == EAnomalyRunEndReason::CashedOut)) return;
        RunPhase = 2; Stage = 99;
        UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this, true)));
    }
}
