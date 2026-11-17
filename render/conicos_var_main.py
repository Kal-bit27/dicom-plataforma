import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
import numpy as np

out, res, smp = args()
_a = sys.argv[sys.argv.index('--') + 1:]
variant = _a[3] if len(_a) > 3 else 'sencillo'
reset(res, smp)

# ---------------------------------------------------------------- materiales
M_RING = steel('anillo', color=(0.50, 0.51, 0.53), rough=0.2, aniso=0.6, noise=0.02, bands=0.05, band_scale=80.0, band_bump=0.2)
M_ROLL = steel('rodillo', color=(0.62, 0.63, 0.65), rough=0.08, noise=0.01)
M_CAGE = steel('jaula', color=(0.45, 0.46, 0.48), rough=0.35, noise=0.03)
M_SHELL = steel('copa', color=(0.50, 0.51, 0.53), rough=0.28, aniso=0.4, noise=0.025, bands=0.04, band_scale=80.0, band_bump=0.12)


# ---------------------------------------------------------------- utilidades
def prof_obj(name, pts_rz, radii, segs, n=5):
    prof = fillet_poly(pts_rz, n=n, radii=radii)
    return lathe(name, scale_pts(prof), segs=segs)


def cutter_boxes(name, Ms, sx, sy, z0, z1):
    """Una sola malla con una caja por cada matriz (ejes locales: x radial, y tangencial, z a lo largo)."""
    verts = []; faces = []
    for M in Ms:
        b = len(verts)
        for dx in (-1, 1):
            for dy in (-1, 1):
                for dz in (z0, z1):
                    verts.append(tuple(M @ Vector((dx * sx / 2, dy * sy / 2, dz))))
        faces += [(b + 0, b + 1, b + 3, b + 2), (b + 4, b + 6, b + 7, b + 5), (b + 0, b + 4, b + 5, b + 1),
                  (b + 2, b + 3, b + 7, b + 6), (b + 0, b + 2, b + 6, b + 4), (b + 1, b + 5, b + 7, b + 3)]
    return mesh_obj(name, verts, faces, smooth=False, merge=0)


def minz(objs):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    m = 1e9
    for ob in objs:
        ev = ob.evaluated_get(dg)
        me = ev.data
        n = len(me.vertices)
        co = np.empty(n * 3, dtype=np.float32)
        me.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)
        W = np.array(ev.matrix_world, dtype=np.float32)
        m = min(m, float((co @ W[:3, :3].T + W[:3, 3])[:, 2].min()))
    return m


def move(objs, M):
    for ob in objs:
        ob.matrix_world = M @ ob.matrix_world


def ground(objs):
    z = minz(objs)
    move(objs, T(0, 0, -z))


# ---------------------------------------------------------------- rodamiento de rodillos cónicos
def taper(P, name='cono', roller_phase=0.0):
    """Cono + rodillos + jaula + copa (mm). Eje Z, cara trasera (grande) del cono en z=0."""
    beta = radians(P['beta']); gam = radians(P['gam'])
    zA, rA, L, rhoL = P['zA'], P['rA'], P['L'], P['rhoL']
    cb, sb = cos(beta), sin(beta)
    N = P['N']
    A = lambda s: (zA + s * cb, rA - s * sb)
    rho = lambda s: rhoL - s * tan(gam)
    at = lambda s, off: (A(s)[0] + off * sb, A(s)[1] + off * cb)       # (z, r)
    inner = lambda s: at(s, -rho(s))
    outer = lambda s: at(s, rho(s))

    def r_at_z(f, z):
        p0 = f(0.0); p1 = f(L)
        return p0[1] + (z - p0[0]) * (p1[1] - p0[1]) / (p1[0] - p0[0])

    B = P['B']; rb = P['rb']
    # ---- cono
    C0 = inner(-0.45); R1 = (C0[0] + P['hrib'] * sb, C0[1] + P['hrib'] * cb)
    E = inner(L + 0.5); F = (E[0] + P['hfr'] * sb, E[1] + P['hfr'] * cb)
    assert F[0] < B - 0.2, (F, B)
    cone_pts = [(rb, 0, 0.7), (R1[1], 0, 1.1), (R1[1], R1[0], 0.7), (C0[1], C0[0], 0.9), (E[1], E[0], 0.7),
                (F[1], F[0], 0.4), (F[1], B, 0.7), (rb, B, 0.7)]
    cone = prof_obj(name + '_cono', [(p[0], p[1]) for p in cone_pts], [p[2] for p in cone_pts], 180)
    finish(cone, sharp=40)
    setmat(cone, M_RING)

    # ---- rodillos
    rp = [(0, 0, 0), (rhoL, 0, 0.7), (rhoL - L * tan(gam), L, 0.7), (0, L, 0)]
    r0 = prof_obj(name + '_rod', [(p[0], p[1]) for p in rp], [p[2] for p in rp], 56, n=4)
    finish(r0, sharp=50, wn=False)
    setmat(r0, M_ROLL)
    Ms = []
    for k in range(N):
        th = 360.0 * (k + roller_phase) / N
        Ms.append(RZ(th) @ T(rA * MM, 0, zA * MM) @ RY(-P['beta']))
    rollers = []
    for k, Mk in enumerate(Ms):
        ob = r0 if k == 0 else instance(r0, name + '_rod%d' % k)
        ob.matrix_world = Mk
        rollers.append(ob)

    # ---- jaula de chapa con ventanas
    def pt(s, off):
        z, r = at(s, off)
        return (r, z)
    loop = [pt(-0.7, 0.5), pt(L + 1.1, 0.5), pt(L + 1.1, -1.4), pt(L + 0.2, -1.4), pt(L + 0.2, -0.5), pt(-0.7, -0.5)]
    cage = lathe(name + '_jaula', scale_pts(loop), segs=N * 12, smooth=True)
    ww = P['win'] * 2 * (rhoL - L / 2 * tan(gam))
    cut(cage, cutter_boxes(name + '_vent', Ms, 14 * MM, ww * MM, 1.3 * MM, (L - 1.1) * MM))
    finish(cage, sharp=35)
    setmat(cage, M_CAGE)

    # ---- copa (separada)
    zc0, zc1, R = P['zc0'], P['zc1'], P['R']
    rl = r_at_z(outer, zc0); rs = r_at_z(outer, zc1)
    cup_info = dict(rl=rl, rs=rs)
    return dict(cone=cone, rollers=rollers, cage=cage, rl=rl, rs=rs, r_at_z=lambda z: r_at_z(outer, z), Ms=Ms)


def cup_single(P, tr, name='copa'):
    zc0, zc1, R = P['zc0'], P['zc1'], P['R']
    pts = [(tr['rl'], zc0, 0.7), (R, zc0, 1.1), (R, zc1, 1.1), (tr['rs'], zc1, 0.7)]
    cup = prof_obj(name, [(p[0], p[1]) for p in pts], [p[2] for p in pts], 220)
    finish(cup, sharp=40)
    setmat(cup, M_RING)
    return cup


P207 = dict(beta=13.3, gam=0.75, zA=3.4, rA=26.7, L=13.4, rhoL=4.09, N=17, B=17.0, rb=17.5,
            hrib=2.0, hfr=1.6, win=0.8, zc0=3.25, zc1=18.25, R=36.0)
P210 = dict(beta=13.5, gam=0.75, zA=4.2, rA=35.2, L=15.0, rhoL=4.3, N=18, B=20.0, rb=25.0,
            hrib=2.2, hfr=1.8, win=0.8, zc0=4.75, zc1=21.75, R=45.0)


# ---------------------------------------------------------------- agujas
def needle_set(name, rp, Dw, Lw, N, z_mid, z_half_win, cage_t=0.5, win=0.82, end_ring=1.1):
    prof = [(0, 0, 0), (Dw / 2, 0, 0.3), (Dw / 2, Lw, 0.3), (0, Lw, 0)]
    n0 = prof_obj(name + '_agu', [(p[0], p[1]) for p in prof], [p[2] for p in prof], 24, n=3)
    finish(n0, sharp=50, wn=False)
    setmat(n0, M_ROLL)
    objs = []
    Ms = []
    for k in range(N):
        th = 360.0 * k / N
        Mk = RZ(th) @ T(rp * MM, 0, (z_mid - Lw / 2) * MM)
        Ms.append(Mk)
        ob = n0 if k == 0 else instance(n0, name + '_agu%d' % k)
        ob.matrix_world = Mk
        objs.append(ob)
    zl0 = z_mid - Lw / 2 - 0.3; zl1 = z_mid + Lw / 2 + 0.3
    loop = [(rp + cage_t / 2, zl0), (rp + cage_t / 2, zl1), (rp - cage_t / 2, zl1), (rp - cage_t / 2, zl0)]
    cage = lathe(name + '_jaula', scale_pts(loop), segs=N * 12)
    cut(cage, cutter_boxes(name + '_vent', Ms, 6 * MM, Dw * win * MM, end_ring * MM + (z_mid - Lw / 2) * MM / MM * 0 + 0, 0))
    return n0, objs, cage, Ms


def needle_cage(name, rp, Dw, Lw, N, z_mid, t=0.5, win=0.8, ring=1.2):
    zl0 = z_mid - Lw / 2 - 0.15; zl1 = z_mid + Lw / 2 + 0.15
    loop = [(rp + t / 2, zl0), (rp + t / 2, zl1), (rp - t / 2, zl1), (rp - t / 2, zl0)]
    cage = lathe(name + '_jaula', scale_pts(loop), segs=N * 12)
    Ms = [RZ(360.0 * k / N) @ T(rp * MM, 0, 0) for k in range(N)]
    cut(cage, cutter_boxes(name + '_vent', Ms, 3 * MM, Dw * win * MM, (zl0 + ring) * MM, (zl1 - ring) * MM))
    finish(cage, sharp=35)
    setmat(cage, M_CAGE)
    return cage


def needles(name, rp, Dw, Lw, N, z_mid):
    prof = [(0, 0, 0), (Dw / 2, 0, 0.3), (Dw / 2, Lw, 0.3), (0, Lw, 0)]
    n0 = prof_obj(name + '_agu', [(p[0], p[1]) for p in prof], [p[2] for p in prof], 24, n=3)
    finish(n0, sharp=50, wn=False)
    setmat(n0, M_ROLL)
    objs = []
    for k in range(N):
        Mk = RZ(360.0 * (k + 0.5) / N) @ T(rp * MM, 0, (z_mid - Lw / 2) * MM)
        ob = n0 if k == 0 else instance(n0, name + '_agu%d' % k)
        ob.matrix_world = Mk
        objs.append(ob)
    return objs


# ================================================================ variantes
if variant == 'sencillo':
    tr = taper(P207, 'c')
    cup = cup_single(P207, tr)
    cone_g = [tr['cone'], tr['cage']] + tr['rollers']
    # cono apoyado sobre su cara grande, a la izquierda-delante
    move(cone_g, RZ(15))
    move(cone_g, T(-24 * MM, -12 * MM, 0))
    # copa de canto, a la derecha-detrás
    zm = (P207['zc0'] + P207['zc1']) / 2
    move([cup], T(0, 0, -zm * MM))
    move([cup], RY(90))                # eje -> X
    move([cup], RZ(-62))
    ground([cup])
    move([cup], T(31 * MM, 26 * MM, 0))
    cam, ctr, R = studio(az=-30, el=22, lens=90, margin=1.2)

elif variant == 'par_df':
    parts = []
    for i in range(2):
        tr = taper(P207, 'b%d' % i, roller_phase=0.5 * i)
        cup = cup_single(P207, tr, 'cu%d' % i)
        g = [tr['cone'], tr['cage'], cup] + tr['rollers']
        if i == 1:
            move(g, RY(180))
        parts += g
    zc0 = P207['zc0']
    sp = prof_obj('espaciador', [(31.6, -zc0, 0), (P207['R'], -zc0, 0), (P207['R'], zc0, 0), (31.6, zc0, 0)],
                  [0.5, 0.7, 0.7, 0.5], 200)
    finish(sp, sharp=40)
    setmat(sp, M_RING)
    parts.append(sp)
    move(parts, RZ(2) @ RX(90))
    ground(parts)
    cam, ctr, R = studio(az=-38, el=20, lens=90, margin=1.22)

elif variant == 'tdo':
    P = P210
    Wt = 50.0
    parts = []
    trs = []
    cones = []
    for i in range(2):
        tr = taper(P, 'd%d' % i, roller_phase=0.5 * i)
        trs.append(tr)
        g = [tr['cone'], tr['cage']] + tr['rollers']
        if i == 1:
            move(g, T(0, 0, Wt * MM) @ RY(180))
        parts += g
    tr = trs[0]
    zc0 = P['zc0']; T_ = P['zc1']; Rr = P['R']
    pts = [(tr['rl'], zc0, 0.7), (Rr, zc0, 1.1), (Rr, Wt - zc0, 1.1), (tr['rl'], Wt - zc0, 0.7),
           (tr['rs'], Wt - T_, 1.2), (tr['rs'], T_, 1.2)]
    cup = prof_obj('copa_doble', [(p[0], p[1]) for p in pts], [p[2] for p in pts], 240)
    hole = cylinder('agujero', 1.9 * MM, 0, 60 * MM, segs=32)
    move([hole], T(0, 0, 0))
    hole.matrix_world = T(0, 0, (Wt / 2) * MM) @ RX(-90)
    cut(cup, hole)
    bevel(cup, 0.3 * MM, segs=2, angle=40)
    finish(cup, sharp=40)
    setmat(cup, M_RING)
    parts.append(cup)
    move(parts, T(0, 0, -Wt / 2 * MM))
    move(parts, RZ(2) @ RX(90))
    # espaciador de cono suelto delante
    sp = prof_obj('espaciador_cono', [(25.0, 0, 0), (28.2, 0, 0), (28.2, 9.6, 0), (25.0, 9.6, 0)], [0.5, 0.7, 0.7, 0.5], 160)
    finish(sp, sharp=40)
    setmat(sp, M_RING)
    move([sp], T(0, 0, -4.8 * MM) @ RZ(0))
    move([sp], RX(90 - 18) if False else RX(90))
    move([sp], RZ(2))
    ground(parts)
    ground([sp])
    move([sp], T(46 * MM, -36 * MM, 0))
    cam, ctr, R = studio(az=-38, el=20, lens=90, margin=1.2)

elif variant == 'agujas':
    # --- HK2016 (casquillo embutido): Fw 20, D 26, C 16
    Cw = 16.0
    sh = [(13.0, 0.4, 0.4), (13.0, Cw - 0.4, 0.4), (12.5, Cw, 0.3), (10.9, Cw, 0.2), (10.9, Cw - 0.8, 0.2), (12.0, Cw - 0.8, 0.5),
          (12.0, 0.8, 0.5), (10.9, 0.8, 0.2), (10.9, 0, 0.2), (12.5, 0, 0.3)]
    shell = prof_obj('hk_casquillo', [(p[0], p[1]) for p in sh], [p[2] for p in sh], 160)
    finish(shell, sharp=40)
    setmat(shell, M_SHELL)
    ndl = needles('hk', 11.0, 2.0, 13.2, 18, Cw / 2)
    cg = needle_cage('hk', 11.0, 2.0, 13.2, 18, Cw / 2, t=0.45, win=0.8, ring=1.1)
    hk = [shell, cg] + ndl
    # --- NK 25/20: Fw 25, D 33, B 20
    Bw = 20.0
    rg = [(13.7, 0, 0.4), (16.5, 0, 0.9), (16.5, Bw, 0.9), (13.7, Bw, 0.4), (13.7, Bw - 1.9, 0.2), (15.0, Bw - 1.9, 0.2),
          (15.0, 1.9, 0.2), (13.7, 1.9, 0.2)]
    ring = prof_obj('nk_anillo', [(p[0], p[1]) for p in rg], [p[2] for p in rg], 200)
    finish(ring, sharp=40)
    setmat(ring, M_RING)
    nn = needles('nk', 13.75, 2.5, 15.6, 20, Bw / 2)
    cg2 = needle_cage('nk', 13.75, 2.5, 15.6, 20, Bw / 2, t=0.5, win=0.8, ring=1.3)
    nk = [ring, cg2] + nn
    for g, c in ((hk, Cw / 2), (nk, Bw / 2)):
        move(g, T(0, 0, -c * MM))
    TURN = -32
    move(hk, RZ(TURN) @ RX(90)); ground(hk); move(hk, T(-17 * MM, 4 * MM, 0))
    move(nk, RZ(TURN - 6) @ RX(90)); ground(nk); move(nk, T(20 * MM, -6 * MM, 0))
    cam, ctr, R = studio(az=-38, el=24, lens=100, margin=1.2)

render(out, res, smp)
