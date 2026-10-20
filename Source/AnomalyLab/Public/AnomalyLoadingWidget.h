#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "AnomalyLoadingWidget.generated.h"

/** Opaque, level-owned loading cover; no account or persistent widget reference. */
UCLASS()
class ANOMALYLAB_API UAnomalyLoadingWidget : public UUserWidget
{
    GENERATED_BODY()
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
};
