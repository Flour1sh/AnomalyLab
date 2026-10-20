#include "AnomalyRegionDefinition.h"
#include "AnomalyBoxDefinition.h"

namespace
{
    const FName PublicTypes[] = {TEXT("Safe"), TEXT("Risky"), TEXT("Unknown")};
    const FName HiddenTypes[] = {TEXT("UnknownSafe"), TEXT("UnknownMedium"), TEXT("UnknownRisky")};
}

bool UAnomalyRegionDefinition::Validate(FString& Reason) const
{
    const auto WeightsValid = [](const TArray<double>& Weights, int32 MinimumSupport)
    {
        if (Weights.Num() != 3) return false;
        double Sum = 0.; int32 Support = 0;
        for (double Weight : Weights)
        {
            if (!FMath::IsFinite(Weight) || Weight < 0.) return false;
            Sum += Weight; Support += Weight > 0. ? 1 : 0;
        }
        return FMath::IsFinite(Sum) && Sum > 0. && Support >= MinimumSupport;
    };
    if (RegionID.IsNone() || DisplayName.IsEmpty() || Description.IsEmpty()
        || !WeightsValid(BoxTypeWeights, 2) || !WeightsValid(HiddenProfileWeights, 1))
    { Reason = TEXT("Region identity/text or three-entry weights invalid (at least two public types required)"); return false; }
    if (!FMath::IsFinite(HighValueWeight) || HighValueWeight < 0.
        || !FMath::IsFinite(TrashWeight) || TrashWeight < 0.
        || !FMath::IsFinite(ThreatWeight) || ThreatWeight < 0.
        || !FMath::IsFinite(HighValueWeight + TrashWeight + ThreatWeight)
        || HighValueWeight + TrashWeight + ThreatWeight <= 0.
        || !FMath::IsFinite(RewardScale) || RewardScale <= 0.
        || !FMath::IsFinite(ScanErrorAdd) || ScanErrorAdd < 0. || ScanErrorAdd > 1.)
    { Reason = TEXT("Invalid outcome/reward/scan modifiers"); return false; }
    TSet<FName> Seen;
    if (AllowedAnomalies.IsEmpty()) { Reason=TEXT("Empty anomaly pool"); return false; }
    for (FName Name:AllowedAnomalies)
    {
        if ((Name!=TEXT("Chaser") && Name!=TEXT("Observer")) || Seen.Contains(Name))
        { Reason=TEXT("Unknown or duplicated anomaly; supported Chaser/Observer"); return false; }
        Seen.Add(Name);
    }
    Reason.Reset(); return true;
}

bool UAnomalyRegionDefinition::ApplyTo(UAnomalyBoxDefinition& Data, FString& Reason) const
{
    if (!Validate(Reason) || !Data.Validate(Reason)) return false;
    const double High = Data.HighValueChance * HighValueWeight;
    const double Trash = Data.TrashChance * TrashWeight;
    const double Threat = Data.ThreatChance * ThreatWeight;
    const double Total = High + Trash + Threat;
    const double LowValue = double(Data.ValueMin) * RewardScale;
    const double HighValue = double(Data.ValueMax) * RewardScale;
    if (!FMath::IsFinite(Total) || Total <= 0. || !FMath::IsFinite(LowValue)
        || !FMath::IsFinite(HighValue) || HighValue > MAX_int32 - 1.)
    { Reason = TEXT("Region modifiers produce zero/nonfinite probability mass or overflowing reward"); return false; }
    Data.HighValueChance = High / Total;
    Data.TrashChance = Trash / Total;
    Data.ThreatChance = Threat / Total;
    Data.ValueMin = FMath::RoundToInt(LowValue);
    Data.ValueMax = FMath::RoundToInt(HighValue);
    Data.ScanProbabilityError = FMath::Clamp(Data.ScanProbabilityError + ScanErrorAdd, 0., 1.);
    return Data.Validate(Reason);
}

int32 UAnomalyRegionDefinition::DrawIndex(const TArray<double>& Weights, FRandomStream& Stream, int32 Exclude)
{
    double Sum = 0.; int32 Last = INDEX_NONE;
    for (int32 Index = 0; Index < Weights.Num(); ++Index)
        if (Index != Exclude && Weights[Index] > 0.) { Sum += Weights[Index]; Last = Index; }
    if (Last == INDEX_NONE || !FMath::IsFinite(Sum)) return INDEX_NONE;
    double Roll = double(Stream.FRand()) * Sum;
    for (int32 Index = 0; Index < Weights.Num(); ++Index)
        if (Index != Exclude && Weights[Index] > 0.)
        { if (Roll < Weights[Index]) return Index; Roll -= Weights[Index]; }
    return Last;
}

FName UAnomalyRegionDefinition::DrawBoxType(FRandomStream& Stream, FName Exclude) const
{
    int32 Excluded = INDEX_NONE;
    for (int32 Index = 0; Index < 3; ++Index) if (PublicTypes[Index] == Exclude) Excluded = Index;
    const int32 Index = DrawIndex(BoxTypeWeights, Stream, Excluded);
    return Index == INDEX_NONE ? NAME_None : PublicTypes[Index];
}
FName UAnomalyRegionDefinition::DrawHiddenProfile(FRandomStream& Stream) const
{
    const int32 Index = DrawIndex(HiddenProfileWeights, Stream);
    return Index == INDEX_NONE ? NAME_None : HiddenTypes[Index];
}
bool UAnomalyRegionDefinition::DrawChoices(const TArray<TObjectPtr<UAnomalyRegionDefinition>>& Regions,
    FRandomStream& Stream, TArray<FName>& Types, FString& Reason)
{
    Types.Reset(); TSet<FName> IDs;
    if (Regions.Num() != 3) { Reason = TEXT("Exactly three slot regions required"); return false; }
    for (const UAnomalyRegionDefinition* Region : Regions)
    {
        if (!IsValid(Region) || !Region->Validate(Reason) || IDs.Contains(Region->RegionID))
        { if (Reason.IsEmpty()) Reason = TEXT("Null or duplicate region"); return false; }
        IDs.Add(Region->RegionID); Types.Add(Region->DrawBoxType(Stream));
    }
    if (Types[0] == Types[1] && Types[1] == Types[2])
    {
        const int32 Slot = Stream.RandRange(0, 2);
        Types[Slot] = Regions[Slot]->DrawBoxType(Stream, Types[Slot]);
    }
    Reason.Reset(); return true;
}
