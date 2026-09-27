"""assets/icon.png → assets/icon.ico (Windows 아이콘)"""
import os
import sys

try:
    from PIL import Image
except ImportError:
    print("Pillow가 없습니다. 설치 중...")
    os.system(f'"{sys.executable}" -m pip install pillow -q')
    from PIL import Image

root = os.path.join(os.path.dirname(__file__), '..')
src = os.path.join(root, 'assets', 'icon.png')
dst = os.path.join(root, 'assets', 'icon.ico')

img = Image.open(src).convert('RGBA')
img.save(dst, format='ICO',
         sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print(f'Generated: {dst}')
