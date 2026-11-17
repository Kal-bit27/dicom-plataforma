import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

out, res, smp = args()
a = sys.argv[sys.argv.index('--') + 1:]
variant = a[3] if len(a) > 3 else 'poliamida'
SPIN = float(a[4]) if len(a) > 4 else 20.0
reset(res, smp)

NR = 13; RP = 23.0; RD = 8.98; LW = 10.0
STEP = 360.0 / NR
A0 = 3.5 * STEP + 0.06; A1 = 6.5 * STEP + 0.06   # sector retirado (entre dos barras de jaula)

def S(pts): return scale_pts(pts)

def wedge():
    pts = [(0, 0)] + [(60 * cos(radians(A0 + (A1 - A0) * k / 24)), 60 * sin(radians(A0 + (A1 - A0) * k / 24))) for k in range(25)]
    return prism('cuna', S(pts), -20 * MM, 20 * MM, smooth=False)

def multi_prism(name, outline, u0, u1, Ms):
    """Prismas radiales: contorno (v tangencial, w axial) extruido de u0 a u1 (radial), uno por matriz."""
    verts = []; faces = []; n = len(outline)
    for M in Ms:
        b = len(verts)
        for u in (u0, u1):
            for (v, w) in outline:
                verts.append(tuple(M @ Vector((u, v, w))))
        for i in range(n):
            j = (i + 1) % n
            faces.append((b + i, b + j, b + n + j, b + n + i))
        faces.append(tuple(b + i for i in range(n)))
        faces.append(tuple(b + n + i for i in range(n)))
    return mesh_obj(name, verts, faces, smooth=False, merge=0)

def rrect(v0, v1, w0, w1, r, n=4):
    return fillet_poly([(v0, w0), (v1, w0), (v1, w1), (v0, w1)], n=n, radii=[r] * 4)

def ang_of(c): return degrees_(atan2(c[1], c[0])) % 360
def degrees_(x): return x * 180 / pi

def cutmask(c):
    for A in (A0, A1):
        d = -sin(radians(A)) * c[0] + cos(radians(A)) * c[1]
        dot = cos(radians(A)) * c[0] + sin(radians(A)) * c[1]
        if abs(d) < 1.5e-4 and dot > 0: return True
    return False

def part(ob, mat, matte, sector=True, bev=None, sharp=40):
    if sector: cut(ob, wedge())
    if bev: bevel(ob, bev * MM, segs=3, angle=35)
    finish(ob, sharp=sharp)
    ob.data.materials.clear(); ob.data.materials.append(mat); ob.data.materials.append(matte)
    for p in ob.data.polygons:
        p.material_index = 1 if cutmask(p.center) else 0
    return ob

# ---- materiales
M_RING = steel('anillo', color=(0.40, 0.41, 0.43), rough=0.22, aniso=0.6, noise=0.02, bands=0.05, band_scale=80.0, band_bump=0.2)
M_MATTE = steel('corte', color=(0.30, 0.31, 0.33), rough=0.5, noise=0.04)
M_ROLL = steel('rodillo', color=(0.62, 0.63, 0.65), rough=0.08, noise=0.01)

# ---- aro exterior NJ: dos rebordes
RZ_ = 5.6
pts = [(31, -10), (31, 10), (25.2, 10), (25.2, RZ_), (27.5, RZ_), (27.5, -RZ_), (25.2, -RZ_), (25.2, -10)]
rad = [1.2, 1.2, 0.7, 0.5, 0.4, 0.4, 0.5, 0.7]
outer = lathe('aro_ext', S(fillet_poly(pts, n=5, radii=rad)), segs=240)
part(outer, M_RING, M_MATTE)
# ---- aro interior con un reborde (lado -z)
pts = [(15, -10), (21.8, -10), (21.8, -RZ_), (18.5, -RZ_), (18.5, 10), (15, 10)]
rad = [0.8, 0.7, 0.4, 0.4, 0.8, 0.8]
inner = lathe('aro_int', S(fillet_poly(pts, n=5, radii=rad)), segs=240)
part(inner, M_RING, M_MATTE)

# ---- rodillos (los del sector se omiten)
rol = cylinder('rodillo', RD / 2 * MM, -LW / 2 * MM, LW / 2 * MM, segs=64, chamfer=0.6 * MM)
bevel(rol, 0.3 * MM, segs=3, angle=30)
finish(rol, sharp=30)
rol.data.materials.clear(); rol.data.materials.append(M_ROLL)
first = True
for k in range(NR):
    ang = STEP * k
    if A0 < ang < A1: continue
    ob = rol if first else instance(rol, 'rod%d' % k)
    first = False
    ob.matrix_world = RZ(ang) @ T(RP * MM, 0, 0)
    if ob is not rol:
        ob.data.materials.clear(); ob.data.materials.append(M_ROLL)

# ---- jaulas
Ms = [RZ(STEP * k) for k in range(NR)]
if variant == 'poliamida':
    mat = plastic('pa66', (0.03, 0.03, 0.033), rough=0.42, sss=0.0)
    pr = [(22.2, -8.8), (24.9, -8.8), (24.9, 8.8), (22.2, 8.8)]
    cage = lathe('jaula', S(fillet_poly(pr, n=4, radii=[0.9] * 4)), segs=240)
    cut(cage,
        multi_prism('vent', S(rrect(-4.85, 4.85, -5.45, 5.45, 1.2)), 20 * MM, 27 * MM, Ms))
    part(cage, mat, mat, bev=0.55, sharp=50)
elif variant == 'laton':
    mat = steel('laton', color=(0.80, 0.58, 0.30), rough=0.25, aniso=0.3, noise=0.015, bands=0.04, band_bump=0.1)
    matm = steel('laton_m', color=(0.62, 0.45, 0.24), rough=0.45, noise=0.03)
    pr = [(22.3, -8.6), (24.9, -8.6), (24.9, 6.5), (22.3, 6.5)]
    comb = lathe('peine', S(fillet_poly(pr, n=3, radii=[0.5, 0.5, 0.2, 0.2])), segs=240)
    cut(comb, multi_prism('vent', S(rrect(-4.85, 4.85, -5.45, 8.0, 0.6, 3)), 20 * MM, 27 * MM, Ms))
    part(comb, mat, matm, bev=0.25, sharp=45)
    pr = [(22.3, 6.5), (24.9, 6.5), (24.9, 8.8), (22.3, 8.8)]
    lid = lathe('tapa', S(fillet_poly(pr, n=3, radii=[0.2, 0.2, 0.5, 0.5])), segs=240)
    part(lid, mat, matm, bev=0.2, sharp=45)
    riv = lathe('remache', S([(0.02, 0), (1.25, 0), (1.25, 0.25), (0.95, 0.65), (0.02, 0.8)]), segs=32)
    finish(riv, sharp=50); riv.data.materials.append(mat)
    for k in range(NR):
        ang = STEP * (k + 0.5)
        if A0 - 3 < ang < A1 + 3: continue
        rv = instance(riv, 'rem%d' % k)
        rv.matrix_world = RZ(ang) @ T(23.6 * MM, 0, 8.8 * MM)
        rv.data.materials.clear(); rv.data.materials.append(mat)
    riv.hide_render = True
else:  # acero: chapa prensada con ventanas
    mat = steel('acero_jaula', color=(0.36, 0.37, 0.39), rough=0.36, aniso=0.2, noise=0.02)
    mo = [(24.9, 0), (24.9, 5.9), (24.0, 6.9), (24.0, 8.8)]
    t = 0.9
    mi = [(24.9 - t, 0), (24.9 - t, 5.9), (24.0 - t, 6.9), (24.0 - t, 8.8)]
    ext = [(r, -z) for (r, z) in mo[:0:-1]] + mo
    itr = [(r, -z) for (r, z) in mi[:0:-1]] + mi
    poly = ext + itr[::-1]
    cage = lathe('jaula', S(poly), segs=240)
    cut(cage, multi_prism('vent', S(rrect(-4.85, 4.85, -5.45, 5.45, 2.0, 5)), 20 * MM, 27 * MM, Ms))
    part(cage, mat, mat, bev=0.2, sharp=45)

allobjs = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render]
for ob in allobjs:
    ob.matrix_world = RX(90) @ RZ(SPIN) @ ob.matrix_world

studio(az=-38, el=22, lens=90, margin=1.2, world=0.55, key=0.85)
render(out, res, smp)
