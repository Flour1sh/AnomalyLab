#include "AnomalyTransitionSubsystem.h"
#include "AnomalyHub.h"
#include "AnomalyTelemetry.h"
#include "AnomalyProgressionConfig.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/PackageName.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

void UAnomalyTransitionSubsystem::Initialize(FSubsystemCollectionBase& C)
{
    Super::Initialize(C); C.InitializeDependency<UAnomalyProgressionSubsystem>();
    if(GEngine) GEngine->OnTravelFailure().AddUObject(this,&UAnomalyTransitionSubsystem::TravelFailure);
    Ticker=FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateUObject(this,&UAnomalyTransitionSubsystem::Tick));
}
void UAnomalyTransitionSubsystem::Deinitialize()
{
    FTSTicker::GetCoreTicker().RemoveTicker(Ticker);
    if(GEngine) GEngine->OnTravelFailure().RemoveAll(this);
    Super::Deinitialize();
}
void UAnomalyTransitionSubsystem::Change(EAnomalyTravelPhase Next,const FString& Cause)
{
    UE_LOG(LogTemp,Display,TEXT("[Travel] Run=%s Version=%lld Phase=%d->%d Trigger=%s"),*Launch.Run.ToString(),Version,int32(Phase),int32(Next),*Cause);
    Phase=Next; Message=Cause;
}
bool UAnomalyTransitionSubsystem::IsHubReady(const UObject* Caller) const
{
    return Caller && Caller->GetWorld()==GetGameInstance()->GetWorld() && Phase==EAnomalyTravelPhase::HubReady
        && UWorld::RemovePIEPrefix(Caller->GetWorld()->GetOutermost()->GetName())==TEXT("/Game/Maps/L_Hub")
        && Cast<AAnomalyHubGameMode>(Caller->GetWorld()->GetAuthGameMode());
}
bool UAnomalyTransitionSubsystem::EnterHub(AAnomalyHubPlayerController* Caller)
{
    if(!Caller || UWorld::RemovePIEPrefix(Caller->GetWorld()->GetOutermost()->GetName())!=TEXT("/Game/Maps/L_Hub")) return false;
    if(Phase==EAnomalyTravelPhase::InRun || Phase==EAnomalyTravelPhase::LoadingLab)
    { Result=FAnomalyEndRunSnapshot(); Result.RunId=Launch.Run; Result.Reason=EAnomalyRunEndReason::Error; }
    if(Phase==EAnomalyTravelPhase::LoadingHub) { HubLoadSeconds=float(FPlatformTime::Seconds()-LoadStarted); FAnomalyRunTelemetry::CompleteHub(Result.RunId,HubLoadSeconds); }
    PendingDestination.Reset(); Deadline=0; Change(EAnomalyTravelPhase::HubReady,TEXT("安全基地已就绪")); return true;
}
bool UAnomalyTransitionSubsystem::RequestLaunch(AAnomalyHubPlayerController* Caller,FString& Reason)
{
    if(!IsHubReady(Caller) || !Caller->CanConfirmDeparture()) { Reason=TEXT("请在基地出发终端确认"); return false; }
    if(!FPackageName::DoesPackageExist(TEXT("/Game/Maps/L_Lab"))) { Reason=TEXT("实验室关卡缺失，出发未扣费"); return false; }
    if(Version==MAX_int64) { Reason=TEXT("过渡序号上限"); return false; }
    Change(EAnomalyTravelPhase::Preparing,TEXT("冻结携带配置"));
    Launch=FAnomalyLaunchContext(); Launch.Run=FGuid::NewGuid(); Launch.Version=++Version; Launch.Seed=FMath::Rand();
    auto Meta=GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>();
    if(!Meta || !Meta->BeginHubRun(this,Launch.Run,Launch.Decoys,Reason))
    { Change(EAnomalyTravelPhase::HubReady,Reason); Launch=FAnomalyLaunchContext(); return false; }
    Launch.Equipment=Meta->GetProgress(); ++LaunchCount;
    Change(EAnomalyTravelPhase::LoadingLab,TEXT("正在加载实验室…")); Deadline=FPlatformTime::Seconds()+45;
    Caller->SetIgnoreMoveInput(true); Caller->SetIgnoreLookInput(true);
    QueueTravel(TEXT("/Game/Maps/L_Lab")); return true;
}
bool UAnomalyTransitionSubsystem::ClaimLab(AAnomalyRoundCoordinator* Caller,FAnomalyLaunchContext& Value,FString& Reason)
{
    if(!Caller || Caller->GetWorld()!=GetGameInstance()->GetWorld() || !Caller->bAwaitLevelLaunch
        || UWorld::RemovePIEPrefix(Caller->GetWorld()->GetOutermost()->GetName())!=TEXT("/Game/Maps/L_Lab")
        || Phase!=EAnomalyTravelPhase::LoadingLab || !Launch.Run.IsValid() || Launch.Version!=Version)
    { Reason=TEXT("没有可接收的出发请求，返回安全基地"); return false; }
    Value=Launch; LabLoadSeconds=float(FPlatformTime::Seconds()-LoadStarted); Deadline=0; Change(EAnomalyTravelPhase::InRun,TEXT("实验室接收唯一出发请求")); return true;
}
bool UAnomalyTransitionSubsystem::CompleteRun(AAnomalyRoundCoordinator* Caller)
{
    if(!Caller || !Caller->IsV05Lab() || Phase!=EAnomalyTravelPhase::InRun || Caller->RunId!=Launch.Run
        || Caller->GetNativeRoundState()!=3 || Caller->GetWorld()!=GetGameInstance()->GetWorld()) return false;
    const auto& Snapshot=Caller->GetEndSnapshot();
    if(Snapshot.RunId!=Launch.Run || Snapshot.Reason==EAnomalyRunEndReason::None
        || (Snapshot.Reason==EAnomalyRunEndReason::CashedOut && !Snapshot.bDurableCredit)) return false;
    Result=Snapshot; ++ResultCount;
    Change(EAnomalyTravelPhase::LoadingHub,TEXT("结果已封存，返回基地…")); Deadline=FPlatformTime::Seconds()+45;
    QueueTravel(TEXT("/Game/Maps/L_Hub")); return true;
}
void UAnomalyTransitionSubsystem::RejectLab(UWorld* World,const FString& Reason)
{
    if(World!=GetGameInstance()->GetWorld()) return;
    Result=FAnomalyEndRunSnapshot(); Result.RunId=Launch.Run; Result.Reason=EAnomalyRunEndReason::Error;
    Result.Detail=Reason;
    Change(EAnomalyTravelPhase::LoadingHub,Reason); Deadline=FPlatformTime::Seconds()+45;
    QueueTravel(TEXT("/Game/Maps/L_Hub"));
}
void UAnomalyTransitionSubsystem::TravelFailure(UWorld* World,ETravelFailure::Type Type,const FString& Reason)
{
    if(World!=GetGameInstance()->GetWorld()) return;
    if(Phase!=EAnomalyTravelPhase::LoadingHub && Phase!=EAnomalyTravelPhase::LoadingLab) return;
    PendingDestination.Reset(); Deadline=0; Change(EAnomalyTravelPhase::Error,TEXT("关卡加载失败：")+Reason);
    if(UWorld::RemovePIEPrefix(World->GetOutermost()->GetName())==TEXT("/Game/Maps/L_Hub")) Change(EAnomalyTravelPhase::HubReady,Message);
    else UGameplayStatics::OpenLevel(World,TEXT("/Game/Prototype/Maps/L_MainMenu"));
}
void UAnomalyTransitionSubsystem::QueueTravel(const FString& Destination)
{
    LoadStarted=FPlatformTime::Seconds(); PendingDestination=Destination; PendingVersion=Version; PendingAt=LoadStarted+.3;
}
bool UAnomalyTransitionSubsystem::Tick(float Delta)
{
    if(!PendingDestination.IsEmpty() && FPlatformTime::Seconds()>=PendingAt)
    {
        const FString Target=PendingDestination; PendingDestination.Reset();
        if(PendingVersion==Version && (Phase==EAnomalyTravelPhase::LoadingHub || Phase==EAnomalyTravelPhase::LoadingLab))
            UGameplayStatics::OpenLevel(GetGameInstance(),FName(*Target));
    }
    if(Deadline>0 && FPlatformTime::Seconds()>Deadline)
    { Deadline=0; Change(EAnomalyTravelPhase::Error,TEXT("加载超时，未兑现本局物品"));
      if(auto World=GetGameInstance()->GetWorld()) UGameplayStatics::OpenLevel(World,TEXT("/Game/Prototype/Maps/L_MainMenu")); }
    return true;
}
