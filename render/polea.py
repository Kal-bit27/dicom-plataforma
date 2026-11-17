import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

out, res, smp = args()
reset(res, smp)

# ---- medidas (mm): polea de dos canales tipo B
Rb = 12.7; Rh0 = 29.0; Rh1 = 26.5; zh = 26.0; tw = 5.5
Rri0 = 56.0; Rri1 = 58.0; zr = 22.0; Ro = 80.0
d = 16.0; wt = 8.25; wb = 2.74; zc = 9.5

P = [
    (Rb, -zh, 0.9), (Rh1, -zh, 1.6), (Rh0, -tw, 5.0), (Rri0, -tw, 5.0), (Rri1, -zr, 1.3), (Ro, -zr, 0.9),
    (Ro, -zc - wt, 0.45), (Ro - d, -zc - wb, 1.1), (Ro - d, -zc + wb, 1.1), (Ro, -zc + wt, 0.4),
    (Ro, zc - wt, 0.4), (Ro - d, zc - wb, 1.1), (Ro - d, zc + wb, 1.1), (Ro, zc + wt, 0.45),
    (Ro, zr, 0.9), (Rri1, zr, 1.3), (Rri0, tw, 5.0), (Rh0, tw, 5.0), (Rh1, zh, 1.6), (Rb, zh, 0.9),
]
prof = fillet_poly([(p[0], p[1]) for p in P], n=6, radii=[p[2] for p in P])
body = lathe('polea', scale_pts(prof), segs=220)

# ---- aligeramientos: cinco ventanas que dejan cinco rayos
NS = 5; half = 180.0 / NS; sw = 7.5; r_in = 35.0; r_out = 50.5
ao = half - math.degrees(asin(sw / r_out)); ai = half - math.degrees(asin(sw / r_in))
for k in range(NS):
    c = 360.0 * k / NS + 90 + half
    pts = arc(0, 0, r_out, c - ao, c + ao, 14) + arc(0, 0, r_in, c + ai, c - ai, 10)
    radii = [0.0] * len(pts)
    radii[0] = radii[14] = 5.5
    radii[15] = radii[25] = 4.5
    pts = fillet_poly(pts, n=6, radii=radii)
    cu = prism('vent%d' % k, scale_pts(pts), -20 * MM, 20 * MM, smooth=False)
    cut(body, cu)

# ---- cuñero y opresor
kw = box('cunero', 6.35 * MM, (Rb + 3.3) * MM, 80 * MM, center=(0, (Rb + 3.3) / 2 * MM, 0))
cut(body, kw)
op = cylinder('opresor', 3.3 * MM, 0, 40 * MM, segs=32)
place(op, T(0, 0, 16 * MM), RX(-90))
cut(body, op)

bevel(body, 0.55 * MM, segs=3, angle=38)
finish(body, sharp=42)

# tornillo opresor (allen) dentro del barreno
ts = cylinder('prisionero', 3.2 * MM, 0, 6 * MM, segs=32, chamfer=0.4 * MM)
hx = prism('hex', scale_pts(arc(0, 0, 1.75, 0, 300, 5)), 3.2 * MM, 7 * MM, smooth=False)
cut(ts, hx)
finish(ts, sharp=30)
place(ts, T(0, 0, 16 * MM), RX(-90), T(0, 0, (Rh0 - 8.2) * MM))

# ---- materiales
torneado = steel('torneado', color=(0.27, 0.275, 0.287), rough=0.25, aniso=0.6, noise=0.02, bands=0.07, band_scale=70.0, band_bump=0.25)
fundido = paint('fundido', (0.016, 0.018, 0.021), rough=0.46, bump=0.9, bump_scale=230.0, coat=0.1)
negro = steel('pavonado', color=(0.05, 0.05, 0.055), rough=0.35)


def cual(c, n):
    r = sqrt(c.x * c.x + c.y * c.y) / MM
    z = abs(c.z) / MM
    if r > Rri1 + 0.9:
        return 0
    if z > zh - 1.4:
        return 0
    if r < Rb + 3.6:
        return 0
    return 1


assign(body, [torneado, fundido], cual)
setmat(ts, negro)

for ob in (body, ts):
    ob.matrix_world = RX(90) @ RZ(-28) @ ob.matrix_world

cam, ctr, R = studio(az=-36, el=16, lens=90, margin=1.25)
render(out, res, smp)
