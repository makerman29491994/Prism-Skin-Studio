import json,sys,tempfile,zipfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path('src').resolve()))
from PrismCapeInstall import install_pack,undo_install,latest_receipt,_snapshot
from PrismSkinPack import export_collection
from PrismInstalledPacks import scan_packs,remove_pack,restore_pack

with tempfile.TemporaryDirectory(dir='work',prefix='cape_install_') as temporary:
    base=Path(temporary).resolve();root=base/'Content/data/skin_packs'
    for folder in ('custom','vanilla','persona'):(root/folder).mkdir(parents=True)
    (root/'custom/manifest.json').write_text('{"header":{"name":"Custom"}}')
    (root/'custom/skins.json').write_text('{"skins":[],"serialize_name":"Custom"}')
    (root/'vanilla/untouched.txt').write_text('vanilla')
    before=_snapshot(root/'custom')
    skin=Image.new('RGBA',(64,64),(80,150,40,255));cape=Image.new('RGBA',(64,32),(150,30,60,255))
    archive=base/'pack.mcpack';export_collection([{'skin':skin,'cape':cape,'name':'Test','zombie':True}],archive,'Test capes',include_custom=True)
    with patch('PrismCapeInstall.minecraft_running',return_value=True):
        try:install_pack(archive,root)
        except ValueError:pass
        else:raise AssertionError('Installed while game was running')
    assert _snapshot(root/'custom')==before
    with patch('PrismCapeInstall.minecraft_running',return_value=False):
        receipt=install_pack(archive,root)
        assert latest_receipt(root)==receipt and _snapshot(receipt.parent/'original')==before
        skins=json.loads((root/'custom/skins.json').read_text())['skins'];assert len(skins)==1
        assert skins[0]['cape']=='cape.png' and 'animations' not in skins[0]
        with Image.open(root/'custom/skin.png') as texture:assert texture.size==(64,64)
        entries,warnings=scan_packs([root])
        assert not warnings and len(entries)==1 and entries[0]['native'] and not entries[0]['removed']
        remove_pack(entries[0]);assert _snapshot(root/'custom')==before
        entries,warnings=scan_packs([root]);assert not warnings and len(entries)==1 and entries[0]['removed']
        restored_receipt=restore_pack(entries[0]);assert latest_receipt(root)==restored_receipt
        undo_install(restored_receipt);assert _snapshot(root/'custom')==before
        # Put the initial pack back for the remaining installer checks.
        receipt=install_pack(archive,root)
        second=install_pack(archive,root)
        undo_install(second);assert _snapshot(root/'custom')==json.loads(receipt.read_text())['installed_files']
        undo_install(receipt);assert _snapshot(root/'custom')==before
        assert (root/'vanilla/untouched.txt').read_text()=='vanilla'
        bad=base/'bad.mcpack'
        with zipfile.ZipFile(bad,'w') as z:z.writestr('../escape.txt','bad')
        try:install_pack(bad,root)
        except ValueError:pass
        else:raise AssertionError('Traversal accepted')
        assert not (base/'escape.txt').exists() and _snapshot(root/'custom')==before
        (root/'custom/skins.json').write_text('{"skins":[{"texture":"other.png"}]}')
        try:install_pack(archive,root)
        except ValueError:pass
        else:raise AssertionError("Overwrote another tool's skins")
print('Cape installer passed: closed-game guard, original-slot backup, native metadata, repeated install/undo, exact restoration, traversal and third-party-pack refusal.')
