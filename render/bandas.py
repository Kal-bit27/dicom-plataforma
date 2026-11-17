import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

out, res, smp = args()
reset(res, smp)

# ---- sección B (mm): x radial (+ hacia afuera), z altura
def section(r=1.0):
    P = [(5.5, -8.5), (5.5, 8.5), (-5.5, 4.5), (-5.5, -4.5)]
    return fillet_poly(P, n=4, radii=[r, r, r, r])

SEC = section(1.0)
NP = len(SEC)

def smooth01(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)

def make_path(a, b, ex, rot, off, wob, N):
    dense = []
    M = 6000
    for i in range(M):
        t = 2 * pi * i / M
        c, s = cos(t), sin(t)
        k = 1 + wob[0] * cos(2 * t + wob[1]) + wob[2] * cos(3 * t + wob[3])
        x = a * k * (abs(c) ** (2 / ex)) * (1 if c >= 0 else -1)
        y = b * k * (abs(s) ** (2 / ex)) * (1 if s >= 0 else -1)
        ca, sa = cos(radians(rot)), sin(radians(rot))
        dense.append((x * ca - y * sa + off[0], x * sa + y * ca + off[1]))
    cum = [0.0]
    for i in range(M):
        j = (i + 1) % M
        cum.append(cum[-1] + math.hypot(dense[j][0] - dense[i][0], dense[j][1] - dense[i][1]))
    L = cum[-1]
    pts = []
    j = 0
    for i in range(N):
        tgt = L * i / N
        while cum[j + 1] < tgt:
            j += 1
        f = (tgt - cum[j]) / (cum[j + 1] - cum[j])
        p0 = dense[j]; p1 = dense[(j + 1) % M]
        pts.append((p0[0] + (p1[0] - p0[0]) * f, p0[1] + (p1[1] - p0[1]) * f))
    return pts, L

def belt(name, a, b, ex, rot, off, wob, zc, cogs=0, N=420):
    if cogs:
        # número entero de dientes con paso ~10 mm
        pts0, L = make_path(a, b, ex, rot, off, wob, 600)
        cogs = int(round(L / 10.0))
        N = cogs * 14
    pts, L = make_path(a, b, ex, rot, off, wob, N)
    rings = []
    for i in range(N):
        p = pts[i]; q = pts[(i + 1) % N]; o = pts[i - 1]
        tx, ty = q[0] - o[0], q[1] - o[1]
        l = math.hypot(tx, ty); tx /= l; ty /= l
        nx, ny = ty, -tx
        w = 0.0
        if cogs:
            u = (i / N) * cogs
            c = cos(2 * pi * u)
            w = smooth01(0.15, 0.85, 0.5 - 0.5 * c)   # 1 en el hueco; 0 en el diente
            w = 1 - smooth01(0.0, 1.0, 0.5 + 0.5 * c) * 0 if False else w
        ring = []
        for (x, z) in SEC:
            xx = x
            if cogs and x < 0:
                xx = x + 4.5 * w * smooth01(0.0, 5.0, -x) * (1.0 if True else 0)
            ring.append(((p[0] + nx * xx) * MM, (p[1] + ny * xx) * MM, (zc + z) * MM))
        rings.append(ring)
    ob = loft(name, rings, closed_u=True)
    return ob

# tres lazos, apilados a ~17 mm
b1 = belt('b1', 96, 105, 2.4, 12, (0, 0), (0.012, 0.5, 0.008, 1.7), 8.5)
b2 = belt('b2', 94, 102, 2.3, -9, (5, -4), (0.010, 2.1, 0.010, 0.4), 25.5)
b3 = belt('b3', 92, 100, 2.35, 31, (-4, 6), (0.008, 1.0, 0.007, 2.6), 42.5, cogs=1)

# ---- materiales
def belt_mat(name, tela=True, rough=0.62):
    m = rubber(name, color=(0.008, 0.008, 0.009), rough=rough, bump=0.0, sheen=0.08)
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 500.0 if tela else 350.0
    nz.inputs['Detail'].default_value = 4.0
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    h = nz.outputs['Fac']
    if tela:
        mp = nt.nodes.new('ShaderNodeMapping')
        mp.inputs['Rotation'].default_value = (0, 0, radians(45))
        mp.inputs['Scale'].default_value = (1, 1, 1)
        nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
        tot = None
        for k, rz in enumerate((0, 90)):
            m2 = nt.nodes.new('ShaderNodeMapping')
            m2.inputs['Rotation'].default_value = (0, 0, radians(45 + rz))
            nt.links.new(tc.outputs['Object'], m2.inputs['Vector'])
            wv = nt.nodes.new('ShaderNodeTexWave')
            wv.wave_type = 'BANDS'; wv.bands_direction = 'X'; wv.wave_profile = 'SIN'
            wv.inputs['Scale'].default_value = 260.0
            wv.inputs['Distortion'].default_value = 0.4
            wv.inputs['Detail'].default_value = 0.0
            nt.links.new(m2.outputs['Vector'], wv.inputs['Vector'])
            ad = nt.nodes.new('ShaderNodeMath'); ad.operation = 'ADD'
            if tot is None:
                ad.inputs[0].default_value = 0.0
            else:
                nt.links.new(tot, ad.inputs[0])
            nt.links.new(wv.outputs['Fac'], ad.inputs[1])
            tot = ad.outputs[0]
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'FLOAT'
        mx.inputs['Factor'].default_value = 0.5
        nt.links.new(tot, mx.inputs['A']); nt.links.new(nz.outputs['Fac'], mx.inputs['B'])
        h = mx.outputs['Result']
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.45 if tela else 0.2
    bp.inputs['Distance'].default_value = 0.0008
    nt.links.new(h, bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m

tela = belt_mat('tela', True, 0.6)
corte = belt_mat('corte', False, 0.7)
setmat(b1, tela); setmat(b2, tela); setmat(b3, corte)

cam, ctr, R = studio(az=-30, el=34, lens=85, margin=1.2)
render(out, res, smp)
