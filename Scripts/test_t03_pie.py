"""Trigger one BP_AnomalyBox interaction in an already-running PIE world.

Set ``builtins.T03_TEST_MODE`` to ``random``, ``highvalue``, ``trash``,
``threat``, or ``suite`` before executing this file from Unreal's Python console.
This harness does not start or stop PIE; each run requires a fresh PIE world.
"""

import builtins
import unreal


PREFIX = "[T03PIE]"
BOX_PATH = "/Game/Anomalies/Containers/BP_AnomalyBox"
INTERNAL_OUTCOMES = {
    "highvalue": "HIGH_VALUE",
    "trash": "TRASH",
    "threat": "THREAT",
}


def fail(message):
    raise RuntimeError(f"{PREFIX} {message}")


mode = str(getattr(builtins, "T03_TEST_MODE", "random")).lower()
if mode not in ("random", "suite", *INTERNAL_OUTCOMES):
    fail(f"Unknown mode: {mode}")

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = editor.get_game_world()
if world is None:
    fail("No active PIE world")

blueprint = unreal.load_asset(BOX_PATH)
if blueprint is None:
    fail("BP_AnomalyBox is missing")

boxes = unreal.GameplayStatics.get_all_actors_of_class(world, blueprint.generated_class())
if len(boxes) != 1:
    fail(f"Expected one PIE anomaly box, found {len(boxes)}")

box = boxes[0]
interactor = unreal.GameplayStatics.get_player_pawn(world, 0)
if interactor is None:
    fail("PIE player pawn is missing")

def trigger(test_mode):
    box.set_editor_property("bOpened", False)
    box.set_editor_property("bResolved", False)
    box.set_editor_property("bForceOutcome", test_mode != "random")
    if test_mode != "random":
        enum_type = type(box.get_editor_property("ForcedOutcome"))
        box.set_editor_property("ForcedOutcome", getattr(enum_type, INTERNAL_OUTCOMES[test_mode]))
    unreal.log(f"{PREFIX} Trigger mode={test_mode} actor={box.get_name()}")
    # The immediate duplicate must be rejected by bOpened, leaving one delayed
    # resolution and one dispatcher call for this case.
    box.call_method("Interact", args=(interactor,))
    box.call_method("Interact", args=(interactor,))


if mode != "suite":
    trigger(mode)
else:
    cases = ["highvalue", "trash", "threat"] + ["random"] * 18
    state = {"index": 0, "elapsed": 0.0, "waiting": False}

    old_handle = getattr(builtins, "T03_TEST_TICK_HANDLE", None)
    if old_handle is not None:
        try:
            unreal.unregister_slate_post_tick_callback(old_handle)
        except Exception:
            pass

    def tick(delta_seconds):
        try:
            state["elapsed"] += float(delta_seconds)
            if not state["waiting"]:
                trigger(cases[state["index"]])
                state["waiting"] = True
                state["elapsed"] = 0.0
                return
            if state["elapsed"] < 1.35:
                return

            case_number = state["index"] + 1
            resolved = bool(box.get_editor_property("bResolved"))
            roll = int(box.get_editor_property("OutcomeRoll"))
            unreal.log(
                f"{PREFIX} Case={case_number}/{len(cases)} "
                f"mode={cases[state['index']]} resolved={resolved} roll={roll}"
            )
            state["index"] += 1
            if state["index"] < len(cases):
                state["waiting"] = False
                state["elapsed"] = 0.0
                return
            unreal.log(f"{PREFIX} SUITE COMPLETE cases={len(cases)}")
        except Exception as error:
            unreal.log_error(f"{PREFIX} SUITE ABORT: {error!r}")
            state["index"] = len(cases)
        handle = getattr(builtins, "T03_TEST_TICK_HANDLE", None)
        if handle is not None:
            unreal.unregister_slate_post_tick_callback(handle)
        builtins.T03_TEST_TICK_HANDLE = None

    builtins.T03_TEST_TICK_HANDLE = unreal.register_slate_post_tick_callback(tick)
    unreal.log(f"{PREFIX} SUITE START cases={len(cases)}")
