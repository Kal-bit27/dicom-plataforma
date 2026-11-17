import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

out, res, smp = args()
reset(res, smp)

# ---------------- materiales
sint = paint('sinterizado', (0.045, 0.047, 0.052), rough=0.5, bump=0.5, bump_scale=300.0, coat=0.0, metallic=0.35, bump_dist=0.002)
sint_c = steel('sint_corte', color=(0.12, 0.125, 0.135), rough=0.4, noise=0.03)
rojo = plastic('poliuretano', (0.78, 0.06, 0.03), rough=0.35, sss=0.06)
negro = steel('pavonado', color=(0.04, 0.04, 0.045), rough=0.35)
acero = steel('acero_buje', color=(0.42, 0.43, 0.45), rough=0.3, aniso=0.6, noise=0.02, bands=0.06, band_scale=80.0, band_bump=0.2)

RB = 11.0; RO = 32.5; LB = 21.0; JL = 15.0


def build_hub(tag):
    prof = fillet_poly([(RB, -LB), (RO, -LB), (RO, 0.0), (RB, 0.0)], n=2, radii=[0.8, 1.0, 0.6, 0.5])
    body = lathe('cuerpo' + tag, scale_pts(prof), segs=180)
    kw = box('cunero' + tag, 6 * MM, 8.8 * MM, 23 * MM, center=(0, 9.4 * MM, -10.5 * MM))
    cut(body, kw)
    op = cylinder('opresor' + tag, 3.0 * MM, 0, 40 * MM, segs=32)
    place(op, T(0, 0, -10.5 * MM), RX(-90))
    cut(body, op)
    bevel(body, 0.45 * MM, segs=2, angle=40)
    finish(body, sharp=42)
    setmat(body, sint)
    assign(body, [sint, sint_c], lambda c_, n_: 1 if sqrt(c_.x ** 2 + c_.y ** 2) < (RB + 3.1) * MM else 0)
    objs = [body]
    for k in range(3):
        c = 120.0 * k
        pts = arc(0, 0, RO, c - 19, c + 19, 14) + arc(0, 0, 17.0, c + 19, c - 19, 8)
        radii = [0.0] * len(pts)
        for i in (0, 14, 15, 23):
            radii[i] = 1.6
        pts = fillet_poly(pts, n=3, radii=radii)
        j = prism('garra%s%d' % (tag, k), scale_pts(pts), -0.4 * MM, JL * MM, smooth=False)
        bevel(j, 0.55 * MM, segs=3, angle=35)
        finish(j, sharp=42)
        setmat(j, sint)
        objs.append(j)
    ts = cylinder('prisionero' + tag, 2.8 * MM, 0, 6 * MM, segs=32, chamfer=0.4 * MM)
    hx = prism('hex' + tag, scale_pts(arc(0, 0, 1.6, 0, 300, 5)), 3.4 * MM, 8 * MM, smooth=False)
    cut(ts, hx)
    finish(ts, sharp=30)
    place(ts, T(0, 0, -10.5 * MM), RX(-90), T(0, 0, (RO - 1.8 - 6.0) * MM))
    setmat(ts, negro)
    objs.append(ts)
    return objs


hubA = build_hub('A')
hubB = build_hub('B')

# ---------------- araña (spider)
pts = []; radii = []
for k in range(6):
    c = 30.0 + 60.0 * k
    o = arc(0, 0, 31.5, c - 10, c + 10, 8)
    i_ = arc(0, 0, 17.5, c + 10 + 0.0, c + 50, 8)
    radii += [1.6] + [0.0] * 7 + [1.6] + [1.4] + [0.0] * 7 + [1.4]
    pts += o + i_
pts = fillet_poly(pts, n=3, radii=radii)
spider = prism('arana', scale_pts(pts), 2 * MM, 15 * MM, smooth=False)
bevel(spider, 0.8 * MM, segs=3, angle=35)
finish(spider, sharp=42)
setmat(spider, rojo)

# colocar en el acoplamiento
Mc = T(0, 0, 0) @ RZ(8) @ RY(90) @ RZ(90) @ T(0, 0, -8.5 * MM)
MB = T(0, 0, 17 * MM) @ RY(180)
for ob in hubA + [spider]:
    ob.matrix_world = Mc @ ob.matrix_world
for ob in hubB:
    ob.matrix_world = Mc @ MB @ ob.matrix_world
coup = hubA + hubB + [spider]

# ---------------- buje cónico
Lh = 16.0
prof = fillet_poly([(15.0, -Lh), (32.75, -Lh), (35.0, Lh), (15.0, Lh)], n=2, radii=[0.8, 1.0, 1.0, 0.8])
buje = lathe('buje', scale_pts(prof), segs=200)
kw = box('cunero_b', 8 * MM, 10.3 * MM, 34 * MM, center=(0, 13.15 * MM, 0))
cut(buje, kw)
sl = box('ranura', 3 * MM, 35 * MM, 34 * MM, center=(0, -27.5 * MM, 0))
cut(buje, sl)
for a in (0.0, 180.0, 125.0):
    h_ = cylinder('medio%d' % a, 5.5 * MM, -4 * MM, 17 * MM, segs=40)
    place(h_, T(35 * MM * cos(radians(a)), 35 * MM * sin(radians(a)), 0))
    cut(buje, h_)
bevel(buje, 0.4 * MM, segs=2, angle=40)
finish(buje, sharp=42)
setmat(buje, acero)

# rotar: z local -> horizontal hacia la cámara, cuñero arriba
d = Vector((-0.74, -0.67, 0.0))
xx = Vector((-d.y, d.x, 0.0)); yy = Vector((0, 0, 1.0))
R3 = Matrix(((xx.x, yy.x, d.x, 0), (xx.y, yy.y, d.y, 0), (xx.z, yy.z, d.z, 0), (0, 0, 0, 1)))
buje.matrix_world = R3 @ RZ(20) @ buje.matrix_world

# posiciones sobre el piso
left = Vector((-0.87, 0.5, 0)); fw = Vector((0.5, 0.87, 0))
pc = left * 44 * MM + fw * 30 * MM
pb = -left * 38 * MM - fw * 22 * MM
for ob in coup:
    ob.matrix_world = T(*pc) @ ob.matrix_world
buje.matrix_world = T(*pb) @ buje.matrix_world
bpy.context.view_layer.update()
for grp in (coup, [buje]):
    mn, mx = bounds(grp)
    for ob in grp:
        ob.matrix_world = T(0, 0, -mn.z) @ ob.matrix_world

studio(az=-30, el=22, lens=85, margin=1.2)
render(out, res, smp)
