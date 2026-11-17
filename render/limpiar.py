"""Pasa a limpio: fondo blanco puro, recorte con margen parejo, cuadrado, WebP."""
import sys, numpy as np
from PIL import Image, ImageFilter
def limpiar(src, dst, size=900, margin=0.08, shadow_keep=True):
    im = Image.open(src)
    if im.mode == 'RGBA':
        x = np.asarray(im).astype(np.float32)
        al = x[..., 3]; sh = x[..., :3].max(axis=2) < 10
        al = np.where(sh, np.clip((al - 34) / (255 - 34), 0, 1) ** 1.15 * 255 * 0.9, al)
        x[..., 3] = al
        im = Image.fromarray(x.astype(np.uint8), 'RGBA')
        b = Image.new('RGBA', im.size, (255, 255, 255, 255)); b.alpha_composite(im); im = b
    im = im.convert('RGB')
    a = np.asarray(im).astype(np.float32)
    # niveles: lo que ya es casi blanco pasa a blanco puro, sin tocar sombras suaves
    lo, hi = 236.0, 251.0
    m = a.min(axis=2, keepdims=True)
    t = np.clip((m - lo) / (hi - lo), 0, 1)
    t = t * t * (3 - 2 * t)
    a = a + (255 - a) * t
    a = np.clip(a, 0, 255)
    # caja del contenido (incluye sombra tenue)
    mask = a.min(axis=2) < 246
    ys, xs = np.where(mask)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    w, h = x1 - x0, y1 - y0
    side = int(max(w, h) * (1 + 2 * margin))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    canvas = Image.new('RGB', (side, side), (255, 255, 255))
    crop = Image.fromarray(a.astype(np.uint8)).crop((x0, y0, x1 + 1, y1 + 1))
    canvas.paste(crop, (int(side / 2 - w / 2), int(side / 2 - h / 2)))
    out = canvas.resize((size, size), Image.LANCZOS)
    out.save(dst, 'WEBP', quality=86, method=6)
    print(dst, (w, h), '->', size)
if __name__ == '__main__':
    limpiar(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 900, float(sys.argv[4]) if len(sys.argv) > 4 else 0.08)
