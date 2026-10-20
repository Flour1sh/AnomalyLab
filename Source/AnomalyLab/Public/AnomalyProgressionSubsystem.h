#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "AnomalyProgressionSubsystem.generated.h"
class UAnomalyProgressionConfig;
class AAnomalyRoundCoordinator;
class UAnomalyTransitionSubsystem;
class AAnomalyHubPlayerController;

USTRUCT(BlueprintType)
struct ANOMALYLAB_API FAnomalyMetaProgress
{
    GENERATED_BODY()
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int32 SchemaVersion=2;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int64 Currency=0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int32 BatteryLevel=0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int32 PrecisionLevel=0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int32 BackpackLevel=0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int32 StoredDecoys=0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int32 Revision=0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int32 Extractions=0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int64 TotalEarned=0;
    UPROPERTY() TArray<FGuid> RecentSettlements;
    UPROPERTY() TArray<FGuid> RecentPurchases;
};
/** Only this authority changes Meta. Widgets receive text or immutable values. */
UCLASS()
class ANOMALYLAB_API UAnomalyProgressionSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    const FAnomalyMetaProgress& GetProgress() const { return Progress; }
    const UAnomalyProgressionConfig* GetConfig() const { return Config; }
    const FString& GetSavePath() const { return SavePath; }
    const FString& GetLoadMessage() const { return LoadMessage; }
    bool IsPersistenceBlocked() const { return bPersistenceBlocked; }
    bool Configure(UAnomalyProgressionConfig* Source, FString& Reason);
    bool Purchase(AAnomalyRoundCoordinator* Caller,int32 Product,int32 ExpectedRevision,const FGuid& Request,FString& Reason);
    bool PurchaseHub(AAnomalyHubPlayerController* Caller,int32 Product,int32 ExpectedRevision,const FGuid& Request,FString& Reason);
    bool CreditExtraction(AAnomalyRoundCoordinator* Caller,const FGuid& Run,int32 Value,FString& Reason);
    bool BeginRun(AAnomalyRoundCoordinator* Caller,int32& Decoys,FString& Reason);
    FString DescribeShop(int32 Selection,const FString& Message) const;
private:
    friend class UAnomalyTransitionSubsystem;
    friend struct FAnomalyV05Probe;
    friend struct FAnomalyJourneyProbe;
    bool BeginHubRun(UAnomalyTransitionSubsystem* Caller,const FGuid& Run,int32& Decoys,FString& Reason);
    bool ImportSave(const FString& Source,FString& Reason);
    bool PurchaseAuthorized(int32 Product,int32 ExpectedRevision,const FGuid& Request,FString& Reason);
    friend struct FAnomalyV04Probe;
    UPROPERTY(Transient) TObjectPtr<UAnomalyProgressionConfig> Config;
    UPROPERTY(Transient) FAnomalyMetaProgress Progress;
    TSet<FGuid> Purchases;
    TSet<FGuid> SettledRuns;
    TSet<FGuid> StartedRuns;
    FString SavePath;
    FString LoadMessage;
    bool bPersistenceBlocked=false;
    int32 SaveFault=0; // Explicit fixture injection only; no command-line/Blueprint setter.
    static void Sanitize(FAnomalyMetaProgress& Value,const UAnomalyProgressionConfig* Config);
    bool Commit(const FAnomalyMetaProgress& Next,FString& Reason);
};
