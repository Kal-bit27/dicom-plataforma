import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from math import degrees

out, res, smp = args()
a_ = sys.argv[sys.argv.index('--') + 1:]
VAR = a_[3] if len(a_) > 3 else 'abierto'
reset(res, smp)

# ------------------------------------------------------------ materiales
M_ring = steel('aro', color=(0.62, 0.63, 0.65), rough=0.18, aniso=0.6, noise=0.02, bands=0.05, band_scale=70.0, band_bump=0.2)
M_ball = steel('bola', color=(0.7, 0.71, 0.73), rough=0.06, noise=0.0)
M_cage = steel('jaula', color=(0.45, 0.46, 0.48), rough=0.35, noise=0.03)
M_shield = steel('escudo', color=(0.70, 0.71, 0.73), rough=0.14, noise=0.01, aniso=0.4, bands=0.02, band_scale=60.0)
M_rub = rubber('hule')
M_pa = plastic('pa66', (0.025, 0.025, 0.027), rough=0.45, sss=0)


# ------------------------------------------------------------ utilidades
def prof_obj(name, pts, mat, segs=200, n=5):
    p = fillet_poly([(q[0], q[1]) for q in pts], n=n, radii=[q[2] if len(q) > 2 else 0.0 for q in pts])
    ob = lathe(name, scale_pts(p), segs=segs)
    finish(ob, sharp=40)
    setmat(ob, mat)
    return ob


def arcpts(cr, cz, rad, a0, a1, n, sgn=-1):
    """punto = (cr + sgn*rad*cos(psi), cz + rad*sin(psi))"""
    return [(cr + sgn * rad * cos(radians(a0 + (a1 - a0) * k / n)), cz + rad * sin(radians(a0 + (a1 - a0) * k / n)), 0.0)
            for k in range(n + 1)]


def mirror_list(pts):
    return [(r, -z, *rest) for (r, z, *rest) in reversed(pts)]


def ball(br, name='bola'):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=br * MM)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, me); link(ob); setmat(ob, M_ball)
    return ob


def cutter(name, kind, centers, rad, z0=0, z1=0, zc=0):
    bm = bmesh.new()
    for (x, y) in centers:
        if kind == 'sphere':
            bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=rad * MM,
                                      matrix=Matrix.Translation((x * MM, y * MM, zc * MM)))
        else:
            bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=rad * MM, radius2=rad * MM, depth=(z1 - z0) * MM,
                                  matrix=Matrix.Translation((x * MM, y * MM, (z0 + z1) / 2 * MM)))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); link(ob)
    return ob


def place_mat(ob, M):
    ob.matrix_world = M @ ob.matrix_world


def ribbon_cage(zc, n, pr, br, phase, t=0.9, rr=1.3):
    """Jaula de chapa remachada de dos mitades (centrada en el plano z=zc). Devuelve lista de objetos."""
    Ri = br + 0.2; Ro = Ri + 0.7; w = 0.66 * br
    angs = [radians(phase + 360.0 * k / n) for k in range(n)]
    ctr = [(pr * cos(a), pr * sin(a)) for a in angs]
    objs = []
    # placa plana (mitad +z) con agujeros
    plate = prof_obj('placa', [(pr - w, 0, 0.25), (pr + w, 0, 0.25), (pr + w, t, 0.25), (pr - w, t, 0.25)], M_cage, segs=180, n=2)
    cut(plate, cutter('c', 'cyl', ctr, Ri, -1, t + 1))
    finish(plate, sharp=40)
    objs.append(plate)
    # cuencos
    fmin = 62.0
    po = [(Ro * sin(radians(f)), Ro * cos(radians(f)), 0.0) for f in [90 - (90 - fmin) * k / 10 for k in range(11)]]
    pi_ = [(Ri * sin(radians(f)), Ri * cos(radians(f)), 0.0) for f in [fmin + (90 - fmin) * k / 10 for k in range(11)]]
    shell0 = prof_obj('cuenco', po + pi_, M_cage, segs=64, n=1)
    for (x, y) in ctr:
        s = bpy.data.objects.new('cuenco', shell0.data); link(s)
        s.matrix_world = T(x * MM, y * MM, 0); s.data.materials.clear(); s.data.materials.append(M_cage)
        objs.append(s)
    shell0.hide_render = True; shell0.hide_viewport = True
    # remaches entre bolas
    rv = prof_obj('remache', [(0, t - 0.05), (rr * 1.15, t - 0.05), (rr * 1.15, t + 0.15), (rr, t + 0.45), (rr * 0.6, t + 0.62), (0, t + 0.66)], M_cage, segs=40, n=2)
    for k in range(n):
        a = radians(phase + 360.0 * (k + 0.5) / n)
        s = bpy.data.objects.new('remache', rv.data); link(s)
        s.matrix_world = T(pr * cos(a) * MM, pr * sin(a) * MM, 0); s.data.materials.append(M_cage)
        objs.append(s)
    rv.hide_render = True; rv.hide_viewport = True
    # mitad inferior = espejo, luego mover al plano zc
    mir = []
    for o in objs:
        s = bpy.data.objects.new(o.name + 'm', o.data); link(s)
        s.matrix_world = o.matrix_world.copy(); s.data.materials.append(M_cage)
        mir.append(s)
    for o in objs:
        o.matrix_world = T(0, 0, zc * MM) @ o.matrix_world
    for o in mir:
        o.matrix_world = T(0, 0, zc * MM) @ RX(180) @ o.matrix_world
    return objs + mir


def balls_row(n, pr, zc, br, phase):
    res_ = []
    for k in range(n):
        a = radians(phase + 360.0 * k / n)
        b = ball(br); b.matrix_world = T(pr * cos(a) * MM, pr * sin(a) * MM, zc * MM)
        res_.append(b)
    return res_


tilt_group = []   # partes que se inclinan (anillo interior, bolas, jaula)
fixed = []
TILT = 0.0
TURN = -20.0

# ------------------------------------------------------------ variantes
if VAR in ('abierto', '2rs', '2z'):
    sealed = VAR != 'abierto'
    br = 5.55; pr = 26.75; H = 8.5
    # aro exterior
    ro = [(36, -H, 1.2), (36, H, 1.2)]
    if sealed:
        ro += [(30.6, H, 0.35), (30.6, 8.15, 0.1), (31.5, 8.15, 0.1), (31.5, 6.6, 0.1), (29.6, 6.6, 0.1)]
    else:
        ro += [(29.6, H, 0.9)]
    ro += [(29.6, 4.88, 0.3)]
    ro += arcpts(26.53, 0, 5.77, 57.8, -57.8, 26, sgn=1)[1:-1]
    ro += [(29.6, -4.88, 0.3)]
    if sealed:
        ro += [(29.6, -6.6, 0.1), (31.5, -6.6, 0.1), (31.5, -8.15, 0.1), (30.6, -8.15, 0.1), (30.6, -H, 0.35)]
    else:
        ro += [(29.6, -H, 0.9)]
    outer = prof_obj('aro_ext', ro, M_ring); fixed.append(outer)
    # aro interior
    ri = [(17.5, H, 0.9)]
    if sealed:
        ri += [(23.9, H, 0.8), (23.9, 7.3, 0.2), (23.2, 7.3, 0.15), (23.2, 6.1, 0.15), (23.9, 6.1, 0.2)]
    else:
        ri += [(23.9, H, 0.8)]
    ri += [(23.9, 4.88, 0.3)]
    ri += arcpts(26.97, 0, 5.77, 57.8, -57.8, 26, sgn=-1)[1:-1]
    ri += [(23.9, -4.88, 0.3)]
    if sealed:
        ri += [(23.9, -6.1, 0.2), (23.2, -6.1, 0.15), (23.2, -7.3, 0.15), (23.9, -7.3, 0.2), (23.9, -H, 0.8)]
    else:
        ri += [(23.9, -H, 0.8)]
    ri += [(17.5, -H, 0.9)]
    inner = prof_obj('aro_int', ri, M_ring); tilt_group.append(inner)
    tilt_group += balls_row(9, pr, 0, br, 0)
    if not sealed:
        tilt_group += ribbon_cage(0, 9, pr, br, 0, t=0.9, rr=1.3)
    else:
        for sg in (1, -1):
            if VAR == '2rs':
                rp = [(31.4, 6.6, 0.15), (31.4, 8.0, 0.25), (28.2, 8.0, 0.4), (25.0, 7.55, 0.5), (23.6, 7.4, 0.2),
                      (23.15, 7.0, 0.1), (23.15, 6.55, 0.1), (23.8, 6.4, 0.2), (25.6, 6.5, 0.4), (29.6, 6.6, 0.2)]
                s = prof_obj('sello', rp, M_rub, segs=200, n=3)
                assign(s, [M_rub, M_shield], lambda c_, n_: 1 if (n_.z > 0.9 and sqrt(c_.x**2 + c_.y**2) > 30.1 * MM) else 0)
                # (apply the steel ring only to the outer rim of the face)
            else:
                sp = [(31.35, 7.5, 0.1), (31.35, 8.0, 0.1), (28.2, 8.0, 0.2), (27.0, 7.5, 0.2), (24.4, 7.5, 0.1), (24.4, 7.0, 0.1),
                      (27.0, 7.0, 0.2), (28.2, 7.5, 0.2)]
                s = prof_obj('escudo', sp, M_shield, segs=200, n=3)
            if sg < 0:
                s.matrix_world = RX(180) @ s.matrix_world
            tilt_group.append(s)  # (no tilt here); sellos van fijos al aro exterior
            tilt_group.remove(s); fixed.append(s)
    TURN = -73.0

elif VAR == 'autoalineable':
    br = 4.76; pr = 26.75; H = 8.5; zr = 3.6; Rs = 31.8; n = 12
    ro = [(36, -H, 1.2), (36, H, 1.2)]
    zs = [H - 2 * H * k / 36 for k in range(37)]
    sph = [(sqrt(Rs**2 - z * z), z, 0.0) for z in zs]
    sph[0] = (sph[0][0], sph[0][1], 0.6); sph[-1] = (sph[-1][0], sph[-1][1], 0.6)
    outer = prof_obj('aro_ext', ro + sph, M_ring); fixed.append(outer)
    half = [(17.5, H, 0.9), (24.5, H, 0.8), (24.5, 7.96, 0.3)]
    psi0 = degrees(asin((7.96 - zr) / 4.95)); psi1 = -degrees(asin(zr / 4.95))
    half += arcpts(26.85, zr, 4.95, psi0, psi1, 22, sgn=-1)[1:]
    half[-1] = (half[-1][0], 0.0, 0.7)
    full = half + mirror_list(half)[1:]
    full = full
    inner = prof_obj('aro_int', full, M_ring); tilt_group.append(inner)
    for zz, ph in ((zr, 0), (-zr, 180.0 / n)):
        tilt_group += balls_row(n, pr, zz, br, ph)
        tilt_group += ribbon_cage(zz, n, pr, br, ph, t=0.8, rr=1.15)
    TILT = 4.0
    TURN = -73.0

elif VAR == 'contacto':
    br = 5.55; pr = 26.75; H = 13.5; zr = 6.0; n = 13; Rg = 5.7
    # inner
    plus = [(17.5, H, 1.0), (25.3, H, 0.8)]
    ar = arcpts(26.75, zr, Rg, 75, -25, 22, sgn=-1)
    plus += ar
    plus += [(22.4, 0.0, 1.3)]
    full = plus + mirror_list(plus[:-1])[0:]
    inner = prof_obj('aro_int', full, M_ring); tilt_group.append(inner)
    # outer
    ar_o = arcpts(26.75, zr, Rg, -25, 75, 22, sgn=1)
    ar_o = [(r, 2 * zr - z, 0.0) for (r, z, _) in ar_o]  # espejo respecto a zr -> (r, zr - Rg sin(psi))
    ar_o = [(26.75 + Rg * cos(radians(p)), zr - Rg * sin(radians(p)), 0.0) for p in [-25 + 100 * k / 22 for k in range(23)]]
    plus_o = [(31.3, H, 0.7)] + ar_o
    ro = [(36, -H, 1.2), (36, H, 1.2)] + plus_o + mirror_list(plus_o)
    outer = prof_obj('aro_ext', ro, M_ring); fixed.append(outer)
    for zz, ph, sg in ((zr, 0, 1), (-zr, 180.0 / n, -1)):
        tilt_group += balls_row(n, pr, zz, br, ph)
        band = prof_obj('jaula', [(24.2, 7.2, 0.5), (29.4, 7.2, 0.5), (29.4, 10.5, 0.5), (24.2, 10.5, 0.5)], M_pa, segs=200, n=3)
        ctr = [(pr * cos(radians(ph + 360.0 * k / n)), pr * sin(radians(ph + 360.0 * k / n))) for k in range(n)]
        cut(band, cutter('cs', 'sphere', ctr, br + 0.3, zc=zr))
        finish(band, sharp=38); setmat(band, M_pa)
        if sg < 0:
            band.matrix_world = T(0, 0, 0) @ RX(180) @ band.matrix_world
            # mirror: rotate pocket phase -> compensate by rotating about z so pockets match row at phase ph
            band.matrix_world = RZ(-2 * ph) @ band.matrix_world if False else band.matrix_world
        tilt_group.append(band)
    TURN = -73.0

# ------------------------------------------------------------ pose
if TILT:
    for o in tilt_group:
        o.matrix_world = RX(TILT) @ o.matrix_world
allobjs = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render]
M = RZ(TURN) @ RX(90)
for o in bpy.data.objects:
    if o.type == 'MESH':
        o.matrix_world = M @ o.matrix_world

cam, ctr, R = studio(az=-38, el=22, lens=85, margin=1.2, world=0.5, key=0.65, fill=0.8)
render(out, res, smp)
