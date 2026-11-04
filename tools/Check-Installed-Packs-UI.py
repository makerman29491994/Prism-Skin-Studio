import sys,tempfile,zipfile,tkinter as tk
from pathlib import Path
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path('src').resolve()))
from PrismSkinTools import SkinStudio,SketchButton
from PrismSkinPack import export_pack
from PrismPackManager import InstalledPacks

with tempfile.TemporaryDirectory(dir='work',prefix='pack_manager_ui_') as temporary:
    base=Path(temporary).resolve();packs=base/'skin_packs';packs.mkdir()
    skin=base/'skin.png';Image.new('RGBA',(64,64),(70,160,80,255)).save(skin)
    archive=base/'test.mcpack';export_pack(skin,archive,'My test skin')
    installed=packs/'test'
    with zipfile.ZipFile(archive) as z:z.extractall(installed)
    root=tk.Tk();root.geometry('1000x960');studio=SkinStudio(root)
    try:
        with patch('PrismPackManager.minecraft_skin_roots',return_value=[packs]), patch('PrismCapeInstall.minecraft_running',return_value=False):
            manager=InstalledPacks(studio);root.update()
            assert len(manager.packs)==1
            manager.list.selection_set(0);manager.selected()
            with patch('PrismPackManager.messagebox.askyesno',return_value=False):manager.remove()
            assert installed.is_dir()
            with patch('PrismPackManager.messagebox.askyesno',return_value=True):manager.remove()
            assert not installed.exists() and not manager.packs, 'Confirmed removal should permanently delete this temporary pack'
            manager.restore()
            assert not installed.exists(), 'Restore must not recreate a purged pack'
            root.update()
            def descendants(widget):
                for child in widget.winfo_children():
                    yield child;yield from descendants(child)
            details=next(w for w in descendants(manager.window) if isinstance(w,tk.Label) and str(w.cget('textvariable'))==str(manager.details))
            paper=details.master.master
            assert details.winfo_rooty()+details.winfo_height()<=paper.winfo_rooty()+paper.winfo_height()
            for button in (w for w in descendants(manager.window) if isinstance(w,SketchButton)):
                assert button.winfo_rootx()>=manager.window.winfo_rootx()
                assert button.winfo_rootx()+button.winfo_width()<=manager.window.winfo_rootx()+manager.window.winfo_width()
                assert button.winfo_rooty()+button.winfo_height()<=manager.window.winfo_rooty()+manager.window.winfo_height()
    finally:root.destroy()
print('Pack manager UI passed: list, cancel, permanent remove, empty restore, status and button bounds using temporary fixtures only.')
