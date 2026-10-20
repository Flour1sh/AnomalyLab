# v0.5 staged verification matrix

Each task: PLAN → IMPLEMENT → COMPILE → AUTOMATED/REGRESSION → VISIBLE → REPORT → SHA CHECKPOINT. Failure blocks the next task. Final executable packaging only T42 after T34–T41 engineering gates.

| Task | Mandatory tests | Current state |
|---|---|---|
| T33 | readonly RC/archive/source SHA, isolated unchanged-source compile, fresh asset reload, old resources/equipment/save/regions/observer/balance/core/menu/Legacy; D3D12 baseline frames | PASS: copied RC11 groups, rebuilt source7, reload16; evidence Saved/V05/T33 |
| T34 | real two .umap fresh reload, mode/input/Pawn/nav/collision, safety, idempotent builder, SHA, 720/1080 | PASS: reload31; runtime138 in6 processes/24 frames; current-source regression11; proxy visual review; summary Saved/V05/T34/verification_summary.json. T35/T36 transactions and T42 package pending |
| T35 | transition/RunId/value DTO, repeat E, launch claim once, physical extraction, same-frame death, failures, restart/crash/old-save import, 3 roundtrips; legacy regression | PASS: T35_REPORT.md / per-stage automated gates and relevant regression; final human testing pending |
| T36 | Hub-only transactions, upgrade carry-in, decoy once, HUD/focus/mouse, blocked Hub Q/F/1/2, Lab purchase rejection; economics regression | PASS: T36_REPORT.md / per-stage automated gates and relevant regression; final human testing pending |
| T37 | nine legal points, seed reproducibility independent reward digest, fallback/conflicts, 20 automated completion paths; region RNG regression | PASS: T37_REPORT.md / per-stage automated gates and relevant regression; final human testing pending |
| T38 | B toggle range/LOS/debounce, numeric scan tradeoff, lighting not black, reset/cancel; scanning/observer regression | PASS: T38_REPORT.md / per-stage automated gates and relevant regression; final human testing pending |
| T39 | C legal/illegal targets and subtypes, one use, no double reward/contain count, death/travel cancel; threat regression | PASS: T39_REPORT.md / per-stage automated gates and relevant regression; final human testing pending |
| T40 | two real non-drop event effects, seeded IDs/time, quiet run, bounded intensity/no fatal simultaneous stack, repeated trigger/cancel | PASS: T40_REPORT.md / per-stage automated gates and relevant regression; final human testing pending |
| T41 | complete structured logs, bounded files, real FPS/frames/loading/route observations; human record separately pending | PASS: T41_REPORT.md / per-stage automated gates and relevant regression; final human testing pending |
| T42 | complete Win64 Development package, 720/1080 D3D12 visual+input 3 roundtrips, all old/new matrix, new-directory restore, immutable archive SHA | PASS engineering: full package matrix, dual-resolution frames, source/package restore, SHA archive; final human validation pending |

Actual commands/reports/exit codes are saved by run_v05_baseline.py. Existing assertion bodies unchanged. Offscreen rendered tests prove frames and automated input routing, not physical human keyboard or subjective audio. NullRHI-only groups never count as visual acceptance.
