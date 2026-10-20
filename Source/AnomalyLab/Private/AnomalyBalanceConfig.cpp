#include "AnomalyBalanceConfig.h"
#include "AnomalyBoxDefinition.h"
bool UAnomalyBalanceConfig::Validate(FString& Reason) const
{
    if (!FMath::IsFinite(ThreatPerRound) || ThreatPerRound<0 || ThreatPerRound>.1
        || !FMath::IsFinite(RewardPerRound) || RewardPerRound<0 || RewardPerRound>.1
        || !FMath::IsFinite(ThreatCap) || ThreatCap<1 || ThreatCap>1.5
        || !FMath::IsFinite(RewardCap) || RewardCap<1 || RewardCap>1.5)
    { Reason=TEXT("Invalid bounded round curve"); return false; }
    Reason.Reset(); return true;
}
double UAnomalyBalanceConfig::ThreatMultiplier(int32 Round) const
{ return FMath::Min(ThreatCap,1.+double(FMath::Max(1,Round)-1)*ThreatPerRound); }
double UAnomalyBalanceConfig::RewardMultiplier(int32 Round) const
{ return FMath::Min(RewardCap,1.+double(FMath::Max(1,Round)-1)*RewardPerRound); }
bool UAnomalyBalanceConfig::ApplyTo(UAnomalyBoxDefinition& Data,int32 Round,FString& Reason) const
{
    if (!Validate(Reason) || Round<1 || !Data.Validate(Reason)) return false;
    const double Threat=Data.ThreatChance*ThreatMultiplier(Round);
    const double Total=Data.HighValueChance+Data.TrashChance+Threat;
    const double Low=Data.ValueMin*RewardMultiplier(Round), High=Data.ValueMax*RewardMultiplier(Round);
    if (!FMath::IsFinite(Total) || Total<=0 || !FMath::IsFinite(High) || High>MAX_int32-1.)
    { Reason=TEXT("Round curve probability/reward overflow"); return false; }
    // Round 1 is exactly the accepted region contract, including floating-point values.
    if (Round==1) return true;
    Data.HighValueChance/=Total; Data.TrashChance/=Total; Data.ThreatChance=Threat/Total;
    Data.ValueMin=FMath::RoundToInt(Low); Data.ValueMax=FMath::RoundToInt(High);
    return Data.Validate(Reason);
}
