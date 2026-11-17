import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
import numpy as np

out, res, smp = args()
a = sys.argv[sys.argv.index('--') + 1:]
variant = a[3] if len(a) > 3 else 'esf_laton'
SPIN = float(a[4]) if len(a) > 4 else 0.0
reset(res, smp)

NR = 18; HB = 18.5
TILT = float(os.environ.get('TILT','13'))
RC, ZC = 55.0, 9.6           # centro del rodillo (fila z>0)
CL = math.hypot(RC, ZC)
PHI = math.atan2(ZC, RC)     # ángulo de contacto
sp, cp = sin(PHI), cos(PHI)
Rr = 6.4                     # radio máx. del rodillo
RS = CL + Rr + 0.08          # esfera de la pista exterior
LH = 9.0                     # semilongitud del rodillo
tdir = (-sp, cp); ndir = (cp, sp)

def S(pts): return scale_pts(pts)

def rho(s):
    P = (RC + s * tdir[0], ZC + s * tdir[1])
    pn = P[0] * ndir[0] + P[1] * ndir[1]
    return -pn + sqrt(pn * pn - (P[0] ** 2 + P[1] ** 2) + RS * RS)

def to_rz(s, n):
    return (RC + s * tdir[0] + n * ndir[0], ZC + s * tdir[1] + n * ndir[1])

# ---- aro exterior: pista esférica, ranura de lubricación
bore = lambda z: sqrt(RS * RS - z * z)
zs = np.linspace(HB, -HB, 25)
bore_pts = [(bore(z), z) for z in zs]
pts = [(70, -HB)] + [(70, -3.0), (67.4, -3.0), (67.4, 3.0), (70, 3.0)] + [(70, HB)] + bore_pts + []
rad = [1.4, 0.5, 0.9, 0.9, 0.5, 1.4] + [1.0] + [0.0] * 23 + [1.0]
outer = lathe('aro_ext', S(fillet_poly(pts, n=5, radii=rad)), segs=240)
for k in range(3):
    c = cylinder('orif%d' % k, 2.4 * MM, 60 * MM, 75 * MM, segs=32)
    c.matrix_world = RZ(115 + 120 * k) @ RY(90)
    cut(outer, c)
finish(outer, sharp=40)

# ---- aro interior (pistas inclinadas; sin rebordes)
def bis(f, a, b):
    for _ in range(50):
        m = (a + b) / 2
        if (f(a) > 0) == (f(m) > 0): a = m
        else: b = m
    return (a + b) / 2
zin = lambda s: to_rz(s, -rho(s))[1]
s0 = bis(lambda s: zin(s) - 0.4, -14, 0)
s1 = bis(lambda s: zin(s) - 15.4, 0, 14)
ss = np.linspace(s0, s1, 22)
C = [(to_rz(s, -rho(s))) for s in ss]
rE = C[-1][0]
up = [(C[0][0], 0.4)] + C + [(rE - 0.9, 18.5), (40, 18.5)]
low = [(r, -z) for (r, z) in up[::-1]]
poly = [(40, -18.5)] + [(r, -z) for (r, z) in up[::-1][1:]] if False else None
poly = [(40, -18.5), (rE - 0.9, -18.5)] + [(r, -z) for (r, z) in C[::-1]] + [(C[0][0], -0.4)] + [(C[0][0], 0.4)] + C + [(rE - 0.9, 18.5), (40, 18.5)]
rad = [1.0, 0.4] + [0.0] * len(C) + [0.0, 0.0] + [0.0] * len(C) + [0.4, 1.0]
inner = lathe('aro_int', S(fillet_poly(poly, n=4, radii=rad)), segs=240)
finish(inner, sharp=40)
r_ridge = C[0][0]

# ---- rodillo barril
sr = np.linspace(-LH, LH, 31)
pr = [(0.02, -LH), (rho(-LH) - 0.9, -LH), (rho(-LH) - 0.06, -LH + 0.8)]
pr += [(rho(s) - 0.06, s) for s in sr[2:-2]]
pr += [(rho(LH) - 0.06, LH - 0.8), (rho(LH) - 0.9, LH), (0.02, LH)]
rol = lathe('rodillo', S(pr), segs=64)
finish(rol, sharp=40)

mat_ring = steel('anillo', color=(0.40, 0.41, 0.43), rough=0.2, aniso=0.6, noise=0.02, bands=0.08, band_bump=0.25)
mat_rol = steel('rodillo', color=(0.40, 0.41, 0.43), rough=0.13, noise=0.01)
setmat(outer, mat_ring); setmat(inner, mat_ring); setmat(rol, mat_rol)

def row_matrix(row, az):
    """matriz mundo para el sistema local (X = eje del rodillo, Y tang., Z = normal radial) de una fila."""
    fr = Matrix(((tdir[0], 0, ndir[0], 0), (0, -1, 0, 0), (tdir[1], 0, ndir[1], 0), (0, 0, 0, 1)))
    M = RZ(az) @ T(RC * MM, 0, ZC * MM) @ fr
    return RX(180) @ M if row < 0 else M

stag = 0.5 * 360.0 / NR
# rodillo: su eje local Z -> eje del rodillo; usamos RY(-phi)
def roll_matrix(row, az):
    M = RZ(az) @ T(RC * MM, 0, ZC * MM) @ RY(-math.degrees(PHI))
    return RX(180) @ M if row < 0 else M
first = True
for row in (1, -1):
    for k in range(NR):
        az = 360.0 * k / NR + (stag if row < 0 else 0)
        if first:
            ob = rol; first = False
        else:
            ob = instance(rol, 'rod')
        ob.matrix_world = roll_matrix(row, az)

cage = []
cm = None
if variant == 'esf_laton':
    cm = steel('laton', color=(0.85, 0.62, 0.28), rough=0.22, aniso=0.3, noise=0.015, bands=0.04, band_bump=0.1)
    pr = fillet_poly([(r_ridge + 0.3, -2.4), (59.5, -2.4), (59.5, 2.4), (r_ridge + 0.3, 2.4)], n=4, radii=[0.4, 0.8, 0.8, 0.4])
    ring = lathe('anillo_c', S(pr), segs=160); finish(ring, sharp=40); setmat(ring, cm)
    prong = box('diente', 10.4 * MM, 5.2 * MM, 16.1 * MM, center=(0.5 * MM, 0, ((7.7 - 8.4) / 2) * MM))
    bevel(prong, 0.45 * MM, segs=2, angle=35); finish(prong, sharp=35); setmat(prong, cm)
    firstp = True
    for row in (1, -1):
        for k in range(NR):
            az = 360.0 * k / NR + (stag if row < 0 else 0) + 180.0 / NR
            ob = prong if firstp else instance(prong, 'dte')
            firstp = False
            ob.matrix_world = roll_matrix(row, az)
            # desplazar a la posición tangencial intermedia: el origen local ya está en el eje del rodillo; moverlo medio paso
            Mp = RZ(az) @ T(RC * MM, 0, 0) @ Matrix.Identity(4)
            ob.matrix_world = (RX(180) if row < 0 else Matrix.Identity(4)) @ RZ(az) @ T(RC * MM, 0, ZC * MM) @ RY(-math.degrees(PHI))
else:
    cm = steel('acero_jaula', color=(0.28, 0.285, 0.30), rough=0.45, aniso=0.2, noise=0.02)
    pb = [to_rz(-7.7, -1.1), to_rz(7.7, -1.1), to_rz(7.7, 1.1), to_rz(-7.7, 1.1)]
    pb = fillet_poly(pb, n=3, radii=[0.5, 0.5, 0.5, 0.5])
    band = lathe('jaula', S(pb), segs=240)
    for k in range(NR):
        ol = fillet_poly([(-7.3, -8.0), (7.3, -8.0), (7.3, 8.0), (-7.3, 8.0)], n=4, radii=[1.8] * 4)
        cu = prism('vk%d' % k, S(ol), -5 * MM, 5 * MM, smooth=False)
        # local: x = eje del rodillo (s), y = tangencial, z = normal
        fr = Matrix(((tdir[0], 0, ndir[0], 0), (0, -1, 0, 0), (tdir[1], 0, ndir[1], 0), (0, 0, 0, 1)))
        cu.matrix_world = RZ(360.0 * k / NR) @ T(RC * MM, 0, ZC * MM) @ fr
        cut(band, cu)
    bevel(band, 0.25 * MM, segs=2, angle=35)
    finish(band, sharp=38); setmat(band, cm)
    b2 = instance(band, 'jaula2')
    # la segunda jaula: espejo en Z y desfasada medio paso
    b2.matrix_world = RX(180) @ RZ(stag)
    pr = fillet_poly([(r_ridge + 0.3, -1.0), (54.4, -1.0), (54.4, 1.0), (r_ridge + 0.3, 1.0)], n=4, radii=[0.4, 0.5, 0.5, 0.4])
    ring = lathe('anillo_g', S(pr), segs=160); finish(ring, sharp=40); setmat(ring, cm)

allobjs = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render]
for ob in allobjs:
    t = Matrix.Identity(4) if ob is outer else RY(TILT)
    ob.matrix_world = RX(90) @ RZ(SPIN) @ t @ ob.matrix_world

studio(az=float(os.environ.get('AZ','-15')), el=float(os.environ.get('EL','10')), lens=90, margin=1.22)
render(out, res, smp)
