import sys,tempfile,zipfile,json,tkinter as tk
from pathlib import Path
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path('src').resolve()))
from PrismSkinPack import export_collection
from PrismInstalledPacks import scan_packs,remove_pack,purge_removed,_io_path
from PrismCapeInstall import install_pack,undo_install,_snapshot
from PrismSkinTools import SkinStudio
from PrismPackManager import InstalledPacks

with tempfile.TemporaryDirectory(dir='work',prefix='purge_checks_') as temporary:
    base=Path(temporary).resolve();imports=base/'imports/skin_packs';imports.mkdir(parents=True)
    pack=base/'pack.mcpack';export_collection([{'skin':Image.new('RGBA',(64,64),(90,150,60,255)),'name':'Test'}],pack,'Test')
    installed=imports/'keep';zipfile.ZipFile(pack).extractall(installed)
    archived=imports/'remove(1).';_io_path(archived).write_bytes(pack.read_bytes())
    entries,_=scan_packs([imports]);remove_pack(next(p for p in entries if p['archive']))
    game=base/'game/Content/data/skin_packs'
    for folder in ('custom','vanilla','persona'):(game/folder).mkdir(parents=True)
    (game/'custom/skins.json').write_text('{"skins":[]}')
    with patch('PrismCapeInstall.minecraft_running',return_value=False):
        receipt=install_pack(pack,game);original=_snapshot(receipt.parent/'original')
        undo_install(receipt)
        # Keep a separate active install, whose original backup must survive.
        live=install_pack(pack,game);active=_snapshot(game/'custom');live_original=_snapshot(live.parent/'original')
        entries,_=scan_packs([imports,game]);removed=[p for p in entries if p['removed']]
        assert len(removed)==2
        window=tk.Tk();window.geometry('1000x960');studio=SkinStudio(window)
        try:
            with patch('PrismPackManager.minecraft_skin_roots',return_value=[imports,game]):
                ui=InstalledPacks(studio)
                with patch('PrismPackManager.messagebox.askyesno',return_value=False):ui.delete_removed()
                assert len([p for p in scan_packs([imports,game])[0] if p['removed']])==2
                with patch('PrismPackManager.messagebox.askyesno',return_value=True):ui.delete_removed()
                assert not [p for p in scan_packs([imports,game])[0] if p['removed']]
        finally:window.destroy()
        assert installed.is_dir() and pack.is_file()
        assert _snapshot(game/'custom')==active and _snapshot(live.parent/'original')==live_original
        assert (live.parent/'receipt.json').is_file()
        entry=next(p for p in scan_packs([imports])[0] if not p['removed'])
        try:purge_removed([dict(entry,removed=True)])
        except ValueError:pass
        else:raise AssertionError('Installed path accepted for deletion')
        assert installed.is_dir()
        undo_install(live);assert _snapshot(game/'custom')==original
print('Purge passed: confirmation cancel, delete all removed archive/native backups, active-pack and Undo-original preservation, installed-path refusal.')
