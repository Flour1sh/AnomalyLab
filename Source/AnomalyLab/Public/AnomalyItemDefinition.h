#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "AnomalyItemDefinition.generated.h"

class UStaticMesh;
class UMaterialInterface;
/** Fixed presentation data; the reward amount belongs to the generated instance. */
UCLASS(BlueprintType)
class ANOMALYLAB_API UAnomalyItemDefinition : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName ItemId;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText DisplayName;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) bool bPickable = true;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) bool bTrash = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) int32 TrashValue = 3;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> Mesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UMaterialInterface> Material;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FVector MeshScale = FVector(.3);
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FLinearColor GlowColour = FLinearColor(.15f, .8f, .8f);
};

USTRUCT(BlueprintType)
struct FAnomalyItemInstance
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) FGuid InstanceId;
    UPROPERTY(BlueprintReadOnly) FName ItemId;
    UPROPERTY(BlueprintReadOnly) FText DisplayName;
    UPROPERTY(BlueprintReadOnly) int32 Value = 0;
    UPROPERTY(BlueprintReadOnly) int32 SourceRoundId = 0;
};
