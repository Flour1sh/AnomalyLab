#include "AnomalyTelemetry.h"
#include "AnomalyRoundCoordinator.h"
#include "AnomalyTransitionSubsystem.h"
#include "AnomalyHealthComponent.h"
#include "AnomalyInventoryComponent.h"
#include "AnomalyThreatCharacter.h"
#include "AnomalyObserverCharacter.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/App.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"

namespace
{
    FString Room(const FVector& P)
    { return P.Y>900?TEXT("Entry"):P.Y<-500?TEXT("C"):P.X<-240?TEXT("A"):P.X>240?TEXT("B"):TEXT("Hall"); }
    bool Save(const FString& Path,const TSharedPtr<FJsonObject>& Data)
    {
        FString Json; if(!FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Json)) || Json.Len()>450000) return false;
        IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);
        if(!FFileHelper::SaveStringToFile(Json,*(Path+TEXT(".tmp")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM)) return false;
        return IFileManager::Get().Move(*Path,*(Path+TEXT(".tmp")),true,false,false,true);
    }
    void Prune(const FString& Folder)
    {
        TArray<FString> Files; IFileManager::Get().FindFiles(Files,*(Folder/TEXT("*.json")),true,false);
        Files.RemoveAll([](const FString& File) { FGuid Id; return !FGuid::ParseExact(FPaths::GetBaseFilename(File),EGuidFormats::Digits,Id); });
        Files.Sort([&Folder](const FString& A,const FString& B) { return IFileManager::Get().GetTimeStamp(*(Folder/A))>IFileManager::Get().GetTimeStamp(*(Folder/B)); });
        for(int32 I=20;I<Files.Num();++I) IFileManager::Get().Delete(*(Folder/Files[I]),false,true);
    }
}
FString FAnomalyRunTelemetry::Path(const FGuid& Run)
{ return FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("V05/Telemetry")/(Run.ToString(EGuidFormats::Digits)+TEXT(".json"))); }
void FAnomalyRunTelemetry::Start(const AAnomalyRoundCoordinator* C)
{
    if(!C || !C->IsV05Lab() || FParse::Param(FCommandLine::Get(),TEXT("NoRunTelemetry"))) return;
    EntryGameSeconds=C->GetWorld()->GetTimeSeconds(); Run=C->RunId; Data=MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("RunId"),Run.ToString()); Data->SetNumberField(TEXT("Seed"),C->RegionSeed);
    Data->SetStringField(TEXT("EntryTime"),FDateTime::UtcNow().ToIso8601());
    Data->SetStringField(TEXT("Renderer"),FParse::Param(FCommandLine::Get(),TEXT("nullrhi"))?TEXT("NullRHI"):TEXT("D3D12_or_engine_default"));
    Data->SetBoolField(TEXT("Automation"),FParse::Param(FCommandLine::Get(),TEXT("AnomalyV05Smoke")));
    Data->SetStringField(TEXT("FrameScope"),TEXT("Actual engine CPU frame delta sampled at Coordinator tick (20Hz), max12000 samples; not GPU/human benchmark"));
    auto T=C->GetGameInstance()->GetSubsystem<UAnomalyTransitionSubsystem>(); const auto& M=T->GetLaunch().Equipment;
    auto Loadout=MakeShared<FJsonObject>(); Loadout->SetNumberField(TEXT("Battery"),M.BatteryLevel); Loadout->SetNumberField(TEXT("Precision"),M.PrecisionLevel);
    Loadout->SetNumberField(TEXT("Backpack"),M.BackpackLevel); Loadout->SetNumberField(TEXT("Decoys"),T->GetLaunch().Decoys);
    Data->SetObjectField(TEXT("UpgradeLoadout"),Loadout); Data->SetNumberField(TEXT("LabLoadSeconds"),T->GetLabLoadSeconds());
    Event(C,TEXT("Entry"),TEXT("Fresh Lab initialized"));
}
void FAnomalyRunTelemetry::Event(const AAnomalyRoundCoordinator* C,const FString& Kind,const FString& Detail)
{
    if(!Data || bFinished || Events.Num()>=512 || !C) return;
    auto E=MakeShared<FJsonObject>(); E->SetStringField(TEXT("Kind"),Kind); E->SetStringField(TEXT("Detail"),Detail.Left(240));
    E->SetNumberField(TEXT("Seconds"),C->GetWorld()->GetTimeSeconds()); E->SetNumberField(TEXT("Round"),C->RoundId);
    if(auto P=UGameplayStatics::GetPlayerPawn(C,0)) E->SetStringField(TEXT("Room"),Room(P->GetActorLocation()));
    Events.Add(MakeShared<FJsonValueObject>(E));
}
void FAnomalyRunTelemetry::Tick(const AAnomalyRoundCoordinator* C)
{
    if(!Data || bFinished) return;
    if(auto P=UGameplayStatics::GetPlayerPawn(C,0))
    { const auto R=Room(P->GetActorLocation()); if(!Rooms.Contains(R)) { Rooms.Add(R); Event(C,TEXT("Room"),R); }
      if(auto H=P->FindComponentByClass<UAnomalyHealthComponent>()) MinHealth=FMath::Min(MinHealth,H->CurrentHealth); }
    const float Ms=float(FApp::GetDeltaTime()*1000.);
    if(FMath::IsFinite(Ms) && Ms>0 && FrameMs.Num()<12000) { FrameMs.Add(Ms); FrameSum+=Ms; MaxFrame=FMath::Max(MaxFrame,double(Ms)); if(Ms>50) ++Hitches; }
    if(C->RoundId!=LastRound)
    {
        LastRound=C->RoundId; FString Points;
        for(int32 I=0;I<C->LastSpawnPointIds.Num();++I) Points+=FString::Printf(TEXT("%c:%d "),TEXT('A')+I,C->LastSpawnPointIds[I]);
        Event(C,TEXT("BoxSpawnPoint"),Points);
    }
    if(IsValid(C->CurrentSpider)) Data->SetStringField(TEXT("ThreatType"),Cast<AAnomalyObserverCharacter>(C->CurrentSpider)?TEXT("Observer"):TEXT("Chaser"));
}
void FAnomalyRunTelemetry::BeginReturn(const AAnomalyRoundCoordinator* C)
{ if(ReturnAt<0 && Data) { ReturnAt=C->GetWorld()->GetTimeSeconds(); Event(C,TEXT("ReturnRequested"),TEXT("Physical entrance still required")); } }
void FAnomalyRunTelemetry::Finish(const AAnomalyRoundCoordinator* C,const FAnomalyEndRunSnapshot& R,bool Interrupted)
{
    if(!Data || bFinished) return;
    Tick(C); Event(C,TEXT("Result"),Interrupted?TEXT("Interrupted; no extra credit"):R.Detail); bFinished=true;
    Data->SetStringField(TEXT("ExitTime"),FDateTime::UtcNow().ToIso8601());
    Data->SetStringField(TEXT("Outcome"),Interrupted?TEXT("Interrupted"):StaticEnum<EAnomalyRunEndReason>()->GetNameStringByValue(int64(R.Reason)));
    const int64 Lost=Interrupted && C->Inventory?C->Inventory->GetCarryValue():R.Lost;
    Data->SetNumberField(TEXT("Duration"),Interrupted?FMath::Max(0.,C->GetWorld()->GetTimeSeconds()-EntryGameSeconds):R.Seconds); Data->SetNumberField(TEXT("CashExtracted"),R.CashedOut); Data->SetNumberField(TEXT("LootValue"),double(R.CashedOut+Lost));
    Data->SetNumberField(TEXT("CarryLost"),double(Lost)); Data->SetNumberField(TEXT("PermanentBalance"),double(R.PermanentBalance));
    if(Interrupted && C->GetGameInstance()) if(auto P=C->GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>()) Data->SetNumberField(TEXT("PermanentBalance"),double(P->GetProgress().Currency)); Data->SetBoolField(TEXT("DurableCredit"),R.bDurableCredit);
    Data->SetNumberField(TEXT("ThreatDamage"),double(DamageTaken)); Data->SetNumberField(TEXT("MinimumHealth"),MinHealth); Data->SetNumberField(TEXT("CompletedRounds"),R.Rounds);
    Data->SetNumberField(TEXT("ReturnRouteTime"),ReturnAt<0?0:FMath::Max(0.,C->GetWorld()->GetTimeSeconds()-ReturnAt));
    int32 Scans=0; int64 Generated=0; for(const auto& Pair:C->RegionStats) { Scans+=Pair.Value.ScanCount; Generated+=Pair.Value.Reward; } Data->SetNumberField(TEXT("LootGeneratedValue"),double(Generated)); Data->SetNumberField(TEXT("ScansUsed"),Scans);
    if(!Data->HasField(TEXT("ThreatType"))) Data->SetStringField(TEXT("ThreatType"),TEXT("None"));
    TArray<TSharedPtr<FJsonValue>> Visited; for(const auto& Rm:Rooms) Visited.Add(MakeShared<FJsonValueString>(Rm)); Data->SetArrayField(TEXT("Room"),Visited);
    Data->SetArrayField(TEXT("Events"),Events); Data->SetNumberField(TEXT("FrameSamples"),FrameMs.Num()); Data->SetNumberField(TEXT("HitchesOver50ms"),Hitches);
    FrameMs.Sort(); const double Mean=FrameMs.IsEmpty()?0:FrameSum/FrameMs.Num(); Data->SetNumberField(TEXT("FPS"),Mean>0?1000/Mean:0);
    Data->SetNumberField(TEXT("CpuFrameMeanMs"),Mean); Data->SetNumberField(TEXT("CpuFrameMaxMs"),MaxFrame);
    Data->SetNumberField(TEXT("CpuFrameP95Ms"),FrameMs.IsEmpty()?0:FrameMs[FMath::Min(FrameMs.Num()-1,FMath::FloorToInt(FrameMs.Num()*.95f))]);
    const bool Saved=Save(Path(Run),Data); if(Saved) Prune(FPaths::GetPath(Path(Run)));
    UE_LOG(LogTemp,Display,TEXT("[Telemetry] Run=%s Saved=%d Samples=%d MeanMs=%.3f Path=%s"),*Run.ToString(),Saved,FrameMs.Num(),Mean,*Path(Run));
}
void FAnomalyRunTelemetry::CompleteHub(const FGuid& Run,float Seconds)
{
    if(!Run.IsValid() || IFileManager::Get().FileSize(*Path(Run))>1024*1024) return;
    FString Json; TSharedPtr<FJsonObject> Data;
    if(FFileHelper::LoadFileToString(Json,*Path(Run)) && FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Data) && Data)
    { Data->SetNumberField(TEXT("HubLoadSeconds"),Seconds); Save(Path(Run),Data); }
}
