#include "AnomalyHub.h"
#include "AnomalyProgressionSubsystem.h"
#include "AnomalyProgressionConfig.h"
#include "AnomalyTransitionSubsystem.h"
#include "AnomalyLoadingWidget.h"
#include "Camera/CameraComponent.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InputComponent.h"
#include "Components/TextBlock.h"
#include "Components/Image.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerInput.h"
#include "GameFramework/InputSettings.h"
#include "InputCoreTypes.h"

AAnomalyHubCharacter::AAnomalyHubCharacter()
{
    GetCapsuleComponent()->InitCapsuleSize(34.f,96.f);
    SetCanBeDamaged(false);
    GetCharacterMovement()->MaxWalkSpeed=350.f;
    GetCharacterMovement()->JumpZVelocity=420.f;
    GetCharacterMovement()->AirControl=.6f;
    GetCharacterMovement()->MaxAcceleration=2048.f;
    GetCharacterMovement()->BrakingDecelerationWalking=2048.f;
    Camera=CreateDefaultSubobject<UCameraComponent>(TEXT("HubCamera"));
    Camera->SetupAttachment(GetCapsuleComponent());
    Camera->SetRelativeLocation(FVector(0,0,64));
    Camera->bUsePawnControlRotation=true;
    Camera->FieldOfView=90.f;
}
void AAnomalyHubCharacter::SetupPlayerInputComponent(UInputComponent* Input)
{
    Super::SetupPlayerInputComponent(Input);
    if(auto PC=Cast<APlayerController>(Controller)) if(PC->PlayerInput)
    {
        PC->PlayerInput->AddAxisMapping(FInputAxisKeyMapping(TEXT("HubForward"),EKeys::W,1.f));
        PC->PlayerInput->AddAxisMapping(FInputAxisKeyMapping(TEXT("HubForward"),EKeys::S,-1.f));
        PC->PlayerInput->AddAxisMapping(FInputAxisKeyMapping(TEXT("HubRight"),EKeys::D,1.f));
        PC->PlayerInput->AddAxisMapping(FInputAxisKeyMapping(TEXT("HubRight"),EKeys::A,-1.f));
    }
    Input->BindAxis(TEXT("HubForward"),this,&AAnomalyHubCharacter::Forward);
    Input->BindAxis(TEXT("HubRight"),this,&AAnomalyHubCharacter::Right);
    Input->BindAxisKey(EKeys::MouseX,this,&AAnomalyHubCharacter::Turn);
    Input->BindAxisKey(EKeys::MouseY,this,&AAnomalyHubCharacter::Look);
    Input->BindKey(EKeys::SpaceBar,IE_Pressed,this,&ACharacter::Jump);
    Input->BindKey(EKeys::SpaceBar,IE_Released,this,&ACharacter::StopJumping);
}
void AAnomalyHubCharacter::Forward(float V) { if(Controller) AddMovementInput(FRotator(0,Controller->GetControlRotation().Yaw,0).Vector(),V); }
void AAnomalyHubCharacter::Back(float V) { Forward(-V); }
void AAnomalyHubCharacter::Right(float V) { if(Controller) AddMovementInput(FRotationMatrix(FRotator(0,Controller->GetControlRotation().Yaw,0)).GetUnitAxis(EAxis::Y),V); }
void AAnomalyHubCharacter::Left(float V) { Right(-V); }
void AAnomalyHubCharacter::Turn(float V) { AddControllerYawInput(V*.4f); }
void AAnomalyHubCharacter::Look(float V) { AddControllerPitchInput(-V*.4f); }

AAnomalyHubTerminal::AAnomalyHubTerminal()
{
    InteractionBounds=CreateDefaultSubobject<UBoxComponent>(TEXT("TerminalBounds"));
    SetRootComponent(InteractionBounds);
    InteractionBounds->InitBoxExtent(FVector(50,45,70));
    InteractionBounds->SetCollisionProfileName(TEXT("BlockAll"));
    Visual=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("TerminalVisual"));
    Visual->SetupAttachment(InteractionBounds);
    Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Visual->SetCanEverAffectNavigation(false);
}
FString AAnomalyHubTerminal::GetTitle() const
{
    switch(Kind) {
    case EAnomalyHubTerminalKind::Shop: return TEXT("商店 · 装备目录");
    case EAnomalyHubTerminalKind::Loadout: return TEXT("整备 · 携带概览");
    case EAnomalyHubTerminalKind::Departure: return TEXT("出发 · 实验室气闸");
    default: return TEXT("战报 · 上次探索"); }
}
void UAnomalyHubWidget::Present(const FString& Focus,const FString& Panel)
{
    if(bTextReady && LastFocus==Focus && LastPanel==Panel) return;
    LastFocus=Focus; LastPanel=Panel; bTextReady=true;
    if(HubTitle) HubTitle->SetText(FText::FromString(TEXT("ANOMALY LAB  /  安全基地\n整备 · 查看装备 · 规划下一次探索")));
    if(HubGuide) HubGuide->SetText(FText::FromString(TEXT("WASD 移动 · 鼠标观察 · 空格跳跃\n对准终端按 E 查看 · ESC 关闭")));
    if(HubFocus) HubFocus->SetText(FText::FromString(Focus));
    if(HubPanel) { HubPanel->SetText(FText::FromString(Panel)); HubPanel->SetVisibility(Panel.IsEmpty()?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible); }
    if(PanelBacking) PanelBacking->SetVisibility(Panel.IsEmpty()?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
}
AAnomalyHubPlayerController::AAnomalyHubPlayerController()
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.TickInterval=0.f; // Controller input must run every frame, including movement axes.
}
void AAnomalyHubPlayerController::BeginPlay()
{
    Super::BeginPlay();
    bShowMouseCursor=false; SetInputMode(FInputModeGameOnly());
    Progression=GetGameInstance()->GetSubsystem<UAnomalyProgressionSubsystem>();
    auto Config=LoadObject<UAnomalyProgressionConfig>(nullptr,TEXT("/Game/Prototype/Data/DA_ProgressionConfig.DA_ProgressionConfig"));
    FString Reason;
    if(!Progression || !Progression->Configure(Config,Reason)) UE_LOG(LogTemp,Error,TEXT("[Hub] Meta configuration unavailable: %s"),*Reason);
    GetGameInstance()->GetSubsystem<UAnomalyTransitionSubsystem>()->EnterHub(this);
    auto Class=LoadClass<UAnomalyHubWidget>(nullptr,TEXT("/Game/Prototype/V05/UI/WBP_Hub.WBP_Hub_C"));
    if(Class) { Widget=CreateWidget<UAnomalyHubWidget>(this,Class); if(Widget) { Widget->AddToViewport(20); Widget->Present(TEXT(""),TEXT("")); } }
    if(!Widget) UE_LOG(LogTemp,Error,TEXT("[Hub] Hub widget unavailable"));
    const auto& Last=GetGameInstance()->GetSubsystem<UAnomalyTransitionSubsystem>()->GetResult();
    if(Last.Reason!=EAnomalyRunEndReason::None)
    { OpenPanel=int32(EAnomalyHubTerminalKind::Report); PanelText=DescribeTerminal(EAnomalyHubTerminalKind::Report);
      SetIgnoreMoveInput(true); SetIgnoreLookInput(true); if(Widget) Widget->Present(TEXT(""),PanelText); }
    UE_LOG(LogTemp,Display,TEXT("[Hub] Safe world ready, report reads immutable result."));
}
void AAnomalyHubPlayerController::SetupInputComponent()
{
    Super::SetupInputComponent();
    InputComponent->BindKey(EKeys::E,IE_Pressed,this,&AAnomalyHubPlayerController::Interact);
    InputComponent->BindKey(EKeys::Escape,IE_Pressed,this,&AAnomalyHubPlayerController::ClosePanel);
    InputComponent->BindKey(EKeys::Enter,IE_Pressed,this,&AAnomalyHubPlayerController::ConfirmPanel);
    InputComponent->BindKey(EKeys::Up,IE_Pressed,this,&AAnomalyHubPlayerController::ShopUp);
    InputComponent->BindKey(EKeys::Down,IE_Pressed,this,&AAnomalyHubPlayerController::ShopDown);
}
AAnomalyHubTerminal* AAnomalyHubPlayerController::TraceTerminal() const
{
    if(!IsValid(GetPawn())) return nullptr;
    FVector Eye; FRotator Rotation; GetPlayerViewPoint(Eye,Rotation);
    FHitResult Hit; FCollisionQueryParams Params(SCENE_QUERY_STAT(HubTerminal),false,GetPawn());
    return GetWorld()->LineTraceSingleByChannel(Hit,Eye,Eye+Rotation.Vector()*300.f,ECC_Visibility,Params)?Cast<AAnomalyHubTerminal>(Hit.GetActor()):nullptr;
}
void AAnomalyHubPlayerController::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    auto Travel=GetGameInstance()->GetSubsystem<UAnomalyTransitionSubsystem>();
    if(Travel->GetPhase()==EAnomalyTravelPhase::LoadingLab && !LoadingWidget)
    { LoadingWidget=CreateWidget<UAnomalyLoadingWidget>(this); if(LoadingWidget) LoadingWidget->AddToViewport(1000); }
    if(Travel->GetPhase()==EAnomalyTravelPhase::HubReady && LoadingWidget)
    { LoadingWidget->RemoveFromParent(); LoadingWidget=nullptr; ResetIgnoreMoveInput(); ResetIgnoreLookInput();
      if(OpenPanel>=0) { SetIgnoreMoveInput(true); SetIgnoreLookInput(true); PanelText=DescribeTerminal(EAnomalyHubTerminalKind(OpenPanel))+TEXT("\n")+Travel->GetMessage(); } }
    auto Target=OpenPanel<0?TraceTerminal():nullptr;
    if(Widget) Widget->Present(Target?TEXT("E  ")+Target->GetTitle():TEXT(""),PanelText);
}
FString AAnomalyHubPlayerController::DescribeTerminal(EAnomalyHubTerminalKind Kind) const
{
    if(!Progression || !Progression->GetConfig()) return TEXT("装备数据暂不可用\n请返回后重试。\n\nESC 关闭");
    if(Progression->IsPersistenceBlocked()) return TEXT("存档需要恢复，原文件已保留。\n购买和出发已禁用。\n\n")+Progression->GetLoadMessage()+TEXT("\n\n请恢复验证过的备份，或在新目录显式导入旧档。\nESC 关闭");
    const auto& M=Progression->GetProgress(); const auto C=Progression->GetConfig();
    const FString Loadout=FString::Printf(TEXT("永久余额  $%lld\n扫描电池  %d / 2 · 精度模块  %d / 2\n背包容量  %d 格 · 预存诱饵  %d\n\n永久升级会保留，局内携带物品须撤离后兑现。"),M.Currency,M.BatteryLevel,M.PrecisionLevel,M.BackpackLevel>0?5:4,M.StoredDecoys);
    switch(Kind) {
    case EAnomalyHubTerminalKind::Shop:
        {
            const TCHAR* Names[]={TEXT("扫描电池 +1次/仪器"),TEXT("精度模块 -25%干扰"),TEXT("背包 4→5 格"),TEXT("一次性诱饵 · 观察者无效")};
            const int32 Levels[]={M.BatteryLevel,M.PrecisionLevel,M.BackpackLevel,M.StoredDecoys};
            FString Text=FString::Printf(TEXT("基地商店 · 永久余额 $%lld\n成功撤离才能兑现携带物品\n\n"),M.Currency);
            for(int32 I=0;I<4;++I) Text+=FString::Printf(TEXT("%s %s\n   $%d · %d/%d\n"),I==ShopSelection?TEXT("▶"):TEXT("  "),Names[I],C->Prices[I],Levels[I],C->MaxLevels[I]);
            return Text+TEXT("\n↑ ↓ 选择 · ENTER 购买 · ESC 关闭\n")+ShopMessage+TEXT("\n")+(Progression->GetLoadMessage().Contains(TEXT("备份")) || Progression->GetLoadMessage().Contains(TEXT("导入"))?Progression->GetLoadMessage():TEXT(""));
        }
    case EAnomalyHubTerminalKind::Loadout: return TEXT("整备 / 携带概览\n\n")+Loadout+TEXT("\n\nESC 关闭");
    case EAnomalyHubTerminalKind::Departure: return TEXT("探索目的地 / 实验室\n\nA 分析区 · B 动力区 · C 收容区\n\nENTER 确认携带并出发。\n成功撤离才能带出收益；死亡会损失本局携带物品。\n\n")+Loadout+TEXT("\n\nESC 关闭");
    default:
        {
            auto Travel=GetGameInstance()->GetSubsystem<UAnomalyTransitionSubsystem>(); const auto& R=Travel->GetResult();
            if(!R.RunId.IsValid() && R.Reason==EAnomalyRunEndReason::None) return TEXT("上次探索 / 行动报告\n\n暂无探索记录。\n\nESC 关闭");
            return FString::Printf(TEXT("上次探索 / 行动报告\n\n%s · 用时 %.1f 秒\n带出 $%d · 损失 $%d\n永久余额 $%lld\n完成 %d 回合 · 收容 %d 次\n\n%s\n%s\n\nESC 关闭"),
                R.Reason==EAnomalyRunEndReason::CashedOut?TEXT("成功撤离"):R.Reason==EAnomalyRunEndReason::Failed?TEXT("死亡，携带物品丢失"):TEXT("技术异常，未兑现"),
                R.Seconds,R.CashedOut,R.Lost,Progression->GetProgress().Currency,R.Rounds,R.Contained,*(R.Detail+TEXT("\n")+R.Items),R.bDurableCredit?TEXT("永久收益已保存"):TEXT("本局未新增永久收入"));
        } }
}
void AAnomalyHubPlayerController::Interact()
{
    if(OpenPanel>=0) return;
    if(auto Terminal=TraceTerminal()) {
        OpenPanel=int32(Terminal->Kind); PanelText=DescribeTerminal(Terminal->Kind);
        UE_LOG(LogTemp,Display,TEXT("[Hub] Opened read-only panel %d"),OpenPanel);
        SetIgnoreMoveInput(true); SetIgnoreLookInput(true);
        if(Widget) Widget->Present(TEXT(""),PanelText);
    }
}
void AAnomalyHubPlayerController::ClosePanel()
{
    if(OpenPanel<0) return;
    OpenPanel=-1; PanelText.Reset(); ResetIgnoreMoveInput(); ResetIgnoreLookInput();
    if(Widget) Widget->Present(TEXT(""),TEXT(""));
}
void AAnomalyHubPlayerController::EndPlay(const EEndPlayReason::Type Reason)
{
    if(LoadingWidget) LoadingWidget->RemoveFromParent(); LoadingWidget=nullptr;
    ClosePanel(); if(Widget) Widget->RemoveFromParent(); Widget=nullptr; Progression=nullptr;
    Super::EndPlay(Reason);
}
AAnomalyHubGameMode::AAnomalyHubGameMode()
{
    DefaultPawnClass=AAnomalyHubCharacter::StaticClass();
    PlayerControllerClass=AAnomalyHubPlayerController::StaticClass(); HUDClass=nullptr;
}

bool AAnomalyHubPlayerController::CanConfirmDeparture() const
{
    auto Target=TraceTerminal();
    return OpenPanel==int32(EAnomalyHubTerminalKind::Departure) && Target && Target->Kind==EAnomalyHubTerminalKind::Departure;
}
bool AAnomalyHubPlayerController::ConfirmDeparture()
{
    FString Reason;
    bool Accepted=GetGameInstance()->GetSubsystem<UAnomalyTransitionSubsystem>()->RequestLaunch(this,Reason);
    if(!Accepted) PanelText=DescribeTerminal(EAnomalyHubTerminalKind::Departure)+TEXT("\n")+Reason;
    return Accepted;
}
void AAnomalyHubPlayerController::ConfirmPanel()
{ if(OpenPanel==int32(EAnomalyHubTerminalKind::Departure)) ConfirmDeparture();
  else if(OpenPanel==int32(EAnomalyHubTerminalKind::Shop)) PurchaseSelection(); }

bool AAnomalyHubPlayerController::CanPurchase() const
{
    auto Target=TraceTerminal();
    return OpenPanel==int32(EAnomalyHubTerminalKind::Shop) && Target && Target->Kind==EAnomalyHubTerminalKind::Shop;
}
bool AAnomalyHubPlayerController::PurchaseSelection()
{
    if(!Progression || !CanPurchase() || LastPurchaseFrame==GFrameCounter) return false;
    bool Bought=Progression->PurchaseHub(this,ShopSelection,Progression->GetProgress().Revision,FGuid::NewGuid(),ShopMessage);
    LastPurchaseFrame=GFrameCounter; PanelText=DescribeTerminal(EAnomalyHubTerminalKind::Shop);
    return Bought;
}
void AAnomalyHubPlayerController::ShopUp()
{ if(OpenPanel==int32(EAnomalyHubTerminalKind::Shop)) { ShopSelection=(ShopSelection+3)%4; ShopMessage.Reset(); PanelText=DescribeTerminal(EAnomalyHubTerminalKind::Shop); } }
void AAnomalyHubPlayerController::ShopDown()
{ if(OpenPanel==int32(EAnomalyHubTerminalKind::Shop)) { ShopSelection=(ShopSelection+1)%4; ShopMessage.Reset(); PanelText=DescribeTerminal(EAnomalyHubTerminalKind::Shop); } }
