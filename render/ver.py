import sys
from PIL import Image
src, dst = sys.argv[1], sys.argv[2]
bg = (255, 255, 255) if len(sys.argv) < 4 else tuple(int(v) for v in sys.argv[3].split(','))
im = Image.open(src).convert('RGBA')
base = Image.new('RGBA', im.size, bg + (255,))
base.alpha_composite(im)
base.convert('RGB').save(dst, quality=92)
print(dst, im.size)
