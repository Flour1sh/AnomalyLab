#include "AnomalyProgressionSubsystem.h"
#include "AnomalyProgressionConfig.h"
#include "AnomalyRoundCoordinator.h"
#include "AnomalyTransitionSubsystem.h"
#include "AnomalyHub.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "AnomalyMetaSaveGame.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"

void UAnomalyProgressionSubsystem::Sanitize(FAnomalyMetaProgress& M,const UAnomalyProgressionConfig* C)
{
    M.SchemaVersion=2; M.Currency=FMath::Clamp<int64>(M.Currency,0,MAX_int32);
    M.BatteryLevel=FMath::Clamp(M.BatteryLevel,0,C?C->MaxLevels[0]:2);
    M.PrecisionLevel=FMath::Clamp(M.PrecisionLevel,0,C?C->MaxLevels[1]:2);
    M.BackpackLevel=FMath::Clamp(M.BackpackLevel,0,1); M.StoredDecoys=FMath::Clamp(M.StoredDecoys,0,1);
    M.Revision=FMath::Max(0,M.Revision); M.Extractions=FMath::Max(0,M.Extractions); M.TotalEarned=FMath::Max<int64>(0,M.TotalEarned);
    const auto Clean=[](TArray<FGuid>& IDs)
    {
        TSet<FGuid> Seen;
        IDs.RemoveAll([&Seen](const FGuid& ID) { if (!ID.IsValid() || Seen.Contains(ID)) return true; Seen.Add(ID); return false; });
        if (IDs.Num()>128) IDs.RemoveAt(0,IDs.Num()-128);
    };
    Clean(M.RecentSettlements); Clean(M.RecentPurchases);
}
void UAnomalyProgressionSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    FString Slot;
    const bool bTest=FParse::Param(FCommandLine::Get(),TEXT("AnomalyV03Smoke")) || FParse::Param(FCommandLine::Get(),TEXT("AnomalyV04Smoke"))
        || FParse::Param(FCommandLine::Get(),TEXT("AnomalyT26Smoke")) || FParse::Param(FCommandLine::Get(),TEXT("AnomalyMigrationSmoke"))
        || FParse::Param(FCommandLine::Get(),TEXT("AnomalyT14Smoke")) || FParse::Param(FCommandLine::Get(),TEXT("AnomalyT15Smoke"))
        || FParse::Param(FCommandLine::Get(),TEXT("AnomalyObserverSmoke")) || FParse::Param(FCommandLine::Get(),TEXT("AnomalyBalanceSmoke"))
        || FParse::Param(FCommandLine::Get(),TEXT("AnomalyMenuSmoke")) || FParse::Param(FCommandLine::Get(),TEXT("AnomalyV05LevelSmoke")) || FParse::Param(FCommandLine::Get(),TEXT("AnomalyV05Smoke"));
    FParse::Value(FCommandLine::Get(),TEXT("AnomalySaveSlot="),Slot);
    if (Slot.IsEmpty()) Slot=bTest?TEXT("Automation_Auto_")+FGuid::NewGuid().ToString(EGuidFormats::Digits):TEXT("AnomalyLab_Meta_v04");
    bool Valid=Slot.Len()<=100 && (!bTest || Slot.StartsWith(TEXT("Automation_")));
    for (TCHAR Ch:Slot) Valid &= FChar::IsAlnum(Ch) || Ch==TEXT('_');
    if (!Valid) { bPersistenceBlocked=true; LoadMessage=TEXT("存档槽无效；测试必须使用 Automation_ 前缀"); UE_LOG(LogTemp,Error,TEXT("[MetaSave] %s"),*LoadMessage); return; }
    SavePath=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("SaveGames")/(Slot+TEXT(".sav")));
    bool Future=false; FAnomalyMetaPersistence::Load(SavePath,Progress,Future,LoadMessage);
    bPersistenceBlocked=Future || (LoadMessage.StartsWith(TEXT("无有效存档"))
        && (IFileManager::Get().FileExists(*SavePath) || IFileManager::Get().FileExists(*(SavePath+TEXT(".bak")))));
    if(bPersistenceBlocked && !Future) LoadMessage=TEXT("已有存档无法读取；保留文件，禁止购买与出发。请恢复验证过的备份。");
    FString Import; FParse::Value(FCommandLine::Get(),TEXT("AnomalyImportSave="),Import);
    if(!Import.IsEmpty() && !IFileManager::Get().FileExists(*SavePath) && !IFileManager::Get().FileExists(*(SavePath+TEXT(".bak"))) && !bTest)
    {
        FString Why;
        if(ImportSave(Import,Why)) LoadMessage=TEXT("已导入旧档，原文件未修改");
        else { bPersistenceBlocked=true; LoadMessage=Why; }
    }
    Sanitize(Progress,nullptr);
    for (const FGuid& ID:Progress.RecentPurchases) Purchases.Add(ID);
    for (const FGuid& ID:Progress.RecentSettlements) SettledRuns.Add(ID);
    UE_LOG(LogTemp,Display,TEXT("[MetaSave] Slot=%s Test=%d Path=%s %s Balance=%lld"),*Slot,bTest,*SavePath,*LoadMessage,Progress.Currency);
}

bool UAnomalyProgressionSubsystem::Configure(UAnomalyProgressionConfig* Source,FString& Reason)
{
    if (!IsValid(Source) || !Source->Validate(Reason)) return false;
    if (!Config) Config=DuplicateObject<UAnomalyProgressionConfig>(Source,this);
    Sanitize(Progress,Config);
    return true;
}
bool UAnomalyProgressionSubsystem::Commit(const FAnomalyMetaProgress& Next,FString& Reason)
{
    check(IsInGameThread());
    if (bPersistenceBlocked || SavePath.IsEmpty()) { Reason=LoadMessage; return false; }
    if (Next.Revision<0 || Next.SchemaVersion!=2) { Reason=TEXT("存档状态或版本无效"); return false; }
    if (!FAnomalyMetaPersistence::Write(SavePath,Next,Reason,SaveFault)) return false;
    Progress=Next; Reason.Reset(); return true;
}
bool UAnomalyProgressionSubsystem::Purchase(AAnomalyRoundCoordinator* Caller,int32 Product,int32 ExpectedRevision,const FGuid& Request,FString& Reason)
{
    check(IsInGameThread());
    if (!IsValid(Caller) || !Caller->IsPreparing() || !Config || Product<0 || Product>=4)
    { Reason=TEXT("仅局外入口整备阶段可购买"); return false; }
    return PurchaseAuthorized(Product,ExpectedRevision,Request,Reason);
}
bool UAnomalyProgressionSubsystem::PurchaseHub(AAnomalyHubPlayerController* Caller,int32 Product,int32 ExpectedRevision,const FGuid& Request,FString& Reason)
{
    if(!Caller || !Caller->CanPurchase() || !GetGameInstance()->GetSubsystem<UAnomalyTransitionSubsystem>()->IsHubReady(Caller))
    { Reason=TEXT("仅安全基地商店终端可购买"); return false; }
    return PurchaseAuthorized(Product,ExpectedRevision,Request,Reason);
}
bool UAnomalyProgressionSubsystem::PurchaseAuthorized(int32 Product,int32 ExpectedRevision,const FGuid& Request,FString& Reason)
{
    if(!Config || Product<0 || Product>=4) { Reason=TEXT("无效商品"); return false; }
    if (!Request.IsValid() || Purchases.Contains(Request) || ExpectedRevision!=Progress.Revision)
    { Reason=TEXT("交易已处理或页面已过期，请重试"); return false; }
    FAnomalyMetaProgress Next=Progress;
    if (Next.Revision==MAX_int32) { Reason=TEXT("交易序号已达上限"); return false; }
    int32* Levels[]={&Next.BatteryLevel,&Next.PrecisionLevel,&Next.BackpackLevel,&Next.StoredDecoys};
    if (*Levels[Product]>=Config->MaxLevels[Product]) { Reason=TEXT("已达上限（永久升级 / 诱饵最多预存 1 个）"); return false; }
    if (Next.Currency<Config->Prices[Product]) { Reason=TEXT("永久余额不足 · 成功撤离才能兑现"); return false; }
    ++*Levels[Product]; Next.Currency-=Config->Prices[Product]; ++Next.Revision;
    Next.RecentPurchases.Add(Request); if (Next.RecentPurchases.Num()>128) Next.RecentPurchases.RemoveAt(0);
    if (!Commit(Next,Reason)) return false;
    Purchases.Add(Request); Reason=TEXT("购买成功 · 下一局生效");
    UE_LOG(LogTemp,Display,TEXT("[Meta] Purchase Product=%d Revision=%d Balance=%lld"),Product,Progress.Revision,Progress.Currency);
    return true;
}
bool UAnomalyProgressionSubsystem::CreditExtraction(AAnomalyRoundCoordinator* Caller,const FGuid& Run,int32 Value,FString& Reason)
{
    if (!IsValid(Caller) || Caller->RunId!=Run || Caller->RunEndReason!=EAnomalyRunEndReason::CashedOut
        || Caller->GetNativeRoundState()!=3 || !Caller->bExtractionAuthorized || Caller->bSettlementDone
        || !Run.IsValid() || SettledRuns.Contains(Run) || Value<0)
    { Reason=TEXT("无效或重复撤离提交"); return false; }
    FAnomalyMetaProgress Next=Progress;
    if (Next.Currency+int64(Value)>MAX_int32 || Next.TotalEarned>MAX_int64-Value || Next.Extractions==MAX_int32 || Next.Revision==MAX_int32)
    { Reason=TEXT("永久收益超出上限"); return false; }
    Next.Currency+=Value; Next.TotalEarned+=Value; ++Next.Extractions; ++Next.Revision;
    Next.RecentSettlements.Add(Run); if (Next.RecentSettlements.Num()>128) Next.RecentSettlements.RemoveAt(0);
    if (!Commit(Next,Reason)) return false;
    SettledRuns.Add(Run);
    UE_LOG(LogTemp,Display,TEXT("[Meta] Extract Run=%s Value=%d Balance=%lld"),*Run.ToString(),Value,Progress.Currency);
    return true;
}
bool UAnomalyProgressionSubsystem::BeginRun(AAnomalyRoundCoordinator* Caller,int32& Decoys,FString& Reason)
{
    Decoys=0;
    if (!IsValid(Caller) || !Caller->IsPreparing() || StartedRuns.Contains(Caller->RunId)) { Reason=TEXT("重复开局"); return false; }
    FAnomalyMetaProgress Next=Progress;
    if (Next.Revision==MAX_int32) { Reason=TEXT("交易序号已达上限"); return false; }
    Decoys=Next.StoredDecoys; Next.StoredDecoys=0; ++Next.Revision;
    if (!Commit(Next,Reason)) { Decoys=0; return false; }
    StartedRuns.Add(Caller->RunId); return true;
}
FString UAnomalyProgressionSubsystem::DescribeShop(int32 Selection,const FString& Message) const
{
    if (!Config) return TEXT("商店配置不可用");
    const TCHAR* Names[]={TEXT("扫描电池扩充 · 永久"),TEXT("精度模块 · 永久"),TEXT("背包升级 · 永久"),TEXT("紧急诱饵 · 一次性")};
    const FString Effects[]={FString::Printf(TEXT("三种仪器新局各 +%d 次 / 级"),Config->ChargesPerLevel),
        FString::Printf(TEXT("减少读数干扰和区间扩展，最多 %.0f%% · 不保证开奖结果"),Config->PrecisionCap*100),
        TEXT("新局背包 4 格 → 5 格 · 不堆叠"),
        FString::Printf(TEXT("下局携带 1 个 · F 落地 · %.0f 米 / %.0f 秒 · 对观察者无效"),Config->DecoyRadius/100,Config->DecoySeconds)};
    const int32 Levels[]={Progress.BatteryLevel,Progress.PrecisionLevel,Progress.BackpackLevel,Progress.StoredDecoys};
    FString Text=FString::Printf(TEXT("入口整备台   |   永久余额 $%lld\n成功撤离所得 · 携带物品尚未兑现\n\n"),Progress.Currency);
    for (int32 I=0; I<4; ++I)
        Text+=FString::Printf(TEXT("%s %s   $%d   %s %d/%d\n    %s\n\n"),I==Selection?TEXT("▶"):TEXT("  "),Names[I],Config->Prices[I],I==3?TEXT("预存"):TEXT("等级"),Levels[I],Config->MaxLevels[I],*Effects[I]);
    return Text+TEXT("↑ ↓ 选择    ENTER 购买    E 开始新局\n")+Message;
}

bool UAnomalyProgressionSubsystem::BeginHubRun(UAnomalyTransitionSubsystem* Caller,const FGuid& Run,int32& Decoys,FString& Reason)
{
    Decoys=0;
    if(!Caller || Caller!=GetGameInstance()->GetSubsystem<UAnomalyTransitionSubsystem>() || Caller->Phase!=EAnomalyTravelPhase::Preparing
        || Caller->Launch.Run!=Run || !Run.IsValid() || StartedRuns.Contains(Run) || !Config)
    { Reason=TEXT("非法或重复出发事务"); return false; }
    auto Next=Progress;
    if(Next.Revision==MAX_int32) { Reason=TEXT("交易序号上限"); return false; }
    const int32 Carry=Next.StoredDecoys; Next.StoredDecoys=0; ++Next.Revision;
    if(!Commit(Next,Reason)) return false;
    StartedRuns.Add(Run); Decoys=Carry;
    UE_LOG(LogTemp,Display,TEXT("[Meta] Hub launch Run=%s Revision=%d Decoys=%d"),*Run.ToString(),Progress.Revision,Decoys);
    return true;
}

bool UAnomalyProgressionSubsystem::ImportSave(const FString& Source,FString& Reason)
{
    if(SavePath.IsEmpty() || IFileManager::Get().FileExists(*SavePath) || IFileManager::Get().FileExists(*(SavePath+TEXT(".bak")))
        || FPaths::ConvertRelativePathToFull(Source)==SavePath) { Reason=TEXT("目标已有存档，导入拒绝覆盖"); return false; }
    TArray<uint8> Bytes; FAnomalyMetaProgress Imported; bool Future=false;
    if(!FFileHelper::LoadFileToArray(Bytes,*Source) || !FAnomalyMetaPersistence::Decode(Bytes,Imported,Future,Reason))
    { Reason=TEXT("旧档导入验证失败：")+Reason; return false; }
    Sanitize(Imported,Config);
    if(!Commit(Imported,Reason)) return false;
    for(const auto& ID:Progress.RecentPurchases) Purchases.Add(ID);
    for(const auto& ID:Progress.RecentSettlements) SettledRuns.Add(ID);
    return true;
}
