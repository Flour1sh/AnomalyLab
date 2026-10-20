#pragma once
#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "AnomalyProgressionSubsystem.h"
#include "AnomalyMetaSaveGame.generated.h"

UCLASS()
class ANOMALYLAB_API UAnomalyMetaSaveGame : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY() FAnomalyMetaProgress Meta;
};

/** Small validated SaveGame envelope. Only paths selected by the subsystem are used. */
struct ANOMALYLAB_API FAnomalyMetaPersistence
{
    static bool Encode(const FAnomalyMetaProgress& Value,TArray<uint8>& Bytes);
    static bool Decode(const TArray<uint8>& Bytes,FAnomalyMetaProgress& Value,bool& Future,FString& Reason);
    static bool Load(const FString& Path,FAnomalyMetaProgress& Value,bool& Future,FString& Reason);
    static bool Write(const FString& Path,const FAnomalyMetaProgress& Value,FString& Reason,int32 Fault=0);
};
