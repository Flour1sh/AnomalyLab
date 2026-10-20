#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AnomalyTelemetry.h"
#include "AnomalyRoundCoordinator.generated.h"

class AAnomalyBoxActor;
class AAnomalyThreatCharacter;
class USceneComponent;
class UAnomalyDecisionWidget;
class UAnomalyHealthComponent;
class UAnomalyExplorationWidget;
class UAnomalyItemDefinition;
class AAnomalyWorldPickup;
class UAnomalyInventoryComponent;
class USoundBase;
class UAudioComponent;
class UAnomalyRegionDefinition;
class UAnomalyProgressionConfig;
class UAnomalyProgressionSubsystem;
class UAnomalyObserverConfig;
class UAnomalyBalanceConfig;
class UAnomalyPlacementConfig;
class UUserWidget;

USTRUCT(BlueprintType)
struct FAnomalyRegionStats
{
    GENERATED_BODY()
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int32 OpenCount = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int32 ScanCount = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int64 Reward = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int32 Threat = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int32 Survive = 0;
};

UENUM(BlueprintType)
enum class EAnomalyPlayMode : uint8
{
    LegacyPrototype,
    Exploration
};

UENUM(BlueprintType)
enum class EAnomalyRunEndReason : uint8
{
    None,
    CashedOut,
    Failed,
    Error
};

UENUM(BlueprintType)
enum class EAnomalyRoundPhase : uint8
{
    Initializing, SpawningChoices, AwaitingSelection, ResolvingOutcome,
    ThreatWarning, ThreatActive, ThreatContainment, PostRoundDecision,
    RunCashedOut, RunFailed, Error, ReturningToExtraction, Preparation
};

USTRUCT(BlueprintType)
struct FAnomalyEndRunSnapshot
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) FGuid RunId;
    UPROPERTY(BlueprintReadOnly) EAnomalyRunEndReason Reason=EAnomalyRunEndReason::None;
    UPROPERTY(BlueprintReadOnly) int32 CashedOut=0;
    UPROPERTY(BlueprintReadOnly) int32 Lost=0;
    UPROPERTY(BlueprintReadOnly) int64 PermanentBalance=0;
    UPROPERTY(BlueprintReadOnly) int32 Rounds=0;
    UPROPERTY(BlueprintReadOnly) int32 Contained=0;
    UPROPERTY(BlueprintReadOnly) float Seconds=0;
    UPROPERTY(BlueprintReadOnly) FString Items;
    UPROPERTY(BlueprintReadOnly) bool bDurableCredit=false;
    UPROPERTY(BlueprintReadOnly) FString Detail;
};

/** Native round owner. Three candidates share one authoritative selection and result. */
UCLASS(Blueprintable)
class ANOMALYLAB_API AAnomalyRoundCoordinator : public AActor
{
    GENERATED_BODY()
public:
    AAnomalyRoundCoordinator();
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Observer") bool bEnableObserverPool=false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Balance") TObjectPtr<UAnomalyBalanceConfig> BalanceConfig;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Observer") TSubclassOf<AActor> ObserverClass;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Observer") TObjectPtr<UAnomalyObserverConfig> ObserverConfig;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Progression") bool bUsePreparation = false;
    /** Lab requires a single-use value-only transition claim. Legacy defaults false. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Level") bool bAwaitLevelLaunch = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Progression") TObjectPtr<UAnomalyProgressionConfig> ProgressionConfig;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Progression") FGuid RunId;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Progression") int32 DecoysRemaining=0;
    UFUNCTION(BlueprintPure, Category="Progression") bool IsPreparing() const;
    UFUNCTION(BlueprintCallable, Category="Progression") bool StartPreparedRun();
    bool PurchaseProduct(int32 Product,int32 ExpectedRevision,const FGuid& Request);
    bool UseDecoy();
    bool IsV05Lab() const { return bV05Lab; }
    void RecordTelemetry(const FString& Kind,const FString& Detail) { if(bV05Lab) Telemetry.Event(this,Kind,Detail); }
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Placement") TObjectPtr<UAnomalyPlacementConfig> PlacementConfig;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Placement") TArray<int32> LastSpawnPointIds;
    const FAnomalyEndRunSnapshot& GetEndSnapshot() const { return EndSnapshot; }
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Region") bool bUseRegionRules = false;
    /** Explicit spawn-slot mapping: left / middle / right. Never inferred from visuals. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Region") TArray<TObjectPtr<UAnomalyRegionDefinition>> RegionRules;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Region|Debug") bool bUseFixedRegionSeed = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Region|Debug") int32 RegionSeed = 26001;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Region") TMap<FName, FAnomalyRegionStats> RegionStats;
    void RecordRegionEvent(const AAnomalyBoxActor* Box, FName Event, int32 Value = 0);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="T20|Exploration") EAnomalyPlayMode PlayMode = EAnomalyPlayMode::LegacyPrototype;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="T20|Exploration") TSubclassOf<UAnomalyExplorationWidget> ExplorationWidgetClass;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="T20|Exploration", meta=(ClampMin="1", ClampMax="300")) float InteractionRange = 300.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="T20|Exploration") FVector EntranceLocation = FVector(0., 1700., 0.);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="T20|Exploration") FVector ExplorationThreatOffset = FVector(0., -300., -3.);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Loot") TArray<TObjectPtr<UAnomalyItemDefinition>> LootDefinitions;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Loot") TArray<TObjectPtr<AAnomalyWorldPickup>> WorldLoot;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Inventory") TObjectPtr<UAnomalyInventoryComponent> Inventory;
    UFUNCTION(BlueprintCallable, Category="Extraction") bool ConfirmExtraction(AActor* Interactor);
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Extraction") bool bSettlementDone = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Extraction") int32 SettlementCount = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Extraction") FString TerminalItems;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Feedback") TMap<FName, TObjectPtr<USoundBase>> FeedbackSounds;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Feedback") TMap<FName, int32> FeedbackCounts;
    UAudioComponent* EmitFeedback(FName Event);
    bool TryPickup(AActor* Interactor, AAnomalyWorldPickup* Pickup);
    AActor* TraceExplorationTarget(const AActor* Interactor) const;
    void HandleExploreInteract();
    void Notify(const FString& Message);
    AAnomalyWorldPickup* SpawnLoot(int32 Outcome, int32 Value, const FTransform& Transform, int32 SourceRound);
    virtual void Tick(float DeltaSeconds) override;
    AAnomalyBoxActor* TraceExplorationBox(const AActor* Interactor) const;
    bool ValidateBoxInteraction(const AActor* Interactor, const AAnomalyBoxActor* Box) const;
    /** Asset-generation helper, refuses game worlds and never changes editor preferences. */
    UFUNCTION(BlueprintCallable, Category="T20|Build", meta=(WorldContext="WorldContextObject"))
    static int32 BuildExplorationNavigation(UObject* WorldContextObject);
    UFUNCTION(BlueprintCallable, Category="Build") static void FinishAssetCompilation();
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Round") TSubclassOf<AAnomalyBoxActor> BoxClass;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Round|Spawn") TObjectPtr<USceneComponent> SpawnRoot;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Round|Spawn") TObjectPtr<USceneComponent> BoxPointLeft;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Round|Spawn") TObjectPtr<USceneComponent> BoxPointMiddle;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Round|Spawn") TObjectPtr<USceneComponent> BoxPointRight;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Round") TArray<TObjectPtr<AAnomalyBoxActor>> CandidateBoxes;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Round") TObjectPtr<AAnomalyBoxActor> SelectedBox;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Round") int32 RoundId = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Round") int32 MaxThreats = 2;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Round") double NextRoundDelay = 3.0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="T15|Threat") float ThreatWarningSeconds = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="T15|Threat") float ThreatSurvivalSeconds = 20.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="T15|Threat") float ContainmentMessageSeconds = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="T15|Threat") float ThreatSpawnRetryDelay = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="T15|Threat") int32 MaxThreatSpawnRetries = 3;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="T14|UI") TSubclassOf<UAnomalyDecisionWidget> DecisionWidgetClass;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="T14|Run") int32 CompletedRounds = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="T14|Run") int32 FinalRunValue = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="T15|Run") int32 LostRunValue = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="T14|Run") float FinalRunSeconds = 0.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="T14|Run") EAnomalyRunEndReason RunEndReason = EAnomalyRunEndReason::None;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Retry") double SpawnRetryDelay = 1.0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Retry") int32 MaxSpawnRetries = 3;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Debug") bool bDebugLogging = true;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Round") TObjectPtr<AAnomalyBoxActor> CurrentBox;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Round") TObjectPtr<AActor> CurrentOutcomeActor;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Round") TObjectPtr<AAnomalyThreatCharacter> CurrentSpider;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Round") int32 ThreatsResolved = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Round") int32 CurrentSpawnRetryCount = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Round") bool bCompleting = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Round") bool bAttackNotified = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Round") bool bPrototypeError = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="T15|Threat") int32 CurrentThreatSpawnRetryCount = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="T15|Threat") bool bThreatPursuitActive = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="T16|State") EAnomalyRoundPhase RoundPhase = EAnomalyRoundPhase::Initializing;

    UFUNCTION(BlueprintCallable, Category="Round") void SpawnInitialBox();
    UFUNCTION(BlueprintCallable, Category="Round") void SpawnNextBox();
    UFUNCTION(BlueprintCallable, Category="Round") void RetryBoxSpawn();
    UFUNCTION(BlueprintCallable, Category="Round") void CompleteCurrentOutcome();
    UFUNCTION(BlueprintCallable, Category="Round") void CleanupCurrentRound();
    UFUNCTION(BlueprintCallable, Category="Round") void EndRun();
    UFUNCTION(BlueprintCallable, Category="T14|Decision") void ContinueRun();
    UFUNCTION(BlueprintCallable, Category="T14|Decision") void CashOut();
    UFUNCTION(BlueprintPure, Category="T14|Decision") bool IsDecisionActive() const { return NativeState == 4; }
    UFUNCTION(BlueprintPure, Category="Round") int32 GetNativeRoundState() const { return NativeState; }
    UFUNCTION(BlueprintPure, Category="T16|State") EAnomalyRoundPhase GetRoundPhase() const { return RoundPhase; }
    UFUNCTION(BlueprintCallable, Category="Round") void FailWithError();
    bool TryLockSelection(AAnomalyBoxActor* Box);
    bool CanResolveBox(const AAnomalyBoxActor* Box) const;
    bool IsSelectableBox(const AAnomalyBoxActor* Box) const;

    UFUNCTION(BlueprintImplementableEvent, Category="Presentation") void PresentRoundState(int32 StateIndex);
    UFUNCTION(BlueprintImplementableEvent, Category="Presentation") void PresentRoundOutcome(int32 OutcomeIndex, AActor* SpawnedActor, bool bSpawnSucceeded);
    UFUNCTION(BlueprintImplementableEvent, Category="Presentation") void PresentThreatCount(int32 Count, int32 Maximum);
    UFUNCTION(BlueprintImplementableEvent, Category="Presentation") void PresentRoundAttack();
    UFUNCTION(BlueprintImplementableEvent, Category="Presentation") void PresentRunEnded(bool bError);
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
    friend struct FAnomalyV05Probe;
    bool bV05Lab=false;
    FAnomalyRunTelemetry Telemetry;
    UPROPERTY(Transient) TObjectPtr<UUserWidget> LoadingWidget;
    int32 V05Capacity=4,V05ChargeBonus=0;
    float V05Precision=0.f;
    FTimerHandle V05StartTimer;
    void InitializeV05Run();
    void BlockV05Restart();
    friend struct FAnomalyV04Probe;
    friend struct FAnomalyObserverProbe;
    friend class UAnomalyProgressionSubsystem;
    UPROPERTY(Transient) FAnomalyEndRunSnapshot EndSnapshot;
    UPROPERTY(Transient) TObjectPtr<UAnomalyProgressionSubsystem> Progression;
    UPROPERTY(Transient) TObjectPtr<AActor> DecoySource;
    int32 ShopSelection=0;
    FString ShopMessage;
    uint64 LastPurchaseFrame=MAX_uint64;
    float DecoyReadyAt=0.f;
    void ShopUp();
    void ShopDown();
    void ShopBuy();
    void HandleDecoyInput();
    FRandomStream RegionStream;
    // Index mapping intentionally matches the existing Blueprint enum until the v0.2 state expansion.
    int32 NativeState = 0; // Ready, Revealing, OutcomeActive, Ended
    TSet<int32> GeneratedRewardRounds;
    float DamageVeilUntil = 0.f;
    UFUNCTION() void HandleHealthChanged(int32 NewHealth, int32 Delta);
    bool bExtractionPending = false;
    bool bExtractionAuthorized = false;
    FTimerHandle ExtractionTimer;
    bool AtEntrance(const AActor* Player) const;
    void CommitExtraction();
    uint64 LastInteractionFrame = MAX_uint64;
    FString FeedbackMessage;
    float FeedbackUntil = 0.f;
    int32 NativeOutcome = 0;
    uint64 RoundGeneration = 0;
    bool bSpawningChoices = false;
    bool bRunClockStarted = false;
    bool bContainmentConfirmed = false;
    float RunStartTime = 0.f;
    float ThreatEndTime = 0.f;
    float OutcomeReadyTime = 0.f;
    UPROPERTY(Transient) TObjectPtr<UAnomalyDecisionWidget> DecisionWidget;
    UPROPERTY(Transient) TObjectPtr<UAnomalyHealthComponent> PlayerHealth;
    UPROPERTY(Transient) TObjectPtr<UAnomalyExplorationWidget> ExplorationWidget;
    FTimerHandle RewardTimer;
    FTimerHandle RetryTimer;
    FTimerHandle FallbackTimer;
    FTimerHandle WarningTimer;
    FTimerHandle ThreatDisplayTimer;
    FTimerHandle ContainmentTimer;
    FTimerHandle ThreatRetryTimer;
    void SetState(int32 State);
    void SetPhase(EAnomalyRoundPhase Phase);
    void ShowDecision();
    void FreezePlayer(bool bFreeze);
    bool BindPlayerHealth();
    void BeginThreatWarning();
    void ActivateCurrentThreat();
    void UpdateThreatDisplay();
    void RetryThreatSpawn();
    UFUNCTION() void HandleNativeOutcome(AActor* Box, int32 OutcomeIndex, AActor* SpawnedActor, bool bSpawnSucceeded);
    UFUNCTION() void HandleNativeThreatResolved(AActor* Spider);
    UFUNCTION() void HandleNativePlayerAttacked(AActor* Spider);
    UFUNCTION() void HandlePlayerDeath();
};
