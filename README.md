# Apex Motorsport

Shared car data and car assets for **APEX: Racing** (the existing browser racing game, Three.js) and **APEX: Tuning** (the new tuning game, PlayCanvas).

## What's here (Stage 0 + first car)
| Path | What |
|---|---|
| `packages/car-data` | Engine-free car data: JSON schema, catalogue (models + parts), `computeSpec`, `.ctcar.json` read/write with v1→v2 migration. `npm test` runs its tests. |
| `assets/pipeline` | Car pipeline: a signed-distance-field modelling kernel (`sdf.py`), original wheel/brake parts (`wheel.py`, `wheels_bpy.py`), Cycles studio (`studio.py`, `materials.py`), and the importer that turns a third-party FBX into a contract GLB (`import_p1.py`, `export_p1.py`, `render_p1.py`). |
| `assets/LICENSES.json` | Licence register. Every external file must be listed, with its caveats. |
| `docs/asset-contract.md` | The rules every car GLB follows (axes, node names, material slots, sockets, LOD budgets). |

## Current car: McLaren P1 GTR (2015)
Imported from an FBX the project owner supplied. Normalised to the asset contract (metres, +X forward, origin on the ground between the axles), materials mapped to paint/trim slots so players can repaint body, accent and calipers, wheels split into `wheel_*` nodes with hub pivots, our own six-piston calipers fitted, and the wing, splitter, exhaust and mirrors exposed as swappable parts. LODs: 293k / 64k / 13k triangles.

**Licence caveat:** the model has no licence file and depicts a real branded car. See `assets/LICENSES.json`. The FBX, textures and GLBs are not committed to this public repository.

The first car, the original Aurion Vanta GT3, was dropped on 2026-11-27; it is in git history.

### Build it
Requires Python 3.13 with `pip install bpy scikit-image scipy`.
```
cd assets/pipeline
python -c "import wheel, sdf, numpy as np; V,F=sdf.mesh_sdf(wheel.caliper,((-0.05,0.25),(-0.05,0.25),(-0.10,0.0)),vox=0.0015); np.savez('cal.npz',V=V,F=F)"
FBX="/path/McLaren P1 GTR 2015.fbx" TEX=/path/textures CAL_NPZ=cal.npz python import_p1.py   # -> ../build/p1/p1_full.blend
for L in lod0 lod1 lod2; do LODS=$L python export_p1.py; done                               # one LOD per process
BLEND=../build/p1/p1_full.blend OUT=../build/p1/renders python render_p1.py                 # studio renders
```
