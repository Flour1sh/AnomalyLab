#include "AnomalyMigrationSmoke.h"
#include "AnomalyRoundCoordinator.h"
#include "AnomalyBoxActor.h"
#include "AnomalyBoxDefinition.h"
#include "AnomalyWalletComponent.h"
#include "AnomalyThreatCharacter.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Blueprint/UserWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Components/TextBlock.h"
#include "Kismet/GameplayStatics.h"
#include "EngineUtils.h"
#include "Engine/World.h"
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
    int32 RestartPhase = 0;
    bool Finished = false;
    TArray<TSharedPtr<FJsonValue>> Results;
}

AAnomalyMigrationSmoke::AAnomalyMigrationSmoke() { PrimaryActorTick.bCanEverTick = true; }
bool AAnomalyMigrationSmoke::Check(const FString& Name, bool Passed)
{
    TSharedRef<FJsonObject> Item = MakeShared<FJsonObject>();
    Item->SetStringField(TEXT("check"), Name); Item->SetBoolField(TEXT("passed"), Passed);
    Results.Add(MakeShared<FJsonValueObject>(Item));
    UE_LOG(LogTemp, Display, TEXT("[MigrationSmoke] %s %s"), Passed ? TEXT("PASS") : TEXT("FAIL"), *Name);
    if (!Passed) Finish(false);
    return Passed;
}

void AAnomalyMigrationSmoke::Finish(bool Passed)
{
    if (Finished) return;
    Finished = true;
    FString Path;
    FParse::Value(FCommandLine::Get(), TEXT("MigrationReport="), Path);
    if (Path.IsEmpty()) Path = FPaths::ProjectSavedDir()/TEXT("CppMigration/runtime.json");
    TSharedRef<FJsonObject> Report = MakeShared<FJsonObject>();
    Report->SetStringField(TEXT("status"), Passed ? TEXT("PASS") : TEXT("FAIL"));
    Report->SetStringField(TEXT("scope"), TEXT("Real map native gameplay and Blueprint event adapters, automated calls; no physical keyboard or rendered visual validation"));
    Report->SetArrayField(TEXT("checks"), Results);
    Report->SetNumberField(TEXT("restart_phase"), RestartPhase);
    FString Text;
    FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Text));
    FPlatformFileManager::Get().GetPlatformFile().CreateDirectoryTree(*FPaths::GetPath(Path));
    const bool Saved = FFileHelper::SaveStringToFile(Text, *Path, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    UE_LOG(LogTemp, Display, TEXT("[MigrationSmoke] RESULT %s Report=%s Saved=%d"), Passed ? TEXT("PASS") : TEXT("FAIL"), *Path, Saved);
    FPlatformMisc::RequestExitWithStatus(false, Passed && Saved ? 0 : 1);
}

bool AAnomalyMigrationSmoke::ValidateDefinitions()
{
    if (!Check(TEXT("Six native definitions available"), SelectedBox->Definitions.Num() == 6)) return false;
    for (const auto& Pair : SelectedBox->Definitions)
    {
        UAnomalyBoxDefinition* Definition = Pair.Value;
        FString Reason;
        if (!Check(TEXT("Valid definition ") + Pair.Key.ToString(), IsValid(Definition) && Definition->Validate(Reason))) return false;
        if (!Check(TEXT("Boundary at zero ") + Pair.Key.ToString(), Definition->SelectOutcome(0.0) == 0)) return false;
        if (!Check(TEXT("HighValue boundary ") + Pair.Key.ToString(), Definition->SelectOutcome(Definition->HighValueChance) == 1)) return false;
        if (!Check(TEXT("Trash boundary ") + Pair.Key.ToString(), Definition->SelectOutcome(Definition->HighValueChance + Definition->TrashChance) == 2)) return false;
        FRandomStream Stream(11002);
        int32 Counts[3] = {0,0,0};
        for (int32 Sample = 0; Sample < 10000; ++Sample) ++Counts[Definition->SelectOutcome(Stream.FRand())];
        const double Expected[] = {Definition->HighValueChance, Definition->TrashChance, Definition->ThreatChance};
        for (int32 Index = 0; Index < 3; ++Index)
        {
            UE_LOG(LogTemp, Display, TEXT("[MigrationSmoke] Distribution %s Outcome=%d Count=%d/10000 Expected=%.6f"), *Pair.Key.ToString(), Index, Counts[Index], Expected[Index]);
            if (!Check(FString::Printf(TEXT("Fixed-seed frequency %s/%d within 2 percentage points"), *Pair.Key.ToString(), Index),
                       FMath::Abs(Counts[Index]/10000.0 - Expected[Index]) <= 0.02)) return false;
        }
    }
    UAnomalyBoxDefinition* Invalid = NewObject<UAnomalyBoxDefinition>(this);
    Invalid->HighValueChance = -0.1;
    FString Reason;
    if (!Check(TEXT("Invalid probability rejected"), !Invalid->Validate(Reason))) return false;
    Invalid->HighValueChance = 0; Invalid->TrashChance = 0; Invalid->ThreatChance = 1;
    if (!Check(TEXT("Zero reward probabilities never selected"), Invalid->Validate(Reason) && Invalid->SelectOutcome(0.0) == 2)) return false;
    return true;
}

void AAnomalyMigrationSmoke::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (Finished) return;
    Elapsed += DeltaSeconds;
    if (Elapsed > 45.0f) { Check(TEXT("Runtime completed within 45 world seconds"), false); return; }
    if (Stage == 0)
    {
        for (TActorIterator<AAnomalyRoundCoordinator> It(GetWorld()); It; ++It) { Coordinator = *It; break; }
        Player = UGameplayStatics::GetPlayerCharacter(this,0);
        if (!Coordinator || !Player || !Coordinator->CurrentBox) return;
        Wallet = Player->FindComponentByClass<UAnomalyWalletComponent>();
        if (!Check(TEXT("Player uses migrated wallet"), IsValid(Wallet))) return;
        if (!Check(TEXT("Fresh run has zero money and threat count"), Wallet->Money == 0 && Coordinator->ThreatsResolved == 0 && Coordinator->GetNativeRoundState() == 0)) return;
        if (RestartPhase == 1) { Finish(true); return; }
        SelectedBox = Coordinator->CurrentBox;
        if (!ValidateDefinitions()) return;
        // Fixed-seed initialization must resolve Unknown once without touching outcome state.
        TArray<AAnomalyBoxActor*> Fixtures;
        for (int32 Index=0; Index<2; ++Index)
        {
            FTransform Transform(FVector(10000.0+Index*200,10000,100));
            AAnomalyBoxActor* Fixture = GetWorld()->SpawnActorDeferred<AAnomalyBoxActor>(Coordinator->BoxClass,Transform,nullptr,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
            if (!Check(TEXT("Spawn deferred unknown fixture"), IsValid(Fixture))) return;
            Fixture->DefinitionID=TEXT("Unknown");Fixture->bUseFixedSeeds=true;
            Fixture->ConfigurationSeed=11001;Fixture->OutcomeSeed=11002;
            Fixture->FinishSpawning(Transform);Fixtures.Add(Fixture);
        }
        if (!Check(TEXT("Fixed seed gives same hidden profile"), Fixtures[0]->ResolvedDefinitionID==Fixtures[1]->ResolvedDefinitionID)) return;
        const FName Resolved=Fixtures[0]->ResolvedDefinitionID;
        Fixtures[0]->InitializeDefinition();
        if (!Check(TEXT("Repeated initialization does not reroll"), Fixtures[0]->ResolvedDefinitionID==Resolved)) return;
        if (!Check(TEXT("Foreign box cannot lock current round"), !Coordinator->TryLockSelection(Fixtures[0]))) return;
        for (AAnomalyBoxActor* Fixture:Fixtures) Fixture->Destroy();
        if (FParse::Param(FCommandLine::Get(), TEXT("AnomalyStatsOnly"))) { Finish(true); return; }
        Stage=1;SelectedBox=nullptr;
    }
    if (Stage>=1 && Stage<=4)
    {
        if (!SelectedBox)
        {
            if (Coordinator->GetNativeRoundState()!=0 || !Coordinator->CurrentBox) return;
            SelectedBox=Coordinator->CurrentBox;
            StartingMoney=Wallet->Money;bSawOutcome=false;
            SelectedBox->bForceOutcome=true;
            const int32 Outcome=Stage==1?0:Stage==2?1:2;
            if (!Check(FString::Printf(TEXT("Open stage %d"),Stage),SelectedBox->NativeInteract(Player,Outcome))) return;
            if (!Check(TEXT("Duplicate interaction rejected"),!SelectedBox->NativeInteract(Player,Outcome))) return;
            if (!Check(TEXT("Open moves coordinator to Revealing"),Coordinator->GetNativeRoundState()==1)) return;
            bool bPlayingCrateAnimation=false;
            TInlineComponentArray<USkeletalMeshComponent*> Meshes(SelectedBox);
            for (USkeletalMeshComponent* Mesh:Meshes)
                if (Mesh->GetName().StartsWith(TEXT("CrateMesh")) && Mesh->GetSkeletalMeshAsset())
                {
                    UAnimSingleNodeInstance* Node=Mesh->GetSingleNodeInstance();
                    bPlayingCrateAnimation=Node && Node->GetCurrentAsset()==SelectedBox->OpeningAnimation && Mesh->IsPlaying();
                }
            if (!Check(TEXT("Crate component plays retained opening animation"),bPlayingCrateAnimation)) return;
            return;
        }
        if (!bSawOutcome && IsValid(SelectedBox) && SelectedBox->bResolved)
        {
            bSawOutcome=true;
            const int32 Outcome=Stage==1?0:Stage==2?1:2;
            if (!Check(TEXT("Forced result preserved"),SelectedBox->OutcomeRoll==Outcome)) return;
            ExpectedMoney=StartingMoney+(Stage==1?SelectedBox->HighValueAmount:Stage==2?3:0);
            if (Stage==1 && !Check(TEXT("HighValue reward inside instance range"),SelectedBox->HighValueAmount>=SelectedBox->DefinitionAsset->ValueMin && SelectedBox->HighValueAmount<=SelectedBox->DefinitionAsset->ValueMax)) return;
            if (!Check(TEXT("Exactly one wallet payment"),Wallet->Money==ExpectedMoney)) return;
            if (Stage==1)
            {
                TArray<UUserWidget*> Widgets;
                UWidgetBlueprintLibrary::GetAllWidgetsOfClass(this,Widgets,UUserWidget::StaticClass(),false);
                FString Actual;
                for (UUserWidget* Widget:Widgets)
                    if (Widget && Widget->WidgetTree)
                        if (UTextBlock* ResultText=Widget->WidgetTree->FindWidget<UTextBlock>(TEXT("ResultText")))
                        { Actual=ResultText->GetText().ToString(); break; }
                const FString Expected=FString::Printf(TEXT("HIGH VALUE +$%s"),*FText::AsNumber(SelectedBox->HighValueAmount).ToString());
                UE_LOG(LogTemp,Display,TEXT("[MigrationSmoke] HUD reward popup Actual=%s Expected=%s"),*Actual,*Expected);
                if (!Check(TEXT("HUD popup matches actual high-value payout"),Actual==Expected)) return;
            }
            SelectedBox->OnNativeOutcomeResolved.Broadcast(SelectedBox,Outcome,Coordinator->CurrentOutcomeActor,true);
            if (!Check(TEXT("Duplicate outcome ignored"),Wallet->Money==ExpectedMoney && Coordinator->GetNativeRoundState()==2)) return;
            if (Outcome==2 && !Check(TEXT("Threat spawned with native base and T10 shell"),IsValid(Coordinator->CurrentSpider))) return;
            if (Outcome==2)
            {
                ThreatStartedAt=Elapsed;ThreatStartLocation=Coordinator->CurrentSpider->GetActorLocation();
                bCheckedThreatMovement=false;bCheckedThreatContact=false;
            }
        }
        if (!bSawOutcome) return;
        if (Stage>=3 && IsValid(Coordinator->CurrentSpider))
        {
            AAnomalyThreatCharacter* Threat=Coordinator->CurrentSpider;
            if (!bCheckedThreatMovement && Elapsed-ThreatStartedAt>=0.5f)
            {
                bCheckedThreatMovement=true;
                if (!Check(TEXT("Threat moves on cooked map navigation"),FVector::Dist2D(ThreatStartLocation,Threat->GetActorLocation())>1.0f)) return;
                // Contact is injected only into this temporary test instance, after validating navigation.
                Threat->SetActorLocation(Player->GetActorLocation(),false,nullptr,ETeleportType::TeleportPhysics);
            }
            if (bCheckedThreatMovement && !bCheckedThreatContact && Elapsed-ThreatStartedAt>=0.75f)
            {
                bCheckedThreatContact=true;
                if (!Check(TEXT("Actual player overlap produces attack notification"),Threat->bAttackTriggered)) return;
            }
        }
        if (Stage<4 && Coordinator->GetNativeRoundState()==0 && Coordinator->CurrentBox!=SelectedBox)
        {
            if (!Check(TEXT("Next round keeps accumulated money"),Wallet->Money==ExpectedMoney)) return;
            if (Stage==3 && !Check(TEXT("First threat counted once"),Coordinator->ThreatsResolved==1)) return;
            ++Stage;SelectedBox=nullptr;return;
        }
        if (Stage==4 && Coordinator->GetNativeRoundState()==3)
        {
            if (!Check(TEXT("Second threat ends current baseline run"),Coordinator->ThreatsResolved==2 && !IsValid(Coordinator->CurrentBox) && !IsValid(Coordinator->CurrentOutcomeActor))) return;
            if (!Check(TEXT("Final money preserved"),Wallet->Money==ExpectedMoney)) return;
            ACharacter* Character=Cast<ACharacter>(Player);
            if (!Check(TEXT("Blueprint run-end adapter disables movement"),Character && Character->GetCharacterMovement()->MovementMode==MOVE_None)) return;
            FBoolProperty* Ended=FindFProperty<FBoolProperty>(Player->GetClass(),TEXT("bT06Ended"));
            if (!Check(TEXT("Blueprint received end event"),Ended && Ended->GetPropertyValue_InContainer(Player))) return;
            RestartPhase=1;Stage=5;
            UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this, true)));
        }
    }
}
