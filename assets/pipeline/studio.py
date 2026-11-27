"""Studio scene + helpers shared by all render scripts (run inside bpy)."""
import bpy, bmesh, numpy as np, math
from mathutils import Vector

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    s.cycles.device = 'CPU'
    s.cycles.samples = 96
    s.cycles.use_denoising = True
    s.cycles.denoiser = 'OPENIMAGEDENOISE'
    s.view_settings.view_transform = 'AgX'
    s.view_settings.look = 'AgX - Medium High Contrast'
    s.render.film_transparent = False
    return s

def mat(name, color=(0.5,0.5,0.5), metallic=0.0, rough=0.5, coat=0.0, coat_rough=0.03, alpha=1.0, transmission=0.0, ior=1.45, emission=None, estrength=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Metallic'].default_value = metallic
    b.inputs['Roughness'].default_value = rough
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Coat Roughness'].default_value = coat_rough
    b.inputs['Transmission Weight'].default_value = transmission
    b.inputs['IOR'].default_value = ior
    b.inputs['Alpha'].default_value = alpha
    if emission:
        b.inputs['Emission Color'].default_value = (*emission, 1)
        b.inputs['Emission Strength'].default_value = estrength
    return m

def car_paint(name, color, flake=0.5, metallic=0.75, rough=0.32):
    m = mat(name, color, metallic, rough, coat=1.0, coat_rough=0.02)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    vor = nt.nodes.new('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 2200
    vor.feature = 'F1'
    nt.links.new(tc.outputs['Object'], vor.inputs['Vector'])
    sep = nt.nodes.new('ShaderNodeMix'); sep.data_type = 'VECTOR'
    # flake normal: random per-cell colour remapped to a normal tilt
    nm = nt.nodes.new('ShaderNodeVectorMath'); nm.operation = 'SUBTRACT'
    nt.links.new(vor.outputs['Color'], nm.inputs[0]); nm.inputs[1].default_value = (0.5,0.5,0.5)
    sc = nt.nodes.new('ShaderNodeVectorMath'); sc.operation = 'SCALE'; sc.inputs['Scale'].default_value = 0.35 * flake
    nt.links.new(nm.outputs[0], sc.inputs[0])
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    ad = nt.nodes.new('ShaderNodeVectorMath'); ad.operation = 'ADD'
    nt.links.new(geo.outputs['Normal'], ad.inputs[0]); nt.links.new(sc.outputs[0], ad.inputs[1])
    no = nt.nodes.new('ShaderNodeVectorMath'); no.operation = 'NORMALIZE'
    nt.links.new(ad.outputs[0], no.inputs[0])
    nt.links.new(no.outputs[0], b.inputs['Normal'])   # base layer gets flakes, coat stays mirror smooth
    return m

def mesh_from_arrays(name, V, F, N=None, mats=None, mat_index=None, smooth=True):
    me = bpy.data.meshes.new(name)
    nv, nf = len(V), len(F)
    me.vertices.add(nv); me.vertices.foreach_set('co', np.ascontiguousarray(V, np.float32).ravel())
    me.loops.add(nf * 3); me.loops.foreach_set('vertex_index', np.ascontiguousarray(F, np.int32).ravel())
    me.polygons.add(nf); me.polygons.foreach_set('loop_start', np.arange(0, nf * 3, 3, dtype=np.int32))
    me.update(calc_edges=True)
    if mats:
        for m in mats: me.materials.append(m)
        if mat_index is not None:
            me.polygons.foreach_set('material_index', np.asarray(mat_index, np.int32))
        mats = None
    me.validate(verbose=False)
    if smooth:
        me.shade_smooth()
    if N is not None:
        # per-vertex custom normals
        me.normals_split_custom_set_from_vertices(np.asarray(N, np.float32).tolist())
    if mats:
        for m in mats: me.materials.append(m)
        if mat_index is not None:
            me.polygons.foreach_set('material_index', np.asarray(mat_index, np.int32))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    try:
        ob.shadow_terminator_geometry_offset = 0.6; ob.shadow_terminator_normal_offset = 0.2
    except Exception: pass
    return ob

def area(name, loc, rot, size, energy, color=(1,1,1), shape='RECTANGLE', size_y=None, spread=180):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.color = color
    l.shape = shape; l.size = size; l.size_y = size_y or size
    l.spread = math.radians(spread)
    o = bpy.data.objects.new(name, l); o.location = loc; o.rotation_euler = rot
    bpy.context.scene.collection.objects.link(o)
    return o

def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

def studio(variant='dark'):
    s = bpy.context.scene
    # world: dim neutral
    w = bpy.data.worlds.new('W'); s.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.012,0.012,0.014,1)
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
    # cyclorama: floor + curved back wall in one sheet
    bm = bmesh.new()
    prof = []
    for i in range(40):
        t = i / 39
        a = t * math.pi / 2
        R = 3.0
        prof.append((-6.0 + 0, 0)) if False else None
    # build as x-extrusion of profile in (y,z): floor from y=+8 to y=-6, then curve up to wall at y=-9
    pts = [(y, 0.0) for y in np.linspace(14, -6, 21)]
    R = 3.0
    for i in range(1, 25):
        a = i / 24 * math.pi / 2
        pts.append((-6 - R * math.sin(a), R - R * math.cos(a)))
    pts += [(-9.0, z) for z in np.linspace(3.5, 9, 6)]
    verts = []
    xs = np.linspace(-14, 14, 29)
    for x in xs:
        for (y, z) in pts:
            verts.append(bm.verts.new((x, y, z)))
    n = len(pts)
    for i in range(len(xs) - 1):
        for j in range(n - 1):
            bm.faces.new([verts[i*n+j], verts[(i+1)*n+j], verts[(i+1)*n+j+1], verts[i*n+j+1]])
    me = bpy.data.meshes.new('cyc'); bm.to_mesh(me); me.shade_smooth()
    cyc = bpy.data.objects.new('cyclorama', me); s.collection.objects.link(cyc)
    floor = mat('studio_floor', (0.09,0.09,0.095) if variant=='dark' else (0.6,0.6,0.62), rough=0.30)
    me.materials.append(floor)
    # lights: big overhead softbox, two side strips, a backdrop wash
    area('key', (0.0, 0.3, 4.2), (0, 0, 0), 5.5, 520, size_y=2.6)
    area('stripL', (1.0, 3.8, 1.5), (math.radians(80), 0, math.radians(180)), 5.0, 260, size_y=0.5)
    area('stripR', (0.5, -3.8, 1.5), (math.radians(-80), 0, 0), 5.0, 160, size_y=0.5)
    area('front', (5.5, 1.5, 1.4), (0, math.radians(80), math.radians(15)), 2.0, 90, size_y=1.2)
    area('wash', (0.0, -5.5, 4.5), (math.radians(-40), 0, 0), 8.0, 380, size_y=2)
    return cyc

def camera(loc, target, lens=55, name='cam'):
    c = bpy.data.cameras.new(name); c.lens = lens
    c.dof.use_dof = False
    o = bpy.data.objects.new(name, c); o.location = loc
    bpy.context.scene.collection.objects.link(o)
    look_at(o, target)
    bpy.context.scene.camera = o
    return o

def render(path, w=1600, h=900, samples=None):
    s = bpy.context.scene
    s.render.resolution_x = w; s.render.resolution_y = h; s.render.resolution_percentage = 100
    if samples: s.cycles.samples = samples
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)
