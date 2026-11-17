import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

out, res, smp = args()
reset(res, smp)

P = 12.7
TH = 1.5


def plate_outline(Rend, hw, nc=28, nw=14):
    h = P / 2
    # concave arc centre (0,c), radius rc: tangent externally to the end circles, waist at hw
    # (h^2 + c^2) = (Rend + rc)^2 , c - rc = hw
    c = (h * h + hw * hw - Rend * Rend - 2 * Rend * hw) / (2 * Rend) if False else None
    # solve: rc = c - hw ; h^2 + c^2 = (Rend + c - hw)^2 -> c = ((Rend-hw)^2 - h^2) / (-2*(Rend-hw)) ... numeric:
    k = Rend - hw
    c = (h * h - k * k) / (2 * k)
    rc = c - hw
    th = atan2(c, -h)  # angle from right-circle centre to top concave centre
    pts = []
    pts += arc(h, 0, Rend, -degrees_(th), degrees_(th), nc)
    a0 = atan2(-c, h)
    pts += arc(0, c, rc, degrees_(a0), degrees_(atan2(-c, -h)), nw)
    pts += arc(-h, 0, Rend, 180 - degrees_(th), 180 + degrees_(th), nc)
    pts += arc(0, -c, rc, degrees_(atan2(c, -h)), degrees_(atan2(c, h)), nw)
    # drop duplicate consecutive points
    res_ = []
    for p in pts:
        if not res_ or (abs(p[0] - res_[-1][0]) + abs(p[1] - res_[-1][1])) > 1e-6:
            res_.append(p)
    if (abs(res_[0][0] - res_[-1][0]) + abs(res_[0][1] - res_[-1][1])) < 1e-6:
        res_.pop()
    return res_, c, rc


def degrees_(a):
    return a * 180.0 / pi


def make_plate(name, Rend, hw):
    o, c, rc = plate_outline(Rend, hw)
    print(name, 'c', round(c, 3), 'rc', round(rc, 3), len(o))
    ob = prism(name, scale_pts(o), -TH / 2 * MM, TH / 2 * MM)
    bevel(ob, 0.25 * MM, segs=2, angle=35)
    finish(ob, sharp=40)
    return ob


pl_in = make_plate('placa_int', 6.0, 4.0)
pl_out = make_plate('placa_ext', 5.2, 3.6)

roller = cylinder('rodillo', 3.96 * MM, -3.9 * MM, 3.9 * MM, segs=64, chamfer=0.3 * MM)
finish(roller, sharp=40)

pr = [(0.01, -8.0), (0.8, -8.2), (1.75, -8.2), (2.15, -7.8), (2.15, -7.0), (1.98, -7.0),
      (1.98, 7.0), (2.15, 7.0), (2.15, 7.8), (1.75, 8.2), (0.8, 8.2), (0.01, 8.0)]
pin = lathe('pasador', [(r * MM, z * MM) for r, z in pr], segs=48)
finish(pin, sharp=50)

m_plate = steel('placa', color=(0.55, 0.56, 0.58), rough=0.32, noise=0.03)
m_roll = steel('rodillo', color=(0.62, 0.63, 0.65), rough=0.18, aniso=0.4, radial_axis='Z', noise=0.015)
m_pin = steel('pasador', color=(0.62, 0.63, 0.65), rough=0.28, aniso=0.4, radial_axis='Z', noise=0.02)
setmat(pl_in, m_plate); setmat(pl_out, m_plate); setmat(roller, m_roll); setmat(pin, m_pin)

# ---- trayectoria
r0, b = 17.0, 12.5
rad = lambda t: r0 + b * t / (2 * pi)
pt = lambda t: (rad(t) * cos(t), rad(t) * sin(t))
th = [0.0]
pts = [pt(0.0)]
tmax = 3.3 * 2 * pi
while th[-1] < tmax:
    t0 = th[-1]
    lo, hi = t0, t0 + 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        d = Vector(pt(mid)) - Vector(pt(t0))
        if d.length < P: lo = mid
        else: hi = mid
    th.append(hi); pts.append(pt(hi))
d = (Vector(pts[-1]) - Vector(pts[-2])).normalized()
ang_end = atan2(d.y, d.x)
for j in range(1, 5):
    pts.append(tuple(Vector(pts[-1]) + d * P))
if len(pts) % 2:
    pts.append(tuple(Vector(pts[-1]) + d * P))
rot = radians(-35) - ang_end
cr, sr = cos(rot), sin(rot)
pts = [(x * cr - y * sr, x * sr + y * cr) for x, y in pts]
print('pines', len(pts), 'eslabones', len(pts) - 1)

for i, p in enumerate(pts):
    ob = instance(roller); ob.matrix_world = T(p[0] * MM, p[1] * MM, 0)
    ob = instance(pin); ob.matrix_world = T(p[0] * MM, p[1] * MM, 0)

for i in range(len(pts) - 1):
    a = Vector(pts[i]); bb = Vector(pts[i + 1])
    mid = (a + bb) / 2
    ang = atan2((bb - a).y, (bb - a).x)
    M = T(mid.x * MM, mid.y * MM, 0) @ Matrix.Rotation(ang, 4, 'Z')
    if i % 2 == 0:
        src, zs = pl_in, (4.68, -4.68)
    else:
        src, zs = pl_out, (6.25, -6.25)
    for z in zs:
        ob = instance(src); ob.matrix_world = M @ T(0, 0, z * MM)

# ocultar fuentes (están en el origen; se mueven bajo el coil y estorbarían)
for s in (pl_in, pl_out, roller, pin):
    s.hide_render = True

cam, ctr, R = studio(az=-28, el=42, lens=85, margin=1.15, world=0.55, key=0.6, fill=0.8)
render(out, res, smp)
