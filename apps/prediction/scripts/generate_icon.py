"""PyQt6로 MAPS 로고를 PNG로 저장."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtCore import Qt

app = QApplication(sys.argv)

from src.gui.widgets.maps_logo import _paint_maps_logo

out_dir = os.path.join(os.path.dirname(__file__), '..', 'assets')
os.makedirs(out_dir, exist_ok=True)

for size in (16, 32, 64, 128, 256):
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    _paint_maps_logo(p, size)
    p.end()
    path = os.path.join(out_dir, f'icon_{size}.png')
    px.save(path, 'PNG')
    print(f'Generated: {path}')

import shutil
shutil.copy(os.path.join(out_dir, 'icon_256.png'),
            os.path.join(out_dir, 'icon.png'))
print('Done!')
