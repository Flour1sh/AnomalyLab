#pragma once
#include "CoreMinimal.h"
class AAnomalyRoundCoordinator;
struct FAnomalyEndRunSnapshot;
class FJsonObject;
class FJsonValue;

/** Bounded diagnostics, value-only samples; never authorizes economic writes. */
struct ANOMALYLAB_API FAnomalyRunTelemetry
{
    void Start(const AAnomalyRoundCoordinator* Owner);
    void Tick(const AAnomalyRoundCoordinator* Owner);
    void Event(const AAnomalyRoundCoordinator* Owner,const FString& Kind,const FString& Detail);
    void BeginReturn(const AAnomalyRoundCoordinator* Owner);
    void Damage(int32 Delta) { if(Delta<0) DamageTaken-=int64(Delta); }
    void Finish(const AAnomalyRoundCoordinator* Owner,const FAnomalyEndRunSnapshot& Result,bool Interrupted=false);
    static void CompleteHub(const FGuid& Run,float Seconds);
    static FString Path(const FGuid& Run);
private:
    FGuid Run;
    bool bFinished=false;
    int32 LastRound=0,MinHealth=100,Hitches=0;
    double ReturnAt=-1,FrameSum=0,MaxFrame=0;
    double EntryGameSeconds=0;
    int64 DamageTaken=0;
    TArray<float> FrameMs;
    TArray<TSharedPtr<FJsonValue>> Events;
    TSet<FString> Rooms;
    TSharedPtr<FJsonObject> Data;
};
