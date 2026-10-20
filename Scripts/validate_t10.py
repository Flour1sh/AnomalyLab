"""Read-only saved Blueprint reload/compile and regression checks; no gameplay."""
import sys
import json
from pathlib import Path
import unreal
sys.path.insert(0, str(Path(__file__).parent))
import build_t10 as b
t, h, B = b.t, b.h, b.B


def main():
    checks = []

    def check(condition, text):
        checks.append({'check': text, 'pass': bool(condition)})
        assert condition, text

    bp = h.load(t.SPIDER)
    t.compile_bp(bp)
    check(h.ASSETS.get_metadata_tag(bp, 'T10BuildVersion') == '1', 'Saved build marker; strict compile')
    baseline = json.loads((b.OUT / 'baseline.json').read_text(encoding='utf-8'))
    current = b.snapshot(bp)
    check(all(current.get(key) == value for key, value in baseline['gameplay'].items()),
          'Original gameplay graph pin defaults and connections unchanged')
    after = b.hashes()
    check(all(after[key] == value for key, value in baseline['hashes'].items()
              if key != 'Anomalies/Creatures/BP_Spider'), 'Other 18 core source packages unchanged')
    cdo = unreal.get_default_object(bp.generated_class())
    for name, value in {**t.DEFAULTS, **b.DEFAULTS}.items():
        check(abs(float(cdo.get_editor_property(name)) - float(value)) < .001, 'Default ' + name)
    move = cdo.get_editor_property('character_movement')
    check(not move.get_editor_property('orient_rotation_to_movement'), 'No competing movement orientation')
    check(not move.get_editor_property('use_controller_desired_rotation'), 'No competing controller desired rotation')
    check(not cdo.get_editor_property('use_controller_rotation_yaw'), 'No competing controller yaw')
    check(move.get_editor_property('max_walk_speed') == 350, 'Movement speed remains 350')
    check(not move.get_editor_property('enable_physics_interaction'), 'No physics pushing')
    check(cdo.get_editor_property('auto_possess_ai') == unreal.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED, 'AI possession retained')
    tick = cdo.get_editor_property('primary_actor_tick')
    check(tick.get_editor_property('start_with_tick_enabled') and tick.get_editor_property('tick_interval') == 0,
          'Tick configured to start enabled with per-frame interval')
    capsule = cdo.get_editor_property('capsule_component')
    check(capsule.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN) == unreal.CollisionResponseType.ECR_OVERLAP, 'Pawn overlap unchanged')
    visual = next(c for c in t.components(bp) if 'AlienVisual' in c.get_name())
    check(visual.get_editor_property('static_mesh').get_path_name().split('.')[0] == t.MESH, 'Original static mesh retained')
    check(visual.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION, 'Cosmetic mesh has no collision')
    height = visual.get_editor_property('static_mesh').get_bounds().box_extent.z * 2 * visual.get_editor_property('relative_scale3d').z
    check(abs(height - 90) < .01, '90 cm visual height retained')
    loc = cdo.get_editor_property('T10BaseLocation')
    check(all(abs(a-v) < .001 for a, v in zip((loc.x, loc.y, loc.z), baseline['base_location'])), 'Neutral visual location preserved')
    for name in b.FUNCTIONS:
        g = next(g for g in B.list_graphs(bp) if g.get_name() == name)
        types = [str(B._get_node_info(n).type_id) for n in B.find_nodes(g)]
        check(any(s.endswith('|IsValid') for s in types), name + ' reference validity guard')
        if name == 'T10FacePlayer':
            check(any(s.endswith('|RInterpTo') for s in types), 'Smooth target rotation')
            rotators = [n for n in B.find_nodes(g) if str(B._get_node_info(n).type_id).endswith('|MakeRotator')]
            check(len(rotators) == 1, 'One horizontal facing target')
            for pin in ('Roll', 'Pitch'):
                p = h.find_pin(rotators[0], 'in', [pin])
                check(not p.list_connected_pins() and float(p.get_pin_value() or 0) == 0, 'Actor facing target ' + pin + '=0')
        else:
            check(any(s.endswith('|GetVelocity') for s in types), 'Animation driven by actual velocity')
            check(any(s.endswith('|FInterpTo') for s in types), 'Movement amplitude blends to rest')
            applies = [n for n in B.find_nodes(g) if str(B._get_node_info(n).type_id).split('|')[-1]
                       in ('K2_SetRelativeLocationAndRotation', 'SetRelativeLocationAndRotation')]
            check(len(applies) == 1, 'One visual transform setter: ' + str(types[-3:]))
            targets = h.find_pin(applies[0], 'in', ['self']).list_connected_pins()
            check(len(targets) == 1 and str(targets[0].get_pin_name()) == 'AlienVisual', 'Motion affects visual component only')
    event = unreal.BlueprintEditorLibrary.find_event_graph(bp)
    ticks = [n for n in B.find_nodes(event) if str(B._get_node_info(n).type_id).endswith('|ReceiveTick')]
    check(len(ticks) == 1 and len(h.find_pin(ticks[0], 'out', ['then']).list_connected_pins()) == 1, 'One connected Tick path')
    # Cross-Blueprint reference still points at the modified class, not a duplicate.
    box = h.load(h.BOX_PATH)
    t.compile_bp(box)
    box_default = unreal.get_default_object(box.generated_class())
    check(box_default.get_editor_property('ThreatClass') == bp.generated_class(), 'Box still spawns this Spider')
    check(not box_default.get_editor_property('bForceOutcome'), 'Normal random outcomes retained')
    report = {'status': 'PASS', 'checks': checks, 'PIE': 'NOT RUN', 'MCP': 'NOT USED',
              'modified_assets': [t.SPIDER], 'runtime_acceptance': 'PENDING USER',
              'backup': baseline['backup'], 'source_hashes_after': after}
    (b.OUT / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log('[T10] STRUCTURAL PASS - independent reload; runtime acceptance NOT RUN')


if __name__ == '__main__':
    main()
