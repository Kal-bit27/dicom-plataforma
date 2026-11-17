"""Taller de render: utilerías para modelar piezas y fotografiarlas como producto.

Unidades: 1 unidad de Blender = 100 mm (MM = 0.01).
"""
import bpy, bmesh, math, os, sys
from math import pi, sin, cos, tan, radians, sqrt, atan2, acos, asin
from mathutils import Vector, Matrix, Euler

MM = 0.01


# ---------------------------------------------------------------- escena
def reset(res=1400, samples=192):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    c = sc.cycles
    c.device = 'CPU'
    c.samples = samples
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.015
    c.use_denoising = True
    try:
        c.denoiser = 'OPENIMAGEDENOISE'
    except Exception as e:
        print('sin OIDN', e)
    c.max_bounces = 10
    c.glossy_bounces = 8
    c.diffuse_bounces = 3
    c.transmission_bounces = 4
    c.caustics_reflective = False
    c.caustics_refractive = False
    sc.render.film_transparent = True
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.color_depth = '8'
    for vt in ('Standard',):
        try:
            sc.view_settings.view_transform = vt
            break
        except Exception as e:
            print('view transform', vt, 'no disponible', e)
    try:
        sc.view_settings.look = 'None'
    except Exception:
        pass
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = 4
    return sc


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


# ---------------------------------------------------------------- mallas
def mesh_obj(name, verts, faces, smooth=True, merge=1e-7):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    bm = bmesh.new()
    bm.from_mesh(me)
    if merge:
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    me.update()
    ob = bpy.data.objects.new(name, me)
    return link(ob)


def instance(src, name=None):
    ob = bpy.data.objects.new(name or src.name + '.i', src.data)
    for m in src.modifiers:
        pass
    return link(ob)


def fillet_poly(pts, r=0.0, n=5, radii=None):
    """Redondea las esquinas de un polígono cerrado 2D."""
    out = []
    N = len(pts)
    for i in range(N):
        p0 = Vector(pts[i - 1]); p1 = Vector(pts[i]); p2 = Vector(pts[(i + 1) % N])
        ri = radii[i] if radii is not None else r
        if ri <= 0:
            out.append((p1.x, p1.y)); continue
        v1 = p0 - p1; v2 = p2 - p1
        l1 = v1.length; l2 = v2.length
        if l1 < 1e-9 or l2 < 1e-9:
            out.append((p1.x, p1.y)); continue
        v1.normalize(); v2.normalize()
        d = max(-1.0, min(1.0, v1.dot(v2)))
        ang = acos(d)
        if ang < 1e-3 or abs(ang - pi) < 1e-3:
            out.append((p1.x, p1.y)); continue
        t = ri / tan(ang / 2)
        t = min(t, l1 * 0.45, l2 * 0.45)
        rr = t * tan(ang / 2)
        a = p1 + v1 * t; b = p1 + v2 * t
        bis = (v1 + v2).normalized()
        c = p1 + bis * (rr / sin(ang / 2))
        a0 = atan2(a.y - c.y, a.x - c.x); a1 = atan2(b.y - c.y, b.x - c.x)
        da = a1 - a0
        while da > pi: da -= 2 * pi
        while da < -pi: da += 2 * pi
        for k in range(n + 1):
            aa = a0 + da * k / n
            out.append((c.x + rr * cos(aa), c.y + rr * sin(aa)))
    return out


def lathe(name, profile, segs=160, smooth=True):
    """Revoluciona un perfil cerrado [(r, z), ...] alrededor de Z."""
    verts = []; faces = []
    n = len(profile)
    for i in range(segs):
        a = 2 * pi * i / segs
        ca, sa = cos(a), sin(a)
        for (r, z) in profile:
            verts.append((r * ca, r * sa, z))
    for i in range(segs):
        i2 = (i + 1) % segs
        for j in range(n):
            j2 = (j + 1) % n
            faces.append((i * n + j, i2 * n + j, i2 * n + j2, i * n + j2))
    return mesh_obj(name, verts, faces, smooth=smooth, merge=0)


def prism(name, outline, z0, z1, smooth=True, hole=None):
    """Prisma recto a partir de un contorno 2D. hole: contorno interior con el mismo número de puntos."""
    n = len(outline)
    verts = [(x, y, z0) for (x, y) in outline] + [(x, y, z1) for (x, y) in outline]
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    if hole is None:
        faces.append(tuple(range(n)))
        faces.append(tuple(range(n, 2 * n)))
    else:
        assert len(hole) == n
        b = len(verts)
        verts += [(x, y, z0) for (x, y) in hole] + [(x, y, z1) for (x, y) in hole]
        for i in range(n):
            j = (i + 1) % n
            faces.append((i, j, b + j, b + i))                      # tapa inferior
            faces.append((n + i, n + j, b + n + j, b + n + i))      # tapa superior
            faces.append((b + i, b + j, b + n + j, b + n + i))      # pared interior
    return mesh_obj(name, verts, faces, smooth=smooth, merge=0)


def loft(name, rings, closed_u=True, cap=False, smooth=True):
    """Une anillos (listas de puntos 3D con el mismo número de puntos) consecutivos."""
    m = len(rings[0])
    verts = [tuple(p) for ring in rings for p in ring]
    faces = []
    R = len(rings)
    last = R if closed_u else R - 1
    for i in range(last):
        i2 = (i + 1) % R
        for j in range(m):
            j2 = (j + 1) % m
            faces.append((i * m + j, i2 * m + j, i2 * m + j2, i * m + j2))
    if cap and not closed_u:
        faces.append(tuple(range(m)))
        faces.append(tuple(range((R - 1) * m, R * m)))
    return mesh_obj(name, verts, faces, smooth=smooth, merge=0)


def cylinder(name, r, z0, z1, segs=64, chamfer=0.0, smooth=True):
    """Cilindro macizo con chaflán opcional (perfil en torno hecho con abanico en las tapas)."""
    c = chamfer
    if c > 0:
        prof = [(r - c, z0), (r, z0 + c), (r, z1 - c), (r - c, z1)]
    else:
        prof = [(r, z0), (r, z1)]
    verts = []; faces = []
    n = len(prof)
    for i in range(segs):
        a = 2 * pi * i / segs
        for (rr, z) in prof:
            verts.append((rr * cos(a), rr * sin(a), z))
    for i in range(segs):
        i2 = (i + 1) % segs
        for j in range(n - 1):
            faces.append((i * n + j, i2 * n + j, i2 * n + j + 1, i * n + j + 1))
    faces.append(tuple(i * n for i in range(segs)))
    faces.append(tuple(i * n + n - 1 for i in range(segs)))
    return mesh_obj(name, verts, faces, smooth=smooth, merge=0)


def box(name, sx, sy, sz, center=(0, 0, 0)):
    cx, cy, cz = center
    v = [(cx + dx * sx / 2, cy + dy * sy / 2, cz + dz * sz / 2)
         for dx in (-1, 1) for dy in (-1, 1) for dz in (-1, 1)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return mesh_obj(name, v, f, smooth=False, merge=0)


def cut(target, cutter, op='DIFFERENCE', solver='EXACT'):
    m = target.modifiers.new('bool', 'BOOLEAN')
    m.operation = op
    m.object = cutter
    try:
        m.solver = solver
    except Exception:
        pass
    cutter.hide_render = True
    cutter.hide_viewport = True
    cutter.display_type = 'WIRE'
    return m


def bevel(ob, width, segs=3, angle=35):
    m = ob.modifiers.new('bevel', 'BEVEL')
    m.width = width
    m.segments = segs
    m.limit_method = 'ANGLE'
    m.angle_limit = radians(angle)
    try:
        m.harden_normals = True
    except Exception:
        pass
    m.miter_outer = 'MITER_ARC'
    return m


def weighted_normals(ob, keep_sharp=False):
    m = ob.modifiers.new('wn', 'WEIGHTED_NORMAL')
    m.mode = 'FACE_AREA'
    m.weight = 60
    m.keep_sharp = keep_sharp
    return m


def sharp_by_angle(ob, angle=45):
    ob.data.set_sharp_from_angle(angle=radians(angle))


def apply_modifiers(ob):
    """Evalúa los modificadores y deja la malla resultante (útil para instanciar)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    ob.modifiers.clear()
    old = ob.data
    ob.data = me
    return ob


# ---------------------------------------------------------------- materiales
def _principled(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    return m, nt, b


def _add(nt, a, b):
    n = nt.nodes.new('ShaderNodeMath'); n.operation = 'ADD'
    for i, v in enumerate((a, b)):
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def _turn_coord(nt, axis='Z'):
    """Coordenada 1D que avanza con el radio y con el eje: marca de torno."""
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sp = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sp.inputs[0])
    ax = {'X': ('Y', 'Z', 'X'), 'Y': ('X', 'Z', 'Y'), 'Z': ('X', 'Y', 'Z')}[axis]
    ln = nt.nodes.new('ShaderNodeCombineXYZ')
    nt.links.new(sp.outputs[ax[0]], ln.inputs[0]); nt.links.new(sp.outputs[ax[1]], ln.inputs[1])
    le = nt.nodes.new('ShaderNodeVectorMath'); le.operation = 'LENGTH'
    nt.links.new(ln.outputs[0], le.inputs[0])
    t = _add(nt, le.outputs['Value'], sp.outputs[ax[2]])
    cb = nt.nodes.new('ShaderNodeCombineXYZ')
    nt.links.new(t, cb.inputs[0])
    return tc, cb.outputs[0], le.outputs['Value']


def steel(name='acero', color=(0.80, 0.81, 0.83), rough=0.22, aniso=0.0, radial_axis='Z',
          noise=0.025, coat=0.0, bands=0.0, band_scale=55.0, band_bump=0.0, tint=None, tint_from=0.0, tint_to=1.0):
    """Acero. bands: variación de brillo en anillos (torneado). tint: color que aparece según el radio."""
    m, nt, b = _principled(name)
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Metallic'].default_value = 1.0
    b.inputs['Roughness'].default_value = rough
    if coat:
        b.inputs['Coat Weight'].default_value = coat
        b.inputs['Coat Roughness'].default_value = 0.12
    tc, tvec, radius = _turn_coord(nt, radial_axis)
    if aniso:
        b.inputs['Anisotropic'].default_value = aniso
        t = nt.nodes.new('ShaderNodeTangent')
        t.direction_type = 'RADIAL'
        t.axis = radial_axis
        nt.links.new(t.outputs['Tangent'], b.inputs['Tangent'])
    r_out = rough
    if noise:
        nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = 700.0
        nz.inputs['Detail'].default_value = 2.0
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['To Min'].default_value = -noise
        mr.inputs['To Max'].default_value = noise
        nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
        nt.links.new(nz.outputs['Fac'], mr.inputs['Value'])
        r_out = _add(nt, r_out, mr.outputs['Result'])
    if bands:
        nb = nt.nodes.new('ShaderNodeTexNoise')
        nb.inputs['Scale'].default_value = band_scale
        nb.inputs['Detail'].default_value = 3.0
        nt.links.new(tvec, nb.inputs['Vector'])
        mb = nt.nodes.new('ShaderNodeMapRange')
        mb.inputs['From Min'].default_value = 0.25
        mb.inputs['From Max'].default_value = 0.75
        mb.inputs['To Min'].default_value = -bands
        mb.inputs['To Max'].default_value = bands
        nt.links.new(nb.outputs['Fac'], mb.inputs['Value'])
        r_out = _add(nt, r_out, mb.outputs['Result'])
        if band_bump:
            bp = nt.nodes.new('ShaderNodeBump')
            bp.inputs['Strength'].default_value = band_bump
            bp.inputs['Distance'].default_value = 0.0006
            nt.links.new(nb.outputs['Fac'], bp.inputs['Height'])
            nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    if not isinstance(r_out, (int, float)):
        nt.links.new(r_out, b.inputs['Roughness'])
    if tint is not None:
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = tint_from
        mr.inputs['From Max'].default_value = tint_to
        nt.links.new(radius, mr.inputs['Value'])
        mx = nt.nodes.new('ShaderNodeMixRGB')
        mx.inputs['Color1'].default_value = (*color, 1)
        mx.inputs['Color2'].default_value = (*tint, 1)
        nt.links.new(mr.outputs['Result'], mx.inputs['Fac'])
        nt.links.new(mx.outputs['Color'], b.inputs['Base Color'])
    return m


def paint(name, color, rough=0.42, bump=0.0, bump_scale=160.0, coat=0.25, metallic=0.0, bump_dist=0.004):
    m, nt, b = _principled(name)
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Metallic'].default_value = metallic
    b.inputs['Roughness'].default_value = rough
    if coat:
        b.inputs['Coat Weight'].default_value = coat
        b.inputs['Coat Roughness'].default_value = 0.25
    if bump:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = bump_scale
        nz.inputs['Detail'].default_value = 5.0
        nz.inputs['Roughness'].default_value = 0.62
        bp = nt.nodes.new('ShaderNodeBump')
        bp.inputs['Strength'].default_value = bump
        bp.inputs['Distance'].default_value = bump_dist
        nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
        nt.links.new(nz.outputs['Fac'], bp.inputs['Height'])
        nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def rubber(name='hule', color=(0.022, 0.022, 0.024), rough=0.58, bump=0.25, bump_scale=420.0, sheen=0.3):
    m, nt, b = _principled(name)
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    try:
        b.inputs['Sheen Weight'].default_value = sheen
    except Exception:
        pass
    if bump:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = bump_scale
        nz.inputs['Detail'].default_value = 3.0
        bp = nt.nodes.new('ShaderNodeBump')
        bp.inputs['Strength'].default_value = bump
        bp.inputs['Distance'].default_value = 0.0015
        nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
        nt.links.new(nz.outputs['Fac'], bp.inputs['Height'])
        nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def plastic(name, color, rough=0.38, sss=0.08):
    m, nt, b = _principled(name)
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    try:
        b.inputs['Subsurface Weight'].default_value = sss
        b.inputs['Subsurface Radius'].default_value = (0.02, 0.006, 0.004)
    except Exception:
        pass
    return m


def setmat(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    return ob


# ---------------------------------------------------------------- estudio
def bounds(objs=None):
    dg = bpy.context.evaluated_depsgraph_get()
    mn = Vector((1e9, 1e9, 1e9)); mx = Vector((-1e9, -1e9, -1e9))
    for ob in (objs or bpy.context.scene.objects):
        if ob.type != 'MESH' or ob.hide_render:
            continue
        if ob.get('studio'):
            continue
        ev = ob.evaluated_get(dg)
        for c in ev.bound_box:
            w = ev.matrix_world @ Vector(c)
            mn.x = min(mn.x, w.x); mn.y = min(mn.y, w.y); mn.z = min(mn.z, w.z)
            mx.x = max(mx.x, w.x); mx.y = max(mx.y, w.y); mx.z = max(mx.z, w.z)
    return mn, mx


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def area_light(name, loc, target, size, energy, color=(1, 1, 1), size_y=None, cam_visible=False):
    L = bpy.data.lights.new(name, 'AREA')
    L.energy = energy
    L.color = color
    if size_y:
        L.shape = 'RECTANGLE'; L.size = size; L.size_y = size_y
    else:
        L.shape = 'SQUARE'; L.size = size
    ob = bpy.data.objects.new(name, L)
    link(ob)
    ob.location = loc
    look_at(ob, target)
    ob['studio'] = 1
    ob.visible_camera = cam_visible
    return ob


def flag(name, loc, target, sx, sy, value=0.0):
    """Tarjeta negra (o gris) que solo se ve en los reflejos."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-sx / 2, -sy / 2, 0), (sx / 2, -sy / 2, 0), (sx / 2, sy / 2, 0), (-sx / 2, sy / 2, 0)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new(name, me)
    link(ob)
    ob.location = loc
    look_at(ob, target)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (value, value, value, 1)
    em.inputs['Strength'].default_value = 1.0
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    ob.data.materials.append(m)
    ob['studio'] = 1
    ob.visible_camera = False
    ob.visible_diffuse = False
    ob.visible_shadow = False
    ob.visible_glossy = True
    return ob


def scene_points(limit=400000):
    import numpy as np
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH' or ob.hide_render or ob.get('studio'):
            continue
        ev = ob.evaluated_get(dg)
        me = ev.data
        n = len(me.vertices)
        if not n:
            continue
        co = np.empty(n * 3, dtype=np.float32)
        me.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)
        M = np.array(ev.matrix_world, dtype=np.float32)
        out.append(co @ M[:3, :3].T + M[:3, 3])
    pts = np.concatenate(out)
    if len(pts) > limit:
        pts = pts[:: len(pts) // limit + 1]
    return pts


def studio(az=-38, el=24, lens=85, margin=1.22, world=0.78, key=1.0, fill=1.0, target_z=None, flags=True,
           shift=(0.0, 0.0)):
    """Cámara, luces y piso alrededor de lo que haya en la escena.

    margin: cuánto más grande es el cuadro que la pieza (1.22 = la pieza ocupa 82 % del cuadro).
    shift: desplaza la pieza dentro del cuadro (fracción del cuadro; y positivo la sube).
    """
    import numpy as np
    sc = bpy.context.scene
    pts = scene_points()
    mn = Vector(pts.min(axis=0).tolist()); mx = Vector(pts.max(axis=0).tolist())
    ctr = (mn + mx) / 2
    R = (mx - mn).length / 2
    # piso que solo recoge sombra (difuso puro: no refleja las tarjetas)
    me = bpy.data.meshes.new('piso')
    s = R * 40
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    piso = bpy.data.objects.new('piso', me)
    link(piso)
    piso.location = (ctr.x, ctr.y, mn.z - 2e-5)
    piso.is_shadow_catcher = True
    pm = bpy.data.materials.new('piso')
    pm.use_nodes = True
    pb = pm.node_tree.nodes['Principled BSDF']
    pb.inputs['Base Color'].default_value = (0.92, 0.92, 0.92, 1)
    pb.inputs['Roughness'].default_value = 1.0
    try:
        pb.inputs['Specular IOR Level'].default_value = 0.0
    except Exception:
        pass
    piso.data.materials.append(pm)
    piso['studio'] = 1
    # mundo
    w = bpy.data.worlds.new('mundo')
    sc.world = w
    w.use_nodes = True
    wn = w.node_tree
    bg = wn.nodes['Background']
    bg.inputs[1].default_value = 1.0
    tcw = wn.nodes.new('ShaderNodeTexCoord')
    spw = wn.nodes.new('ShaderNodeSeparateXYZ')
    wn.links.new(tcw.outputs['Generated'], spw.inputs[0])
    cr = wn.nodes.new('ShaderNodeValToRGB')
    mrw = wn.nodes.new('ShaderNodeMapRange')
    mrw.inputs['From Min'].default_value = -1.0
    mrw.inputs['From Max'].default_value = 1.0
    wn.links.new(spw.outputs['Z'], mrw.inputs['Value'])
    wn.links.new(mrw.outputs['Result'], cr.inputs['Fac'])
    e = cr.color_ramp.elements
    e[0].position = 0.0; e[0].color = (world * 0.9, world * 0.9, world * 0.9, 1)
    e[1].position = 1.0; e[1].color = (world * 1.35, world * 1.35, world * 1.37, 1)
    for pos, k in ((0.47, 0.78), (0.56, 0.52), (0.72, 0.95)):
        el_ = e.new(pos); el_.color = (world * k, world * k, world * k * 1.01, 1)
    wn.links.new(cr.outputs['Color'], bg.inputs[0])
    # cámara: dirección fija, distancia y centro ajustados a la silueta real
    cam_d = bpy.data.cameras.new('cam')
    cam_d.lens = lens
    cam_d.sensor_width = 36
    cam = bpy.data.objects.new('cam', cam_d)
    link(cam)
    a = radians(az); e = radians(el)
    back = Vector((sin(a) * cos(e), -cos(a) * cos(e), sin(e)))
    fwd = -back
    right = fwd.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(fwd).normalized()
    th = 18.0 / lens
    dist = R / th * 1.3
    F = np.array(fwd); Rg = np.array(right); U = np.array(up)
    c = np.array(ctr)
    for _ in range(6):
        v = pts - (c - F * dist)
        zc = v @ F
        tx = (v @ Rg) / zc; ty = (v @ U) / zc
        cx = (tx.min() + tx.max()) / 2; cy = (ty.min() + ty.max()) / 2
        h = max((tx.max() - tx.min()) / 2, (ty.max() - ty.min()) / 2)
        c = c + Rg * cx * dist + U * cy * dist
        dist = dist * h * margin / th
    c = c - Rg * shift[0] * 2 * th * dist - U * shift[1] * 2 * th * dist
    aim = Vector(c.tolist())
    cam.location = aim + back * dist
    look_at(cam, aim)
    cam_d.clip_start = dist * 0.05
    cam_d.clip_end = dist * 30
    sc.camera = cam
    cam['studio'] = 1
    if target_z is not None:
        ctr.z = target_z
    # luces (relativas a la cámara)
    E = key * 150 * R * R
    area_light('clave', ctr - fwd * R * 1.6 - right * R * 2.4 + Vector((0, 0, R * 5.0)), ctr, R * 4.0, E * 1.0)
    area_light('cenital', ctr + Vector((0, 0, R * 4.6)) + fwd * R * 0.3, ctr, R * 6.0, E * 0.9)
    area_light('relleno', ctr - fwd * R * 2.6 + right * R * 3.4 + Vector((0, 0, R * 1.2)), ctr, R * 3.0, E * 0.4 * fill)
    area_light('contra', ctr + fwd * R * 3.4 + right * R * 1.2 + Vector((0, 0, R * 2.4)), ctr, R * 2.6, E * 0.5,
               size_y=R * 5.0)
    # tarjetas oscuras para dar contraste al metal
    if flags:
        flag('negro_izq', ctr - right * R * 5.0 - fwd * R * 0.5 + Vector((0, 0, R * 0.6)), ctr, R * 1.3, R * 5.0, 0.02)
        flag('negro_der', ctr + right * R * 5.2 + fwd * R * 1.0 + Vector((0, 0, R * 0.9)), ctr, R * 1.0, R * 5.0, 0.03)
        flag('negro_frente', cam.location + up * (-R * 1.6) - fwd * R * 0.2, ctr, R * 5.0, R * 0.8, 0.05)
    return cam, ctr, R


def render(path, res=None, samples=None):
    sc = bpy.context.scene
    if res:
        sc.render.resolution_x = res; sc.render.resolution_y = res
    if samples:
        sc.cycles.samples = samples
    sc.render.filepath = path
    import time
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print('render', path, round(time.time() - t, 1), 's')


def args():
    a = sys.argv
    a = a[a.index('--') + 1:] if '--' in a else a[1:]
    out = a[0] if len(a) > 0 else 'out.png'
    res = int(a[1]) if len(a) > 1 else 700
    smp = int(a[2]) if len(a) > 2 else 96
    return out, res, smp


# ---------------------------------------------------------------- extras
def assign(ob, mats, fn):
    """Reparte materiales por cara: fn(centro, normal) -> índice."""
    me = ob.data
    me.materials.clear()
    for m in mats:
        me.materials.append(m)
    for p in me.polygons:
        p.material_index = fn(p.center, p.normal)
    return ob


def place(ob, *mats4):
    M = Matrix.Identity(4)
    for m in mats4:
        M = M @ m
    ob.matrix_world = M
    return ob


def RX(a): return Matrix.Rotation(radians(a), 4, 'X')
def RY(a): return Matrix.Rotation(radians(a), 4, 'Y')
def RZ(a): return Matrix.Rotation(radians(a), 4, 'Z')
def T(x, y, z): return Matrix.Translation((x, y, z))


def finish(ob, sharp=40, wn=True):
    """Aplica modificadores, marca aristas vivas por ángulo y suaviza el resto."""
    apply_modifiers(ob)
    for p in ob.data.polygons:
        p.use_smooth = True
    sharp_by_angle(ob, sharp)
    if wn:
        weighted_normals(ob, keep_sharp=True)
    return ob


def arc(cx, cy, r, a0, a1, n):
    return [(cx + r * cos(radians(a0 + (a1 - a0) * k / n)), cy + r * sin(radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]


def scale_pts(pts, s=MM):
    return [(p[0] * s, p[1] * s) for p in pts]
