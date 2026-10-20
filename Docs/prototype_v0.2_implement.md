# Anomaly Lab Prototype v0.2 Implementation Plan

> 本文件保留为 v0.2 原始实施提纲。已确认规则与分阶段验收见 [prototype_v0.2_decisions.md](prototype_v0.2_decisions.md)。截至 2026-10-05，T11、T11E、T12、T13、T14 已由用户验收；T15 完成构建和资产重载，待玩法测试。事实以 STATE.md 为准。本机纯 Python 构建采用下述 DataAsset 选项，取代 Struct/DataTable 工程默认方案。

## 0. Document Purpose

This document defines the implementation plan for **Anomaly Lab Prototype v0.2**.

The goal of v0.2 is **not** to expand the project into a full game, add multiplayer, or build a complex combat system.

The goal is to evolve the existing v0.1 prototype from:

```text
Approach Box
→ Press E
→ Random Outcome
→ Resolve
→ Next Round
```

into a gameplay loop based on:

```text
Information
→ Comparison
→ Decision
→ Risk
→ Consequence
→ Continue or Cash Out
```

v0.1 already provides the technical foundation:

* First-person movement
* Interaction raycast
* Interactable interface
* One-time box interaction
* Random HighValue / Trash / Threat outcome
* Wallet and money updates
* Threat spawning and chasing
* Threat resolution
* Round coordination
* HUD
* Run Over
* Restart
* Windows Development packaging

The current system already separates responsibilities reasonably well:

* Box determines its outcome.
* Wallet owns money modification.
* Spawner coordinates round lifecycle.
* HUD only presents information.
* Interaction component does not depend on a specific box type.
* Level Blueprint is not responsible for round logic.

v0.2 must preserve these boundaries unless there is a strong technical reason to change them.

---

# 1. v0.2 Core Goal

The player should have a meaningful reason to hesitate before opening a box.

By the end of v0.2, a complete run should roughly behave like this:

```text
Start Run
    ↓
Spawn Multiple Candidate Boxes
    ↓
Player Inspects / Scans Boxes
    ↓
Receive Incomplete Information
    ↓
Player Chooses One Box
    ↓
Open Selected Box
    ↓
Resolve Reward / Trash / Threat
    ↓
Player Survives or Fails
    ↓
Post-Round Decision
    ↓
CONTINUE or CASH OUT
    ↓
Next Round / Run Complete
```

The main design pillars are:

1. **Incomplete information**
2. **Meaningful choice**
3. **Risk versus reward**
4. **Accumulated value**
5. **Possibility of losing unbanked progress**

---

# 2. Scope Rules

## 2.1 Included in v0.2

v0.2 includes:

* Data-driven box definitions
* Multiple box choices per round
* Scanner system
* Approximate / incomplete scan information
* One-box-per-round choice locking
* Continue / Cash Out decision
* Simple player failure state
* Threat consequences
* Round state expansion
* Balance/debug support
* Full PIE validation
* Windows Development package

---

## 2.2 Explicitly Out of Scope

Do **not** implement the following unless separately approved:

* Multiplayer
* Steam Sessions
* Online subsystem
* Inventory
* Equipment system
* Full combat system
* Guns
* Ammunition
* Complex enemy AI
* Multiple maps
* Procedural level generation
* Shop system
* Permanent progression
* Skill tree
* Save system
* Complex loot inventory
* Crafting
* Advanced VFX pass
* Advanced audio system
* Character animation overhaul
* Large-scale architecture rewrite

The purpose of v0.2 is gameplay validation, not feature expansion.

---

# 3. Existing Architecture to Preserve

The following responsibilities from v0.1 should remain stable.

## `BPC_Interaction`

Responsible for:

* Camera-center raycast
* Focus detection
* Interaction prompt
* Interact input routing

Should not:

* Know concrete box subclasses
* Decide anomaly results
* Modify money
* Control rounds

---

## `BPI_Interactable`

Responsible for:

```text
Interact(Interactor)
```

May be extended only if required.

Avoid replacing the interaction architecture with direct casts.

---

## `BP_AnomalyBox`

Responsible for:

* Box-specific state
* Open-once protection
* Box opening presentation
* Box outcome data
* Outcome selection
* Result request / notification

In v0.2 it may additionally own:

* Box definition
* Hidden true risk/value data
* Scan-visible information
* Scan state

It should **not** become the round manager.

---

## `BPC_Wallet`

Must remain the authoritative source for money changes.

Responsibilities:

* Current run money
* Money modification
* Money changed event

Do not directly modify money inside HUD, Spawner, loot Actors, or Scanner.

---

## `BP_BoxSpawner`

Currently acts as the round coordinator.

In v0.2 this responsibility expands.

It should control:

* Round start
* Candidate box spawning
* Box selection lock
* Round resolution
* Cleanup
* Threat lifecycle coordination
* Post-round decision
* Continue
* Cash Out
* Run end

This should remain the central gameplay flow coordinator.

---

## `BP_Spider`

Responsible for threat behavior.

Existing behavior:

* Chase player
* Attack notification
* Threat resolution support

v0.2 should extend consequences without turning Spider into a global gameplay controller.

---

## `WBP_PrototypeHUD`

Presentation only.

May display:

* Money
* Crosshair
* Interaction prompt
* Scan results
* Current risk/value estimate
* HP
* Round decision UI
* Cash Out UI
* Death / Run Over state

Should not own gameplay rules.

---

# 4. Proposed v0.2 Systems

---

# T11 — Data-Driven Box Definitions

## Goal

Replace the current concept of identical boxes with multiple box categories that have different value and threat characteristics.

---

## Recommended Data Structure

Create either:

```text
FAnomalyBoxData
```

and use a DataTable,

or:

```text
PDA_AnomalyBoxDefinition
```

using Primary/Data Assets.

Prefer the implementation that produces the cleanest Blueprint workflow.

Suggested fields:

```text
BoxID
DisplayName

ValueMin
ValueMax

ThreatChance

TrashChance
HighValueChance

ScanValueError
ScanRiskError

BoxVisualType

OptionalDebugColor
```

Probabilities must be validated.

For example:

```text
HighValueChance + TrashChance + ThreatChance = 1.0
```

or equivalent integer weight representation.

---

## Initial Box Types

Only create approximately three prototype definitions.

### Safe Box

```text
Risk: Low
Expected Value: Low
```

Example:

```text
HighValueChance = 0.30
TrashChance     = 0.60
ThreatChance    = 0.10
```

---

### Risky Box

```text
Risk: High
Expected Value: High
```

Example:

```text
HighValueChance = 0.55
TrashChance     = 0.10
ThreatChance    = 0.35
```

---

### Unknown Box

```text
Risk: Uncertain
Expected Value: Uncertain
```

Its scan result should be less precise.

---

## Requirements

The actual values do not need to be balanced yet.

The important requirement is:

> Different box definitions must produce meaningfully different player decisions.

---

## Acceptance

PASS if:

* At least three box definitions exist.
* BP_AnomalyBox receives or selects a definition.
* Outcome selection uses definition data.
* Existing HighValue / Trash / Threat results still work.
* Forced debug result mode still works if already present.
* No money is directly changed by the box itself outside the existing wallet request path.

---

# T12 — Scanner System

## Goal

Allow the player to inspect a box before opening it.

The scanner must provide **incomplete information**, not reveal the answer.

---

## Player Interaction

Suggested input:

```text
Q = Scan
```

Exact key may change if input conflict exists.

Scanner should work only when:

* A valid anomaly box is focused.
* Player is within valid scan range.
* Round state permits scanning.
* Box has not already been resolved.

---

## Suggested Component

Prefer a new component:

```text
BPC_Scanner
```

Responsibilities:

* Receive scan input
* Detect currently focused scan target
* Request scan information
* Forward presentation data to HUD

Do not merge scanner logic into BPC_Interaction unless implementation is significantly simpler and responsibility remains clear.

---

## Scan Information

Example display:

```text
VALUE ESTIMATE
$1500 - $4200

DANGER
MEDIUM

SIGNAL
BIOLOGICAL?
```

Possible fields:

```text
EstimatedValueMin
EstimatedValueMax

RiskCategory

SignalCategory

Confidence
```

---

## Critical Rule

Scanner data must derive from the underlying box data but include uncertainty.

Example:

True box:

```text
Average value:
$5000

Threat chance:
40%
```

Possible scan:

```text
Estimated value:
$3500 - $7000

Danger:
MEDIUM / HIGH
```

Do not display:

```text
Threat Chance: 40%
```

unless temporarily enabled for debug mode.

---

## Recommended Risk Categories

Use simple categories:

```text
LOW
MEDIUM
HIGH
UNKNOWN
```

Do not overcomplicate statistical modeling.

---

## Scan State

A box may track:

```text
bHasBeenScanned
CachedScanResult
```

Recommended behavior:

> Repeated scanning of the same box during one round should return the same result.

This prevents players from repeatedly scanning until they receive favorable noise.

---

## Acceptance

PASS if:

* Player can scan a focused box.
* Invalid targets do not scan.
* Scan information appears on HUD.
* Scan result does not reveal exact outcome.
* Repeated scan does not reroll information.
* Opening still works after scanning.
* Scanner does not modify box outcome.
* Scanner does not modify money.

---

# T13 — Multi-Box Round

## Goal

Replace the single-box round with multiple candidate boxes.

---

## Default Setup

Each round should spawn:

```text
3 candidate boxes
```

The exact number should preferably be configurable.

---

## Spawn Points

Do not hardcode world coordinates directly inside gameplay graphs if avoidable.

Recommended options:

```text
BP_BoxSpawnPoint
```

or:

```text
SceneComponents / TargetPoints
```

owned or referenced by BP_BoxSpawner.

---

## Round Flow

At round start:

```text
Spawn Box A
Spawn Box B
Spawn Box C
```

Each may receive a different box definition.

Player may:

```text
Inspect A
Inspect B
Inspect C
Scan A
Scan B
Scan C
```

Once one is opened:

```text
SelectedBox = OpenedBox
```

Then:

```text
Other boxes become unavailable.
```

They may either:

* Disable interaction immediately
* Visually lock
* Destroy after outcome starts

Prefer clear visual feedback over instant unexplained disappearance.

---

## Selection Lock

Spawner must ensure only one box can become the round selection.

Recommended conceptual function:

```text
TryLockRoundSelection(Box)
```

Pseudo logic:

```text
if RoundState != AwaitingSelection:
    reject

if SelectedBox is valid:
    reject

SelectedBox = Box
RoundState = Resolving
DisableOtherBoxes()
```

This must protect against duplicate callbacks.

---

## Important

Do not rely only on each box independently setting:

```text
bOpened = true
```

because three boxes exist.

The **round-level selection** must be authoritative in Spawner.

---

## Acceptance

PASS if:

* Three boxes spawn.
* Player can inspect all three.
* Player can scan all three.
* Opening one locks the round.
* Remaining two cannot produce results.
* Duplicate interact input cannot produce multiple outcomes.
* Cleanup removes all candidate boxes.
* Next round creates a fresh candidate set.

---

# T14 — Post-Round Decision: Continue / Cash Out

## Goal

After a successful round, stop automatically progressing.

Make the player decide whether to continue risking accumulated money.

---

## Post-Round State

After loot or threat successfully resolves:

```text
RoundState = PostRoundDecision
```

HUD displays:

```text
CURRENT RUN VALUE
$XXXX

[CONTINUE]

[CASH OUT]
```

---

## Continue

Continue means:

```text
Keep current run money
Start next round
Spawn new candidate boxes
```

---

## Cash Out

Cash Out means:

```text
Finish current run successfully
Preserve displayed final amount
Disable further gameplay
Show successful run result
Allow restart
```

For v0.2, a permanent bank/save system is NOT required.

Cash Out only needs to mean:

> This run ended successfully with this amount.

---

## Input

Possible implementation:

```text
1 = Continue
2 = Cash Out
```

or UI buttons.

Choose whichever is most reliable for prototype testing.

---

## Acceptance

PASS if:

* Round completion enters decision state.
* No next round auto-spawns before player chooses.
* Continue keeps current money.
* Continue starts another round.
* Cash Out ends the run.
* Cash Out displays final amount.
* Interaction and scan inputs are disabled after run completion.
* Restart resets everything.

---

# T15 — Player HP and Failure Consequence

## Goal

Threat encounters must create a real gameplay risk.

The current threat must be capable of causing failure.

Do not build a full combat system.

---

## Minimal Player Health

Suggested:

```text
MaxHP = 100
CurrentHP = 100
```

May use:

```text
BPC_Health
```

if that produces clean separation.

Responsibilities:

* Health state
* Receive damage
* Health changed event
* Death event

---

## Threat Damage

Example:

```text
Spider Hit Damage = 40
```

Values are placeholder.

Existing attack notification logic should be extended into:

```text
Spider attacks
    ↓
Health receives damage
    ↓
HUD updates
```

---

## Attack Protection

Spider must not apply damage every frame.

Use:

* Attack cooldown
* One-hit guard
* Existing attack state
* Timer

Suggested:

```text
AttackCooldown = 1.0–2.0 seconds
```

---

## Death

When:

```text
CurrentHP <= 0
```

trigger:

```text
PlayerDeath
```

Spawner should receive death notification and enter:

```text
RunFailed
```

---

## Failure Rule

For v0.2:

```text
Player Death
→ Current unbanked run ends
→ Final successful cash-out value = 0
```

Do not implement long-term currency persistence.

The main purpose is to make Continue dangerous.

---

## Important Existing Extension Point

The threat system already has a concept of threat resolution.

Prefer integrating with the existing threat lifecycle rather than creating an unrelated second round system.

Threat resolution and player death must not both advance the round.

Use guards.

---

## Acceptance

PASS if:

* Player has visible HP.
* Spider deals controlled damage.
* Damage cannot trigger every frame.
* Player can die.
* Death ends run.
* Death prevents further scanning/opening.
* Death does not spawn next round.
* Restart restores HP and run state.

---

# T16 — Round State Machine Expansion

## Goal

Make the expanded gameplay flow explicit and robust.

---

## Suggested Enum

Extend:

```text
EPrototypeRoundState
```

Suggested states:

```text
Initializing

SpawningChoices

AwaitingSelection

ResolvingOutcome

ThreatActive

PostRoundDecision

RunCashedOut

RunFailed

Error
```

Exact names may differ.

The important requirement is that state transitions are explicit.

---

## Suggested Main Flow

```text
BeginPlay
    ↓
Initializing
    ↓
SpawnCandidateBoxes
    ↓
AwaitingSelection
    ↓
Player scans / compares
    ↓
Box selected
    ↓
ResolvingOutcome
```

Reward case:

```text
ResolvingOutcome
    ↓
Reward Result
    ↓
Cleanup
    ↓
PostRoundDecision
```

Threat case:

```text
ResolvingOutcome
    ↓
ThreatActive
    ↓
Threat resolved successfully
    ↓
PostRoundDecision
```

Death case:

```text
ThreatActive
    ↓
PlayerDeath
    ↓
RunFailed
```

Continue:

```text
PostRoundDecision
    ↓
SpawnCandidateBoxes
    ↓
AwaitingSelection
```

Cash Out:

```text
PostRoundDecision
    ↓
RunCashedOut
```

---

## Transition Rule

Prefer centralized transition functions rather than many unrelated:

```text
Set Round State
```

nodes spread across multiple Blueprints.

Suggested functions:

```text
StartRound()
HandleBoxSelected()
HandleOutcomeResolved()
HandleThreatResolved()
EnterPostRoundDecision()
ContinueRun()
CashOutRun()
HandlePlayerDeath()
EndRun()
```

---

## Acceptance

PASS if:

* Every gameplay phase maps to a clear state.
* Invalid inputs are rejected based on state.
* Duplicate result callbacks do not advance twice.
* Death and successful threat resolution cannot both trigger round advancement.
* Restart returns to clean initialization state.

---

# T17 — HUD v0.2

## Goal

Expose enough information for player decisions without turning the HUD into a final art pass.

---

## Required HUD Elements

Existing:

```text
Money
Threat info
Crosshair
Interact prompt
Messages
Run Over
```

Add:

```text
Player HP

Scan panel

Estimated Value

Danger Level

Signal / Unknown Info

Post-Round Decision Panel

CONTINUE

CASH OUT

Run Failed

Cashed Out Amount
```

---

## HUD Rule

HUD receives events and displays state.

Do not implement gameplay decisions directly in widgets unless input/UI routing requires it.

Widget callbacks should call controller/coordinator functions.

---

# T18 — Debug and Balance Support

## Goal

Make testing deterministic enough that future Codex sessions can validate individual systems.

---

## Recommended Debug Options

Add development-only controls where practical:

```text
Force Box Type

Force Outcome

Force Threat

Disable Threat Damage

Force Scan Result Category

Set Starting Money

Set Player HP

Spawn Single Test Box

Skip to Post-Round Decision
```

These must not replace real gameplay logic.

They are testing aids.

---

## Logging

Continue using:

```text
BFL_PrototypeLog
```

Important events should log:

```text
Round Started

Candidate Boxes Spawned

Box Scanned

Box Selected

Outcome Selected

Threat Started

Threat Resolved

Player Damaged

Player Died

Post Round Decision Entered

Continue Selected

Cash Out Selected

Run Ended
```

Do not spam Tick logs.

---

# 5. Suggested Asset Layout

Keep the current structure where possible.

Possible additions:

```text
/Game/Prototype/Core/Components/
    BPC_Scanner
    BPC_Health

/Game/Prototype/Core/Types/
    EScanRiskLevel
    FAnomalyBoxData

/Game/Prototype/Data/
    DT_AnomalyBoxes
```

or:

```text
/Game/Prototype/Data/Boxes/
    PDA_Box_Safe
    PDA_Box_Risky
    PDA_Box_Unknown
```

UI:

```text
/Game/Prototype/UI/
    WBP_PrototypeHUD
```

Prefer extending the current HUD before creating many separate widgets unless complexity requires it.

---

# 6. Dependency Order

Implement tickets in this order.

```text
T11 Box Data
    ↓
T12 Scanner
    ↓
T13 Multi-Box Round
    ↓
T14 Continue / Cash Out
    ↓
T15 HP / Failure
    ↓
T16 State Machine Hardening
    ↓
T17 HUD Pass
    ↓
T18 Debug / Balance / Validation
```

T16 may partially evolve alongside earlier tickets, but perform a dedicated cleanup pass after gameplay is functional.

---

# 7. Development Strategy for Codex

## Rule 1 — Small Changes

Do not attempt the entire v0.2 in one implementation session.

Each ticket should be implemented and verified independently.

---

## Rule 2 — Read Existing Documentation First

Before modifying assets, inspect:

```text
Docs/STATE.md

Docs/01_CONTRACTS.md

Docs/ASSET_MAP.md

Prototype_v0.1_Implementation.md

Anomaly Lab Prototype v0.1 summary
```

Existing contracts take priority over assumptions.

---

## Rule 3 — Preserve Working Systems

Do not rewrite working v0.1 systems merely for architectural preference.

Especially preserve:

```text
BPC_Interaction

BPI_Interactable

BPC_Wallet

BP_BoxSpawner

BP_AnomalyBox

BP_Spider

WBP_PrototypeHUD
```

unless modification is directly required.

---

## Rule 4 — Avoid Blueprint Mega-Graphs

When adding functionality:

Prefer:

```text
Named Functions
Components
Enums
Structs
Dispatchers
Small responsibility boundaries
```

Avoid placing the entire v0.2 loop into one Event Graph.

---

## Rule 5 — No Level Blueprint Gameplay Logic

Level Blueprint should not become the gameplay coordinator.

---

## Rule 6 — No Hidden Direct Dependencies

Examples to avoid:

```text
HUD directly modifies wallet

Scanner directly changes outcome

Spider directly spawns next round

Box directly ends the run

Loot directly controls round state
```

Use the existing coordinator/event structure.

---

# 8. Required Validation Per Ticket

For every ticket:

1. Save all changed assets.
2. Confirm Blueprint compilation succeeds.
3. Check for broken references.
4. Run PIE.
5. Test primary success path.
6. Test invalid input path.
7. Test duplicate input protection.
8. Test restart.
9. Record modified assets.
10. Record known limitations.

Do not mark a ticket complete only because assets compile.

---

# 9. v0.2 Full Acceptance Test

Before v0.2 is considered complete, test the following complete flow.

---

## Test A — Box Choice

```text
Start run
→ Three boxes appear
→ Inspect all boxes
→ Scan all boxes
→ Open one
→ Other boxes cannot resolve
```

Expected:

```text
PASS
```

---

## Test B — Scan Stability

```text
Scan same box repeatedly
```

Expected:

```text
Same cached scan information
```

---

## Test C — Reward

```text
Force HighValue
```

Expected:

```text
Money increases
Round resolves
Post-round decision appears
```

---

## Test D — Trash

```text
Force Trash
```

Expected:

```text
Correct reward
Round resolves
Decision appears
```

---

## Test E — Threat Survival

```text
Force Threat
→ Survive threat
```

Expected:

```text
Threat resolves once
Round enters decision state
```

---

## Test F — Player Death

```text
Force Threat
→ Receive lethal damage
```

Expected:

```text
Run Failed
No next round
No box interaction
No scanner interaction
Restart available
```

---

## Test G — Continue

```text
Earn money
→ Continue
```

Expected:

```text
Money preserved
Fresh box choices spawn
```

---

## Test H — Cash Out

```text
Earn money
→ Cash Out
```

Expected:

```text
Run ends successfully
Final value displayed
No new round
```

---

## Test I — Restart

Test restart from:

```text
Run Failed

Run Cashed Out
```

Expected:

```text
Money reset

HP reset

Round state reset

Old Actors removed

New boxes valid

HUD reset
```

---

# 10. Balance Target

Do not spend significant time balancing before the full loop works.

Initial balance only needs to create obvious differences between choices.

Example:

| Box     |    Value |   Threat |
| ------- | -------: | -------: |
| Safe    |      Low |      Low |
| Risky   |     High |     High |
| Unknown | Variable | Variable |

The purpose of the first balance pass is to answer:

> Does the player ever hesitate?

If not, adjust:

* Reward spread
* Threat probability
* Scan accuracy
* Failure punishment

---

# 11. v0.2 Definition of Done

Prototype v0.2 is complete when:

```text
✓ Multiple boxes spawn per round

✓ Boxes have different data-driven risk/reward profiles

✓ Player can scan boxes

✓ Scan results provide incomplete information

✓ Player selects only one box per round

✓ Outcomes still correctly produce Reward / Trash / Threat

✓ Threat can create meaningful failure

✓ Player has HP

✓ Player can die

✓ Completed rounds lead to Continue / Cash Out

✓ Continue preserves current run value

✓ Cash Out ends the run successfully

✓ Death ends the run unsuccessfully

✓ Round state prevents duplicate transitions

✓ Restart fully restores clean initial state

✓ PIE validation passes

✓ Windows Development package launches and completes a run
```

---

# 12. Expected v0.2 Gameplay Loop

Final target:

```text
START RUN

    ↓

ROUND START

    ↓

Spawn 3 Boxes

    ↓

Inspect

    ↓

Scan

    ↓

Compare Information

    ↓

Choose One Box

    ↓

OPEN

 ┌────────────┬─────────────┬─────────────┐
 │ High Value │    Trash    │   Threat    │
 └────────────┴─────────────┴─────────────┘
        ↓             ↓             ↓
      Money         Money        Survive
        │             │             │
        └───────┬─────┴─────────────┘
                ↓
       POST ROUND DECISION
                ↓

       ┌─────────────────┐
       │                 │
   CONTINUE           CASH OUT
       │                 │
       ↓                 ↓
   NEXT ROUND       RUN COMPLETE

Threat Failure
       ↓
PLAYER DEATH
       ↓
RUN FAILED
```

---

# 13. Design Principle

Every major implementation decision in v0.2 should support the following question:

> Before opening a box, does the player have enough information to make a decision, but not enough information to know the answer?

And after each successful round:

> Does the player have a meaningful reason to consider stopping instead of automatically continuing?

If a proposed feature does not materially improve one of these two decisions, it should probably not be included in v0.2.

---

# 14. v0.3 Boundary

Do not begin v0.3 until v0.2 is validated.

v0.3 is expected to focus primarily on:

```text
Multiplayer Foundation

Server-authoritative Box Opening

Replicated Outcomes

Replicated Threat State

Replicated Money / Run State

2–4 Player Session Testing
```

Do not mix these concerns into v0.2.

---

# Final Instruction to Codex

Implement v0.2 incrementally.

Do not attempt to “improve” or rewrite all existing architecture at once.

For every ticket:

```text
Read existing contracts
→ Inspect affected assets
→ Propose minimal change
→ Implement
→ Compile
→ PIE test
→ Verify regression
→ Update project documentation
```

The primary success criterion is not feature count.

The primary success criterion is:

> Transform Anomaly Lab from a random box-opening prototype into a small but meaningful risk/reward decision game.
