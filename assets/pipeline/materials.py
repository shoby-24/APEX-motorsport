"""Procedural PBR upgrades: 2x2 twill carbon, satin trims (no external textures needed)."""
import bpy

def carbon(m, scale=110.0):
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    # tows along two axes: sine bands give the fibre direction; checker decides which tow is on top (twill-ish)
    w1 = nt.nodes.new('ShaderNodeTexWave'); w1.wave_type = 'BANDS'; w1.bands_direction = 'X'; w1.inputs['Scale'].default_value = 1.0
    w2 = nt.nodes.new('ShaderNodeTexWave'); w2.wave_type = 'BANDS'; w2.bands_direction = 'Y'; w2.inputs['Scale'].default_value = 1.0
    for w in (w1, w2):
        w.inputs['Distortion'].default_value = 0.0; w.inputs['Detail'].default_value = 0.0
        nt.links.new(mp.outputs['Vector'], w.inputs['Vector'])
    ck = nt.nodes.new('ShaderNodeTexChecker'); ck.inputs['Scale'].default_value = 0.5
    nt.links.new(mp.outputs['Vector'], ck.inputs['Vector'])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'FLOAT'
    nt.links.new(ck.outputs['Fac'], mix.inputs['Factor']); nt.links.new(w1.outputs['Fac'], mix.inputs['A']); nt.links.new(w2.outputs['Fac'], mix.inputs['B'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.006, 0.006, 0.007, 1); ramp.color_ramp.elements[1].color = (0.05, 0.05, 0.055, 1)
    nt.links.new(mix.outputs['Result'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.15; bump.inputs['Distance'].default_value = 0.0004
    nt.links.new(mix.outputs['Result'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.32; b.inputs['Metallic'].default_value = 0.0
    b.inputs['Coat Weight'].default_value = 1.0; b.inputs['Coat Roughness'].default_value = 0.025
    b.inputs['Anisotropic'].default_value = 0.4

def upgrade(M):
    import os
    carbon(M['carbon'])
    if os.environ.get('LIVERY'): livery_stripes(M['paint_body'])
    gl = bpy.data.materials.get('glass')

def livery_stripes(m, color=(0.02, 0.02, 0.022), inner=0.05, outer=0.19, pin=(0.6, 0.02, 0.02)):
    """Twin racing stripes over bonnet/roof/boot from object coordinates (|y| band, top surfaces only)."""
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    src = b.inputs['Base Color'].default_value[:]
    tc = nt.nodes.new('ShaderNodeTexCoord'); sx = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sx.inputs[0])
    ab = nt.nodes.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; nt.links.new(sx.outputs['Y'], ab.inputs[0])
    def band(lo, hi):
        g1 = nt.nodes.new('ShaderNodeMath'); g1.operation = 'GREATER_THAN'; g1.inputs[1].default_value = lo; nt.links.new(ab.outputs[0], g1.inputs[0])
        l1 = nt.nodes.new('ShaderNodeMath'); l1.operation = 'LESS_THAN'; l1.inputs[1].default_value = hi; nt.links.new(ab.outputs[0], l1.inputs[0])
        mu = nt.nodes.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'; nt.links.new(g1.outputs[0], mu.inputs[0]); nt.links.new(l1.outputs[0], mu.inputs[1])
        return mu
    st = band(inner, outer); pn = band(outer + 0.012, outer + 0.020)
    zt = nt.nodes.new('ShaderNodeMath'); zt.operation = 'GREATER_THAN'; zt.inputs[1].default_value = 0.62; nt.links.new(sx.outputs['Z'], zt.inputs[0])
    m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; nt.links.new(st.outputs[0], m1.inputs[0]); nt.links.new(zt.outputs[0], m1.inputs[1])
    m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'; nt.links.new(pn.outputs[0], m2.inputs[0]); nt.links.new(zt.outputs[0], m2.inputs[1])
    mixA = nt.nodes.new('ShaderNodeMix'); mixA.data_type = 'RGBA'
    mixA.inputs['A'].default_value = src; mixA.inputs['B'].default_value = (*color, 1)
    nt.links.new(m1.outputs[0], mixA.inputs['Factor'])
    mixB = nt.nodes.new('ShaderNodeMix'); mixB.data_type = 'RGBA'
    nt.links.new(mixA.outputs['Result'], mixB.inputs['A']); mixB.inputs['B'].default_value = (*pin, 1)
    nt.links.new(m2.outputs[0], mixB.inputs['Factor'])
    nt.links.new(mixB.outputs['Result'], b.inputs['Base Color'])
    # stripes are less metallic (satin vinyl)
    me = nt.nodes.new('ShaderNodeMath'); me.operation = 'MULTIPLY_ADD'
    nt.links.new(m1.outputs[0], me.inputs[0]); me.inputs[1].default_value = -0.6; me.inputs[2].default_value = b.inputs['Metallic'].default_value
    nt.links.new(me.outputs[0], b.inputs['Metallic'])
