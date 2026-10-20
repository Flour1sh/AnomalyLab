# v0.5 T33 architecture audit and frozen migration

Baseline: Human Accepted `AnomalyLab_v04_RC_20261013T131738`, UE 5.8 / Win64 Development. Working copy: `F:/AnomalyLab/AnomalyLab_v05`. Original `F:/AnomalyLab/我的项目3` and its Builds/Releases are protected, never used as test output. No Git; use complete SHA checkpoints. This document separates audited facts from planned T34–T42 behavior.

## Audited authority and precise migration

Paths below are relative to the working copy. Native paths start at `Source/AnomalyLab/`.

| Existing entry / owner | Actual v0.4 implementation | Planned v0.5 boundary |
|---|---|---|
| Main menu | `Private/AnomalyMenuGameMode.cpp`: `StartLevel01` guards repeated start, shows loading, timer calls `OpenLevel(/Game/Prototype/Maps/L_Prototype)`; separate menu mode/controller, no pawn | Keep menu mode/UI, route production start/continue to `/Game/Maps/L_Hub`; no economy in UI. Continue loads permanent progress, not a Lab snapshot |
| Normal map | `Content/Prototype/Maps/L_Prototype.umap`; map instance `BP_BoxSpawner : AAnomalyRoundCoordinator`, Exploration, Preparation enabled | Preserve disk map and Legacy paths; duplicate exploration to `Content/Maps/L_Lab.umap`; build new `Content/Maps/L_Hub.umap` independently |
| Shop | Coordinator::`IsPreparing` requires Preparation, live health, entrance proximity; `ShopUp/Down/Buy/PurchaseProduct`; UI `WBP_ExplorationPrompt` ShopText/ShopBacking/MetaText | New Hub controller/terminal owns focus and input. Purchase remains a method of the existing Progression subsystem. Production Lab always rejects buying; legacy fixtures retain old preparation path |
| Permanent account | `Public/AnomalyProgressionSubsystem.h`, `Private/AnomalyProgressionSubsystem.cpp`, `UGameInstanceSubsystem` | Keep this sole money/upgrade authority across OpenLevel. Factor validated transaction body and add typed Hub authorization; do not expose a generic unchecked purchase Boolean |
| Save | `AnomalyMetaSaveGame.h/.cpp`: Schema2 USaveGame CRC/length envelope; temp/readback/backup/replace; recent 128 purchase/settlement GUIDs; memory updated after durable write | Keep fields/schema/slot compatibility. Tighten unreadable-existing-file behavior for v0.5, define explicit import for relocated saves (SAVE_MIGRATION.md) |
| Launch | Coordinator::BeginPlay creates RunId; `StartPreparedRun → Progression::BeginRun` consumes stored decoy durably, then scanner/capacity initialized in SAME world | Transition subsystem owns unique RunId and frozen value-only loadout. Hub launch consumes once; Lab claims once, reuses scanner/inventory setup WITHOUT another BeginRun. Do not generate a second RunId on Lab BeginPlay |
| Scanning | `AnomalyScannerComponent.cpp` / `AnomalyBoxActor.cpp`, BPC_Scanner bridge, WBP_ScanPanel | Remains Lab-local, 1 sec / 300cm / LOS / cache / finite charges. Hub scanner and equipment input disabled before any scan operation |
| Box choice / RNG | Coordinator::SpawnNextBox; three explicit BoxPointLeft/Middle/Right + RegionRules; box configuration/outcome/visual streams | Keep select-one-lock-two and outcome RNG. T37 separate seed stream for three legal candidates per region; do not consume old result stream |
| Loot / Wallet | `AnomalyWorldPickup`, `AnomalyInventoryComponent`: local carry; Wallet only terminal adapter | No carry/actor pointers in GameInstance. Only successful physical extraction becomes permanent currency |
| Physical extraction | `ConfirmExtraction → next tick CommitExtraction → EndRun`; XY325 / Z180 / LOS, valid phases; pending next frame lets same-frame death win | Preserve validation/death priority; close Lab interactions, produce immutable DTO, durable commit once, publish result then request Hub travel |
| Settlement | `EndRun` seals NativeState=3; `CreditExtraction` validates caller RunId/end reason/authorization/not settled; snapshot copied once | Keep economy/RunId dedupe; Transition owns result copy across unload. Hub report reads DTO only; never calls credit. Missing Progression in v0.5 Lab MUST fail closed (old code can fall back to Wallet only) |
| Death / error | `HandlePlayerDeath → EndRun`; lose carry, clear local world; EndPlay removes health delegates/widgets and timers | Result Failed/Error, no credit, quiesce AI/audio/timers, return Hub alive with fresh pawn. Technical travel failure remains a safe error, never successful extraction |
| R restart | `BP_FirstPersonCharacter`, graph `T06Restart`: Ended gate → GetCurrentLevelName → OpenLevel(current) | v0.5 Lab end returns Hub; R must not reopen Lab. Preserve accepted Legacy graph/path behavior with an explicit mode route |
| Threats | `AnomalyThreatCharacter` / `AnomalyObserverCharacter`, existing warning/chase/health/LOS and observer hysteresis | Lab only. Hub has no coordinator, threat spawner, box, loot or damage activation. Clear world-owned callbacks on departure |
| HUD | `AnomalyExplorationWidget`, `AnomalyStatusWidget`, `AnomalyDecisionWidget`; widget passive, coordinator updates | Separate Hub widget, Lab HUD stays passive. Result screen in Hub from DTO; GameOnly vs UIOnly focus explicit |

## Proposed modules (not implemented in T33)

- `UAnomalyTransitionSubsystem : UGameInstanceSubsystem`: lifecycle/travel authority only, no independent economy. Values: RunId, monotonic transition version, target package, seed, loadout, result; never world Actor/component/widget references. Soft asset IDs allowed; value DTOs copied.
- `AAnomalyHubGameMode` + Hub controller/terminal + passive Hub widget: create safe pawn, shop/loadout/departure/report; spatial interaction distance and LOS; all transaction permission validated against active Hub world and HubReady.
- Existing `AAnomalyRoundCoordinator`: retain legacy branch; add explicit Lab role/transition claim, configure existing Progression regardless of `bUsePreparation`, apply frozen loadout, existing in-run logic, end cleanup/result handoff.
- Separate environment config/service for T38–T40: B power, C containment and seeded event effects; threat/scan interfaces consume a bounded snapshot, HUD only renders it.
- Scripts: new `build_v05_levels.py` target allowlist and versioned modules; never run old `build_t20_assets.py`/`build_scene_polish.py` to build new levels because they hardcode L_Prototype and shared assets.

## Lifecycle contract frozen before gameplay changes

`HubReady → Preparing → LaunchRequested → LoadingLab → LabInitializing → InRun → ExtractionRequested/Died/Error → FinalizingRun → ResultCommitted → LoadingHub → HubReady`.

1. Hub checks destination exists, freezes values and unique RunId, commits existing decoy-consumption transaction once. Failed persistence leaves Hub ready and unchanged. Failed travel after durable launch is an abandoned run; consumed decoy is not refunded (same v0.4 quit rule).
2. Lab consumes matching RunId/version once. Repeated E, BeginPlay, old delegates and a stale version cannot create another run/travel. Unauthorized direct Lab returns Hub; explicit Development inspection flag only permits a read-only map audit without boxes/transactions.
3. Death wins over a pending extraction before any success is sealed. EndSnapshot contains only values. Success persists once via existing Progression; death/error produce zero credit. Publish snapshot only after commit result is known.
4. Stop timers, scans, threat movement/attacks, looping and one-shot audio sources owned by the departing world, and input before travel. EndPlay defensively repeats idempotent cleanup. No old-world callback may mutate a new run.
5. Crash/restart has no resumed Lab carry: menu → Hub with saved permanent progress. Never replay the previous report as a financial transaction. No new persistent active-run state needed for this policy.

## Build / fixtures

Engine `E:/UE_5.8`; use a NEW ASCII build workspace in this copy's Saved/BuildWork and its own `Saved/CppMigration/latest.json`. Build once sequentially, MaxParallelActions=2, no shared old context. Tests reuse original unmodified assertions: run_v04(T27/T28), run_t29, run_t26, run_t30, run_t31, run_v03, run_t19_menu, run_t18. `run_v05_baseline.py` orchestrates only and stops on failure. Native test reports/screenshots are separate from human observations. Baseline runtime tests execute a COPIED RC in `Saved/V05/T33/BaselinePackage/Windows`, never the accepted RC itself.

Fresh-process actual asset/class/transform/config inspection: `Scripts/audit_v05_baseline_assets.py` → `Saved/V05/T33/asset_audit.json`. No asset saves or generation in T33.

Fresh reload completed: 16/16 checks PASS. Menu46 actors, no Coordinator/Pawn start; exploration277 actors, exactly one Coordinator and PlayerStart `(0,1750,110)` yaw-90, one NavBounds+Recast, no placed boxes. Legacy44 actors, preparation/regions disabled. Real gameplay class refs: `/Game/FirstPerson/Blueprints/BP_FirstPersonGameMode.BP_FirstPersonGameMode_C`, Pawn=`BP_FirstPersonCharacter_C`, controller=`BP_FirstPersonPlayerController_C`, HUD=`/Script/Engine.HUD`. Exploration assets: `/Game/Prototype/Data/DA_ProgressionConfig`, `/Game/Prototype/Data/DA_BalanceConfig`, `/Game/Prototype/Observer/DA_ObserverConfig`, `/Game/Prototype/Data/Regions/DA_Region_{A,B,C}`, `/Game/UI/WBP_ExplorationPrompt`.

## T34 actual implementation (supersedes planned map ownership above)

`Public/AnomalyHub.h` / `Private/AnomalyHub.cpp`: independent safe AAnomalyHubCharacter, HubPlayerController, HubGameMode, native passive HubWidget contract and ID-only HubTerminal. Capsule34/96, walk350, jump420, aircontrol.6 copied from audited player defaults; camera90° at standing eye160cm. Original player/BPs unchanged. Local controller-only WASD axis mappings do not mutate project/global input settings. No Health/Scanner/Equipment/Inventory/Wallet on safe pawn; TakeDamage returns0.

`Scripts/build_v05_levels.py` + `t34_layout.py`: authored safe modules, real copied Lab, four spatial ID terminals, new `Prototype/V05/UI/WBP_Hub`, duplicated `WBP_MainMenu_V05` with DEVELOPMENT version, new warm/mint materials. Default menu code uses new menu copy and Hub package; only explicit non-Shipping `-AnomalyLegacyMenuRoute` selects original menu+L_Prototype. Original menu asset/three maps/shared Content remain byte-identical.

Lab map uses original BP_FirstPersonGameMode/Pawn/controller and Coordinator, `bAwaitLevelLaunch=true`, `bUsePreparation=false`. While awaiting: existing meta config initialized read-only, RunId invalid, no boxes, no consumption/purchase/extraction/end-credit, HUD reports waiting. T35 must replace this gate with real transition claim; no stage placeholder is considered completed economic routing. Hub terminal panels are read-only in T34; T35/T36 add departure and existing authorized purchases. No new financial authority/schema.

`Private/AnomalyV05LevelSmoke.cpp`: explicit Development fixture registered in module, safe Automation_ slot detection; validates default menu button→Hub (no compatibility override), independent map worlds, real W/E/ESC synthetic input, wall collision, NavMesh completeness, terminal LOS and safe gameplay-key rejection. Runtime views/fixtures are reported separately from human input. T34 regression wrappers preserve old assertion bodies and explicitly request old menu route for old core/menu contract tests.

## T35 frozen lifecycle contract
TransitionSubsystem owns only value DTOs/RunId/version. Hub authorizes physical departure, Progression persists consumption once, Lab claims once and applies frozen equipment. Existing Coordinator owns extraction and death priority; durable success then immutable report and cleanup before Hub travel. Schema2 unchanged. Unreadable existing saves block financial writes; explicit import reads source without modifying it. User authorized sequential T35–T42 with per-stage gates and final unified human tests.

## T36–T41 implemented modules (supersedes earlier stage placeholders)

Progression.PurchaseAuthorized is the single private purchase/commit authority; typed Hub authorization and legacy Coordinator share prices/caps/revision/GUID logic. ImportSave validates old bytes, refuses an existing destination/backup and writes Schema2 without modifying source. Both-corrupt/future saves block writes and departure.

AnomalyPlacementConfig owns authored candidates, floor/collision/standing/LOS/NavMesh/threat clearance checks and bounded fallback. Layout RNG is isolated from region/outcome/reward RNG. Actual saved Lab has 284 actors including world-owned environment service and two consoles; Hub has51 and no gameplay service.

AnomalyEnvironmentConfig/Controller/Terminal own B power, C one-use3-second Chaser stasis and seeded PowerFluctuation/ContainmentAlarm. Event plans allow quiet runs, warning, bounded durations and spacing; box-warning overlap delays effects. No economic authority. All services cancel/restore on EndRun/EndPlay.

AnomalyTelemetry is a Coordinator-owned value recorder: UTC RunId/seed/rooms/box-point events/scans/generated and extracted value/loss/equipment/threat damage/environment responses/return time/loading/actual sampled CPU frame delta. At most12000 frame samples,512 event rows,450000 JSON characters and20 strict RunId files. Temp+move writes to Saved/V05/Telemetry, separate from MetaSave; -NoRunTelemetry disables it without changing financial behavior. No human identifiers. Events are structured rows with Kind (BoxSpawnPoint/EventId/EventResponse) and Detail.

AnomalyLoadingWidget is opaque, world-owned and removed during unload. Transition queues OpenLevel after0.3seconds so a loading frame renders; subsystem stores only destination/version/timestamps, with the existing45-second watchdog. Map checks normalize PIE prefixes. No persistent Actor or Widget references cross worlds.

AnomalyJourneySmoke drives actual synthetic W collision/navigation, Q/E/arrow/Enter and production menu button through three trips without teleporting. Initial funds, safe reward and lethal death are explicit fixtures; other suites separately exercise random distributions/threats/events and durability failures. Automated routes/performance are not human pace/balance evidence.

## T42 package-discovered pickup correction

The first package exposed A6's original box-relative `(0,-130,35)` drop behind a specimen rack. Placement now validates a configurable pickup offset plus a finite fallback at the validated standing position (sphere clearance, range and visibility). Coordinator revalidates the chosen pickup spot at spawn only for v0.5; legacy transforms and outcome/value RNG are unchanged. Placement20 now aims at and E-picks the real generated item in every trip, carrying its exact value through success/death/save-fault checks. The first candidate and failed report remain intact. Journey screenshots now hold intermediate panels across a rendered frame before ESC.
