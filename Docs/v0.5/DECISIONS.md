# v0.5 decisions

2026-10-13 / Asia/Shanghai. T33 contract/design only; no gameplay changes yet.

1. **Isolation**: independent engineering copy `F:/AnomalyLab/AnomalyLab_v05`; accepted original source/RC/v0.3 and v0.4 release archives never mutated or executed. Baseline RC copied for runtime; before/after full SHA verification. No Git exists, so full checkpoints replace commits.
2. **Sequence**: follow plan §13.2 one Txx per agent session, §14 first T33 only. Finish audit/compile/regression/visible baseline/report/checkpoint; T34–T42 remain explicit subsequent stages. No package creation before all feature stages pass. Existing copied RC is a regression fixture, not a v0.5 package.
3. **Real levels**: `/Game/Maps/L_Hub`, `/Game/Maps/L_Lab`; preserve `/Game/Prototype/Maps/L_Prototype` and Legacy. Duplicate current saved Lab scene; new allowlisted builder, no blind historical scene regeneration.
4. **Money**: existing ProgressionSubsystem/SaveGame sole authority; Wallet remains run display, inventory run carry. Hub authorization wraps existing transaction implementation. No independent Hub wallet/shop balance.
5. **Travel**: separate GameInstance transition subsystem for RunId/version/value DTOs, standard OpenLevel, loading frame first. No world actor refs. Lab cannot enable old Preparation as a shortcut because that grants purchasing and consumes a second launch. Explicit role/claim plus fail-closed meta configuration required.
6. **Equipment**: preserve prices1000/1500/2500/600, maxima2/2/1/1, charges/precision/capacity effects. No added loadout-slot economy. Existing decoy consumed durably once on accepted launch; no refund after abandonment/death. Lab applies frozen snapshot once.
7. **End**: death-before-pending-credit priority unchanged. Seal world entry points, immutable result, durable financial result, cleanup, Hub. Hub report display cannot write currency. Repeated callbacks/requests validated against RunId/version/world role. Errors never receive loot credit.
8. **Persistence**: retain economic Schema2/default slot; no persistent active-run replay. Existing-unreadable save must block writes in v0.5, preserving evidence/backup. Relocated package requires explicit validated save import, not a fresh-account assumption. See SAVE_MIGRATION.md.
9. **Legacy**: old test assertions/graphs remain intact; no production force-success. Production Lab gets no shop/restart loophole. Direct Lab without a valid launch returns Hub; only explicit read-only map inspection bypasses that return. Declared deterministic fixtures exercise individual branches separately from distribution tests and human play.
10. **RNG/extensibility**: placement/event streams independent of old outcome streams, point IDs/config data. Environment mechanics own bounded effect snapshots and cleanup; UI only shows feedback. T38/T39 determine actual numeric effects using real code/tests, not assumptions in T33.
11. **Evidence**: automated tests, rendered agent review, actual physical-input tests, and human balance samples recorded separately. v0.4 user overall acceptance valid; no claimed 5×3 sample, duration, subjective sound or performance evidence. T42 marked Engineering Verified/Awaiting Human Validation until explicit new confirmation.
12. **Build permission**: initial unchanged-source build hit sandbox writes in UBT user-log directory; retain failure. Retry authorized same build with appropriate sandbox permission, no full engine/repository changes. Keep limited compile concurrency and distinct ASCII work context.

T34执行补充：使用独立安全Pawn而不是复制旧玩家的战斗组件；真实移动参数先审计，项目全局输入不改，Hub每Controller私有轴映射。终端T34只读，经济出发/购买留T35/T36；Lab明确等待授权而非无持久化自动开局。新菜单Widget由旧资产复制并改DEVELOPMENT版本，原菜单资产不动；旧回归通过显式Development兼容参数选择旧路由，正常菜单路由另有新增测试。T34不运行打包。

## T35 frozen lifecycle contract
TransitionSubsystem owns only value DTOs/RunId/version. Hub authorizes physical departure, Progression persists consumption once, Lab claims once and applies frozen equipment. Existing Coordinator owns extraction and death priority; durable success then immutable report and cleanup before Hub travel. Schema2 unchanged. Unreadable existing saves block financial writes; explicit import reads source without modifying it. User authorized sequential T35–T42 with per-stage gates and final unified human tests.

## T36 shared financial body
Legacy Purchase and typed Hub PurchaseHub authorize separately then call one private PurchaseAuthorized body. Hub requires physical Shop panel/LOS/range and HubReady; same prices/limits/revisions/request GUID/durable commit. UI selection/text only. Immutable report auto-opens on return; ESC restores movement. Error report carries failed-persistence detail and uncredited carry loss. No Save schema change.

## T37 independent placement
APoints/BPoints/CPoints hold finite authored candidates. Placement stream derives Seed/Round/Region but never consumes RegionStream/box streams. Box configuration/outcome seed derives only RunSeed/Round/Region, never PointID; Legacy branches unchanged. Candidate checks include floor, crate volume, standing approach/LOS, complete entrance Nav route and threat projected capsule. Finite cyclic fallback; no valid candidates produces Error and safe Hub return. Existing old Content remains immutable.

## T38/T39 chosen tradeoffs (planned, gates required before implementation)
Actual Observer has no scan-noise registration interface. B power-off therefore costs a frozen 1.75x scan duration for B boxes and benefits sustained visual suppression: when both player and Observer are in B, tolerance becomes 1.5x (4→6 seconds), rather than inventing noise probability. Other regions/Legacy unaffected, no reward RNG changes. Toggling cancels an in-progress scan; completion still costs one charge and cached scans remain free.
C chamber supports one Chaser in a marked radius with 3 seconds stasis, no direct ResolveThreat, no money or contained-stat increment. Observer explicitly immune with a visible explanation, preserving its observation mechanic. Stasis affects only the chosen target's movement/contact; another threat may still damage. World-local weak reference/timer only, cleared on unload. Environment IDs/config/snapshots separated from economy.

## T40–T42 execution decisions

Events use an independent seeded plan:50% quiet, max2, first12–16seconds,2-second warning,4-second effect, at least10seconds spacing. Power fluctuation uses the actual B light/scan/observation interfaces and manual recovery. C alarm changes tagged lights and ordinary Chaser speed1.08×; Chamber/withdrawal remain responses. Existing box warnings delay the effect to avoid simultaneous opaque cues.

Telemetry is bounded, separate from financial persistence and can be disabled. FPS is actual sampled CPU delta, not GPU timing. Real synthetic W navigation through the normal menu/Hub/shop/Lab/pickup/extraction is tested without teleports; initial currency and deterministic branch outcomes are explicitly reported fixtures. Loading cover renders before queued travel. No human sample or3–5minute claim comes from these routes.

User explicitly authorized T35–T42 sequential work with a test gate after each stage and final unified human testing. T42 produces Engineering Verified/Awaiting Human Validation. Full new package, new-directory source/package restoration and immutable archive SHA are required; no automatic HumanAccepted. No task writes to the original RC/archives. Four externally maintained original Docs differences retain exact SHA exceptions and the original strict FAIL audit.
