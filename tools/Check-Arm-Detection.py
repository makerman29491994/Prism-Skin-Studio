"""Arm suggestions, conservative fallbacks, manual overrides and export."""
import hashlib,json,sys,tempfile,tkinter as tk,zipfile
from pathlib import Path
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path('src').resolve()))
from PrismSkinPack import guess_slim,load_skin,export_collection
from PrismSkinTools import SkinStudio

with tempfile.TemporaryDirectory(dir='work',prefix='arm-detection-') as temporary:
    base=Path(temporary);paths=[]
    for scale in (1,2):
        classic=Image.new('RGBA',(64*scale,64*scale),(70,120,180,255))
        slim=classic.copy();draw=ImageDraw.Draw(slim)
        for box in ((50,16,52,20),(54,20,56,32),(42,48,44,52),(46,52,48,64)):
            x,y,r,b=(v*scale for v in box)
            draw.rectangle((x,y,r-1,b-1),fill=(200,100,80,0))
        for name,image,expected in (('classic',classic,False),('slim',slim,True)):
            path=base/f'{name}-{scale}.png';image.save(path)
            assert guess_slim(load_skin(path)) is expected
            paths.append((path,expected))
        slim.putpixel((54*scale,20*scale),(0,0,0,1))
        assert not guess_slim(slim),'Painted padding must keep classic fallback'
    assert not guess_slim(Image.new('RGBA',(64,64)))
    legacy=base/'legacy.png';Image.new('RGBA',(64,32),(60,100,120,255)).save(legacy)
    assert not guess_slim(load_skin(legacy))
    originals={path:hashlib.sha256(path.read_bytes()).digest() for path,_ in paths}
    root=tk.Tk();studio=SkinStudio(root)
    try:
        for path,expected in paths:
            studio.set_skin(path)
            assert studio.model.get().startswith('Slim') is expected
            studio.model.set('Classic (4-pixel arms)' if expected else 'Slim (3-pixel arms)')
            studio.add_to_pack()
            assert studio.skins[-1]['slim'] is (not expected)
        for index,(_,expected) in enumerate(paths):
            studio.select_skin(index)
            assert studio.model.get().startswith('Slim') is (not expected),'Override lost on reselect'
        output=base/'overrides.mcpack'
        export_collection(studio.skins,output,'Overrides')
        with zipfile.ZipFile(output) as archive:
            entries=json.loads(archive.read('skins.json'))['skins']
            assert [entry['geometry'].endswith('customSlim') for entry in entries]==[not value for _,value in paths]
        # Picking again replaces the selected pack entry, preserving its edits.
        studio.select_skin(0);studio.skin_name.set('Custom name')
        cape=Image.new('RGBA',(64,32),(10,20,30,255))
        studio.cape=cape;studio.cape_path.set('chosen-cape.png')
        studio.set_skin(paths[1][0])
        assert len(studio.skins)==4 and studio.selected_index==0 and studio.draft is None
        assert studio.skin_path.get()==str(paths[1][0]) and studio.model.get().startswith('Slim')
        assert studio.skin_name.get()=='Custom name' and studio.cape is cape
        studio.select_skin(None);studio.set_skin(paths[0][0])
        studio.set_skin(paths[1][0])
        assert len(studio.skins)==4 and studio.draft['skin_path']==str(paths[1][0])
        assert studio.skin_name.get()==paths[1][0].stem and studio.model.get().startswith('Slim')
        before=studio.draft
        invalid=base/'invalid.png';invalid.write_bytes(b'not a PNG')
        try:studio.set_skin(invalid)
        except OSError:pass
        else:raise AssertionError('Invalid PNG accepted')
        assert studio.draft is before and studio.skin_path.get()==str(paths[1][0])
        from unittest.mock import patch
        with patch('PrismSkinTools.filedialog.askopenfilename',return_value=''):
            studio.pick_skin()
        assert studio.draft is before
        studio.add_to_pack();assert len(studio.skins)==5
    finally:root.destroy()
    assert all(hashlib.sha256(path.read_bytes()).digest()==digest for path,digest in originals.items())
print('Arm detection passed: classic/slim, HD, legacy, ambiguous/blank PNGs, manual overrides, reselection, export and unchanged files.')
