"""Restore-only Marketplace screen; generated fixtures only."""
import json,sys,tempfile,tkinter as tk,uuid
from pathlib import Path
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path('src').resolve()))
from PrismSkinTools import SkinStudio
from PrismSkinPack import export_collection
from PrismMarketplaceUI import MarketplaceInstaller
from PrismMarketplaceInstall import _fingerprint,replace_pack,cached_pack
with tempfile.TemporaryDirectory(dir='work',prefix='restore_ui_') as temporary:
    base=Path(temporary).resolve();cache=base/'premium_cache/skin_packs';host=cache/'host';host.mkdir(parents=True)
    (host/'manifest.json').write_text(json.dumps({'header':{'name':'Fixture Marketplace','uuid':str(uuid.uuid4()),'version':[1,0,0]},'modules':[{'type':'skin_pack','uuid':str(uuid.uuid4()),'version':[1,0,0]}]}))
    (host/'skins.json').write_bytes(b'original fixture assets');original=_fingerprint(host)
    pack=base/'own.mcpack';export_collection([{'skin':Image.new('RGBA',(64,64),(80,150,40,255)),'name':'Fixture'}],pack,'Fixture')
    root=tk.Tk();root.geometry('1000x960');studio=SkinStudio(root);errors=[]
    try:
        with patch('PrismMarketplaceInstall.minecraft_running',return_value=False),patch('PrismMarketplaceUI.marketplace_roots',return_value=[cache]),patch('PrismMarketplaceUI.messagebox.showinfo'),patch('PrismMarketplaceUI.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)):
            replace_pack(pack,cached_pack(host));ui=MarketplaceInstaller(studio);root.update();assert len(ui.packs)==1
            ui.search.set('nothing');assert not ui.visible
            ui.search.set('fixture');assert len(ui.visible)==1
            ui.list.selection_set(0);ui.selected()
            before=_fingerprint(host);ui.install()
            assert 'removed' in ui.status.get() and _fingerprint(host)==before
            for size in ('840x660','780x620','1024x740'):
                ui.window.geometry(size);root.update();assert ui.list.winfo_height()>40
            with patch('PrismMarketplaceUI.messagebox.askyesno',return_value=False):ui.restore()
            assert _fingerprint(host)==before
            with patch('PrismMarketplaceUI.messagebox.askyesno',return_value=True):ui.restore()
            assert not errors and _fingerprint(host)==original,errors
            assert not ui.packs
    finally:root.destroy()
print('Restore-only Marketplace UI passed: search, retired-install no-op, layout, cancellation and exact original restoration.')
