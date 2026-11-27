# Apex Motorsport

Shared car data and car assets for **APEX: Racing** (the existing browser racing game, Three.js) and **APEX: Tuning** (the new tuning game, PlayCanvas).

## What's here (Stage 0 + first car)
| Path | What |
|---|---|
| `packages/car-data` | Engine-free car data: JSON schema, catalogue (models + parts), `computeSpec`, `.ctcar.json` read/write with v1→v2 migration. `npm test` runs its tests. |
| `assets/pipeline` | The modelling pipeline for original cars: a signed-distance-field modelling kernel (`sdf.py`), the Aurion Vanta GT3 body, wheels, aero parts, lights and interior, Cycles studio renders and the GLB exporter. |
| `assets/LICENSES.json` | Licence register. Every external file must be listed; the Vanta uses none. |
| `docs/asset-contract.md` | The rules every car GLB follows (axes, node names, material slots, sockets, LOD budgets). |
| `docs/renders/` | Studio renders of the current car. |

## First car: Aurion Vanta GT3 (fictional)
An original front-engine GT3 race car: wide arches with slatted vents, louvred bonnet, vaned grille, carbon splitter with canards and rods, side skirts, finned diffuser, swan-neck wing, 12-spoke centre-lock wheels with drilled discs and six-piston calipers, LED lamps, and a race interior (roll cage, bucket seat with harness, race wheel, carbon dash, switch panel).

### Build it
Requires Python 3.13 with `pip install bpy scikit-image scipy matplotlib`. Intermediate caches go to `assets/build/cache` (or `$APEX_WORK`).
```
cd assets/pipeline
python -c "import body3, sdf, numpy as np; V,F=sdf.mesh_sdf(body3.outer,((-2.45,2.5),(-1.1,1.1),(0.08,1.26)),vox=0.004); np.savez('body.npz',V=V,F=F)"
NPZ=body.npz PARTS=1 INTERIOR=1 CARBON_TEX=1 LIVERY=1 python render_car.py      # studio renders (Cycles)
NPZ=body.npz OUT=../build/glb python export_glb.py                              # lod0/lod1/lod2 GLBs
```
