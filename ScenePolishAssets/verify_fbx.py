"""Re-import the actual exported FBX files into a fresh background Blender process."""
from pathlib import Path
import bpy,json,math
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
manifest=json.loads((ROOT/'mesh_manifest.json').read_text(encoding='utf-8'))
checks=[]
for name,info in manifest['meshes'].items():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=str(ROOT/'fbx'/(name+'.fbx')))
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    assert len(objects)==1,(name,len(objects))
    o=objects[0];points=[o.matrix_world@Vector(v) for v in o.bound_box]
    lo=[min(p[a] for p in points) for a in range(3)];hi=[max(p[a] for p in points) for a in range(3)]
    dimensions=[hi[a]-lo[a] for a in range(3)]
    assert max(abs(dimensions[a]-info['dimensions_m'][a]) for a in range(3))<.002,(name,dimensions)
    assert max(abs(lo[a]-info['bounds_min_m'][a]) for a in range(3))<.002,(name,lo)
    assert all(not p.use_smooth for p in o.data.polygons),name
    assert set(m.name.split('.')[0] for m in o.data.materials)==set(info['materials']),name
    checks.append(dict(mesh=name,dimensions_m=dimensions,triangles=sum(len(p.vertices)-2 for p in o.data.polygons),passed=True))
(ROOT.parent/'Saved/ScenePolish/fbx_reload.json').write_text(json.dumps(dict(status='PASS',checks=checks),indent=2),encoding='utf-8')
print('EXPORTED FBX RELOAD PASS',len(checks))
