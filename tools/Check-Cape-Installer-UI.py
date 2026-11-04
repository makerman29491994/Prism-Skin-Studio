import json,sys,tempfile,tkinter as tk
from pathlib import Path
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path('src').resolve()))
from PrismSkinTools import SkinStudio,SketchButton
from PrismCapeInstallerUI import CapeInstaller

with tempfile.TemporaryDirectory(dir='work',prefix='cape_installer_ui_') as temporary:
    base=Path(temporary).resolve();game=base/'Content/data/skin_packs'
    for folder in ('custom','vanilla','persona'):(game/folder).mkdir(parents=True)
    (game/'custom/skins.json').write_text('{"skins":[]}')
    original=(game/'custom/skins.json').read_bytes()
    skin=base/'skin.png';Image.new('RGBA',(64,64),(90,150,70,255)).save(skin)
    root=tk.Tk();root.geometry('1000x960');studio=SkinStudio(root)
    studio.set_skin(skin);studio.cape=Image.new('RGBA',(64,32),(150,60,30,255));studio.update_preview()
    studio.add_to_pack()
    errors=[]
    try:
        with patch('tempfile.tempdir',str(base)),patch('PrismCapeInstallerUI.game_skin_roots',return_value=[game]),patch('PrismCapeInstall.minecraft_running',return_value=False),patch('PrismCapeInstallerUI.messagebox.askyesno',return_value=True),patch('PrismCapeInstallerUI.messagebox.showinfo'),patch('PrismCapeInstallerUI.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)):
            ui=CapeInstaller(studio);root.update()
            ui.install();assert not errors and 'Installed!' in ui.status.get(),errors
            skin_entry=json.loads((game/'custom/skins.json').read_text())['skins'][0]
            assert 'cape' in skin_entry
            ui.undo();assert not errors and (game/'custom/skins.json').read_bytes()==original
            root.update()
            def descendants(widget):
                for child in widget.winfo_children():
                    yield child;yield from descendants(child)
            for size in ('640x420','620x400'):
                ui.window.geometry(size);root.update()
                for button in (w for w in descendants(ui.window) if isinstance(w,SketchButton)):
                    left,top=button.winfo_rootx(),button.winfo_rooty()
                    right,bottom=left+button.winfo_width(),top+button.winfo_height()
                    parent=button.master
                    while parent is not None:
                        assert left>=parent.winfo_rootx() and top>=parent.winfo_rooty(),(size,button.text)
                        assert right<=parent.winfo_rootx()+parent.winfo_width() and bottom<=parent.winfo_rooty()+parent.winfo_height(),(size,button.text,'clipped')
                        if parent is ui.window:break
                        parent=parent.master
    finally:root.destroy()
print('Cape installer UI passed: current collection export, native install, undo, notices and button bounds in temporary fixtures.')
