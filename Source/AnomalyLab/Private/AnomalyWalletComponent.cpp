#include "AnomalyWalletComponent.h"

UAnomalyWalletComponent::UAnomalyWalletComponent() { PrimaryComponentTick.bCanEverTick = false; }

void UAnomalyWalletComponent::NativeAddMoney(int32 Amount)
{
    const int64 Candidate = static_cast<int64>(Money) + Amount;
    if (Candidate < MIN_int32 || Candidate > MAX_int32)
    { UE_LOG(LogTemp, Error, TEXT("[Wallet] Rejected overflowing change Amount=%d Money=%d"), Amount, Money); return; }
    Money = static_cast<int32>(Candidate);
    UE_LOG(LogTemp, Display, TEXT("[Wallet] Money=%d Delta=%d"), Money, Amount);
    PresentMoneyChanged(Money, Amount);
}

void UAnomalyWalletComponent::NativeResetMoney()
{
    const int64 Delta = -static_cast<int64>(Money);
    if (Delta > MAX_int32)
    { UE_LOG(LogTemp, Error, TEXT("[Wallet] Reset delta exceeds the legacy int32 event range")); return; }
    NativeAddMoney(static_cast<int32>(Delta));
}
