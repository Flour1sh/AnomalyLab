#include "AnomalyEnvironment.h"
#include "AnomalyRoundCoordinator.h"
#include "AnomalyBoxActor.h"
#include "AnomalyRegionDefinition.h"
#include "AnomalyScannerComponent.h"
#include "AnomalyHealthComponent.h"
#include "AnomalyThreatCharacter.h"
#include "AnomalyObserverCharacter.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Camera/CameraComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/World.h"
#include "EngineUtils.h"

namespace { bool InB(const FVector& P) { return P.X>240 && P.X<1400 && P.Y>-500 && P.Y<900; } }
bool UAnomalyEnvironmentConfig::Validate() const
{
    return FMath::IsFinite(PowerScanMultiplier) && PowerScanMultiplier>=1 && PowerScanMultiplier<=3
        && FMath::IsFinite(PowerObserveMultiplier) && PowerObserveMultiplier>=1 && PowerObserveMultiplier<=2
        && FMath::IsFinite(PowerLightMultiplier) && PowerLightMultiplier>=.2f && PowerLightMultiplier<=1
        && FMath::IsFinite(InteractCooldown) && InteractCooldown>=.2f && InteractCooldown<=2
        && FMath::IsFinite(ChamberSeconds) && ChamberSeconds>=1 && ChamberSeconds<=5
        && FMath::IsFinite(ChamberRadius) && ChamberRadius>=150 && ChamberRadius<=400 && !ChamberCenter.ContainsNaN()
        && FMath::IsFinite(EventChance) && EventChance>=0 && EventChance<=1 && MaxEvents>=0 && MaxEvents<=2
        && FMath::IsFinite(EventFirstDelay) && EventFirstDelay>=8 && EventFirstDelay<=60
        && FMath::IsFinite(EventSpacing) && EventSpacing>=8 && EventSpacing<=60
        && FMath::IsFinite(EventWarningSeconds) && EventWarningSeconds>=1 && EventWarningSeconds<=4
        && FMath::IsFinite(EventSeconds) && EventSeconds>=2 && EventSeconds<=6
        && FMath::IsFinite(AlarmSpeedMultiplier) && AlarmSpeedMultiplier>=1 && AlarmSpeedMultiplier<=1.15f;
}
AAnomalyEnvironmentTerminal::AAnomalyEnvironmentTerminal()
{
    Bounds=CreateDefaultSubobject<UBoxComponent>(TEXT("TerminalBounds")); SetRootComponent(Bounds);
    Bounds->InitBoxExtent(FVector(50,45,70)); Bounds->SetCollisionProfileName(TEXT("BlockAll"));
    Visual=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("TerminalVisual")); Visual->SetupAttachment(Bounds);
    Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision); Visual->SetCanEverAffectNavigation(false);
}
bool AAnomalyEnvironmentTerminal::ValidatePlayer(AActor* Player) const
{
    auto Service=AAnomalyEnvironmentController::Find(GetWorld());
    if(!Service || !Service->Active() || Player!=UGameplayStatics::GetPlayerPawn(this,0)) return false;
    auto Health=Player->FindComponentByClass<UAnomalyHealthComponent>();
    auto Camera=Player->FindComponentByClass<UCameraComponent>(); if(!Health || Health->bDead || !Camera) return false;
    FHitResult Hit; FCollisionQueryParams Params(SCENE_QUERY_STAT(V05EnvironmentInput),false,Player);
    const FVector Eye=Camera->GetComponentLocation();
    return GetWorld()->LineTraceSingleByChannel(Hit,Eye,Eye+Camera->GetForwardVector()*300.f,ECC_Visibility,Params) && Hit.GetActor()==this;
}
bool AAnomalyEnvironmentTerminal::Interact(AActor* Player)
{
    auto Service=AAnomalyEnvironmentController::Find(GetWorld()); if(!Service) return false;
    FString Reason; const bool Done=Kind==EAnomalyEnvironmentKind::Power?Service->TogglePower(this,Player,Reason):Service->TriggerChamber(this,Player,Reason);
    for(TActorIterator<AAnomalyRoundCoordinator> It(GetWorld());It;++It) if(It->IsV05Lab()) It->Notify(Reason);
    return Done;
}
FString AAnomalyEnvironmentTerminal::Describe() const
{
    auto Service=AAnomalyEnvironmentController::Find(GetWorld());
    return Service?(Kind==EAnomalyEnvironmentKind::Power?Service->DescribePower():Service->DescribeChamber()):TEXT("控制台不可用");
}
AAnomalyEnvironmentController::AAnomalyEnvironmentController()
{ PrimaryActorTick.bCanEverTick=true; PrimaryActorTick.TickInterval=.05f; SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("EnvironmentRoot"))); }
AAnomalyEnvironmentController* AAnomalyEnvironmentController::Find(const UWorld* World)
{ if(World) for(TActorIterator<AAnomalyEnvironmentController> It(const_cast<UWorld*>(World));It;++It) return *It; return nullptr; }
AAnomalyRoundCoordinator* AAnomalyEnvironmentController::Coordinator() const
{ for(TActorIterator<AAnomalyRoundCoordinator> It(GetWorld());It;++It) if(It->IsV05Lab()) return *It; return nullptr; }
bool AAnomalyEnvironmentController::Active() const
{ auto C=Coordinator(); return UWorld::RemovePIEPrefix(GetWorld()->GetOutermost()->GetName())==TEXT("/Game/Maps/L_Lab") && Config && Config->Validate() && C && C->GetNativeRoundState()!=3; }
void AAnomalyEnvironmentController::BeginPlay()
{
    Super::BeginPlay(); bPowerOn=true; PowerReadyAt=0;
    for(TActorIterator<AActor> It(GetWorld());It;++It) if(It->ActorHasTag(TEXT("V05PowerB")))
    { TArray<UPointLightComponent*> Components; It->GetComponents(Components);
      for(auto Light:Components) { Lights.Add(Light); InitialIntensities.Add(Light->Intensity); } }
    for(TActorIterator<AActor> It(GetWorld());It;++It) if(It->ActorHasTag(TEXT("V05AlarmC")))
    { TArray<UPointLightComponent*> Components; It->GetComponents(Components);
      for(auto Light:Components) { AlarmLights.Add(Light); InitialAlarmColours.Add(Light->GetLightColor()); } }
    ApplyLights();
}
void AAnomalyEnvironmentController::ApplyLights()
{ for(int32 I=0;I<Lights.Num();++I) if(Lights[I].IsValid()) Lights[I]->SetIntensity(InitialIntensities[I]*((bPowerOn && !bEventPowerOff) || !Config?1.f:Config->PowerLightMultiplier)); }
bool AAnomalyEnvironmentController::TogglePower(AAnomalyEnvironmentTerminal* Terminal,AActor* Player,FString& Reason)
{
    if(!Active() || !Terminal || Terminal->Kind!=EAnomalyEnvironmentKind::Power || !Terminal->ValidatePlayer(Player)) { Reason=TEXT("请靠近并对准配电终端"); return false; }
    if(GetWorld()->GetTimeSeconds()<PowerReadyAt) { Reason=TEXT("配电开关切换中，请稍候"); return false; }
    if(auto Scanner=Player->FindComponentByClass<UAnomalyScannerComponent>()) Scanner->CancelScan();
    if(CurrentEvent.Type==EAnomalyDynamicEvent::PowerFluctuation && EventPhase!=EAnomalyEventPhase::Quiet)
    { EndEvent(TEXT("玩家手动恢复供电")); bPowerOn=true; }
    else bPowerOn=!bPowerOn;
    PowerReadyAt=GetWorld()->GetTimeSeconds()+Config->InteractCooldown; ApplyLights();
    Reason=bPowerOn?TEXT("B供电恢复：扫描正常，正视压制窗口恢复正常"):FString::Printf(TEXT("B断电：扫描耗时×%.2f，正视观察者窗口×%.2f"),Config->PowerScanMultiplier,Config->PowerObserveMultiplier);
    if(auto C=Coordinator()) C->EmitFeedback(TEXT("ScanStart"));
    UE_LOG(LogTemp,Display,TEXT("[Environment] Run=%s Power=%d ScanMultiplier=%.2f ObserveMultiplier=%.2f"),*Coordinator()->RunId.ToString(),bPowerOn,Config->PowerScanMultiplier,Config->PowerObserveMultiplier);
    Coordinator()->RecordTelemetry(TEXT("EventResponse"),Reason);
    return true;
}
float AAnomalyEnvironmentController::ScanMultiplier(const AAnomalyBoxActor* Target) const
{ return Active() && (!bPowerOn || bEventPowerOff) && Target && Target->RegionDefinition && Target->RegionDefinition->RegionID==TEXT("B")?Config->PowerScanMultiplier:1.f; }
float AAnomalyEnvironmentController::ObserveMultiplier(const AActor* Observer) const
{
    auto Player=UGameplayStatics::GetPlayerPawn(this,0);
    return Active() && (!bPowerOn || bEventPowerOff) && Observer && Player && InB(Observer->GetActorLocation()) && InB(Player->GetActorLocation())?Config->PowerObserveMultiplier:1.f;
}
FString AAnomalyEnvironmentController::DescribePower() const
{ return (bPowerOn && !bEventPowerOff)?TEXT("B 供电 ON · E 断电\n断电：扫描较慢，正视观察者可压制更久"):FString::Printf(TEXT("B 供电 OFF · E 恢复\n扫描×%.2f · B区正视压制×%.2f"),Config->PowerScanMultiplier,Config->PowerObserveMultiplier); }
void AAnomalyEnvironmentController::Tick(float Delta)
{
    Super::Tick(Delta);
    TickEvents();
    if(!Config || !Config->bEnableChamber) return;
    if(ChamberPhase==EAnomalyChamberPhase::Triggered)
    {
        if(!Active() || !Held.IsValid() || GetWorld()->GetTimeSeconds()>=HoldUntil)
        { CancelEvents(TEXT("离开关卡")); if(Held.IsValid()) Held->SetEnvironmentStasis(false); Held.Reset(); ChamberPhase=EAnomalyChamberPhase::Spent; }
    }
    else if(ChamberPhase!=EAnomalyChamberPhase::Spent)
    { bool Observer=false; ChamberPhase=Active() && ChamberTarget(Observer)?EAnomalyChamberPhase::Armed:EAnomalyChamberPhase::Idle; }
}
void AAnomalyEnvironmentController::EndPlay(const EEndPlayReason::Type Reason)
{ CancelEvents(TEXT("离开关卡")); if(Held.IsValid()) Held->SetEnvironmentStasis(false); Held.Reset(); HoldUntil=0; bPowerOn=true; ApplyLights(); Lights.Empty(); InitialIntensities.Empty(); Super::EndPlay(Reason); }

AAnomalyThreatCharacter* AAnomalyEnvironmentController::ChamberTarget(bool& ObserverOnly) const
{
    ObserverOnly=false; AAnomalyThreatCharacter* Target=nullptr; float Best=MAX_flt;
    if(!Config) return nullptr;
    for(TActorIterator<AAnomalyThreatCharacter> It(GetWorld());It;++It)
    {
        if(It->bResolved || !It->bThreatActive) continue;
        const float Distance=FVector::DistSquared2D(It->GetActorLocation(),Config->ChamberCenter);
        if(Distance>FMath::Square(Config->ChamberRadius) || FMath::Abs(It->GetActorLocation().Z-Config->ChamberCenter.Z)>180) continue;
        if(Cast<AAnomalyObserverCharacter>(*It)) { ObserverOnly=true; continue; }
        if(Distance<Best) { Target=*It; Best=Distance; }
    }
    return Target;
}
bool AAnomalyEnvironmentController::TriggerChamber(AAnomalyEnvironmentTerminal* Terminal,AActor* Player,FString& Reason)
{
    if(!Active() || !Config->bEnableChamber || !Terminal || Terminal->Kind!=EAnomalyEnvironmentKind::Chamber || !Terminal->ValidatePlayer(Player))
    { Reason=TEXT("请靠近并对准收容舱控制台"); return false; }
    if(ChamberPhase==EAnomalyChamberPhase::Triggered || ChamberPhase==EAnomalyChamberPhase::Spent)
    { Reason=TEXT("本局收容舱已使用"); return false; }
    bool ObserverOnly=false; auto Target=ChamberTarget(ObserverOnly);
    if(!Target) { Reason=ObserverOnly?TEXT("观察者无法被收容舱控制；正视眼部压制它"):TEXT("标记区域内没有活动追逐者"); return false; }
    Coordinator()->RecordTelemetry(TEXT("EventResponse"),TEXT("Chamber stasis"));
    Held=Target; HoldUntil=GetWorld()->GetTimeSeconds()+Config->ChamberSeconds;
    ChamberPhase=EAnomalyChamberPhase::Triggered; Target->SetEnvironmentStasis(true);
    Reason=FString::Printf(TEXT("封锁 %.1f 秒 · 本局仅一次 · 没有额外奖励"),Config->ChamberSeconds);
    if(auto C=Coordinator()) C->EmitFeedback(TEXT("Containment"));
    UE_LOG(LogTemp,Display,TEXT("[Environment] Run=%s Chamber=Triggered Target=%s Seconds=%.2f"),*Coordinator()->RunId.ToString(),*Target->GetName(),Config->ChamberSeconds);
    return true;
}
FString AAnomalyEnvironmentController::DescribeChamber() const
{
    if(ChamberPhase==EAnomalyChamberPhase::Spent) return TEXT("C 收容舱 · 本局已使用");
    if(ChamberPhase==EAnomalyChamberPhase::Triggered) return FString::Printf(TEXT("C 封锁 %.1f 秒 · 仅暂停追逐者"),FMath::Max(0.f,HoldUntil-GetWorld()->GetTimeSeconds()));
    return ChamberPhase==EAnomalyChamberPhase::Armed?TEXT("C 收容舱已就绪 · E 封锁追逐者\n本局一次；观察者免疫"):TEXT("C 收容舱 · 等待追逐者进入绿色区域\n本局一次；观察者免疫");
}

TArray<FAnomalyEventSpec> UAnomalyEnvironmentConfig::BuildEventPlan(int32 Seed) const
{
    TArray<FAnomalyEventSpec> Plan; if(!bEnableEvents || !Validate() || MaxEvents<=0) return Plan;
    FRandomStream Events(int32(uint32(Seed)^0x6d2b79f5u));
    if(Events.FRand()>=EventChance) return Plan;
    FAnomalyEventSpec First; First.Type=Events.RandRange(0,1)==0?EAnomalyDynamicEvent::PowerFluctuation:EAnomalyDynamicEvent::ContainmentAlarm;
    First.At=EventFirstDelay+Events.FRand()*4; First.Duration=EventSeconds; Plan.Add(First);
    if(MaxEvents>=2 && Events.FRand()<EventChance)
    { auto Second=First; Second.Type=First.Type==EAnomalyDynamicEvent::PowerFluctuation?EAnomalyDynamicEvent::ContainmentAlarm:EAnomalyDynamicEvent::PowerFluctuation;
      Second.At=First.At+EventWarningSeconds+EventSeconds+EventSpacing+Events.FRand()*4; Plan.Add(Second); }
    return Plan;
}
float AAnomalyEnvironmentController::ThreatSpeedMultiplier(const AAnomalyThreatCharacter* Target) const
{
    if(!Active() || EventPhase!=EAnomalyEventPhase::Active || CurrentEvent.Type!=EAnomalyDynamicEvent::ContainmentAlarm
        || !Target || Cast<AAnomalyObserverCharacter>(Target)) return 1.f;
    const auto P=Target->GetActorLocation();
    return P.X>-800 && P.X<800 && P.Y>-1500 && P.Y<-500?Config->AlarmSpeedMultiplier:1.f;
}
void AAnomalyEnvironmentController::ApplyAlarmLights()
{
    for(int32 I=0;I<AlarmLights.Num();++I) if(AlarmLights[I].IsValid())
        AlarmLights[I]->SetLightColor(CurrentEvent.Type==EAnomalyDynamicEvent::ContainmentAlarm && EventPhase!=EAnomalyEventPhase::Quiet
            ?(EventPhase==EAnomalyEventPhase::Warning?FLinearColor(1,.45f,.08f):FLinearColor(1,.12f,.04f)):InitialAlarmColours[I]);
}
bool AAnomalyEnvironmentController::StartEvent(const FAnomalyEventSpec& Spec)
{
    if(!Active() || !Config->bEnableEvents || bEventsCancelled || EventPhase!=EAnomalyEventPhase::Quiet
        || EventCount>=Config->MaxEvents || GetWorld()->GetTimeSeconds()<EventReadyAt
        || (Spec.Type!=EAnomalyDynamicEvent::PowerFluctuation && Spec.Type!=EAnomalyDynamicEvent::ContainmentAlarm)
        || !FMath::IsFinite(Spec.Duration) || Spec.Duration<2 || Spec.Duration>6) return false;
    Coordinator()->RecordTelemetry(TEXT("EventId"),FString::Printf(TEXT("%d Warning"),int32(Spec.Type)));
    CurrentEvent=Spec; ++EventCount; EventPhase=EAnomalyEventPhase::Warning;
    EventDeadline=GetWorld()->GetTimeSeconds()+Config->EventWarningSeconds; ApplyAlarmLights();
    if(auto C=Coordinator()) { C->Notify(DescribeEvent()); C->EmitFeedback(TEXT("Warning")); }
    UE_LOG(LogTemp,Display,TEXT("[Event] Run=%s Seed=%d Id=%d Phase=Warning Duration=%.2f"),*Coordinator()->RunId.ToString(),Coordinator()->RegionSeed,int32(Spec.Type),Spec.Duration); return true;
}
void AAnomalyEnvironmentController::EndEvent(const FString& Cause)
{
    if(EventPhase==EAnomalyEventPhase::Quiet) return;
    UE_LOG(LogTemp,Display,TEXT("[Event] Id=%d End=%s"),int32(CurrentEvent.Type),*Cause);
    if(auto C=Coordinator()) C->RecordTelemetry(TEXT("EventEnd"),Cause);
    EventPhase=EAnomalyEventPhase::Quiet; CurrentEvent=FAnomalyEventSpec(); bEventPowerOff=false;
    EventReadyAt=GetWorld()->GetTimeSeconds()+(Config?Config->EventSpacing:10); ApplyLights(); ApplyAlarmLights();
    for(TActorIterator<AAnomalyThreatCharacter> It(GetWorld());It;++It) if(It->bThreatActive && !It->bResolved) It->GetCharacterMovement()->MaxWalkSpeed=float(It->MoveSpeed);
}
void AAnomalyEnvironmentController::CancelEvents(const FString& Reason)
{ bEventsCancelled=true; EventPlan.Empty(); EndEvent(Reason); }
void AAnomalyEnvironmentController::TickEvents()
{
    if(!Active()) { if(EventPhase!=EAnomalyEventPhase::Quiet) CancelEvents(TEXT("局已结束")); return; }
    if(!Config->bEnableEvents || bEventsCancelled) return;
    auto C=Coordinator(); const float Now=GetWorld()->GetTimeSeconds();
    if(!bPlanBuilt) { bPlanBuilt=true; RunStarted=Now; EventPlan=Config->BuildEventPlan(C->RegionSeed); }
    if(EventPhase==EAnomalyEventPhase::Quiet && EventPlan.IsValidIndex(NextEvent) && Now>=RunStarted+EventPlan[NextEvent].At && Now>=EventReadyAt)
    { if(StartEvent(EventPlan[NextEvent])) ++NextEvent; }
    if(EventPhase==EAnomalyEventPhase::Warning && Now>=EventDeadline)
    {
        // Do not stack a faster pursuit into the box's spawn-warning frame.
        if(C->GetRoundPhase()==EAnomalyRoundPhase::ThreatWarning || C->GetRoundPhase()==EAnomalyRoundPhase::ResolvingOutcome) return;
        EventPhase=EAnomalyEventPhase::Active; EventDeadline=Now+CurrentEvent.Duration;
        bEventPowerOff=CurrentEvent.Type==EAnomalyDynamicEvent::PowerFluctuation; ApplyLights(); ApplyAlarmLights();
        C->Notify(DescribeEvent()); UE_LOG(LogTemp,Display,TEXT("[Event] Run=%s Id=%d Phase=Active"),*C->RunId.ToString(),int32(CurrentEvent.Type));
    }
    if(EventPhase==EAnomalyEventPhase::Active && Now>=EventDeadline) EndEvent(TEXT("持续时间结束"));
    if(EventPhase==EAnomalyEventPhase::Active && CurrentEvent.Type==EAnomalyDynamicEvent::ContainmentAlarm)
        for(TActorIterator<AAnomalyThreatCharacter> It(GetWorld());It;++It) if(It->bThreatActive && !It->bResolved)
            It->GetCharacterMovement()->MaxWalkSpeed=float(It->MoveSpeed)*ThreatSpeedMultiplier(*It);
}
FString AAnomalyEnvironmentController::DescribeEvent() const
{
    if(EventPhase==EAnomalyEventPhase::Quiet) return TEXT("");
    if(CurrentEvent.Type==EAnomalyDynamicEvent::PowerFluctuation)
        return EventPhase==EAnomalyEventPhase::Warning?TEXT("供电波动预警 · B终端可恢复供电"):TEXT("B供电波动 · 扫描较慢\n用配电终端恢复，或等待结束");
    return EventPhase==EAnomalyEventPhase::Warning?TEXT("C收容警报预警 · 准备利用收容舱"):TEXT("C收容警报 · 追逐者短暂加速\n利用收容舱或离开C区；观察者仍需正视");
}
