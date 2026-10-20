#include "AnomalyMetaSaveGame.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Crc.h"
#include "HAL/FileManager.h"

namespace
{
    constexpr uint32 Magic=0x414C3034;
    constexpr int64 MaxBytes=1024*1024;
    bool Read(const FString& Path,TArray<uint8>& Bytes)
    {
        const int64 Size=IFileManager::Get().FileSize(*Path);
        return Size>=16 && Size<=MaxBytes && FFileHelper::LoadFileToArray(Bytes,*Path);
    }
    bool ValidFile(const FString& Path,FAnomalyMetaProgress& Value,bool& Future,FString& Reason)
    { TArray<uint8> Bytes; return Read(Path,Bytes) && FAnomalyMetaPersistence::Decode(Bytes,Value,Future,Reason); }
}
bool FAnomalyMetaPersistence::Encode(const FAnomalyMetaProgress& Value,TArray<uint8>& Bytes)
{
    auto Save=Cast<UAnomalyMetaSaveGame>(UGameplayStatics::CreateSaveGameObject(UAnomalyMetaSaveGame::StaticClass()));
    if (!Save) return false;
    Save->Meta=Value; TArray<uint8> Payload;
    if (!UGameplayStatics::SaveGameToMemory(Save,Payload) || Payload.Num()>MaxBytes-16) return false;
    const uint32 Header[]={Magic,1,uint32(Payload.Num()),FCrc::MemCrc32(Payload.GetData(),Payload.Num())};
    Bytes.SetNumUninitialized(16+Payload.Num()); FMemory::Memcpy(Bytes.GetData(),Header,16);
    FMemory::Memcpy(Bytes.GetData()+16,Payload.GetData(),Payload.Num()); return true;
}
bool FAnomalyMetaPersistence::Decode(const TArray<uint8>& Bytes,FAnomalyMetaProgress& Value,bool& Future,FString& Reason)
{
    Future=false;
    if (Bytes.Num()<16 || Bytes.Num()>MaxBytes) { Reason=TEXT("存档长度无效"); return false; }
    uint32 Header[4]; FMemory::Memcpy(Header,Bytes.GetData(),16);
    if (Header[0]!=Magic || Header[1]!=1 || Header[2]!=uint32(Bytes.Num()-16)
        || Header[3]!=FCrc::MemCrc32(Bytes.GetData()+16,Bytes.Num()-16))
    { Reason=TEXT("存档校验失败"); return false; }
    TArray<uint8> Payload; Payload.Append(Bytes.GetData()+16,Bytes.Num()-16);
    auto Save=Cast<UAnomalyMetaSaveGame>(UGameplayStatics::LoadGameFromMemory(Payload));
    if (!Save) { Reason=TEXT("SaveGame 类型无效"); return false; }
    if (Save->Meta.SchemaVersion>2) { Future=true; Reason=TEXT("发现更高版本存档，保留原档并禁止覆盖"); return false; }
    if (Save->Meta.SchemaVersion<1) { Reason=TEXT("不支持的旧 Schema"); return false; }
    Value=Save->Meta;
    Reason=Value.SchemaVersion==1?TEXT("Schema 1 将迁移至 2"):TEXT("Schema 2 已加载");
    return true;
}
bool FAnomalyMetaPersistence::Load(const FString& Path,FAnomalyMetaProgress& Value,bool& Future,FString& Reason)
{
    Future=false; Value=FAnomalyMetaProgress();
    if (ValidFile(Path,Value,Future,Reason)) return true;
    if (Future) return false;
    if (IFileManager::Get().FileExists(*Path))
    {
        const FString Bad=Path+TEXT(".bad.")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
        IFileManager::Get().Copy(*Bad,*Path,false,false);
        UE_LOG(LogTemp,Warning,TEXT("[MetaSave] Invalid primary preserved: %s"),*Bad);
    }
    if (ValidFile(Path+TEXT(".bak"),Value,Future,Reason)) { Reason=TEXT("主档无效或缺失，已从验证过的备份恢复"); return true; }
    if (Future) return false;
    Value=FAnomalyMetaProgress(); Reason=TEXT("无有效存档，安全默认：永久余额 0、无升级"); return true;
}
bool FAnomalyMetaPersistence::Write(const FString& Path,const FAnomalyMetaProgress& Value,FString& Reason,int32 Fault)
{
    check(IsInGameThread());
    const auto Fail=[&Reason](const TCHAR* Message) { Reason=FString(TEXT("保存失败："))+Message+TEXT("；请检查磁盘/权限后重试"); UE_LOG(LogTemp,Warning,TEXT("[MetaSave] %s"),*Reason); return false; };
    if (Fault==1) return Fail(TEXT("测试写入故障"));
    TArray<uint8> Bytes,Verify;
    if (!Encode(Value,Bytes)) return Fail(TEXT("序列化"));
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);
    const FString Temp=Path+TEXT(".tmp");
    if (!FFileHelper::SaveArrayToFile(Bytes,*Temp) || !Read(Temp,Verify) || Verify!=Bytes) return Fail(TEXT("临时文件或读回校验"));
    if (Fault==2) return Fail(TEXT("临时文件后模拟中断，旧主档仍有效"));
    FAnomalyMetaProgress Old; bool Future=false; FString Why;
    if (ValidFile(Path,Old,Future,Why))
    {
        const FString BackupTemp=Path+TEXT(".bak.tmp");
        if (IFileManager::Get().Copy(*BackupTemp,*Path,true,false)!=COPY_OK || !ValidFile(BackupTemp,Old,Future,Why)
            || !IFileManager::Get().Move(*(Path+TEXT(".bak")),*BackupTemp,true,false,false,true)) return Fail(TEXT("旧版本备份"));
    }
    else if (Future) return Fail(TEXT("未来 Schema 不允许覆盖"));
    if (!IFileManager::Get().Move(*Path,*Temp,true,false,false,true)) return Fail(TEXT("主档替换（旧版本可从备份恢复）"));
    if (!Read(Path,Verify) || Verify!=Bytes)
    {
        if (IFileManager::Get().FileExists(*(Path+TEXT(".bak")))) IFileManager::Get().Copy(*Path,*(Path+TEXT(".bak")),true,false);
        return Fail(TEXT("主档读回校验，已尝试恢复备份"));
    }
    Reason.Reset(); return true;
}
