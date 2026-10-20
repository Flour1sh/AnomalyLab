#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "AnomalyWalletComponent.generated.h"

UCLASS(Blueprintable, ClassGroup=(AnomalyLab), meta=(BlueprintSpawnableComponent))
class ANOMALYLAB_API UAnomalyWalletComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UAnomalyWalletComponent();
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Wallet") int32 Money = 0;
    UFUNCTION(BlueprintCallable, Category="Wallet") void NativeAddMoney(int32 Amount);
    UFUNCTION(BlueprintCallable, Category="Wallet") void NativeResetMoney();
    UFUNCTION(BlueprintPure, Category="Wallet") int32 NativeGetMoney() const { return Money; }
    UFUNCTION(BlueprintImplementableEvent, Category="Presentation") void PresentMoneyChanged(int32 NewMoney, int32 Delta);
};
