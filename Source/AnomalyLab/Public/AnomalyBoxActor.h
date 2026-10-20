#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AnomalyBoxDefinition.h"
#include "AnomalyScanTarget.h"
#include "AnomalyBoxActor.generated.h"

class UAnimationAsset;
class USoundBase;
class AAnomalyRoundCoordinator;
class UStaticMesh;
class UStaticMeshComponent;
class UUserWidget;
class UAnomalyRegionDefinition;
class UAnomalyObserverConfig;
class UAnomalyBalanceConfig;
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FNativeBoxOpened, AActor*, Box);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_FourParams(FNativeBoxOutcome, AActor*, Box, int32, OutcomeIndex, AActor*, SpawnedActor, bool, bSpawnSucceeded);

/** Gameplay base. Existing BP_AnomalyBox keeps its meshes and legacy interface/presentation adapters. */
UCLASS(Blueprintable)
class ANOMALYLAB_API AAnomalyBoxActor : public AActor, public IAnomalyScanTarget
{
    GENERATED_BODY()
public:
    AAnomalyBoxActor();
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Box") FName DefinitionID;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Box") FName ResolvedDefinitionID;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Box") bool bDefinitionInitialized = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Box") bool bDefinitionValid = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Box") bool bOpened = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Box") bool bResolved = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Box") bool bSelectionLocked = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Box") int32 RoundId = 0;
    UPROPERTY(Transient) bool bExplorationSpawn = false;
    UPROPERTY(Transient, BlueprintReadOnly, Category="Region") TObjectPtr<UAnomalyRegionDefinition> RegionDefinition;
    UPROPERTY(Transient) FVector ExplorationThreatOffset = FVector(0., -300., -3.);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Box") double RevealDelay = 1.0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Debug") bool bDebugLogging = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Debug") bool bForceOutcome = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Debug") bool bUseFixedSeeds = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Debug") int32 ConfigurationSeed = 11001;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Debug") int32 OutcomeSeed = 11002;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Reward") int32 HighValueAmount = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Reward") int32 TrashAmount = 3;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Assets") TSubclassOf<AActor> HighValueClass;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Assets") TSubclassOf<AActor> TrashClass;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Assets") TSubclassOf<AActor> ThreatClass;
    UPROPERTY(Transient) bool bUseObserverPool=false;
    UPROPERTY(Transient) TSubclassOf<AActor> ObserverClass;
    UPROPERTY(Transient) TObjectPtr<UAnomalyObserverConfig> ObserverConfig;
    UPROPERTY(Transient) TObjectPtr<UAnomalyBalanceConfig> BalanceConfig;
    AActor* SpawnThreatActor();
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Assets") TObjectPtr<UAnimationAsset> OpeningAnimation;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Assets") TObjectPtr<USoundBase> OpeningSound;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Assets") TMap<FName, TObjectPtr<UAnomalyBoxDefinition>> Definitions;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Box") TObjectPtr<UAnomalyBoxDefinition> DefinitionAsset;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Box") int32 OutcomeRoll = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Box") TObjectPtr<AActor> OpeningInteractor;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="T11E|Visual") TObjectPtr<UStaticMesh> MetalBraceMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="T11E|Visual") TObjectPtr<UStaticMesh> WarningMarkerMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="T11E|Visual") TObjectPtr<UStaticMesh> WearPatchMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="T13|Visual") TSubclassOf<UUserWidget> LockedWidgetClass;

    UPROPERTY(BlueprintAssignable) FNativeBoxOpened OnNativeBoxOpened;
    UPROPERTY(BlueprintAssignable) FNativeBoxOutcome OnNativeOutcomeResolved;
    UFUNCTION(BlueprintCallable, Category="Box") bool NativeInteract(AActor* Interactor, int32 DebugOutcomeIndex = 0);
    UFUNCTION(BlueprintCallable, Category="Box") void InitializeDefinition();
    UFUNCTION(BlueprintPure, Category="Box") int32 NativeSelectOutcome(double UnitRoll) const;
    UFUNCTION(BlueprintImplementableEvent, Category="Presentation") void PresentBoxOpened(AActor* Box);
    UFUNCTION(BlueprintImplementableEvent, Category="Presentation") void PresentOutcome(int32 OutcomeIndex, AActor* SpawnedActor, bool bSpawnSucceeded);
    void SetCoordinator(AAnomalyRoundCoordinator* Coordinator);
    void LockUnselected();
    FTransform GetThreatSpawnTransform() const { return SpawnTransformFor(true); }
    virtual bool CanScan() const override;
    virtual FAnomalyScanReading GetCachedReading(EAnomalyEquipment Instrument) const override;
    virtual bool CompleteScan(EAnomalyEquipment Instrument, FAnomalyScanReading& Reading) override;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
    friend struct FAnomalyRegionProbe;
    friend struct FAnomalyObserverProbe;
    UPROPERTY(Transient) TSubclassOf<AActor> ResolvedThreatClass;
    TSubclassOf<AActor> SelectThreatClass() const;
    UPROPERTY(Transient) TMap<EAnomalyEquipment, FAnomalyScanReading> ScanCache;
    FRandomStream ConfigurationStream;
    FRandomStream OutcomeStream;
    FRandomStream VisualStream;
    FTimerHandle RevealTimer;
    TWeakObjectPtr<AAnomalyRoundCoordinator> RoundCoordinator;
    int32 PendingDebugOutcome = 0;
    void ResolveOutcome();
    FTransform SpawnTransformFor(bool bThreat) const;
    void InitializeVisualClues();
    void AddVisualClue(UStaticMesh* Mesh, USkeletalMeshComponent* Crate,
        const FVector& Scale, const FVector& Center, const TCHAR* ComponentName);
};
