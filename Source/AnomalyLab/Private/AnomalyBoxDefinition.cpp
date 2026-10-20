#include "AnomalyBoxDefinition.h"

bool UAnomalyBoxDefinition::Validate(FString& Reason) const
{
    const auto Probability = [](double P) { return FMath::IsFinite(P) && P >= 0.0 && P <= 1.0; };
    if (!Probability(HighValueChance) || !Probability(TrashChance) || !Probability(ThreatChance)
        || !FMath::IsNearlyEqual(HighValueChance + TrashChance + ThreatChance, 1.0, 1.e-6))
    { Reason = TEXT("Outcome probabilities must be finite, nonnegative and sum to one"); return false; }
    if (ValueMin < 0 || ValueMax < ValueMin || ValueMax > MAX_int32 - 1)
    { Reason = TEXT("Invalid reward range"); return false; }
    if (!FMath::IsFinite(ValueLowerScale) || ValueLowerScale < 0.0 || ValueLowerScale > 1.0
        || !FMath::IsFinite(ValueUpperScale) || ValueUpperScale < 1.0 || !Probability(ScanProbabilityError)
        || !Probability(MetalChance) || !Probability(WarningChance) || !Probability(WearChance))
    { Reason = TEXT("Invalid scan or visual configuration"); return false; }
    Reason.Reset();
    return true;
}

int32 UAnomalyBoxDefinition::SelectOutcome(double UnitRoll) const
{
    // RandomStream yields [0,1). Zero-probability results cannot be selected at boundaries.
    if (UnitRoll < HighValueChance) return 0;
    if (UnitRoll < HighValueChance + TrashChance) return 1;
    return 2;
}
