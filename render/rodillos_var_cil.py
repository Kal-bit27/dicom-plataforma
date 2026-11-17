import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

out, res, smp = args()
a = sys.argv[sys.argv.index('--') + 1:]
variant = a[3] if len(a) > 3 else 'laton'
reset(res, smp)

NR = 15; RP = 70.0; RR = 12.0; LW = 24.0; HB = 17.0
SPIN = float(a[4]) if len(a) > 4 else 0.0

def S(pts): return scale_pts(pts)

# ---- aro exterior (dos rebordes) NU220
pts = [(72.5, -HB), (90, -HB), (90, HB), (72.5, HB), (72.5, 12.3), (82, 12.3), (82, -12.3), (72.5, -12.3)]
rad = [0.9, 1.5, 1.5, 0.9, 0.7, 0.9, 0.9, 0.7]
outer = lathe('aro_ext', S(fillet_poly(pts, n=5, radii=rad)), segs=240)
finish(outer, sharp=40)
# ---- aro interior liso
pts = [(50, -HB), (58, -HB), (58, HB), (50, HB)]
inner = lathe('aro_int', S(fillet_poly(pts, n=5, radii=[1.2, 1.3, 1.3, 1.2])), segs=240)
finish(inner, sharp=40)

# ---- rodillo
rol = cylinder('rodillo', RR * MM, -LW / 2 * MM, LW / 2 * MM, segs=64, chamfer=1.0 * MM)
bevel(rol, 0.45 * MM, segs=3, angle=30)
finish(rol, sharp=30)

rollers = []
for k in range(NR):
    ob = rol if k == 0 else instance(rol, 'rod%d' % k)
    ob.matrix_world = RZ(360.0 * k / NR) @ T(RP * MM, 0, 0) @ ob.matrix_world if k == 0 else RZ(360.0 * k / NR) @ T(RP * MM, 0, 0)
    rollers.append(ob)

mat_ring = steel('anillo', color=(0.62, 0.63, 0.65), rough=0.18, aniso=0.6, noise=0.02, bands=0.05, band_bump=0.2)
mat_rol = steel('rodillo', color=(0.70, 0.71, 0.73), rough=0.06, noise=0.01)
setmat(outer, mat_ring); setmat(inner, mat_ring)
rol.data.materials.clear(); rol.data.materials.append(mat_rol)
for r in rollers: r.data.materials.clear(); r.data.materials.append(mat_rol)

parts = [outer, inner]
off = 0.5 * 360.0 / NR   # jaula desfasada medio paso (entre rodillos)
cage_objs = []

if variant == 'laton':
    mat = steel('laton', color=(0.80, 0.58, 0.30), rough=0.25, aniso=0.3, noise=0.015, bands=0.04, band_bump=0.1)
    for sg in (1, -1):
        z0, z1 = 12.4, 15.6
        pr = [(63.5, z0), (70.0, z0), (70.0, z1), (63.5, z1)]
        pr = fillet_poly(pr, n=4, radii=[0.5, 0.5, 0.8, 0.8])
        if sg < 0: pr = [(r, -z) for (r, z) in pr]
        ring = lathe('anillo_c', S(pr), segs=200); finish(ring, sharp=40); setmat(ring, mat); cage_objs.append(ring)
    bar = box('barra', 3.8 * MM, 3.8 * MM, 24.6 * MM, center=(0, 0, 0))
    bar.location = (0, 0, 0)
    # barra radial 62.5..77 (x), ancho 3.8 (y), largo z
    bar.data.transform(Matrix.Translation(((62.5 + 77) / 2 * MM - 0, 0, 0)) @ Matrix.Scale((77 - 62.5) / 3.8, 4, Vector((1, 0, 0))))
    bevel(bar, 0.4 * MM, segs=2, angle=35); finish(bar, sharp=35); setmat(bar, mat)
    riv = lathe('remache', S([(0.02, 0), (2.2, 0), (2.2, 0.35), (1.7, 0.85), (0.9, 1.15), (0.02, 1.1)]), segs=32)
    finish(riv, sharp=50); setmat(riv, mat)
    for k in range(NR):
        ang = 360.0 * k / NR + off
        b = bar if k == 0 else instance(bar, 'barra%d' % k)
        b.matrix_world = RZ(ang) if k > 0 else RZ(ang) @ b.matrix_world
        cage_objs.append(b)
        for sg in (1, -1):
            rv = instance(riv, 'rem')
            M = RZ(ang) @ T(66.75 * MM, 0, sg * 15.6 * MM)
            if sg < 0: M = M @ RX(180)
            rv.matrix_world = M
            cage_objs.append(rv)
    riv.matrix_world = T(0, 0, -50 * MM); riv.hide_render = True

elif variant == 'poliamida':
    mat = plastic('pa66', (0.025, 0.025, 0.027), rough=0.45, sss=0.0)
    pr = [(62.5, -16.4), (71.5, -16.4), (71.5, -12.0), (77, -12.0), (77, 12.0), (71.5, 12.0), (71.5, 16.4), (62.5, 16.4)]
    pr = fillet_poly(pr, n=4, radii=[0.9, 0.9, 0.6, 1.2, 1.2, 0.6, 0.9, 0.9])
    cage = lathe('jaula_pa', S(pr), segs=240)
    for k in range(NR):
        ang = 360.0 * k / NR
        c = cylinder('pk%d' % k, 12.7 * MM, -12.4 * MM, 12.4 * MM, segs=48)
        c.matrix_world = RZ(ang) @ T(RP * MM, 0, 0)
        cut(cage, c)
    bevel(cage, 0.5 * MM, segs=3, angle=35)
    finish(cage, sharp=38)
    setmat(cage, mat); cage_objs.append(cage)

else:  # acero: banda prensada con ventanas
    mat = steel('acero_jaula', color=(0.34, 0.35, 0.37), rough=0.38, aniso=0.2, noise=0.02)
    o = [(71.3, 0), (71.3, 12.5), (68.3, 14.2), (68.3, 16.2)]
    i = [(68.7, 0), (68.7, 12.5), (65.7, 14.2), (65.7, 16.2)]
    half = o + i[::-1]
    full = [(r, -z) for (r, z) in half[::-1] if not (z == 0)] + [(r, z) for (r, z) in half if not (z == 0)]
    # polígono cerrado: exterior de -16.2..16.2 y regreso por el interior
    ext = [(r, -z) for (r, z) in o[::-1]] + [(r, z) for (r, z) in o[1:]]
    itr = [(r, -z) for (r, z) in i[::-1]] + [(r, z) for (r, z) in i[1:]]
    poly = ext + itr[::-1]
    poly = fillet_poly(poly, n=3, radii=[0.6 if (k in (0, len(ext) - 1, len(ext), len(poly) - 1)) else 0.0 for k in range(len(poly))])
    cage = lathe('jaula_acero', S(poly), segs=240)
    for k in range(NR):
        ang = 360.0 * k / NR
        ol = fillet_poly([(-12.4, -12.4), (12.4, -12.4), (12.4, 12.4), (-12.4, 12.4)], n=4, radii=[2.2] * 4)
        # contorno (tangencial, axial) y prisma radial 62..76
        ol = [(x, z) for (x, z) in ol]
        cu = prism('vk%d' % k, S(ol), 60 * MM, 78 * MM, smooth=False)
        # prisma en Z -> hay que llevar su Z a radial X: eje local z->x, x->tang(y), y->axial(z)
        Mx = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
        cu.data.transform(Mx)
        cu.matrix_world = RZ(ang)
        cut(cage, cu)
    bevel(cage, 0.3 * MM, segs=2, angle=35)
    finish(cage, sharp=38)
    setmat(cage, mat); cage_objs.append(cage)

allobjs = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render]
for ob in allobjs:
    ob.matrix_world = RX(90) @ RZ(SPIN) @ ob.matrix_world

studio(az=-36, el=22, lens=90, margin=1.22)
render(out, res, smp)
