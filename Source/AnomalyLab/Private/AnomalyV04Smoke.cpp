// Explicit opt-in Development fixtures. Production never installs a test driver.
#include "CoreMinimal.h"
#if !UE_BUILD_SHIPPING
#include "AnomalyRoundCoordinator.h"
#include "AnomalyBoxActor.h"
#include "AnomalyScannerComponent.h"
#include "AnomalyProgressionSubsystem.h"
#include "AnomalyProgressionConfig.h"
#include "AnomalyMetaSaveGame.h"
#include "AnomalyInventoryComponent.h"
#include "AnomalyWorldPickup.h"
#include "AnomalyThreatCharacter.h"
#include "AnomalyWalletComponent.h"
#include "Engine/GameInstance.h"
#include "Components/StaticMeshComponent.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "InputCoreTypes.h"
#include "InputKeyEventArgs.h"
#include "HAL/PlatformTime.h"
#include "UnrealClient.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Character.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

struct FAnomalyV04Probe
{
    static void Reset(UAnomalyScannerComponent* S, int32 Bonus=0) { S->InitializeRunResources(Bonus); }
    static void Charges(UAnomalyScannerComponent* S, int32 N) { S->Remaining={N,N,N}; }
    static void Money(UAnomalyProgressionSubsystem* P,int64 N) { P->Progress.Currency=N; }
    static void Precision(UAnomalyScannerComponent* S,float N) { S->PrecisionReduction=N; }
    static bool Store(UAnomalyInventoryComponent* I,AAnomalyWorldPickup* L) { return I->TryStore(L); }
    static void Clear(UAnomalyInventoryComponent* I) { I->Items.Empty(); I->ClaimedIds.Empty(); }
    static AActor* Decoy(AAnomalyRoundCoordinator* C) { return C->DecoySource; }
    static int32 Selection(AAnomalyRoundCoordinator* C) { return C->ShopSelection; }
    static FString Message(AAnomalyRoundCoordinator* C) { return C->ShopMessage; }
    static void Fault(UAnomalyProgressionSubsystem* P,int32 N) { P->SaveFault=N; }
    static void Sanitize(FAnomalyMetaProgress& M) { UAnomalyProgressionSubsystem::Sanitize(M,nullptr); }
    static bool Persist(UAnomalyProgressionSubsystem* P,const FAnomalyMetaProgress& M,FString& Why) { return P->Commit(M,Why); }
    static void Terminal(AAnomalyRoundCoordinator* C,EAnomalyRunEndReason Why)
    { C->NativeState=3; C->RunEndReason=Why; C->bExtractionAuthorized=Why==EAnomalyRunEndReason::CashedOut; }
    static void Prep(AAnomalyRoundCoordinator* C) { C->NativeState=0; C->RunEndReason=EAnomalyRunEndReason::None; C->bExtractionAuthorized=false; }
};
namespace V04Smoke
{
    FDelegateHandle Handle;
    FString Output;
    bool Finished=false;
    FString Task;
    FString SaveCase,SlotPath;
    int32 Stage=0;
    float NextTime=2.f;
    TWeakObjectPtr<AAnomalyThreatCharacter> LuredThreat;
    float InitialDistance=0;
    TArray<TSharedPtr<FJsonValue>> Checks;
    bool Check(const TCHAR* Name, bool Pass)
    {
        auto Entry=MakeShared<FJsonObject>(); Entry->SetStringField(TEXT("check"),Name); Entry->SetBoolField(TEXT("passed"),Pass);
        Checks.Add(MakeShared<FJsonValueObject>(Entry));
        UE_LOG(LogTemp,Display,TEXT("[V04Smoke] %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Name);
        return Pass;
    }
    void Finish(bool Pass)
    {
        Finished=true;
        auto Report=MakeShared<FJsonObject>(); Report->SetStringField(TEXT("status"),Pass?TEXT("PASS"):TEXT("FAIL"));
        Report->SetStringField(TEXT("scope"),TEXT("Native transactional boundary fixtures. Real held-input cancellation paths are separately covered by V03 regression. Human samples: 0."));
        Report->SetArrayField(TEXT("checks"),Checks);
        Report->SetStringField(TEXT("save_path"),SlotPath);
        FString Json; FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
        IFileManager::Get().MakeDirectory(*Output,true);
        const bool Saved=FFileHelper::SaveStringToFile(Json,*(Output/TEXT("report.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
        FPlatformMisc::RequestExitWithStatus(false,Pass&&Saved?0:1);
    }
    bool ScanFixtures(AAnomalyRoundCoordinator* C)
    {
        auto S=UGameplayStatics::GetPlayerCharacter(C,0)->FindComponentByClass<UAnomalyScannerComponent>();
        if (!Check(TEXT("Exploration charge authority and configurable 3/3/3 defaults"),S && S->UsesCharges()
            && S->GetRemaining(EAnomalyEquipment::MetalDetector)==3 && S->GetMaximum(EAnomalyEquipment::MatterAnalyzer)==3)) return false;
        const auto Original=C->CandidateBoxes;
        TArray<AAnomalyBoxActor*> Boxes;
        for (int32 I=0; I<3; ++I)
        {
            const FTransform T(FVector(10000+I*300,10000,50));
            auto B=C->GetWorld()->SpawnActorDeferred<AAnomalyBoxActor>(C->BoxClass,T,C,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
            B->RoundId=C->RoundId; B->DefinitionID=TEXT("Safe"); B->SetCoordinator(C); B->FinishSpawning(T); Boxes.Add(B);
        }
        C->CandidateBoxes={Boxes[0],Boxes[1],Boxes[2]};
        FAnomalyScanReading R;
        S->CancelScan();
        if (!Check(TEXT("Cancellation alone never charges"),S->GetRemaining(EAnomalyEquipment::MetalDetector)==3)) return false;
        FAnomalyV04Probe::Charges(S,1);
        if (!Check(TEXT("One charge commits valid reading and consumes exactly one"),Boxes[0]->CompleteScan(EAnomalyEquipment::MetalDetector,R)
            && R.bScanned && S->GetRemaining(EAnomalyEquipment::MetalDetector)==0)) return false;
        for (int32 I=0; I<20; ++I)
            if (!Boxes[0]->CompleteScan(EAnomalyEquipment::MetalDetector,R)) return Check(TEXT("Duplicate completion cache"),false);
        if (!Check(TEXT("Twenty duplicate completions are free at zero"),S->GetRemaining(EAnomalyEquipment::MetalDetector)==0 && R.bScanned)) return false;
        if (!Check(TEXT("Zero charges reject different box without cache or negative balance"),!Boxes[1]->CompleteScan(EAnomalyEquipment::MetalDetector,R)
            && !R.bScanned && !Boxes[1]->GetCachedReading(EAnomalyEquipment::MetalDetector).bScanned && S->GetRemaining(EAnomalyEquipment::MetalDetector)==0)) return false;
        if (!Check(TEXT("Instrument budgets independent"),Boxes[1]->CompleteScan(EAnomalyEquipment::BioDetector,R)
            && S->GetRemaining(EAnomalyEquipment::BioDetector)==0 && S->GetRemaining(EAnomalyEquipment::MatterAnalyzer)==1)) return false;
        ++Boxes[2]->RoundId;
        if (!Check(TEXT("Stale round callback rejects without charge"),!Boxes[2]->CompleteScan(EAnomalyEquipment::MatterAnalyzer,R)
            && S->GetRemaining(EAnomalyEquipment::MatterAnalyzer)==1)) return false;
        --Boxes[2]->RoundId; Boxes[2]->LockUnselected();
        if (!Check(TEXT("Locked target rejects without charge"),!Boxes[2]->CompleteScan(EAnomalyEquipment::MatterAnalyzer,R)
            && S->GetRemaining(EAnomalyEquipment::MatterAnalyzer)==1)) return false;
        FAnomalyV04Probe::Reset(S,1);
        if (!Check(TEXT("New run applies capacity bonus to each instrument"),S->GetRemaining(EAnomalyEquipment::MetalDetector)==4
            && S->GetRemaining(EAnomalyEquipment::BioDetector)==4 && S->GetRemaining(EAnomalyEquipment::MatterAnalyzer)==4)) return false;
        FAnomalyV04Probe::Reset(S);
        if (!Check(TEXT("Fresh run resets all charges and scan progress"),S->GetRemaining(EAnomalyEquipment::MetalDetector)==3 && S->Progress==0)) return false;
        C->CandidateBoxes=Original; for (auto B:Boxes) B->Destroy();
        return true;
    }
    void Shot(const TCHAR* Name)
    {
        if (!FParse::Param(FCommandLine::Get(),TEXT("nullrhi")))
            FScreenshotRequest::RequestScreenshot(Output/(FString(Name)+TEXT(".png")),true,false,false,FIntRect(),true);
    }
    void Key(ACharacter* Player,FKey Key,bool Pressed)
    { Player->GetController<APlayerController>()->InputKey(FInputKeyEventArgs(nullptr,INPUTDEVICEID_NONE,Key,Pressed?IE_Pressed:IE_Released,Pressed?1.f:0.f,false,FPlatformTime::Cycles64())); }
    bool ShopFixtures(AAnomalyRoundCoordinator* C)
    {
        auto P=C->GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>();
        FString Why; auto Bad=NewObject<UAnomalyProgressionConfig>(); Bad->Prices[0]=0;
        if (!Check(TEXT("Invalid zero price is rejected"),!Bad->Validate(Why))) return false;
        if (!Check(TEXT("Preparation has zero permanent balance, no boxes, no extraction"),C->IsPreparing() && P->GetProgress().Currency==0
            && C->CandidateBoxes.IsEmpty() && !C->ConfirmExtraction(UGameplayStatics::GetPlayerCharacter(C,0)))) return false;
        const auto Id=FGuid::NewGuid();
        if (!Check(TEXT("Insufficient balance changes nothing"),!C->PurchaseProduct(0,P->GetProgress().Revision,Id) && P->GetProgress().Currency==0)) return false;
        FAnomalyV04Probe::Money(P,20000); const int32 Revision=P->GetProgress().Revision;
        if (!Check(TEXT("Purchase debits configured price once"),C->PurchaseProduct(0,Revision,Id) && P->GetProgress().Currency==19000 && P->GetProgress().BatteryLevel==1)) return false;
        if (!Check(TEXT("Fast same-frame UI purchase rejected"),!C->PurchaseProduct(1,P->GetProgress().Revision,FGuid::NewGuid()))) return false;
        if (!Check(TEXT("Duplicate request and stale revision rejected"),!P->Purchase(C,0,P->GetProgress().Revision,Id,Why)
            && !P->Purchase(C,0,Revision,FGuid::NewGuid(),Why) && P->GetProgress().Currency==19000)) return false;
        if (!Check(TEXT("Battery max level enforced"),P->Purchase(C,0,P->GetProgress().Revision,FGuid::NewGuid(),Why)
            && !P->Purchase(C,0,P->GetProgress().Revision,FGuid::NewGuid(),Why) && P->GetProgress().BatteryLevel==2)) return false;
        if (!Check(TEXT("Precision bounded upgrade, backpack and next-run decoy purchased"),P->Purchase(C,1,P->GetProgress().Revision,FGuid::NewGuid(),Why)
            && P->Purchase(C,1,P->GetProgress().Revision,FGuid::NewGuid(),Why) && P->Purchase(C,2,P->GetProgress().Revision,FGuid::NewGuid(),Why)
            && P->Purchase(C,3,P->GetProgress().Revision,FGuid::NewGuid(),Why) && P->GetProgress().Currency==11900)) return false;
        if (!Check(TEXT("Backpack/decoy caps reject repeats"),!P->Purchase(C,2,P->GetProgress().Revision,FGuid::NewGuid(),Why)
            && !P->Purchase(C,3,P->GetProgress().Revision,FGuid::NewGuid(),Why))) return false;
        return true;
    }
    bool EquipmentFixtures(AAnomalyRoundCoordinator* C)
    {
        auto Player=UGameplayStatics::GetPlayerCharacter(C,0);
        auto S=Player->FindComponentByClass<UAnomalyScannerComponent>();
        auto P=C->GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>(); FString Why;
        if (!Check(TEXT("New run applies 5/5/5 charges, bounded precision, five slots and exactly one decoy"),S->GetRemaining(EAnomalyEquipment::MetalDetector)==5
            && S->GetRemaining(EAnomalyEquipment::BioDetector)==5 && S->GetRemaining(EAnomalyEquipment::MatterAnalyzer)==5
            && S->GetPrecisionReduction()==.5f && C->Inventory->GetCapacity()==5 && C->DecoysRemaining==1 && P->GetProgress().StoredDecoys==0)) return false;
        if (!Check(TEXT("Run start idempotent and shop closed in run"),!C->StartPreparedRun() && !P->Purchase(C,3,P->GetProgress().Revision,FGuid::NewGuid(),Why))) return false;
        FAnomalyV04Probe::Reset(S);
        if (!ScanFixtures(C)) return false;
        FAnomalyV04Probe::Reset(S,2);
        const auto Original=C->CandidateBoxes;
        TArray<AAnomalyBoxActor*> Pair;
        for (int32 I=0;I<2;++I)
        {
            const FTransform T(FVector(10000+I*300,10000,50));
            auto B=C->GetWorld()->SpawnActorDeferred<AAnomalyBoxActor>(C->BoxClass,T,C,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
            B->RoundId=C->RoundId; B->DefinitionID=TEXT("Risky"); B->bExplorationSpawn=true; B->SetCoordinator(C); B->FinishSpawning(T); Pair.Add(B);
        }
        C->CandidateBoxes={Pair[0],Pair[1],Original[0]}; FAnomalyScanReading Before,After;
        FAnomalyV04Probe::Precision(S,0); const bool Base=Pair[0]->CompleteScan(EAnomalyEquipment::MetalDetector,Before);
        FAnomalyV04Probe::Precision(S,.5f); const bool Upgraded=Pair[1]->CompleteScan(EAnomalyEquipment::MetalDetector,After);
        if (!Check(TEXT("Precision really narrows the generated interval without outcome resolution"),Base && Upgraded && After.ValueMin>=Before.ValueMin
            && After.ValueMax<=Before.ValueMax && After.ValueMax-After.ValueMin<Before.ValueMax-Before.ValueMin && !Pair[0]->bResolved && !Pair[1]->bResolved)) return false;
        C->CandidateBoxes=Original; for (auto B:Pair) B->Destroy();
        for (int32 I=0;I<6;++I)
        {
            auto L=C->GetWorld()->SpawnActor<AAnomalyWorldPickup>(AAnomalyWorldPickup::StaticClass(),FVector(10000,10000,0),FRotator::ZeroRotator);
            if (!L->InitializeItem(C->LootDefinitions[0],123,C->RoundId)) return Check(TEXT("Initialize inventory fixture"),false);
            const bool Stored=FAnomalyV04Probe::Store(C->Inventory,L);
            if (I<5 && !Stored) return Check(TEXT("Five real item instances can be stored"),false);
            if (I==5)
            {
                if (!Check(TEXT("Sixth item stays in world; fifth slot visible and value correct"),!Stored && !L->bClaimed && C->Inventory->GetCount()==5
                    && C->Inventory->GetCarryValue()==615 && C->Inventory->Describe().Contains(TEXT("[5]")))) return false;
                L->Destroy();
            }
        }
        return true;
    }
    bool SaveFixtures(AAnomalyRoundCoordinator* C)
    {
        auto P=C->GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>();
        const FString Path=P->GetSavePath()+TEXT(".fixture");
        FAnomalyMetaProgress M,Loaded; bool Future=false; FString Why; TArray<uint8> Bytes;
        if (!Check(TEXT("Missing slot is safe zero and schema 2"),FAnomalyMetaPersistence::Load(Path,Loaded,Future,Why) && Loaded.Currency==0 && Loaded.SchemaVersion==2)) return false;
        M.Currency=100; M.BatteryLevel=1;
        if (!Check(TEXT("USaveGame envelope roundtrip"),FAnomalyMetaPersistence::Encode(M,Bytes) && FAnomalyMetaPersistence::Decode(Bytes,Loaded,Future,Why)
            && Loaded.Currency==100 && Loaded.BatteryLevel==1)) return false;
        Bytes.Last()^=0x40;
        if (!Check(TEXT("CRC rejects damaged payload before deserialization"),!FAnomalyMetaPersistence::Decode(Bytes,Loaded,Future,Why))) return false;
        M.SchemaVersion=1; M.Currency=-9; M.BatteryLevel=99; M.PrecisionLevel=-5; M.BackpackLevel=9; M.StoredDecoys=40; M.Revision=-2;
        if (!Check(TEXT("Schema 1 validly loads for migration"),FAnomalyMetaPersistence::Encode(M,Bytes) && FAnomalyMetaPersistence::Decode(Bytes,Loaded,Future,Why) && Loaded.SchemaVersion==1)) return false;
        FAnomalyV04Probe::Sanitize(Loaded);
        if (!Check(TEXT("Loaded upgrades/currency/inventory/revision sanitized and migrated"),Loaded.SchemaVersion==2 && Loaded.Currency==0
            && Loaded.BatteryLevel==2 && Loaded.PrecisionLevel==0 && Loaded.BackpackLevel==1 && Loaded.StoredDecoys==1 && Loaded.Revision==0)) return false;
        M=FAnomalyMetaProgress(); M.Currency=100;
        if (!Check(TEXT("First durable write"),FAnomalyMetaPersistence::Write(Path,M,Why))) return false;
        M.Currency=200; ++M.Revision;
        if (!Check(TEXT("Second write preserves previous valid backup"),FAnomalyMetaPersistence::Write(Path,M,Why)
            && FAnomalyMetaPersistence::Load(Path+TEXT(".bak"),Loaded,Future,Why) && Loaded.Currency==100)) return false;
        M.Currency=300; ++M.Revision;
        if (!Check(TEXT("Simulated interruption after temp preserves committed main"),!FAnomalyMetaPersistence::Write(Path,M,Why,2)
            && FAnomalyMetaPersistence::Load(Path,Loaded,Future,Why) && Loaded.Currency==200)) return false;
        FFileHelper::SaveStringToFile(TEXT("truncated"),*Path);
        if (!Check(TEXT("Corrupt primary recovers verified backup"),FAnomalyMetaPersistence::Load(Path,Loaded,Future,Why) && Loaded.Currency==100 && Why.Contains(TEXT("备份")))) return false;
        const FString FuturePath=Path+TEXT(".future"); M.SchemaVersion=99;
        FAnomalyMetaPersistence::Encode(M,Bytes); FFileHelper::SaveArrayToFile(Bytes,*FuturePath);
        if (!Check(TEXT("Future schema is detected and retained, not overwritten"),!FAnomalyMetaPersistence::Load(FuturePath,Loaded,Future,Why) && Future
            && !FAnomalyMetaPersistence::Write(FuturePath,FAnomalyMetaProgress(),Why))) return false;
        M=FAnomalyMetaProgress(); M.Currency=3000;
        if (!FAnomalyV04Probe::Persist(P,M,Why)) return Check(TEXT("Persist isolated test funds"),false);
        FAnomalyV04Probe::Fault(P,1); const auto Request=FGuid::NewGuid();
        if (!Check(TEXT("Purchase persistence failure does not debit or grant"),!C->PurchaseProduct(0,P->GetProgress().Revision,Request)
            && P->GetProgress().Currency==3000 && P->GetProgress().BatteryLevel==0 && FAnomalyV04Probe::Message(C).Contains(TEXT("保存失败")))) return false;
        FAnomalyV04Probe::Fault(P,2);
        if (!Check(TEXT("Interrupted purchase leaves both live and loaded state unchanged"),!C->PurchaseProduct(0,P->GetProgress().Revision,Request)
            && FAnomalyMetaPersistence::Load(P->GetSavePath(),Loaded,Future,Why) && Loaded.Currency==3000 && Loaded.BatteryLevel==0 && P->GetProgress().Currency==3000)) return false;
        FAnomalyV04Probe::Fault(P,0);
        if (!Check(TEXT("Failed purchase can be retried and then durably grants exactly once"),C->PurchaseProduct(0,P->GetProgress().Revision,Request)
            && FAnomalyMetaPersistence::Load(P->GetSavePath(),Loaded,Future,Why) && Loaded.Currency==2000 && Loaded.BatteryLevel==1
            && Loaded.RecentPurchases.Contains(Request) && !P->Purchase(C,0,P->GetProgress().Revision,Request,Why))) return false;
        FAnomalyV04Probe::Terminal(C,EAnomalyRunEndReason::Failed);
        if (!Check(TEXT("Death cannot commit permanent income"),!P->CreditExtraction(C,C->RunId,123,Why) && P->GetProgress().Currency==2000)) return false;
        FAnomalyV04Probe::Terminal(C,EAnomalyRunEndReason::Error);
        if (!Check(TEXT("Technical error cannot commit permanent income"),!P->CreditExtraction(C,C->RunId,123,Why) && P->GetProgress().Currency==2000)) return false;
        FAnomalyV04Probe::Terminal(C,EAnomalyRunEndReason::CashedOut);
        if (!Check(TEXT("Authorized extraction has a durable RunId and only credits once"),P->CreditExtraction(C,C->RunId,123,Why)
            && !P->CreditExtraction(C,C->RunId,123,Why) && FAnomalyMetaPersistence::Load(P->GetSavePath(),Loaded,Future,Why)
            && Loaded.Currency==2123 && Loaded.Extractions==1 && Loaded.RecentSettlements.Contains(C->RunId))) return false;
        FAnomalyV04Probe::Prep(C); return true;
    }
    bool ColdFixture(AAnomalyRoundCoordinator* C)
    {
        auto P=C->GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>(); FString Why;
        if (SaveCase==TEXT("write"))
        {
            FAnomalyMetaProgress M; M.Currency=5000;
            if (!FAnomalyV04Probe::Persist(P,M,Why)) return Check(TEXT("Cold fixture seed persisted"),false);
            const auto Request=FGuid::NewGuid();
            return Check(TEXT("Cold process purchases battery and stores decoy durably"),P->Purchase(C,0,P->GetProgress().Revision,Request,Why)
                && P->Purchase(C,3,P->GetProgress().Revision,FGuid::NewGuid(),Why) && P->GetProgress().Currency==3400);
        }
        if (SaveCase==TEXT("quit_write"))
        {
            FAnomalyMetaProgress M; M.Currency=5000; M.StoredDecoys=1;
            if (!FAnomalyV04Probe::Persist(P,M,Why) || !C->StartPreparedRun()) return Check(TEXT("Start quit fixture"),false);
            auto L=C->GetWorld()->SpawnActor<AAnomalyWorldPickup>();
            return Check(TEXT("Quit with carry does not cash out; next-run decoy already consumed"),L->InitializeItem(C->LootDefinitions[0],999,C->RoundId)
                && FAnomalyV04Probe::Store(C->Inventory,L) && C->Inventory->GetCarryValue()==999 && P->GetProgress().Currency==5000 && P->GetProgress().StoredDecoys==0);
        }
        if (SaveCase==TEXT("quit_read"))
            return Check(TEXT("Cold restart after quit restores no carry income or duplicate consumable"),P->GetProgress().Currency==5000
                && P->GetProgress().StoredDecoys==0 && C->Inventory->GetCount()==0 && C->IsPreparing());
        if (SaveCase==TEXT("migrate_write") || SaveCase==TEXT("future_write"))
        {
            FAnomalyMetaProgress M; M.SchemaVersion=SaveCase==TEXT("migrate_write")?1:99;
            M.Currency=-9; M.BatteryLevel=99; M.PrecisionLevel=-3; M.BackpackLevel=99; M.StoredDecoys=40;
            TArray<uint8> Bytes;
            IFileManager::Get().MakeDirectory(*FPaths::GetPath(P->GetSavePath()),true);
            return Check(TEXT("Write isolated old/future schema fixture"),FAnomalyMetaPersistence::Encode(M,Bytes) && FFileHelper::SaveArrayToFile(Bytes,*P->GetSavePath()));
        }
        if (SaveCase==TEXT("migrate_read"))
        {
            FAnomalyMetaProgress Loaded; bool Future=false;
            const bool Valid=P->GetProgress().SchemaVersion==2 && P->GetProgress().Currency==0 && P->GetProgress().BatteryLevel==2
                && P->GetProgress().PrecisionLevel==0 && P->GetProgress().BackpackLevel==1 && P->GetProgress().StoredDecoys==1;
            return Check(TEXT("Actual subsystem cold-loads schema 1, sanitizes, applies and commits schema 2"),Valid && C->StartPreparedRun()
                && C->DecoysRemaining==1 && C->Inventory->GetCapacity()==5 && FAnomalyMetaPersistence::Load(P->GetSavePath(),Loaded,Future,Why)
                && Loaded.SchemaVersion==2 && Loaded.StoredDecoys==0);
        }
        if (SaveCase==TEXT("future_read"))
        {
            TArray<uint8> Before,After; FFileHelper::LoadFileToArray(Before,*P->GetSavePath());
            const bool Blocked=!C->StartPreparedRun() && C->IsPreparing() && P->GetLoadMessage().Contains(TEXT("更高版本"));
            FFileHelper::LoadFileToArray(After,*P->GetSavePath());
            return Check(TEXT("Actual future-schema cold load blocks gameplay commits and preserves bytes"),Blocked && Before==After);
        }
        if (SaveCase!=TEXT("read")) return Check(TEXT("Known save fixture requested"),false);
        return Check(TEXT("New OS process restores permanent money/upgrades/decoy/history"),P->GetProgress().SchemaVersion==2
            && P->GetProgress().Currency==3400 && P->GetProgress().BatteryLevel==1 && P->GetProgress().StoredDecoys==1
            && P->GetProgress().RecentPurchases.Num()==2 && C->IsPreparing() && C->Inventory->GetCount()==0);
    }
    void Tick(UWorld* W,ELevelTick,float)
    {
        if (Finished || !W || !W->IsGameWorld() || !W->HasBegunPlay() || W->GetTimeSeconds()<NextTime) return;
        for (TActorIterator<AAnomalyRoundCoordinator> It(W);It;++It)
        {
            auto C=*It; auto Player=UGameplayStatics::GetPlayerCharacter(W,0); if (!Player) return;
            SlotPath=C->GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>()->GetSavePath();
            if (Task==TEXT("T29") && SaveCase==TEXT("extract_fail"))
            {
                auto P=C->GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>(); FString Why;
                if (Stage==0)
                {
                    FAnomalyMetaProgress M; M.Currency=5000;
                    if (!FAnomalyV04Probe::Persist(P,M,Why) || !C->StartPreparedRun()) { Finish(Check(TEXT("Prepare failed settlement fixture"),false)); return; }
                    auto L=W->SpawnActor<AAnomalyWorldPickup>(); L->InitializeItem(C->LootDefinitions[0],123,C->RoundId); FAnomalyV04Probe::Store(C->Inventory,L);
                    FAnomalyV04Probe::Fault(P,1);
                    if (!Check(TEXT("Physical entrance queues extraction before injected save failure"),C->ConfirmExtraction(Player))) { Finish(false); return; }
                    Stage=1; NextTime=W->GetTimeSeconds()+.3f; return;
                }
                Finish(Check(TEXT("Failed durable settlement is Error, clears local carry and preserves prior Meta"),C->RunEndReason==EAnomalyRunEndReason::Error
                    && C->FinalRunValue==0 && C->SettlementCount==0 && C->Inventory->GetCount()==0 && P->GetProgress().Currency==5000
                    && Player->FindComponentByClass<UAnomalyWalletComponent>()->NativeGetMoney()==0 && !C->GetEndSnapshot().bDurableCredit)); return;
            }
            if (Task==TEXT("T29") && !SaveCase.IsEmpty())
            { Finish(SaveCase==TEXT("boundaries")?SaveFixtures(C):ColdFixture(C)); return; }
            if (Task==TEXT("T27"))
            { if (C->IsPreparing()) C->StartPreparedRun(); if (C->CandidateBoxes.Num()==3) Finish(ScanFixtures(C)); return; }
            if (Stage==0) { Shot(TEXT("00_preparation")); Key(Player,EKeys::Down,true); Stage=10; NextTime=W->GetTimeSeconds()+.4f; return; }
            if (Stage==10)
            {
                Key(Player,EKeys::Down,false);
                if (!Check(TEXT("Real Down input navigates shop selection"),FAnomalyV04Probe::Selection(C)==1)) { Finish(false); return; }
                Key(Player,EKeys::Enter,true); Stage=11; NextTime=W->GetTimeSeconds()+.4f; return;
            }
            if (Stage==11)
            {
                Key(Player,EKeys::Enter,false);
                if (!Check(TEXT("Real Enter input displays insufficient-balance reason"),FAnomalyV04Probe::Message(C).Contains(TEXT("余额不足")))) { Finish(false); return; }
                Shot(TEXT("00_insufficient")); Stage=1; NextTime=W->GetTimeSeconds()+.4f; return;
            }
            if (Stage==1)
            { if (!ShopFixtures(C)) { Finish(false); return; } Shot(TEXT("01_shop_owned")); Stage=2; NextTime=W->GetTimeSeconds()+.4f; return; }
            if (Stage==2)
            {
                if (!Check(TEXT("Prepared run starts once"),C->StartPreparedRun()) || !EquipmentFixtures(C)) { Finish(false); return; }
                Stage=3; NextTime=W->GetTimeSeconds()+.4f; return;
            }
            if (Stage==3)
            {
                AAnomalyRoundCoordinator::FinishAssetCompilation(); Shot(TEXT("02_five_slots"));
                Stage=33; NextTime=W->GetTimeSeconds()+.4f; return;
            }
            if (Stage==33)
            {
                auto Threat=W->SpawnActor<AAnomalyThreatCharacter>(AAnomalyThreatCharacter::StaticClass(),FVector(0,1100,98),FRotator::ZeroRotator);
                Threat->ActivateThreat(); LuredThreat=Threat;
                Key(Player,EKeys::F,true); Stage=34; NextTime=W->GetTimeSeconds()+.3f; return;
            }
            if (Stage==34)
            {
                Key(Player,EKeys::F,false);
                if (!Check(TEXT("Real F input creates a decoy source and redirects eligible AI exactly once"),C->DecoysRemaining==0 && LuredThreat.IsValid()
                    && IsValid(FAnomalyV04Probe::Decoy(C)) && LuredThreat->GetPursuitTarget()==FAnomalyV04Probe::Decoy(C) && IsValid(FAnomalyV04Probe::Decoy(C)->FindComponentByClass<UStaticMeshComponent>()->GetStaticMesh())
                    && !C->UseDecoy())) { Finish(false); return; }
                InitialDistance=FVector::DistSquared2D(LuredThreat->GetActorLocation(),FAnomalyV04Probe::Decoy(C)->GetActorLocation());
                Player->SetActorLocation(FVector(500,1400,98),false); Stage=4; NextTime=W->GetTimeSeconds()+.8f; return;
            }
            if (Stage==4)
            {
                if (!Check(TEXT("Decoy changes actual navigation movement toward source"),LuredThreat.IsValid() && IsValid(FAnomalyV04Probe::Decoy(C))
                    && FVector::DistSquared2D(LuredThreat->GetActorLocation(),FAnomalyV04Probe::Decoy(C)->GetActorLocation())<InitialDistance-1000)) { Finish(false); return; }
                Stage=5; NextTime=W->GetTimeSeconds()+5.f; return;
            }
            if (Stage==5)
            {
                const bool Pass=Check(TEXT("Expired decoy returns pursuit to player without duplicating inventory"),LuredThreat.IsValid()
                    && LuredThreat->GetPursuitTarget()==Player && C->DecoysRemaining==0 && !IsValid(FAnomalyV04Probe::Decoy(C)));
                if (LuredThreat.IsValid()) LuredThreat->Destroy();
                FAnomalyV04Probe::Clear(C->Inventory); Finish(Pass); return;
            }
        }
    }
}
void RegisterAnomalyV04Smoke()
{
    if (!FParse::Param(FCommandLine::Get(),TEXT("AnomalyV04Smoke"))) return;
    FParse::Value(FCommandLine::Get(),TEXT("V04Evidence="),V04Smoke::Output);
    FParse::Value(FCommandLine::Get(),TEXT("V04Stage="),V04Smoke::Task);
    FParse::Value(FCommandLine::Get(),TEXT("V04SaveCase="),V04Smoke::SaveCase);
    if (V04Smoke::Output.IsEmpty()) V04Smoke::Output=FPaths::ProjectSavedDir()/TEXT("V04/Runtime");
    V04Smoke::Handle=FWorldDelegates::OnWorldTickStart.AddStatic(&V04Smoke::Tick);
}
void UnregisterAnomalyV04Smoke() { FWorldDelegates::OnWorldTickStart.Remove(V04Smoke::Handle); }
#endif
