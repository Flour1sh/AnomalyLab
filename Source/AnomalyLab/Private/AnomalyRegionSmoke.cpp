// Opt-in Development-only T26 tests. Normal startup never installs this driver.
#include "CoreMinimal.h"
#if !UE_BUILD_SHIPPING
#include "AnomalyRegionDefinition.h"
#include "AnomalyBoxActor.h"
#include "AnomalyRoundCoordinator.h"
#include "AnomalyExplorationWidget.h"
#include "AnomalyWalletComponent.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Components/TextBlock.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"
#include <limits>

struct FAnomalyRegionProbe
{
    static int32 OutcomeSeed(const AAnomalyBoxActor& Box) { return Box.OutcomeStream.GetCurrentSeed(); }
};

namespace T26Smoke
{
    FDelegateHandle Handle;
    FString Output;
    bool Finished = false;
    int32 Stage = 0;
    uint64 LogicalDigest = 14695981039346656037ULL;
    float NextTime = 2.f;
    TArray<TSharedPtr<FJsonValue>> Checks, Samples, Signatures;
    void Finish(bool Passed)
    {
        if (Finished) return;
        Finished = true;
        auto Report = MakeShared<FJsonObject>();
        Report->SetStringField(TEXT("status"), Passed ? TEXT("PASS") : TEXT("FAIL"));
        Report->SetStringField(TEXT("scope"), TEXT("Native region sampling and live box/cache fixtures; synthetic camera setup and optional real rendered screenshots. No human input, audio or survival simulation."));
        Report->SetNumberField(TEXT("seed"), 26001);
        Report->SetNumberField(TEXT("round_samples"), 60000);
        Report->SetStringField(TEXT("logical_digest"), FString::Printf(TEXT("%016llx"), LogicalDigest));
        Report->SetArrayField(TEXT("checks"), Checks);
        Report->SetArrayField(TEXT("regions"), Samples);
        Report->SetArrayField(TEXT("fixture_signatures"), Signatures);
        FString Json; FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json));
        IFileManager::Get().MakeDirectory(*Output, true);
        const bool Saved = FFileHelper::SaveStringToFile(Json, *(Output / TEXT("report.json")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
        FPlatformMisc::RequestExitWithStatus(false, Passed && Saved ? 0 : 1);
    }
    bool Check(const FString& Name, bool Passed)
    {
        auto Entry = MakeShared<FJsonObject>(); Entry->SetStringField(TEXT("check"), Name); Entry->SetBoolField(TEXT("passed"), Passed);
        Checks.Add(MakeShared<FJsonValueObject>(Entry));
        UE_LOG(LogTemp, Display, TEXT("[T26Smoke] %s %s"), Passed ? TEXT("PASS") : TEXT("FAIL"), *Name);
        if (!Passed) Finish(false);
        return Passed;
    }
    bool Statistics(AAnomalyRoundCoordinator* C)
    {
        const auto& Definitions = C->CurrentBox->Definitions;
        const FName Public[] = {TEXT("Safe"), TEXT("Risky"), TEXT("Unknown")};
        FString Reason;
        TArray<TMap<FName, UAnomalyBoxDefinition*>> Data;
        for (auto Region : C->RegionRules)
        {
            TMap<FName, UAnomalyBoxDefinition*> Adjusted;
            for (const auto& Pair : Definitions)
            {
                auto Copy = DuplicateObject<UAnomalyBoxDefinition>(Pair.Value, C);
                if (!Check(Region->RegionID.ToString()+TEXT(" valid adjusted ")+Pair.Key.ToString(), Region->ApplyTo(*Copy, Reason))) return false;
                FRandomStream Stream(26004); int32 Counts[3] = {0,0,0};
                for (int32 N=0; N<10000; ++N) ++Counts[Copy->SelectOutcome(Stream.FRand())];
                const double Probabilities[] = {Copy->HighValueChance, Copy->TrashChance, Copy->ThreatChance};
                bool Frequencies = true;
                for (int32 I=0; I<3; ++I) Frequencies &= FMath::Abs(Counts[I]/10000.-Probabilities[I]) < .02;
                if (!Check(TEXT("Adjusted outcome frequencies within 2pp"), Frequencies)) return false;
                Adjusted.Add(Pair.Key, Copy);
            }
            Data.Add(Adjusted);
        }
        constexpr int32 N = 60000;
        double Sum[3]={0,0,0}, SumSq[3]={0,0,0};
        int32 Threats[3]={0,0,0}, TypesSeen[3][3]={}, HiddenSeen[3][3]={};
        FRandomStream Choices(26001);
        for (int32 Sample=0; Sample<N; ++Sample)
        {
            TArray<FName> Types;
            if (!UAnomalyRegionDefinition::DrawChoices(C->RegionRules, Choices, Types, Reason)
                || (Types[0]==Types[1] && Types[1]==Types[2])) return Check(TEXT("All sampled rounds have three candidates and two types"), false);
            for (int32 R=0; R<3; ++R)
            {
                FRandomStream Config(static_cast<int32>(Choices.GetUnsignedInt()));
                FRandomStream Outcome(static_cast<int32>(Choices.GetUnsignedInt()));
                const FName Resolved = Types[R]==TEXT("Unknown") ? C->RegionRules[R]->DrawHiddenProfile(Config) : Types[R];
                for (int32 I=0; I<3; ++I) TypesSeen[R][I] += Types[R]==Public[I] ? 1 : 0;
                HiddenSeen[R][0] += Resolved==TEXT("UnknownSafe") ? 1 : 0;
                HiddenSeen[R][1] += Resolved==TEXT("UnknownMedium") ? 1 : 0;
                HiddenSeen[R][2] += Resolved==TEXT("UnknownRisky") ? 1 : 0;
                const UAnomalyBoxDefinition* D = Data[R][Resolved];
                const int32 Result = D->SelectOutcome(Outcome.FRand());
                const int32 Reward = Result==0 ? Outcome.RandRange(D->ValueMin, D->ValueMax) : Result==1 ? 3 : 0;
                const auto HashPart = [](uint32 Part) { LogicalDigest ^= Part; LogicalDigest *= 1099511628211ULL; };
                HashPart(static_cast<uint32>(Config.GetInitialSeed())); HashPart(static_cast<uint32>(Outcome.GetInitialSeed()));
                for (TCHAR Character : Types[R].ToString()) HashPart(static_cast<uint32>(Character));
                HashPart(0); for (TCHAR Character : Resolved.ToString()) HashPart(static_cast<uint32>(Character));
                HashPart(0); HashPart(static_cast<uint32>(Result)); HashPart(static_cast<uint32>(Reward));
                Sum[R]+=Reward; SumSq[R]+=double(Reward)*Reward; Threats[R]+=Result==2 ? 1 : 0;
                if (Sample<12)
                    Signatures.Add(MakeShared<FJsonValueString>(FString::Printf(TEXT("%d/%s/%s/%s/%d/%d"), Sample,
                        *C->RegionRules[R]->RegionID.ToString(), *Types[R].ToString(), *Resolved.ToString(), Result, Reward)));
            }
        }
        double Mean[3], Error[3], Rate[3], RateError[3];
        for (int32 R=0; R<3; ++R)
        {
            Mean[R]=Sum[R]/N;
            const double Variance=(SumSq[R]-Sum[R]*Sum[R]/N)/(N-1);
            Error[R]=1.96*FMath::Sqrt(Variance/N);
            Rate[R]=double(Threats[R])/N; RateError[R]=1.96*FMath::Sqrt(Rate[R]*(1.-Rate[R])/N);
            auto Entry=MakeShared<FJsonObject>();
            Entry->SetStringField(TEXT("region"), C->RegionRules[R]->RegionID.ToString());
            Entry->SetNumberField(TEXT("open_count"), N); Entry->SetNumberField(TEXT("reward"), Sum[R]);
            Entry->SetNumberField(TEXT("reward_mean"), Mean[R]); Entry->SetNumberField(TEXT("reward_variance"), Variance);
            Entry->SetNumberField(TEXT("reward_ci95_half"), Error[R]); Entry->SetNumberField(TEXT("threat"), Threats[R]);
            Entry->SetNumberField(TEXT("threat_rate"), Rate[R]); Entry->SetNumberField(TEXT("threat_ci95_half"), RateError[R]);
            TArray<TSharedPtr<FJsonValue>> TypeCounts, HiddenCounts;
            for (int32 I=0; I<3; ++I)
            { TypeCounts.Add(MakeShared<FJsonValueNumber>(TypesSeen[R][I])); HiddenCounts.Add(MakeShared<FJsonValueNumber>(HiddenSeen[R][I])); }
            Entry->SetArrayField(TEXT("public_type_counts"),TypeCounts); Entry->SetArrayField(TEXT("hidden_profile_counts"),HiddenCounts);
            Samples.Add(MakeShared<FJsonValueObject>(Entry));
            if (!Check(TEXT("Every region retains all three public and hidden types"),
                TypesSeen[R][0]>0 && TypesSeen[R][1]>0 && TypesSeen[R][2]>0 && HiddenSeen[R][0]>0 && HiddenSeen[R][1]>0 && HiddenSeen[R][2]>0)) return false;
        }
        if (!Check(TEXT("A/B/C mean face rewards have ordered nonoverlapping 95% intervals"),
            Mean[0]+Error[0]<Mean[1]-Error[1] && Mean[1]+Error[1]<Mean[2]-Error[2])) return false;
        if (!Check(TEXT("A/B/C threat rates have ordered nonoverlapping 95% intervals"),
            Rate[0]+RateError[0]<Rate[1]-RateError[1] && Rate[1]+RateError[1]<Rate[2]-RateError[2])) return false;

        auto Invalid=DuplicateObject<UAnomalyRegionDefinition>(C->RegionRules[0],C);
        Invalid->BoxTypeWeights={1.,0.,0.};
        if (!Check(TEXT("Single-type region rejected"),!Invalid->Validate(Reason))) return false;
        Invalid->BoxTypeWeights={1.,-1.,1.};
        if (!Check(TEXT("Negative weights rejected"),!Invalid->Validate(Reason))) return false;
        Invalid->BoxTypeWeights={1.,std::numeric_limits<double>::quiet_NaN(),1.};
        if (!Check(TEXT("Nonfinite weights rejected"),!Invalid->Validate(Reason))) return false;
        Invalid->BoxTypeWeights={1.,1.,0.}; Invalid->HiddenProfileWeights={0.,0.,0.};
        if (!Check(TEXT("Zero hidden mass rejected"),!Invalid->Validate(Reason))) return false;
        Invalid->HiddenProfileWeights={1.,1.,1.}; Invalid->AllowedAnomalies={FName(TEXT("NotImplemented"))};
        if (!Check(TEXT("Unimplemented anomaly rejected"),!Invalid->Validate(Reason))) return false;
        Invalid->AllowedAnomalies={FName(TEXT("Chaser"))}; Invalid->RewardScale=MAX_dbl;
        auto Copy=DuplicateObject<UAnomalyBoxDefinition>(Definitions[TEXT("Safe")],C);
        if (!Check(TEXT("Reward overflow rejected"),!Invalid->ApplyTo(*Copy,Reason))) return false;
        Invalid->RewardScale=1.; Invalid->HighValueWeight=0.; Invalid->TrashWeight=0.; Invalid->ThreatWeight=0.;
        if (!Check(TEXT("Zero outcome multipliers rejected"),!Invalid->Validate(Reason))) return false;
        Invalid->HighValueWeight=1.; Invalid->ScanErrorAdd=1.;
        if (!Check(TEXT("Legal zero probabilities and scan clamp"),Invalid->ApplyTo(*Copy,Reason)
            && Copy->ThreatChance==0. && Copy->TrashChance==0. && Copy->SelectOutcome(0.)==0 && Copy->ScanProbabilityError==1.)) return false;
        FRandomStream ZeroStream(5);
        for (int32 I=0; I<1000; ++I)
            if (Invalid->DrawBoxType(ZeroStream)==TEXT("Unknown")) return Check(TEXT("Zero-weight type never sampled"),false);
        return Check(TEXT("Zero-weight type never sampled"),true);
    }

    bool Fixtures(AAnomalyRoundCoordinator* C)
    {
        const auto Original=C->CandidateBoxes; const auto Stats=C->RegionStats;
        const auto Wallet=UGameplayStatics::GetPlayerCharacter(C,0)->FindComponentByClass<UAnomalyWalletComponent>();
        const int32 Money=Wallet->Money;
        for (auto Region:C->RegionRules)
        {
            TArray<AAnomalyBoxActor*> Pair;
            for (int32 I=0; I<2; ++I)
            {
                const FTransform Transform(FVector(10000+I*300,10000,50));
                auto Box=C->GetWorld()->SpawnActorDeferred<AAnomalyBoxActor>(C->BoxClass,Transform,C,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
                Box->RegionDefinition=Region; Box->DefinitionID=TEXT("Unknown"); Box->bUseFixedSeeds=true;
                Box->ConfigurationSeed=26002; Box->OutcomeSeed=26003; Box->RoundId=C->RoundId; Box->SetCoordinator(C);
                Box->FinishSpawning(Transform); Pair.Add(Box);
            }
            C->CandidateBoxes={Pair[0],Pair[1],Original[0]};
            const int32 Seed=FAnomalyRegionProbe::OutcomeSeed(*Pair[0]);
            const FName Profile=Pair[0]->ResolvedDefinitionID;
            const double BaseThreat=Pair[0]->Definitions[Profile]->ThreatChance;
            if (!Check(TEXT("Fixed region/box/seed gives identical valid hidden profile and adjusted data"),Pair[0]->bDefinitionValid && Pair[1]->bDefinitionValid
                && Pair[0]->ResolvedDefinitionID==Pair[1]->ResolvedDefinitionID
                && Pair[0]->DefinitionAsset->ThreatChance==Pair[1]->DefinitionAsset->ThreatChance
                && Pair[0]->DefinitionAsset!=Pair[0]->Definitions[Profile])) return false;
            for (int32 I=0; I<3; ++I)
            {
                FAnomalyScanReading Reading;
                if (!Check(TEXT("Live candidate completes scan"),Pair[0]->CompleteScan(static_cast<EAnomalyEquipment>(I),Reading) && Reading.bScanned)) return false;
            }
            const int32 Scans=C->RegionStats[Region->RegionID].ScanCount;
            FAnomalyScanReading Cached;
            Pair[0]->CompleteScan(EAnomalyEquipment::MetalDetector,Cached); Pair[0]->InitializeDefinition();
            if (!Check(TEXT("Cache reread/init consumes no outcome RNG, reward, money or extra scan count"),
                Seed==FAnomalyRegionProbe::OutcomeSeed(*Pair[0]) && Seed==FAnomalyRegionProbe::OutcomeSeed(*Pair[1])
                && Pair[0]->HighValueAmount==0 && !Pair[0]->bOpened && !Pair[0]->bResolved
                && Pair[0]->ResolvedDefinitionID==Profile && Wallet->Money==Money && C->RegionStats[Region->RegionID].ScanCount==Scans
                && Pair[0]->Definitions[Profile]->ThreatChance==BaseThreat)) return false;
            auto Sig=MakeShared<FJsonObject>(); Sig->SetStringField(TEXT("region"),Region->RegionID.ToString());
            Sig->SetStringField(TEXT("hidden"),Profile.ToString()); Sig->SetNumberField(TEXT("seed_after_scan"),Seed);
            Sig->SetNumberField(TEXT("threat"),Pair[0]->DefinitionAsset->ThreatChance); Sig->SetNumberField(TEXT("high"),Pair[0]->DefinitionAsset->HighValueChance);
            Sig->SetNumberField(TEXT("value_low"),Cached.ValueMin); Sig->SetNumberField(TEXT("value_high"),Cached.ValueMax);
            Signatures.Add(MakeShared<FJsonValueObject>(Sig));
            ++Pair[0]->RoundId;
            if (!Check(TEXT("Stale round rejects scan"),!Pair[0]->CompleteScan(EAnomalyEquipment::BioDetector,Cached))) return false;
            --Pair[0]->RoundId; Pair[0]->LockUnselected();
            if (!Check(TEXT("Locked box rejects cached scan and selection"),!Pair[0]->CanScan() && !Pair[0]->CompleteScan(EAnomalyEquipment::MetalDetector,Cached))) return false;
            C->CandidateBoxes=Original;
            if (!Check(TEXT("Foreign fixture cannot select current round"),!C->TryLockSelection(Pair[1]))) return false;
            for (auto Box:Pair) Box->Destroy();
        }
        C->RegionStats=Stats;
        return true;
    }
    void Tick(UWorld* World,ELevelTick,float)
    {
        if (Finished || !World || !World->IsGameWorld() || !World->HasBegunPlay() || World->GetTimeSeconds()<NextTime) return;
        AAnomalyRoundCoordinator* C=nullptr;
        for (TActorIterator<AAnomalyRoundCoordinator> It(World);It;++It) { C=*It; break; }
        if (C && C->IsPreparing()) C->StartPreparedRun(); // T26 probability fixture, not an input test.
        if (!C || C->CandidateBoxes.Num()!=3) return;
        auto Player=UGameplayStatics::GetPlayerCharacter(World,0);
        if (!Player) return;
        if (Stage==0)
        {
            if (!Check(TEXT("Production map uses three explicitly mapped region contexts"),C->bUseRegionRules && C->RegionRules.Num()==3
                && C->CandidateBoxes[0]->RegionDefinition->RegionID==TEXT("A") && C->CandidateBoxes[1]->RegionDefinition->RegionID==TEXT("B")
                && C->CandidateBoxes[2]->RegionDefinition->RegionID==TEXT("C"))) return;
            if (!Statistics(C) || !Fixtures(C)) return;
            Stage=1;
        }
        if (Stage>=1 && Stage<=3)
        {
            const auto Box=C->CandidateBoxes[Stage-1];
            Player->SetActorLocation(Box->GetActorLocation()+FVector(0,-180,48),false);
            Player->GetCharacterMovement()->StopMovementImmediately();
            auto Camera=Player->FindComponentByClass<UCameraComponent>();
            Player->GetController()->SetControlRotation((Box->GetActorLocation()+FVector(0,0,35)-Camera->GetComponentLocation()).Rotation());
            Stage+=10; NextTime=World->GetTimeSeconds()+.5f; return;
        }
        if (Stage>=11 && Stage<=13)
        {
            TArray<UUserWidget*> Widgets;
            UWidgetBlueprintLibrary::GetAllWidgetsOfClass(World,Widgets,UAnomalyExplorationWidget::StaticClass(),true);
            auto Widget=Widgets.Num()==1 ? Widgets[0] : nullptr;
            auto Text=Widget && Widget->WidgetTree ? Widget->WidgetTree->FindWidget<UTextBlock>(TEXT("RegionText")) : nullptr;
            const auto Region=C->RegionRules[Stage-11];
            if (!Check(TEXT("Focus HUD shows public region name/description without hidden profile"),Text
                && Text->GetText().ToString()==Region->DisplayName.ToString()+TEXT("\n")+Region->Description.ToString()
                && !Text->GetText().ToString().Contains(TEXT("Unknown")))) return;
            if (!FParse::Param(FCommandLine::Get(),TEXT("nullrhi")))
            {
                const FVector2D Size=Text->GetCachedGeometry().GetLocalSize();
                if (!Check(TEXT("Region HUD has room for three Chinese lines"),Size.X>=640 && Size.Y>=110)) return;
                FScreenshotRequest::RequestScreenshot(Output/(Region->RegionID.ToString()+TEXT("_region.png")),true,false,false,FIntRect(),true);
            }
            Stage=Stage-10+1; NextTime=World->GetTimeSeconds()+.5f; return;
        }
        if (Stage==4) Finish(true);
    }
}
void RegisterAnomalyRegionSmoke()
{
    if (!FParse::Param(FCommandLine::Get(),TEXT("AnomalyT26Smoke"))) return;
    FParse::Value(FCommandLine::Get(),TEXT("T26Evidence="),T26Smoke::Output);
    if (T26Smoke::Output.IsEmpty()) T26Smoke::Output=FPaths::ProjectSavedDir()/TEXT("V04/T26/Runtime");
    T26Smoke::Handle=FWorldDelegates::OnWorldTickStart.AddStatic(&T26Smoke::Tick);
}
void UnregisterAnomalyRegionSmoke() { FWorldDelegates::OnWorldTickStart.Remove(T26Smoke::Handle); }
#endif
