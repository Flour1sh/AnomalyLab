#include "AnomalyPlacementConfig.h"
#include "AnomalyRoundCoordinator.h"
#include "AnomalyBoxActor.h"
#include "AnomalyWorldPickup.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Character.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"

const TArray<FVector>& UAnomalyPlacementConfig::Points(int32 Region) const
{ return Region==0?APoints:Region==1?BPoints:CPoints; }
bool UAnomalyPlacementConfig::FindPickupSpot(AAnomalyRoundCoordinator* Owner,const FVector& Point,FVector& Location) const
{
    if(!Owner || !Owner->GetWorld() || Point.ContainsNaN() || LootOffset.ContainsNaN()) return false;
    auto W=Owner->GetWorld(); auto Player=UGameplayStatics::GetPlayerCharacter(Owner,0);
    const FVector Eye=Point+FVector(165,0,160-Point.Z);
    FCollisionQueryParams Params(SCENE_QUERY_STAT(V05PickupSpace),false,Player); Params.AddIgnoredActor(Owner);
    for(TActorIterator<AAnomalyBoxActor> It(W);It;++It) Params.AddIgnoredActor(*It);
    for(TActorIterator<AAnomalyWorldPickup> It(W);It;++It) Params.AddIgnoredActor(*It);
    // Finite, deterministic fallback stays inside the already validated standing capsule.
    const FVector Spots[]={LootLocation(Point),Point+FVector(165,0,35)};
    for(const FVector& Loot:Spots)
    {
        if(FVector::DistSquared(Eye,Loot)>FMath::Square(280.f)
            || W->OverlapBlockingTestByChannel(Loot,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeSphere(32.f),Params)) continue;
        FHitResult Hit; if(W->LineTraceSingleByChannel(Hit,Eye,Loot,ECC_Visibility,Params)) continue;
        Location=Loot; return true;
    }
    return false;
}
bool UAnomalyPlacementConfig::Legal(AAnomalyRoundCoordinator* Owner,const FVector& Point) const
{
    if(!Owner || !Owner->GetWorld()) return false;
    auto W=Owner->GetWorld(); auto Player=UGameplayStatics::GetPlayerCharacter(Owner,0);
    auto Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(W); if(!Player || !Nav) return false;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(V05Placement),false,Player); Params.AddIgnoredActor(Owner);
    for(TActorIterator<AAnomalyBoxActor> It(W);It;++It) Params.AddIgnoredActor(*It);
    FHitResult Floor;
    if(!W->LineTraceSingleByChannel(Floor,Point+FVector(0,0,180),Point-FVector(0,0,90),ECC_Visibility,Params)
        || Floor.ImpactNormal.Z<.95f || FMath::Abs(Floor.ImpactPoint.Z)>8) return false;
    if(W->OverlapBlockingTestByChannel(Point+FVector(0,0,55),FQuat::Identity,ECC_Pawn,FCollisionShape::MakeBox(FVector(68,68,55)),Params)) return false;
    const FVector Approach=Point+FVector(165,0,96-Point.Z);
    if(W->OverlapBlockingTestByChannel(Approach,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(32,90),Params)) return false;
    FHitResult LOS;
    if(W->LineTraceSingleByChannel(LOS,Approach+FVector(0,0,64),Point+FVector(0,0,60),ECC_Visibility,Params)) return false;
    FNavLocation Projected,Threat;
    if(!Nav->ProjectPointToNavigation(Approach,Projected,FVector(45,45,150)) || FVector::DistSquared2D(Projected.Location,Approach)>FMath::Square(40.f)
        || !Nav->ProjectPointToNavigation(Point+Owner->ExplorationThreatOffset,Threat,FVector(45,45,150))) return false;
    auto Path=UNavigationSystemV1::FindPathToLocationSynchronously(W,Owner->EntranceLocation+FVector(0,0,96),Projected.Location);
    if(!Path || !Path->IsValid() || Path->IsPartial()) return false;
    return PickupSpace(Owner,Point) && !W->OverlapBlockingTestByChannel(Threat.Location+FVector(0,0,48),FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(32,43),Params);
}
TArray<int32> UAnomalyPlacementConfig::LegalPoints(AAnomalyRoundCoordinator* Owner,int32 Region) const
{
    TArray<int32> Result; const auto& Candidates=Points(Region);
    for(int32 I=0;I<Candidates.Num();++I) if(Legal(Owner,Candidates[I])) Result.Add(I);
    return Result;
}
bool UAnomalyPlacementConfig::Choose(AAnomalyRoundCoordinator* Owner,int32 Region,int32 Seed,int32 Round,FTransform& Transform,int32& PointId) const
{
    const auto& Candidates=Points(Region); if(Candidates.Num()<3 || Region<0 || Region>2) return false;
    // Placement never consumes RegionStream or a box configuration/outcome stream.
    FRandomStream Placement(int32(uint32(Seed)^uint32(Round)*0x9e3779b9u^uint32(Region+1)*0x85ebca6bu));
    const int32 First=Placement.RandRange(0,Candidates.Num()-1);
    for(int32 N=0;N<Candidates.Num();++N)
    {
        const int32 Id=(First+N)%Candidates.Num();
        if(!Legal(Owner,Candidates[Id])) continue;
        PointId=Id; Transform=FTransform(FRotator::ZeroRotator,Candidates[Id]); return true;
    }
    PointId=INDEX_NONE; return false; // finite failure, Coordinator error returns Hub
}
