#include "AnomalyObserverConfig.h"
bool UAnomalyObserverConfig::Validate(FString& Reason) const
{
    const float Values[]={ObserveDistance,EnterDot,ExitDot,LostSightGrace,MinimumDwell,AcquireSeconds,ContactGrace,ObservationTolerance,UnobservableSeconds,MixedPoolWeight};
    for (float V:Values) if (!FMath::IsFinite(V)) { Reason=TEXT("观察者配置非有限值"); return false; }
    if (ObserveDistance<300 || ObserveDistance>4000 || EnterDot<=ExitDot || EnterDot>.99 || ExitDot<.1
        || LostSightGrace<.05 || LostSightGrace>.5 || MinimumDwell<.05 || MinimumDwell>.5 || AcquireSeconds<.02 || AcquireSeconds>.3
        || ContactGrace<.1 || ContactGrace>1 || ObservationTolerance<2 || ObservationTolerance>8 || UnobservableSeconds<.5 || UnobservableSeconds>2
        || MixedPoolWeight<0 || MixedPoolWeight>1)
    { Reason=TEXT("观察者阈值超出支持范围"); return false; }
    return true;
}
