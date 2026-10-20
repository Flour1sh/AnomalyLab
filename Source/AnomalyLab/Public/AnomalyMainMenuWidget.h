#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "AnomalyMainMenuWidget.generated.h"

class UButton;
class UCanvasPanel;
class UTextBlock;
class USoundBase;

/** Menu commands and input routing. Layout, typography and colours live in WBP_MainMenu. */
UCLASS()
class ANOMALYLAB_API UAnomalyMainMenuWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    UPROPERTY(EditDefaultsOnly, Category="Menu|Audio") TObjectPtr<USoundBase> HoverSound;
    UPROPERTY(EditDefaultsOnly, Category="Menu|Audio") TObjectPtr<USoundBase> SelectSound;
    void PresentLoading();
    void ShowLaunchError();
    int32 GetActivePanel() const { return ActivePanel; }
protected:
    virtual void NativeOnInitialized() override;
    virtual FReply NativeOnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    virtual FReply NativeOnMouseButtonDown(const FGeometry& Geometry, const FPointerEvent& Event) override;

    UPROPERTY(meta=(BindWidget)) TObjectPtr<UButton> StartButton;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UButton> SettingsButton;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UButton> GuideButton;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UButton> QuitButton;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UButton> ResolutionButton;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UButton> WindowModeButton;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UButton> QualityButton;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UButton> ApplyButton;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UButton> SettingsBackButton;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UButton> GuideBackButton;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UButton> ConfirmQuitButton;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UButton> CancelQuitButton;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UCanvasPanel> SettingsPanel;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UCanvasPanel> GuidePanel;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UCanvasPanel> QuitPanel;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UCanvasPanel> LoadingPanel;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UTextBlock> SettingsStatus;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UTextBlock> LaunchStatus;
private:
    // 0 = main, 1 = settings, 2 = guide, 3 = quit, 4 = loading.
    int32 ActivePanel = 0;
    int32 SelectedIndex = 0;
    FIntPoint PendingResolution;
    int32 PendingWindowMode = 2;
    int32 PendingQuality = 2;
    void ShowPanel(int32 Panel);
    void RefreshSettingsLabels();
    void SelectButton(int32 Index);
    void PlaySelectSound();
    TArray<UButton*> ActiveButtons() const;
    UFUNCTION() void StartGame();
    UFUNCTION() void OpenSettings();
    UFUNCTION() void OpenGuide();
    UFUNCTION() void OpenQuit();
    UFUNCTION() void BackToMain();
    UFUNCTION() void CycleResolution();
    UFUNCTION() void CycleWindowMode();
    UFUNCTION() void CycleQuality();
    UFUNCTION() void ApplySettings();
    UFUNCTION() void ConfirmQuit();
    UFUNCTION() void RefreshHoveredSelection();
};
