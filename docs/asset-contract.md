# Car asset contract (GLB)

Every car and part GLB must follow these rules so both games (APEX: Racing on Three.js, APEX: Tuning on PlayCanvas) can load, paint and modify it the same way.

## Space
- Units: metres. Origin on the ground, centred between the axles.
- glTF axes: **+X forward, +Y up, +Z right** (the racing game's car space). In Blender this is X forward, Z up, Y left; the exporter converts.

## Nodes
| Node | Meaning |
|---|---|
| `aurion_vanta_gt3` (root) | the car, named by model id |
| `body` | painted shell incl. lamps, intakes, grooves |
| `interior` | cockpit (LOD0 and LOD1 only) |
| `wheel_fl`, `wheel_fr`, `wheel_rl`, `wheel_rr` | rim + tyre + disc + bell. Origin at the hub so games can spin (about Z) and steer (about Y) |
| `caliper_fl` … `caliper_rr` | brake calipers; steer with the wheel, never spin |
| `socket_*` | empties marking where swappable parts attach: `socket_wing`, `socket_splitter`, `socket_exhaust`, `socket_mirrors`, `socket_wheel_*` |
| `part_<partId>` | the default part fitted to a socket, a child of that socket. Games hide it and load a different part GLB to swap |

## Materials (names are slot names)
`paint_body`, `paint_accent`, `trim_black`, `carbon`, `grille`, `lamp_housing`, `interior_trim`, `interior_seat`, `interior_alcantara`, `cage`,
`glass`, `lens_clear`, `lens_red`, `emissive_drl`, `emissive_tail`, `emissive_indicator`, `rim`, `tyre`, `disc`, `disc_hat`, `caliper`, `mirror_glass`, `titanium`, `strap`.

The games replace `paint_*`, `rim` and `caliper` with the car file's colours and finishes; the other slots keep the GLB values.

## Budgets (checked by the pipeline)
| LOD | Use | Triangles |
|---|---|---|
| lod0 | showroom, garage, photo mode | ≤ 450k incl. interior |
| lod1 | racing (near) | ≤ 70k, simplified interior |
| lod2 | racing (far), menus | ≤ 14k, no interior |

Textures (when used): KTX2/Basis, ≤ 2K for hero slots, ≤ 1K otherwise. Meshes are meshopt-compressed for delivery.
