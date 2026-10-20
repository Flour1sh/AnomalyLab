#pragma once
#include "CoreMinimal.h"
#include "Containers/Ticker.h"
#include "Engine/EngineBaseTypes.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "AnomalyProgressionSubsystem.h"
#include "AnomalyRoundCoordinator.h"
#include "AnomalyTransitionSubsystem.generated.h"
class AAnomalyHubPlayerController;

UENUM()
enum class EAnomalyTravelPhase : uint8 { HubReady, Preparing, LoadingLab, InRun, LoadingHub, Error };

USTRUCT()
struct FAnomalyLaunchContext
{
    GENERATED_BODY()
    UPROPERTY() FGuid Run;
    UPROPERTY() int64 Version=0;
    UPROPERTY() int32 Seed=0;
    UPROPERTY() int32 Decoys=0;
    UPROPERTY() FAnomalyMetaProgress Equipment;
};

/** Travel authority stores values only; Progression remains the sole account. */
UCLASS()
class ANOMALYLAB_API UAnomalyTransitionSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;
    bool EnterHub(AAnomalyHubPlayerController* Caller);
    bool RequestLaunch(AAnomalyHubPlayerController* Caller,FString& Reason);
    bool ClaimLab(AAnomalyRoundCoordinator* Caller,FAnomalyLaunchContext& Value,FString& Reason);
    bool CompleteRun(AAnomalyRoundCoordinator* Caller);
    void RejectLab(UWorld* World,const FString& Reason);
    bool IsHubReady(const UObject* Caller) const;
    EAnomalyTravelPhase GetPhase() const { return Phase; }
    const FAnomalyLaunchContext& GetLaunch() const { return Launch; }
    const FAnomalyEndRunSnapshot& GetResult() const { return Result; }
    const FString& GetMessage() const { return Message; }
    int32 GetLaunchCount() const { return LaunchCount; }
    int32 GetResultCount() const { return ResultCount; }
    float GetLabLoadSeconds() const { return LabLoadSeconds; }
    float GetHubLoadSeconds() const { return HubLoadSeconds; }
private:
    friend class UAnomalyProgressionSubsystem;
    friend struct FAnomalyV05Probe;
    UPROPERTY() FAnomalyLaunchContext Launch;
    UPROPERTY() FAnomalyEndRunSnapshot Result;
    EAnomalyTravelPhase Phase=EAnomalyTravelPhase::HubReady;
    FString Message;
    int64 Version=0;
    int32 LaunchCount=0,ResultCount=0;
    double Deadline=0;
    double LoadStarted=0,PendingAt=0;
    int64 PendingVersion=0;
    FString PendingDestination;
    float LabLoadSeconds=0,HubLoadSeconds=0;
    void QueueTravel(const FString& Destination);
    FTSTicker::FDelegateHandle Ticker;
    void Change(EAnomalyTravelPhase Next,const FString& Cause);
    bool Tick(float Delta);
    void TravelFailure(UWorld* World,ETravelFailure::Type Type,const FString& Reason);
};
