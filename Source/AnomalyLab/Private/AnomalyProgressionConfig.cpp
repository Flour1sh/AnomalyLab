#include "AnomalyProgressionConfig.h"
bool UAnomalyProgressionConfig::Validate(FString& Reason) const
{
    if (Prices.Num()!=4 || MaxLevels.Num()!=4) { Reason=TEXT("商品配置必须四项"); return false; }
    for (int32 I=0; I<4; ++I)
        if (Prices[I]<=0 || Prices[I]>1000000 || MaxLevels[I]<1 || MaxLevels[I]>(I<2?2:1))
        { Reason=TEXT("商品价格或上限无效"); return false; }
    if (ChargesPerLevel<1 || ChargesPerLevel>5 || !FMath::IsFinite(PrecisionPerLevel) || PrecisionPerLevel<=0
        || !FMath::IsFinite(PrecisionCap) || PrecisionCap<=0 || PrecisionCap>.75f
        || !FMath::IsFinite(DecoyRadius) || DecoyRadius<100 || DecoyRadius>3000
        || !FMath::IsFinite(DecoySeconds) || DecoySeconds<1 || DecoySeconds>15
        || !FMath::IsFinite(DecoyCooldown) || DecoyCooldown<.5f || DecoyCooldown>30)
    { Reason=TEXT("装备效果配置无效"); return false; }
    return true;
}
