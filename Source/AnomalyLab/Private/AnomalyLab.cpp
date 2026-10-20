#include "Modules/ModuleManager.h"

#if !UE_BUILD_SHIPPING
void RegisterAnomalyJourneySmoke();
void UnregisterAnomalyJourneySmoke();
void RegisterAnomalyV05Smoke();
void UnregisterAnomalyV05Smoke();
void RegisterAnomalyMenuSmoke();
void UnregisterAnomalyMenuSmoke();
void RegisterAnomalyRegionSmoke();
void UnregisterAnomalyRegionSmoke();
void RegisterAnomalyV04Smoke();
void UnregisterAnomalyV04Smoke();
void RegisterAnomalyBalanceSmoke();
void UnregisterAnomalyBalanceSmoke();
void RegisterAnomalyObserverSmoke();
void UnregisterAnomalyObserverSmoke();
void RegisterAnomalyV05LevelSmoke();
void UnregisterAnomalyV05LevelSmoke();
#endif

class FAnomalyLabModule : public FDefaultGameModuleImpl
{
public:
    virtual void StartupModule() override
    {
        FDefaultGameModuleImpl::StartupModule();
#if !UE_BUILD_SHIPPING
        RegisterAnomalyJourneySmoke();
        RegisterAnomalyV05Smoke();
        RegisterAnomalyMenuSmoke();
        RegisterAnomalyRegionSmoke();
        RegisterAnomalyV04Smoke();
        RegisterAnomalyObserverSmoke();
        RegisterAnomalyBalanceSmoke();
        RegisterAnomalyV05LevelSmoke();
#endif
    }
    virtual void ShutdownModule() override
    {
#if !UE_BUILD_SHIPPING
        UnregisterAnomalyJourneySmoke();
        UnregisterAnomalyV05Smoke();
        UnregisterAnomalyMenuSmoke();
        UnregisterAnomalyRegionSmoke();
        UnregisterAnomalyV04Smoke();
        UnregisterAnomalyObserverSmoke();
        UnregisterAnomalyBalanceSmoke();
        UnregisterAnomalyV05LevelSmoke();
#endif
        FDefaultGameModuleImpl::ShutdownModule();
    }
};

IMPLEMENT_PRIMARY_GAME_MODULE(FAnomalyLabModule, AnomalyLab, "AnomalyLab");
