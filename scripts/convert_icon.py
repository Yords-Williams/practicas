"""
Convert assets/app.png to assets/app.ico using Pillow.
Run:
    .\venv311\Scripts\python.exe scripts\convert_icon.py
"""
from PIL import Image
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
assets = os.path.join(ROOT, 'assets')
png = os.path.join(assets, 'app.png')
ico = os.path.join(assets, 'app.ico')

if not os.path.exists(png):
    print(f"PNG not found: {png}\nPlease place your logo image at this path (e.g. save the attached image as assets/app.png)")
    raise SystemExit(1)

im = Image.open(png)
# Ensure RGBA
if im.mode not in ('RGBA', 'RGB'):
    im = im.convert('RGBA')

# Save ICO with multiple sizes for compatibility
sizes = [(256,256), (128,128), (64,64), (48,48), (32,32), (16,16)]
im.save(ico, format='ICO', sizes=sizes)
print(f"Saved ICO: {ico}")
