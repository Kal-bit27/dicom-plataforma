import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

out, res, smp = args()
reset(res, smp)

# ---- catarina paso 5/8" (ANSI 50), 19 dientes, tipo B (con maza)
P = 15.875; Dr = 10.16; N = 19; h = 4.35
Rp = P / (2 * sin(pi / N))
Ro = P * (0.6 + 1 / tan(pi / N)) / 2
rs = 0.505 * Dr + 0.04
gam = radians(25.0)
phi0 = pi / 2 - gam
Rb = 12.7; Rh = 35.0; zf = h + 23.0; r_in = 30.0

# contorno de un paso (hueco k centrado en theta_k)
def gap(theta):
    er = (cos(theta), sin(theta)); et = (-sin(theta), cos(theta))
    def pt(u, v):
        return ((Rp + v) * er[0] + u * et[0], (Rp + v) * er[1] + u * et[1])
    u0 = rs * sin(phi0); v0 = -rs * cos(phi0)
    # donde el flanco corta el diámetro exterior
    a = 1.0; b = 2 * ((Rp + v0) * cos(gam) + u0 * sin(gam)); c = (Rp + v0) ** 2 + u0 ** 2 - Ro ** 2
    s = (-b + sqrt(b * b - 4 * a * c)) / 2
    ut = u0 + s * sin(gam); vt = v0 + s * cos(gam)
    pts = [(pt(-ut, vt), 0.9)]
    for k in range(13):
        ph = -phi0 + 2 * phi0 * k / 12
        pts.append((pt(rs * sin(ph), -rs * cos(ph)), 0.0))
    pts.append((pt(ut, vt), 0.9))
    return pts

raw = []
for k in range(N):
    raw += gap(2 * pi * k / N)
outline = fillet_poly([p[0] for p in raw], n=4, radii=[p[1] for p in raw])
m = len(outline)

# capas en z: los dientes se adelgazan hacia la punta con un arco
r0 = Rp - 1.2
dz = h - 2.1
rho = ((Ro - r0) ** 2 + dz ** 2) / (2 * dz)
def rmax(z):
    z = abs(z)
    if z <= 2.1:
        return Ro + 5
    return r0 + sqrt(max(0.0, rho ** 2 - (rho - (h - z)) ** 2))

zs = [-h + (h - 2.1) * q for q in (0.0, 0.06, 0.16, 0.3, 0.46, 0.64, 0.82, 1.0)]
zs = zs + [-z for z in reversed(zs)]

def ring(z):
    rm = rmax(z)
    out_ = []
    for (x, y) in outline:
        r = sqrt(x * x + y * y)
        f = min(1.0, rm / r)
        out_.append((x * f * MM, y * f * MM, z * MM))
    return out_

inner = lambda z: [(r_in * x / sqrt(x * x + y * y) * MM, r_in * y / sqrt(x * x + y * y) * MM, z * MM) for (x, y) in outline]
rings = [inner(-h)] + [ring(z) for z in zs] + [inner(h)]
plato = loft('plato', rings, closed_u=True)
bevel(plato, 0.3 * MM, segs=2, angle=32)
finish(plato, sharp=38)

# ---- maza
Pm = [(Rb, -h, 0.6), (33.0, -h, 0.0), (33.0, 2.0, 0.0), (Rh + 3.0, 2.0, 0.0), (Rh + 3.0, h - 0.05, 0.0),
      (Rh, h - 0.05, 2.2), (Rh, zf, 1.4), (Rb, zf, 0.9)]
prof = fillet_poly([(p[0], p[1]) for p in Pm], n=6, radii=[p[2] for p in Pm])
maza = lathe('maza', scale_pts(prof), segs=200)
kw = box('cunero', 6.35 * MM, (Rb + 3.2) * MM, 120 * MM, center=(0, (Rb + 3.2) / 2 * MM, 0))
cut(maza, kw)
zo = h + 12.0
for i, ang in enumerate((0, -90)):
    op = cylinder('opresor%d' % i, 3.6 * MM, 0, 60 * MM, segs=36)
    place(op, RZ(ang), T(0, 0, zo * MM), RX(-90), T(0, 0, (Rb + 6.5) * MM))
    cut(maza, op)
bevel(maza, 0.35 * MM, segs=2, angle=38)
finish(maza, sharp=42)

pris = []
for i, ang in enumerate((0, -90)):
    ts = cylinder('prisionero%d' % i, 3.5 * MM, 0, 7 * MM, segs=36, chamfer=0.45 * MM)
    hx = prism('hex%d' % i, scale_pts(arc(0, 0, 2.0, 0, 300, 5)), 3.6 * MM, 8 * MM, smooth=False)
    cut(ts, hx)
    finish(ts, sharp=30)
    place(ts, RZ(ang), T(0, 0, zo * MM), RX(-90), T(0, 0, (Rh - 8.5) * MM))
    pris.append(ts)

# ---- materiales
acero = steel('acero_cat', color=(0.56, 0.57, 0.585), rough=0.24, aniso=0.55, noise=0.02, bands=0.06, band_scale=80.0,
              band_bump=0.2, tint=(0.19, 0.2, 0.225), tint_from=(Rp - Dr / 2 - 2.5) * MM, tint_to=(Rp - Dr / 2 + 2.0) * MM)
acero_m = steel('acero_maza', color=(0.58, 0.59, 0.605), rough=0.22, aniso=0.6, noise=0.02, bands=0.06, band_scale=80.0,
                band_bump=0.2)
negro = steel('pavonado', color=(0.045, 0.045, 0.05), rough=0.33)
liso = steel('acero_liso', color=(0.5, 0.51, 0.525), rough=0.3, noise=0.03)
setmat(plato, acero)
assign(maza, [acero_m, liso], lambda c_, n_: 1 if (abs(c_.x) < 3.3 * MM and Rb * 0.9 * MM < c_.y < (Rb + 3.4) * MM and abs(n_.z) < 0.5) else 0)
for t in pris:
    setmat(t, negro)

rot = 360.0 * 5 / N - 90.0 + 90.0
for ob in [plato, maza] + pris:
    ob.matrix_world = RX(90) @ RZ(-85.26) @ ob.matrix_world

cam, ctr, R = studio(az=-34, el=13, lens=90, margin=1.25)
render(out, res, smp)
