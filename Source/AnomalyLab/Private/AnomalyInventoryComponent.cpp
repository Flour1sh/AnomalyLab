#include "AnomalyInventoryComponent.h"
#include "AnomalyWorldPickup.h"

int32 UAnomalyInventoryComponent::GetCarryValue() const
{
    int64 Value = 0;
    for (const FAnomalyItemInstance& Item : Items) Value += Item.Value;
    return int32(FMath::Min<int64>(Value, MAX_int32));
}
bool UAnomalyInventoryComponent::Contains(const FGuid& Id) const { return ClaimedIds.Contains(Id); }
bool UAnomalyInventoryComponent::TryStore(AAnomalyWorldPickup* Pickup)
{
    check(IsInGameThread());
    if (bSealed || Items.Num() >= CurrentCapacity || !IsValid(Pickup) || !Pickup->bInitialized || !Pickup->bPickable
        || Pickup->bClaimed || !Pickup->Item.InstanceId.IsValid() || Pickup->Item.Value < 0
        || ClaimedIds.Contains(Pickup->Item.InstanceId) || int64(GetCarryValue()) + Pickup->Item.Value > MAX_int32) return false;
    // Commit the ownership transfer before hiding/destroying the world proxy. No delegate can re-enter halfway.
    Pickup->bClaimed = true;
    Items.Add(Pickup->Item);
    ClaimedIds.Add(Pickup->Item.InstanceId);
    Pickup->SetActorEnableCollision(false);
    Pickup->SetActorHiddenInGame(true);
    Pickup->Destroy();
    return true;
}
void UAnomalyInventoryComponent::SealAndClear() { bSealed = true; Items.Empty(); }
FString UAnomalyInventoryComponent::Describe() const
{
    FString Text = FString::Printf(TEXT("携带  %d / %d 格  ·  $%d\n"), Items.Num(), CurrentCapacity, GetCarryValue());
    for (int32 Slot = 0; Slot < CurrentCapacity; ++Slot)
        Text += Items.IsValidIndex(Slot)
            ? FString::Printf(TEXT("[%d] %s  $%d\n"), Slot + 1, *Items[Slot].DisplayName.ToString(), Items[Slot].Value)
            : FString::Printf(TEXT("[%d] —\n"), Slot + 1);
    return Text + TEXT("返回入口撤离后兑现；死亡丢失携带物品");
}
