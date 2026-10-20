#include "AnomalyScannerComponent.h"
#include "AnomalyScanWidget.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"
#include "InputCoreTypes.h"
#include "AnomalyRoundCoordinator.h"
#include "AnomalyEnvironment.h"
#include "AnomalyBoxActor.h"
#include "EngineUtils.h"
#include "Components/AudioComponent.h"

UAnomalyScannerComponent::UAnomalyScannerComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    // Observe this frame's movement, camera and interaction before accepting completion.
    PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
}

void UAnomalyScannerComponent::BeginPlay()
{
    Super::BeginPlay();
    InitializeRunResources();
    const APawn* Pawn = Cast<APawn>(GetOwner());
    if (!IsValid(Pawn) || !Pawn->IsLocallyControlled()) SetComponentTickEnabled(false);
}

bool UAnomalyScannerComponent::UsesCharges() const
{
    if (!GetWorld()) return false;
    for (TActorIterator<AAnomalyRoundCoordinator> It(GetWorld()); It; ++It)
        if (It->PlayMode == EAnomalyPlayMode::Exploration) return true;
    return false;
}
int32 UAnomalyScannerComponent::GetMaximum(EAnomalyEquipment Instrument) const
{
    const int32 Index = int32(Instrument);
    return MaxCharges.IsValidIndex(Index) ? FMath::Clamp(MaxCharges[Index], 0, 20) : 0;
}
int32 UAnomalyScannerComponent::GetRemaining(EAnomalyEquipment Instrument) const
{
    const int32 Index = int32(Instrument);
    return Remaining.IsValidIndex(Index) ? Remaining[Index] : 0;
}
void UAnomalyScannerComponent::InitializeRunResources(int32 CapacityBonus)
{
    CancelScan();
    Remaining.SetNum(3);
    for (int32 I=0; I<3; ++I) Remaining[I] = FMath::Clamp(GetMaximum(EAnomalyEquipment(I)) + CapacityBonus, 0, 20);
}
bool UAnomalyScannerComponent::CommitCharge(EAnomalyEquipment Instrument)
{
    check(IsInGameThread());
    if (!UsesCharges()) return true;
    const int32 Index = int32(Instrument);
    if (!Remaining.IsValidIndex(Index) || Remaining[Index] <= 0) return false;
    --Remaining[Index];
    UE_LOG(LogTemp, Display, TEXT("[Scan] Charged Instrument=%d Remaining=%d"), Index, Remaining[Index]);
    return true;
}

void UAnomalyScannerComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    CancelScan();
    Focus.Reset();
    if (IsValid(Panel)) Panel->RemoveFromParent();
    Panel = nullptr;
    Super::EndPlay(Reason);
}

void UAnomalyScannerComponent::CancelScan()
{
    if (IsValid(ScanAudio)) { ScanAudio->Stop(); ScanAudio = nullptr; }
    ScanningTarget.Reset();
    Elapsed = 0.f;
    Progress = 0.f;
    // Equipment/state/target changes require a fresh Q press, not a held old input.
    bRequireRelease = true;
}

AActor* UAnomalyScannerComponent::FindTarget() const
{
    const UCameraComponent* Camera = GetOwner()->FindComponentByClass<UCameraComponent>();
    if (!IsValid(Camera) || !GetWorld()) return nullptr;
    const FVector Start = Camera->GetComponentLocation();
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(AnomalyScan), false, GetOwner());
    if (!GetWorld()->LineTraceSingleByChannel(Hit, Start, Start + Camera->GetForwardVector() * ScanRange, ECC_Visibility, Params)) return nullptr;
    AActor* Target = Hit.GetActor();
    const IAnomalyScanTarget* Scan = Cast<IAnomalyScanTarget>(Target);
    return IsValid(Target) && Scan && Scan->CanScan() ? Target : nullptr;
}

void UAnomalyScannerComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTick)
{
    Super::TickComponent(DeltaTime, TickType, ThisTick);
    ACharacter* Character = Cast<ACharacter>(GetOwner());
    APlayerController* PC = IsValid(Character) ? Cast<APlayerController>(Character->GetController()) : nullptr;
    UAnomalyEquipmentComponent* Equipment = GetOwner()->FindComponentByClass<UAnomalyEquipmentComponent>();
    if (!IsValid(PC) || !IsValid(Equipment)) { CancelScan(); return; }
    if (!Panel && PanelClass)
    {
        Panel = CreateWidget<UAnomalyScanWidget>(PC, PanelClass);
        if (Panel) Panel->AddToViewport(5);
    }
    const bool bEnabled = IsValid(Character->GetCharacterMovement())
        && Character->GetCharacterMovement()->MovementMode != MOVE_None;
    const bool bQ = PC->IsInputKeyDown(EKeys::Q);
    if (!bQ) { CancelScan(); bRequireRelease = false; }
    AActor* Target = bEnabled ? FindTarget() : nullptr;
    if (Focus.Get() != Target)
    {
        if (ScanningTarget.IsValid()) CancelScan();
        Focus = Target;
    }
    const EAnomalyEquipment Instrument = Equipment->GetEffectiveEquipment();
    if (!bEnabled || !Target || !Equipment->IsScannerEquipped() || PC->WasInputKeyJustPressed(EKeys::E)) CancelScan();
    else if (bQ && !bRequireRelease)
    {
        IAnomalyScanTarget* Scan = Cast<IAnomalyScanTarget>(Target);
        if (!Scan->GetCachedReading(Instrument).bScanned)
        {
            if (UsesCharges() && GetRemaining(Instrument) <= 0) { CancelScan(); Present(Instrument, bEnabled); return; }
            if (!ScanningTarget.IsValid())
            {
                ScanAudio = Feedback(TEXT("ScanStart"));
                ScanningTarget = Target;
                auto Environment=AAnomalyEnvironmentController::Find(GetWorld());
                ActiveScanSeconds=ScanDuration*(Environment?Environment->ScanMultiplier(Cast<AAnomalyBoxActor>(Target)):1.f);
                ScanningInstrument = Instrument;
                Elapsed = 0.f;
            }
            else if (ScanningInstrument != Instrument) CancelScan();
            else
            {
                Elapsed += DeltaTime;
                Progress = FMath::Clamp(Elapsed / FMath::Max(ActiveScanSeconds, .001f), 0.f, 1.f);
                if (Progress >= 1.f)
                {
                    FAnomalyScanReading Reading;
                    if (Scan->CompleteScan(Instrument, Reading))
                    {
                        Feedback(TEXT("ScanComplete"));
                        UE_LOG(LogTemp, Display, TEXT("[Scan] Completed Target=%s Instrument=%d"), *Target->GetName(), int32(Instrument));
                    }
                    CancelScan();
                }
            }
        }
    }
    Present(Instrument, bEnabled);
}

void UAnomalyScannerComponent::Present(EAnomalyEquipment Instrument, bool bEnabled)
{
    if (!Panel) return;
    const IAnomalyScanTarget* Scan = Cast<IAnomalyScanTarget>(Focus.Get());
    FString Summary = TEXT("当前箱子 · 扫描记录\n");
    const TCHAR* Labels[] = {TEXT("高价值金额"), TEXT("威胁可能性"), TEXT("高价值可能性")};
    for (int32 Index = 0; Index < 3 && Scan; ++Index)
    {
        const FAnomalyScanReading Reading = Scan->GetCachedReading(static_cast<EAnomalyEquipment>(Index));
        Summary += FString::Printf(TEXT("\n%s："), Labels[Index]);
        if (!Reading.bScanned) Summary += TEXT("未扫描\n");
        else
        {
            Summary += Index == 0 ? FString::Printf(TEXT("$%lld – $%lld"), Reading.ValueMin, Reading.ValueMax) : Reading.Level.ToString();
            Summary += TEXT("\n可靠性：") + Reading.Reliability.ToString() + TEXT("\n");
        }
    }
    Summary += TEXT("\n金额仅指高价值结果。\n等级不保证本次结果。");
    const TCHAR* Names[] = {TEXT("金属价值探测仪"), TEXT("生物探测仪"), TEXT("物质分析仪"), TEXT("枪（武器功能尚未启用）")};
    FString Hint = FString::Printf(TEXT("%s  |  1 切换仪器  ·  2 装备枪\n"), Names[static_cast<uint8>(Instrument)]);
    if (Instrument != EAnomalyEquipment::Gun && UsesCharges())
        Hint += FString::Printf(TEXT("扫描剩余：%d 次（本局）\n"), GetRemaining(Instrument));
    Hint += Instrument == EAnomalyEquipment::Gun ? TEXT("装备扫描仪后可扫描")
        : !Scan ? TEXT("对准 300 厘米内的未开启箱子")
        : Scan->GetCachedReading(Instrument).bScanned ? TEXT("当前仪器已扫描 · 读数已保存  |  E 开箱")
        : UsesCharges() && GetRemaining(Instrument) <= 0 ? TEXT("扫描次数已耗尽 · 缓存可免费查看  |  E 直接开箱")
        : Progress > 0.f ? FString::Printf(TEXT("扫描中 %d%% · 保持对准并按住 Q"), FMath::FloorToInt(Progress * 100.f))
        : FString::Printf(TEXT("按住 Q %.2f 秒扫描  |  E 直接开箱"),ScanDuration*(AAnomalyEnvironmentController::Find(GetWorld())?AAnomalyEnvironmentController::Find(GetWorld())->ScanMultiplier(Cast<AAnomalyBoxActor>(Focus.Get())):1.f));
    // UMG changes only on presentation changes; no widget property bindings.
    const FString Key = Summary + Hint + FString::Printf(TEXT("|%d|%d|%.4f"), Scan != nullptr, bEnabled, Progress);
    if (Key != LastPresentation)
    {
        Panel->Present(Summary, Hint, Progress, Scan != nullptr, bEnabled);
        LastPresentation = Key;
    }
}

UAudioComponent* UAnomalyScannerComponent::Feedback(FName Event)
{
    for (TActorIterator<AAnomalyRoundCoordinator> It(GetWorld()); It; ++It)
        if (It->PlayMode == EAnomalyPlayMode::Exploration) return It->EmitFeedback(Event);
    return nullptr;
}
