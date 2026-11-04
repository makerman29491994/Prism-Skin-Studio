"""Regression for UTF-8 text accidentally decoded as Windows-1252."""
import sys,tkinter as tk
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path('src').resolve()))
from PrismSkinTools import SkinStudio,SketchButton
from PrismCapeInstallerUI import CapeInstaller
for path in Path('src').glob('Prism*.py'):
    text=path.read_text(encoding='utf-8')
    assert not any(marker in text for marker in ('\u00e2\u20ac','\u00c2\u00b7','\ufffd')),path
root=tk.Tk();studio=SkinStudio(root)
try:
    with patch('PrismCapeInstallerUI.game_skin_roots',return_value=[]):installer=CapeInstaller(studio)
    root.update()
    def descendants(widget):
        for child in widget.winfo_children():yield child;yield from descendants(child)
    labels={w.text for w in descendants(installer.window) if isinstance(w,SketchButton)}
    assert 'Choose game folder\u2026' in labels,labels
    assert 'Install skins\u2026' in labels,labels
finally:root.destroy()
print('Installer text passed: readable ellipses and no corrupted UTF-8 markers.')
