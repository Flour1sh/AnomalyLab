# Low Poly Lab Room — Generation Guide

## Requirements

- Blender 5.1.2 (the prototype was generated and validated with this version)
- No add-ons or external Python packages are required

The script uses only Blender's bundled `bpy` API.

## Generate the complete scene

Open PowerShell in this directory and run:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' `
  --background --factory-startup --python .\generate_lab_room.py
```

The script clears the starting scene, creates all assets and collections, validates
the required names and transforms, renders a preview, saves the Blender project,
and exports the FBX. It can safely be run again to rebuild the deliverables.

Generated files:

- `low_poly_lab_room.blend` — complete editable Blender scene
- `low_poly_lab_room.fbx` — mesh-only FBX for Unreal Engine 5
- `low_poly_lab_preview.png` — Blender preview render

## Change the main parameters

Edit the constants near the top of `generate_lab_room.py`:

```python
ROOM_WIDTH = 16.0
ROOM_LENGTH = 20.0
ROOM_HEIGHT = 4.0
BEVEL_WIDTH = 0.02
PIPE_RADIUS = 0.12
PIPE_SEGMENTS = 8
```

The `COLORS` dictionary in the same section controls the shared material palette.
Keep `PIPE_SEGMENTS` at 6, 8, or 12 to preserve the low-poly silhouette.

The current version expands the original 8 × 10 m footprint to 16 × 20 m while
keeping all prop dimensions unchanged. `relayout_for_expanded_room()` translates
logical groups together, so computers stay on desks and crates stay on shelves.

## Blender collection layout

```text
LowPolyLab
├── Architecture
├── Props
├── Pipes
├── Lights
└── Gameplay
```

Mesh assets use `SM_` names. Preview-only Blender light objects use `LGT_`, and
the preview camera uses `CAM_`. Preview lights and the camera are deliberately not
included in the FBX.

## UE5 import

The FBX is exported with `Forward = -Y`, `Up = Z`, unit scaling enabled, applied
mesh rotation/scale, and individual named mesh objects.

Recommended UE5 import settings:

- Import Type: Static Mesh
- Combine Meshes: Off (keeps the `SM_` objects separate)
- Import Uniform Scale: 1.0
- Convert Scene / Convert Scene Unit: On
- Generate Missing Collision: On for prototype use, or replace with authored collision later
- Import Materials: optional

FBX reliably carries meshes, object names, material slots, and basic material
colors. Blender node-based emission and preview lighting do not reproduce exactly
inside UE5. For the intended result, create a small UE master-material palette and
map the imported material slots by their existing `M_` names.

The current generation environment does not contain Unreal Editor, so the FBX is
validated through successful export and Blender-side structural checks rather than
an automated UE5 import.
