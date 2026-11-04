import json,os,sys,tempfile,zipfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path('src').resolve()))
from PrismSkinPack import export_pack
from PrismInstalledPacks import minecraft_skin_roots,scan_packs,remove_pack,restore_pack,_io_path

with tempfile.TemporaryDirectory(dir='work',prefix='installed_packs_') as temporary:
    base=Path(temporary).resolve()
    root=base/'roaming/Minecraft Bedrock/Users/Shared/games/com.mojang/skin_packs'
    root.mkdir(parents=True)
    skin=base/'skin.png';Image.new('RGBA',(64,64),(50,150,80,255)).save(skin)
    archive=base/'test.mcpack';export_pack(skin,archive,'Test skin')
    original_archive=archive.read_bytes()
    installed=root/'test_skin'
    with zipfile.ZipFile(archive) as z:z.extractall(installed)
    expected={str(p.relative_to(installed)):p.read_bytes() for p in installed.rglob('*') if p.is_file()}
    other=root/'unrelated';other.mkdir()
    (other/'manifest.json').write_text('{"header":{"description":"Other app"}}')
    (root/'broken').mkdir();(root/'broken/manifest.json').write_text('invalid')
    with patch.dict(os.environ,{'APPDATA':str(base/'roaming'),'LOCALAPPDATA':str(base/'local')}),patch('PrismCapeInstall.game_skin_roots',return_value=[]):
        assert minecraft_skin_roots()==[root]
    packs,warnings=scan_packs([root]);assert not warnings and len(packs)==1
    imported=root/'Imported(1).'
    _io_path(imported).write_bytes(original_archive)
    detected,warnings=scan_packs([root]);assert not warnings and len(detected)==2
    archived=next(p for p in detected if p['archive'])
    assert archived['path'].name=='Imported(1).'
    remove_pack(archived);assert not _io_path(imported).exists()
    removed=next(p for p in scan_packs([root])[0] if p['removed'])
    restore_pack(removed);assert _io_path(imported).read_bytes()==original_archive
    _io_path(imported).rename(_io_path(base/'imported-copy.mcpack'))
    entry=remove_pack(packs[0]);assert not installed.exists() and (entry/'pack').is_dir()
    assert archive.read_bytes()==original_archive and other.is_dir()
    packs,warnings=scan_packs([root]);assert len(packs)==1 and packs[0]['removed']
    installed.mkdir()
    try:restore_pack(packs[0])
    except FileExistsError:pass
    else:raise AssertionError('Restore overwrote an existing folder')
    installed.rmdir();restore_pack(packs[0])
    assert {str(p.relative_to(installed)):p.read_bytes() for p in installed.rglob('*') if p.is_file()}==expected
    packs,_=scan_packs([root]);assert len(packs)==1 and not packs[0]['removed']
    # A stale selection must not remove a replaced pack.
    manifest=installed/'manifest.json';data=json.loads(manifest.read_text());data['header']['description']='Other app';manifest.write_text(json.dumps(data))
    try:remove_pack(packs[0])
    except ValueError:pass
    else:raise AssertionError('Unverified pack removed')
    assert installed.exists() and not scan_packs([root])[0]
    assert scan_packs([base])[1], 'Wrong folder accepted'
    # A directory junction is never a valid pack-management root.
    import subprocess
    link=base/'linked'
    result=subprocess.run(['cmd','/c','mklink','/J',str(link),str(root)],capture_output=True)
    if result.returncode==0:
        try:assert scan_packs([link])[1]
        finally:link.rmdir()
print('Installed packs passed: discovery, Prism-only filtering, reversible removal, exact restore, conflict refusal, stale selection and junction rejection.')
