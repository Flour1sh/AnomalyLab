#include "CoreMinimal.h"
#if !UE_BUILD_SHIPPING
#include "AnomalyBalanceConfig.h"
#include "AnomalyBoxDefinition.h"
#include "AnomalyBoxActor.h"
#include "AnomalyRoundCoordinator.h"
#include "AnomalyRegionDefinition.h"
#include "AnomalyObserverConfig.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include <limits>

namespace BalanceSmoke
{
    FDelegateHandle Handle; bool Finished=false; FString Output;
    TArray<TSharedPtr<FJsonValue>> Checks,Results;
    uint64 Digest=14695981039346656037ULL;
    void Hash(uint32 N) { Digest^=N; Digest*=1099511628211ULL; }
    bool Check(const TCHAR* Name,bool Pass)
    {
        auto R=MakeShared<FJsonObject>(); R->SetStringField(TEXT("check"),Name); R->SetBoolField(TEXT("passed"),Pass); Checks.Add(MakeShared<FJsonValueObject>(R));
        UE_LOG(LogTemp,Display,TEXT("[BalanceSmoke] %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Name); return Pass;
    }
    void Finish(bool Pass)
    {
        Finished=true; auto R=MakeShared<FJsonObject>(); R->SetStringField(TEXT("status"),Pass?TEXT("PASS"):TEXT("FAIL"));
        R->SetStringField(TEXT("scope"),TEXT("Production configuration/outcome simulation; conditional mortality is an explicit sensitivity assumption, not observed human or AI survival. No travel time, scan policy or decoy benefit is modeled."));
        R->SetNumberField(TEXT("seed"),31001);R->SetNumberField(TEXT("runs_per_cell"),5000);R->SetNumberField(TEXT("human_samples"),0);
        R->SetStringField(TEXT("logical_digest"),FString::Printf(TEXT("%016llx"),Digest));R->SetArrayField(TEXT("checks"),Checks);R->SetArrayField(TEXT("cells"),Results);
        FString Json;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Json));IFileManager::Get().MakeDirectory(*Output,true);
        const bool Saved=FFileHelper::SaveStringToFile(Json,*(Output/TEXT("report.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
        FPlatformMisc::RequestExitWithStatus(false,Pass&&Saved?0:1);
    }
    bool Run(AAnomalyRoundCoordinator* C)
    {
        FString Why;auto Config=C->BalanceConfig;
        if (!Check(TEXT("Production balance config is valid and opt-in Explorer only"),Config && Config->Validate(Why) && C->MaxThreats==2)) return false;
        if (!Check(TEXT("Round one exact identity and round two small growth"),Config->ThreatMultiplier(1)==1. && Config->RewardMultiplier(1)==1.
            && FMath::IsNearlyEqual(Config->ThreatMultiplier(2),1.03) && FMath::IsNearlyEqual(Config->RewardMultiplier(2),1.05))) return false;
        if (!Check(TEXT("Extreme rounds remain bounded without signed overflow"),Config->ThreatMultiplier(MAX_int32)==Config->ThreatCap
            && Config->RewardMultiplier(MAX_int32)==Config->RewardCap && Config->ThreatMultiplier(MIN_int32)==1.)) return false;
        auto Bad=DuplicateObject<UAnomalyBalanceConfig>(Config,C);Bad->ThreatPerRound=std::numeric_limits<double>::infinity();
        if (!Check(TEXT("Nonfinite growth rejected"),!Bad->Validate(Why))) return false;
        Bad->ThreatPerRound=.03;Bad->RewardCap=2.;if (!Check(TEXT("Excessive cap rejected"),!Bad->Validate(Why))) return false;
        const auto Defaults=C->BoxClass->GetDefaultObject<AAnomalyBoxActor>();
        auto Test=DuplicateObject<UAnomalyBoxDefinition>(Defaults->Definitions[TEXT("Safe")],C);
        const int32 OldMin=Test->ValueMin;const double OldThreat=Test->ThreatChance;
        if (!Check(TEXT("Invalid round rejects without changing definition"),!Config->ApplyTo(*Test,0,Why) && Test->ValueMin==OldMin && Test->ThreatChance==OldThreat)) return false;
        Test->ValueMax=MAX_int32-1;Test->ValueMin=MAX_int32-2;
        if (!Check(TEXT("Reward overflow rejected before mutation"),!Config->ApplyTo(*Test,2,Why) && Test->ValueMax==MAX_int32-1)) return false;
        if (!Check(TEXT("Real preparation applies resources and spawns three first-round copies"),C->StartPreparedRun() && C->CandidateBoxes.Num()==3)) return false;
        auto First=C->CurrentBox;
        if (!Check(TEXT("Live box receives actual production curve reference"),First->BalanceConfig==Config && First->RoundId==1)) return false;
        auto Expected=DuplicateObject<UAnomalyBoxDefinition>(Defaults->Definitions[TEXT("Risky")],C);
        if (!C->RegionRules[2]->ApplyTo(*Expected,Why) || !Config->ApplyTo(*Expected,2,Why)) return false;
        auto Live=C->GetWorld()->SpawnActorDeferred<AAnomalyBoxActor>(C->BoxClass,FTransform(FVector(0,0,50)),C,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        Live->bExplorationSpawn=true;Live->DefinitionID=TEXT("Risky");Live->RegionDefinition=C->RegionRules[2];Live->BalanceConfig=Config;Live->RoundId=2;
        Live->FinishSpawning(FTransform(FVector(0,0,50)));
        if (!Check(TEXT("Real deferred round-two box matches normalized model without shared mutation"),Live->bDefinitionValid
            && Live->DefinitionAsset->ValueMax==Expected->ValueMax && Live->DefinitionAsset->ThreatChance==Expected->ThreatChance
            && Defaults->Definitions[TEXT("Risky")]->ValueMax==6000 && Defaults->Definitions[TEXT("Risky")]->ThreatChance==.35)) return false;
        Live->Destroy();
        TArray<TArray<TMap<FName,UAnomalyBoxDefinition*>>> Cache;
        for (int32 Round=0;Round<8;++Round)
        {
            TArray<TMap<FName,UAnomalyBoxDefinition*>> Regions;
            for (auto Region:C->RegionRules)
            {
                TMap<FName,UAnomalyBoxDefinition*> Data;
                for (const auto& Pair:Defaults->Definitions)
                {
                    auto D=DuplicateObject<UAnomalyBoxDefinition>(Pair.Value,C);
                    if (!Region->ApplyTo(*D,Why) || (Round>0 && !Config->ApplyTo(*D,Round,Why))) return false;
                    Data.Add(Pair.Key,D);
                }
                Regions.Add(Data);
            }
            Cache.Add(Regions);
        }
        const double Mortality[]={0.,.25,.75,1.};
        const TCHAR* Policies[]={TEXT("A_low_risk"),TEXT("C_high_reward"),TEXT("random_region")};
        for (int32 Curve=0;Curve<2;++Curve) for (int32 Capacity=4;Capacity<=5;++Capacity)
        for (double Death:Mortality) for (int32 Policy=0;Policy<3;++Policy)
        {
            int32 Deaths=0,ContainedTotal=0,RoundTotal=0,ThreatTotal=0,ObserverTotal=0,Trash=0,High=0,Choices[3]={};
            double Payout=0.,PayoutSq=0.;TArray<int32> Values;
            for (int32 N=0;N<5000;++N)
            {
                FRandomStream ChoicesStream(31001+N),Agent((31001+N)^0x48554D31);
                int32 Items=0,Contained=0,Carry=0,Round=0;bool Died=false;
                while (Items<Capacity && Contained<2)
                {
                    ++Round;if (Round>7) return Check(TEXT("Simulated stop conditions bound rounds"),false);
                    TArray<FName> Types;if (!UAnomalyRegionDefinition::DrawChoices(C->RegionRules,ChoicesStream,Types,Why)) return false;
                    const int32 Pick=Policy==0?0:Policy==1?2:Agent.RandRange(0,2);++Choices[Pick];
                    for (int32 R=0;R<3;++R)
                    {
                        FRandomStream Configuration(static_cast<int32>(ChoicesStream.GetUnsignedInt()));
                        FRandomStream Outcome(static_cast<int32>(ChoicesStream.GetUnsignedInt()));
                        const int32 TypeSeed=Configuration.GetInitialSeed();
                        const FName ID=Types[R]==TEXT("Unknown")?C->RegionRules[R]->DrawHiddenProfile(Configuration):Types[R];
                        if (R!=Pick) continue;
                        const auto D=Cache[Curve?Round:0][R][ID];const int32 Result=D->SelectOutcome(Outcome.FRand());
                        Hash(TypeSeed);Hash(Result);
                        if (Result==2)
                        {
                            ++ThreatTotal;FRandomStream Encounter(TypeSeed^0x4F425331);
                            if (Encounter.FRand()<C->ObserverConfig->MixedPoolWeight) ++ObserverTotal;
                            if (Agent.FRand()<Death) { Died=true;break; }++Contained;
                        }
                        else { const int32 Value=Result==0?Outcome.RandRange(D->ValueMin,D->ValueMax):3;Hash(Value);Carry+=Value;++Items;High+=Result==0;Trash+=Result==1; }
                    }
                    if (Died) break;
                }
                const int32 Value=Died?0:Carry;Hash(Value);Values.Add(Value);Payout+=Value;PayoutSq+=double(Value)*Value;
                Deaths+=Died;ContainedTotal+=Contained;RoundTotal+=Round;
            }
            Values.Sort();auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("policy"),Policies[Policy]);
            R->SetBoolField(TEXT("curve_enabled"),Curve!=0);R->SetNumberField(TEXT("capacity"),Capacity);R->SetNumberField(TEXT("assumed_death_given_threat"),Death);
            R->SetNumberField(TEXT("runs"),5000);R->SetNumberField(TEXT("modeled_deaths"),Deaths);R->SetNumberField(TEXT("modeled_survival_rate"),1.-Deaths/5000.);
            R->SetNumberField(TEXT("payout_mean"),Payout/5000.);R->SetNumberField(TEXT("payout_ci95_half"),1.96*FMath::Sqrt((PayoutSq-Payout*Payout/5000.)/4999./5000.));
            R->SetNumberField(TEXT("payout_median"),Values[2500]);R->SetNumberField(TEXT("payout_p95"),Values[4750]);
            R->SetNumberField(TEXT("rounds_mean"),RoundTotal/5000.);R->SetNumberField(TEXT("modeled_containments_mean"),ContainedTotal/5000.);
            R->SetNumberField(TEXT("threats"),ThreatTotal);R->SetNumberField(TEXT("observers"),ObserverTotal);R->SetNumberField(TEXT("trash_drops"),Trash);R->SetNumberField(TEXT("high_drops"),High);
            TArray<TSharedPtr<FJsonValue>> Counts;for (int32 Count:Choices) Counts.Add(MakeShared<FJsonValueNumber>(Count));R->SetArrayField(TEXT("region_opens"),Counts);
            Results.Add(MakeShared<FJsonValueObject>(R));
        }
        return Check(TEXT("48 sensitivity cells, 240000 configuration simulations completed"),Results.Num()==48);
    }
    void Tick(UWorld* W,ELevelTick,float)
    {
        if (Finished || !W || !W->IsGameWorld() || !W->HasBegunPlay() || W->GetTimeSeconds()<2) return;
        for (TActorIterator<AAnomalyRoundCoordinator> It(W);It;++It) { Finish(Run(*It));return; }
    }
}
void RegisterAnomalyBalanceSmoke()
{
    if (!FParse::Param(FCommandLine::Get(),TEXT("AnomalyBalanceSmoke"))) return;
    FParse::Value(FCommandLine::Get(),TEXT("T31Evidence="),BalanceSmoke::Output);
    if (BalanceSmoke::Output.IsEmpty()) BalanceSmoke::Output=FPaths::ProjectSavedDir()/TEXT("V04/T31/Runtime");
    BalanceSmoke::Handle=FWorldDelegates::OnWorldTickStart.AddStatic(&BalanceSmoke::Tick);
}
void UnregisterAnomalyBalanceSmoke() { FWorldDelegates::OnWorldTickStart.Remove(BalanceSmoke::Handle); }
#endif
