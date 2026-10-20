#pragma once

#include "CoreMinimal.h"
#include "UObject/Interface.h"
#include "AnomalyEquipmentComponent.h"
#include "AnomalyScanTarget.generated.h"

/** Presentation-only data: no definition IDs, exact probabilities or outcome. */
USTRUCT(BlueprintType)
struct ANOMALYLAB_API FAnomalyScanReading
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) bool bScanned = false;
    UPROPERTY(BlueprintReadOnly) int64 ValueMin = 0;
    UPROPERTY(BlueprintReadOnly) int64 ValueMax = 0;
    UPROPERTY(BlueprintReadOnly) FText Level;
    UPROPERTY(BlueprintReadOnly) FText Reliability;
};

UINTERFACE(MinimalAPI, meta=(CannotImplementInterfaceInBlueprint))
class UAnomalyScanTarget : public UInterface { GENERATED_BODY() };

class ANOMALYLAB_API IAnomalyScanTarget
{
    GENERATED_BODY()
public:
    virtual bool CanScan() const = 0;
    virtual FAnomalyScanReading GetCachedReading(EAnomalyEquipment Instrument) const = 0;
    virtual bool CompleteScan(EAnomalyEquipment Instrument, FAnomalyScanReading& Reading) = 0;
};
