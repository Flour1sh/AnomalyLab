#include "AnomalyMainMenuWidget.h"
#include "AnomalyMenuGameMode.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Button.h"
#include "Components/CanvasPanel.h"
#include "Components/TextBlock.h"
#include "Engine/Engine.h"
#include "GameFramework/GameUserSettings.h"
#include "Input/Reply.h"
#include "InputCoreTypes.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Kismet/GameplayStatics.h"

void UAnomalyMainMenuWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    SetIsFocusable(true);
    StartButton->OnClicked.AddDynamic(this, &UAnomalyMainMenuWidget::StartGame);
    SettingsButton->OnClicked.AddDynamic(this, &UAnomalyMainMenuWidget::OpenSettings);
    GuideButton->OnClicked.AddDynamic(this, &UAnomalyMainMenuWidget::OpenGuide);
    QuitButton->OnClicked.AddDynamic(this, &UAnomalyMainMenuWidget::OpenQuit);
    ResolutionButton->OnClicked.AddDynamic(this, &UAnomalyMainMenuWidget::CycleResolution);
    WindowModeButton->OnClicked.AddDynamic(this, &UAnomalyMainMenuWidget::CycleWindowMode);
    QualityButton->OnClicked.AddDynamic(this, &UAnomalyMainMenuWidget::CycleQuality);
    ApplyButton->OnClicked.AddDynamic(this, &UAnomalyMainMenuWidget::ApplySettings);
    SettingsBackButton->OnClicked.AddDynamic(this, &UAnomalyMainMenuWidget::BackToMain);
    GuideBackButton->OnClicked.AddDynamic(this, &UAnomalyMainMenuWidget::BackToMain);
    ConfirmQuitButton->OnClicked.AddDynamic(this, &UAnomalyMainMenuWidget::ConfirmQuit);
    CancelQuitButton->OnClicked.AddDynamic(this, &UAnomalyMainMenuWidget::BackToMain);
    for (UButton* Button : {StartButton.Get(), SettingsButton.Get(), GuideButton.Get(), QuitButton.Get(),
        ResolutionButton.Get(), WindowModeButton.Get(), QualityButton.Get(), ApplyButton.Get(),
        SettingsBackButton.Get(), GuideBackButton.Get(), ConfirmQuitButton.Get(), CancelQuitButton.Get()})
        Button->OnHovered.AddDynamic(this, &UAnomalyMainMenuWidget::RefreshHoveredSelection);
    ShowPanel(0);
}

TArray<UButton*> UAnomalyMainMenuWidget::ActiveButtons() const
{
    switch (ActivePanel)
    {
    case 0: return {StartButton, SettingsButton, GuideButton, QuitButton};
    case 1: return {ResolutionButton, WindowModeButton, QualityButton, ApplyButton, SettingsBackButton};
    case 2: return {GuideBackButton};
    case 3: return {CancelQuitButton, ConfirmQuitButton};
    default: return {};
    }
}

void UAnomalyMainMenuWidget::ShowPanel(int32 Panel)
{
    ActivePanel = Panel;
    SettingsPanel->SetVisibility(Panel == 1 ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
    GuidePanel->SetVisibility(Panel == 2 ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
    QuitPanel->SetVisibility(Panel == 3 ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
    LoadingPanel->SetVisibility(Panel == 4 ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
    for (UButton* Button : {StartButton.Get(), SettingsButton.Get(), GuideButton.Get(), QuitButton.Get()})
        Button->SetIsEnabled(Panel == 0);
    SelectButton(0);
    if (IsInViewport()) SetKeyboardFocus();
}

void UAnomalyMainMenuWidget::SelectButton(int32 Index)
{
    const TArray<UButton*> Buttons = ActiveButtons();
    if (Buttons.IsEmpty()) return;
    SelectedIndex = (Index + Buttons.Num()) % Buttons.Num();
    for (int32 I = 0; I < Buttons.Num(); ++I)
    {
        UButton* Button = Buttons[I];
        const bool bSelected = I == SelectedIndex;
        FButtonStyle Style = Button->GetStyle();
        Style.Normal.TintColor = FSlateColor(bSelected ? FLinearColor(.9f, .42f, .13f, 1.f) : FLinearColor(.04f, .05f, .05f, .84f));
        Button->SetStyle(Style);
        if (UTextBlock* Label = Cast<UTextBlock>(WidgetTree->FindWidget(FName(*(Button->GetName() + TEXT("Label"))))))
            Label->SetColorAndOpacity(FSlateColor(bSelected ? FLinearColor(.02f, .025f, .025f, 1.f) : FLinearColor(.8f, .82f, .76f, 1.f)));
    }
}

void UAnomalyMainMenuWidget::RefreshHoveredSelection()
{
    const TArray<UButton*> Buttons = ActiveButtons();
    for (int32 I = 0; I < Buttons.Num(); ++I)
        if (Buttons[I]->IsHovered())
        {
            SelectButton(I);
            if (HoverSound) UGameplayStatics::PlaySound2D(this, HoverSound, .35f);
            break;
        }
    SetKeyboardFocus();
}

FReply UAnomalyMainMenuWidget::NativeOnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if (ActivePanel == 4) return FReply::Handled();
    const FKey Key = Event.GetKey();
    if (Key == EKeys::Up || Key == EKeys::W)
    { SelectButton(SelectedIndex - 1); if (HoverSound) UGameplayStatics::PlaySound2D(this, HoverSound, .35f); return FReply::Handled(); }
    if (Key == EKeys::Down || Key == EKeys::S || Key == EKeys::Tab)
    { SelectButton(SelectedIndex + (Event.IsShiftDown() ? -1 : 1)); if (HoverSound) UGameplayStatics::PlaySound2D(this, HoverSound, .35f); return FReply::Handled(); }
    if (Key == EKeys::Enter || Key == EKeys::SpaceBar)
    {
        if (!Event.IsRepeat())
        {
            const TArray<UButton*> Buttons = ActiveButtons();
            if (Buttons.IsValidIndex(SelectedIndex)) Buttons[SelectedIndex]->OnClicked.Broadcast();
        }
        return FReply::Handled();
    }
    if (Key == EKeys::Escape)
    {
        if (!Event.IsRepeat()) { if (ActivePanel == 0) OpenQuit(); else BackToMain(); }
        return FReply::Handled();
    }
    return Super::NativeOnKeyDown(Geometry, Event);
}

FReply UAnomalyMainMenuWidget::NativeOnMouseButtonDown(const FGeometry& Geometry, const FPointerEvent& Event)
{
    return FReply::Handled().SetUserFocus(TakeWidget());
}

void UAnomalyMainMenuWidget::StartGame()
{
    if (ActivePanel == 0)
        if (AAnomalyMenuPlayerController* Controller = Cast<AAnomalyMenuPlayerController>(GetOwningPlayer()))
        { PlaySelectSound(); Controller->StartLevel01(); }
}
void UAnomalyMainMenuWidget::PlaySelectSound()
{ if (SelectSound) UGameplayStatics::PlaySound2D(this, SelectSound, .45f); }
void UAnomalyMainMenuWidget::OpenSettings()
{
    if (ActivePanel != 0) return;
    PlaySelectSound();
    if (UGameUserSettings* Settings = GEngine->GetGameUserSettings())
    {
        PendingResolution = Settings->GetScreenResolution();
        if (PendingResolution.X <= 0 || PendingResolution.Y <= 0) PendingResolution = FIntPoint(1280, 720);
        PendingWindowMode = static_cast<int32>(Settings->GetFullscreenMode());
        PendingQuality = FMath::Clamp(Settings->GetOverallScalabilityLevel(), 0, 3);
    }
    SettingsStatus->SetText(FText::FromString(TEXT("修改后点击应用；返回将放弃未应用的修改。")));
    RefreshSettingsLabels();
    ShowPanel(1);
}
void UAnomalyMainMenuWidget::OpenGuide() { if (ActivePanel == 0) { PlaySelectSound(); ShowPanel(2); } }
void UAnomalyMainMenuWidget::OpenQuit() { if (ActivePanel == 0) { PlaySelectSound(); ShowPanel(3); } }
void UAnomalyMainMenuWidget::BackToMain() { if (ActivePanel != 4) { PlaySelectSound(); ShowPanel(0); } }

void UAnomalyMainMenuWidget::CycleResolution()
{
    if (ActivePanel != 1) return;
    PendingResolution = PendingResolution == FIntPoint(1280, 720) ? FIntPoint(1920, 1080) : FIntPoint(1280, 720);
    PlaySelectSound();
    RefreshSettingsLabels();
}
void UAnomalyMainMenuWidget::CycleWindowMode()
{
    if (ActivePanel != 1) return;
    PendingWindowMode = PendingWindowMode == 2 ? 1 : 2;
    PlaySelectSound();
    RefreshSettingsLabels();
}
void UAnomalyMainMenuWidget::CycleQuality()
{
    if (ActivePanel != 1) return;
    PendingQuality = (PendingQuality + 1) % 4;
    PlaySelectSound();
    RefreshSettingsLabels();
}
void UAnomalyMainMenuWidget::RefreshSettingsLabels()
{
    const TCHAR* Qualities[] = {TEXT("低"), TEXT("中"), TEXT("高"), TEXT("极高")};
    const TPair<UButton*, FString> Labels[] = {
        {ResolutionButton, FString::Printf(TEXT("分辨率    %d × %d"), PendingResolution.X, PendingResolution.Y)},
        {WindowModeButton, FString::Printf(TEXT("显示模式    %s"), PendingWindowMode == 2 ? TEXT("窗口") : TEXT("无边框全屏"))},
        {QualityButton, FString::Printf(TEXT("画面质量    %s"), Qualities[PendingQuality])}};
    for (const auto& Pair : Labels)
        if (UTextBlock* Label = Cast<UTextBlock>(WidgetTree->FindWidget(FName(*(Pair.Key->GetName() + TEXT("Label"))))))
            Label->SetText(FText::FromString(Pair.Value));
}
void UAnomalyMainMenuWidget::ApplySettings()
{
    if (ActivePanel != 1) return;
    PlaySelectSound();
    if (UGameUserSettings* Settings = GEngine->GetGameUserSettings())
    {
        Settings->SetScreenResolution(PendingResolution);
        Settings->SetFullscreenMode(static_cast<EWindowMode::Type>(PendingWindowMode));
        Settings->SetOverallScalabilityLevel(PendingQuality);
        Settings->ApplySettings(false);
        Settings->ConfirmVideoMode();
        Settings->SaveSettings();
        SettingsStatus->SetText(FText::FromString(TEXT("设置已应用并保存。")));
    }
    SetKeyboardFocus();
}
void UAnomalyMainMenuWidget::ConfirmQuit()
{
    if (ActivePanel == 3) UKismetSystemLibrary::QuitGame(this, GetOwningPlayer(), EQuitPreference::Quit, false);
}
void UAnomalyMainMenuWidget::PresentLoading() { ShowPanel(4); }
void UAnomalyMainMenuWidget::ShowLaunchError()
{
    LaunchStatus->SetText(FText::FromString(TEXT("关卡加载失败，请检查游戏文件后重试。")));
    ShowPanel(0);
}
