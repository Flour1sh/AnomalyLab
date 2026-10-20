#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "AnomalyExplorationWidget.generated.h"

class UTextBlock;
class UImage;

/** Passive T20 prompts. Owns no input, round state or money. */
UCLASS()
class ANOMALYLAB_API UAnomalyExplorationWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void PresentDamage(bool bDamaged);
    void PresentShop(const FString& Text,bool bOpen);
    void PresentMeta(const FString& Text);
    void PresentRegion(const FString& Hint);
    void PresentInventory(const FString& Items, const FString& Notice);
    void Present(const FString& Focus, const FString& Objective, bool bEnabled);
protected:
    UPROPERTY(meta=(BindWidgetOptional)) TObjectPtr<UTextBlock> ShopText;
    UPROPERTY(meta=(BindWidgetOptional)) TObjectPtr<UTextBlock> MetaText;
    UPROPERTY(meta=(BindWidgetOptional)) TObjectPtr<UTextBlock> RegionText;
    UPROPERTY(meta=(BindWidgetOptional)) TObjectPtr<UImage> DamageVeil;
    UPROPERTY(meta=(BindWidgetOptional)) TObjectPtr<UTextBlock> InventoryText;
    UPROPERTY(meta=(BindWidgetOptional)) TObjectPtr<UTextBlock> NoticeText;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UTextBlock> InteractionPrompt;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UTextBlock> ExplorationObjective;
private:
    FString LastFocus;
    FString LastObjective;
};
