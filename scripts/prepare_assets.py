"""
Prepare assets: convert any WhatsApp image in assets/ to app.png and app.ico
Run with the project virtualenv python.
"""
from PIL import Image
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
assets = os.path.join(ROOT, 'assets')
# Find candidate image
candidates = [f for f in os.listdir(assets) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.svg'))]
if not candidates:
    print('No image found in assets/ to convert. Place your logo in assets/ then run this script.')
    raise SystemExit(1)

# Prefer whatsapp file if present
src_name = None
for name in candidates:
    if 'whatsapp' in name.lower() or 'logo' in name.lower() or 'alert' in name.lower():
        src_name = name
        break
if src_name is None:
    src_name = candidates[0]

src = os.path.join(assets, src_name)
dst_png = os.path.join(assets, 'app.png')
dst_ico = os.path.join(assets, 'app.ico')
print('Using source:', src)

im = Image.open(src)
if im.mode not in ('RGBA','RGB'):
    im = im.convert('RGBA')

im.save(dst_png)
print('Saved', dst_png)

sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)]
im.save(dst_ico, format='ICO', sizes=sizes)
print('Saved', dst_ico)
