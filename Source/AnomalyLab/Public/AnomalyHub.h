#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "Blueprint/UserWidget.h"
#include "AnomalyHub.generated.h"

class UCameraComponent;
class UBoxComponent;
class UStaticMeshComponent;
class UTextBlock;
class UImage;
class UAnomalyProgressionSubsystem;

UENUM(BlueprintType)
enum class EAnomalyHubTerminalKind : uint8 { Shop, Loadout, Departure, Report };

/** Safe-world pawn: same movement dimensions, no run components or economic state. */
UCLASS()
class ANOMALYLAB_API AAnomalyHubCharacter : public ACharacter
{
    GENERATED_BODY()
public:
    AAnomalyHubCharacter();
    virtual float TakeDamage(float Amount, FDamageEvent const& Event, AController* EventInstigator, AActor* Causer) override { return 0.f; }
    UPROPERTY(VisibleAnywhere) TObjectPtr<UCameraComponent> Camera;
protected:
    virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
private:
    void Forward(float V); void Back(float V); void Right(float V); void Left(float V);
    void Turn(float V); void Look(float V);
};

/** Level-owned interaction surface; carries an ID, never a wallet or run. */
UCLASS()
class ANOMALYLAB_API AAnomalyHubTerminal : public AActor
{
    GENERATED_BODY()
public:
    AAnomalyHubTerminal();
    UPROPERTY(EditAnywhere, BlueprintReadOnly) EAnomalyHubTerminalKind Kind=EAnomalyHubTerminalKind::Shop;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UBoxComponent> InteractionBounds;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Visual;
    FString GetTitle() const;
};

UCLASS()
class ANOMALYLAB_API UAnomalyHubWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Present(const FString& Focus, const FString& Panel);
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UTextBlock> HubTitle;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UTextBlock> HubGuide;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UTextBlock> HubFocus;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UTextBlock> HubPanel;
    UPROPERTY(meta=(BindWidget)) TObjectPtr<UImage> PanelBacking;
private:
    bool bTextReady=false;
    FString LastFocus,LastPanel;
};

UCLASS()
class ANOMALYLAB_API AAnomalyHubPlayerController : public APlayerController
{
    GENERATED_BODY()
public:
    AAnomalyHubPlayerController();
    virtual void Tick(float DeltaSeconds) override;
    AAnomalyHubTerminal* TraceTerminal() const;
    UAnomalyHubWidget* GetHubWidget() const { return Widget; }
    int32 GetOpenPanel() const { return OpenPanel; }
    void ClosePanel();
    bool CanConfirmDeparture() const;
    bool ConfirmDeparture();
    bool CanPurchase() const;
    bool PurchaseSelection();
    int32 GetShopSelection() const { return ShopSelection; }
    bool IsLoadingVisible() const { return LoadingWidget!=nullptr; }
protected:
    virtual void BeginPlay() override;
    virtual void SetupInputComponent() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(Transient) TObjectPtr<UAnomalyHubWidget> Widget;
    UPROPERTY(Transient) TObjectPtr<UUserWidget> LoadingWidget;
    UPROPERTY(Transient) TObjectPtr<UAnomalyProgressionSubsystem> Progression;
    int32 OpenPanel=-1;
    FString PanelText;
    void Interact();
    void ConfirmPanel();
    void ShopUp();
    void ShopDown();
    int32 ShopSelection=0;
    uint64 LastPurchaseFrame=MAX_uint64;
    FString ShopMessage;
    FString DescribeTerminal(EAnomalyHubTerminalKind Kind) const;
};

UCLASS()
class ANOMALYLAB_API AAnomalyHubGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AAnomalyHubGameMode();
};
