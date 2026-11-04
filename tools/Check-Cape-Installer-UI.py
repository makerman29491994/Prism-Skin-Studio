import json,sys,tempfile,tkinter as tk
from pathlib import Path
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path('src').resolve()))
from PrismSkinTools import SkinStudio,SketchButton
from PrismCapeInstallerUI import CapeInstaller
from PrismCapeInstall import game_skin_roots

def available(path):
    if str(path).startswith('F:'):raise PermissionError('Inaccessible XboxGames drive')
    return str(path).startswith('C:')
with patch('PrismCapeInstall.Path.is_dir',available):
    assert len(game_skin_roots())==1,'One inaccessible drive blocked game discovery'

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
            from PrismSkinPack import export_collection
            saved=base/'two-skins.mcpack'
            export_collection([{'skin':Image.new('RGBA',(64,64),(100,50,70,255)),'cape':Image.new('RGBA',(64,32),(40,170,80,255)),'name':'With cape'},
                               {'skin':Image.new('RGBA',(64,64),(70,90,120,255)),'name':'Without cape'}],saved,'Two skins',include_custom=True)
            with patch('PrismCapeInstallerUI.filedialog.askopenfilename',return_value=str(saved)):ui.choose_pack()
            assert '2 skins' in ui.pack_status.get() and '1 capes' in ui.pack_status.get()
            ui.install();assert not errors,errors
            installed=json.loads((game/'custom/skins.json').read_text())['skins']
            assert len(installed)==2 and 'cape' in installed[0] and 'cape' not in installed[1]
            assert len(studio.skins)==1,'Installing a saved file changed the Studio collection'
            ui.undo();assert (game/'custom/skins.json').read_bytes()==original
            ui.use_studio();assert ui.pack_path is None and '1 skins' in ui.pack_status.get()
            root.update()
            def descendants(widget):
                for child in widget.winfo_children():
                    yield child;yield from descendants(child)
            for size in ('560x400','540x380'):
                ui.window.geometry(size);root.update()
                for button in (w for w in descendants(ui.window) if isinstance(w,SketchButton) and w.winfo_ismapped()):
                    left,top=button.winfo_rootx(),button.winfo_rooty()
                    right,bottom=left+button.winfo_width(),top+button.winfo_height()
                    parent=button.master
                    while parent is not None:
                        assert left>=parent.winfo_rootx() and top>=parent.winfo_rooty(),(size,button.text)
                        assert right<=parent.winfo_rootx()+parent.winfo_width() and bottom<=parent.winfo_rooty()+parent.winfo_height(),(size,button.text,'clipped')
                        if parent is ui.window:break
                        parent=parent.master
            visible={w.text for w in descendants(ui.window) if isinstance(w,SketchButton) and w.winfo_ismapped()}
            assert visible=={'Choose .mcpack\u2026','More options\u2026','Install skins\u2026'},visible
            ui.more_options();root.update();options=ui.options_window
            assert options.winfo_exists()
            assert {w.text for w in descendants(options) if isinstance(w,SketchButton)}=={'Choose game folder\u2026','Save Studio copy\u2026','Undo last install','Restore old packs\u2026'}
            for size in ('600x300','580x280'):
                options.geometry(size);root.update()
                for button in (w for w in descendants(options) if isinstance(w,SketchButton)):
                    assert button.winfo_rootx()+button.winfo_width()<=options.winfo_rootx()+options.winfo_width()
                    assert button.winfo_rooty()+button.winfo_height()<=options.winfo_rooty()+options.winfo_height()
            with patch('PrismCapeInstallerUI.game_skin_roots',return_value=[]):missing=CapeInstaller(studio)
            root.update();assert missing.folder_button.winfo_ismapped()
            assert missing.folder_button.winfo_rooty()+missing.folder_button.winfo_height()<=missing.window.winfo_rooty()+missing.window.winfo_height()
            missing.root_path.set(str(game));root.update();assert not missing.folder_button.winfo_ismapped()
    finally:root.destroy()
print('Cape installer UI passed: current collection export, native install, undo, notices and button bounds in temporary fixtures.')
