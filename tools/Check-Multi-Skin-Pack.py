import io,json,sys,tempfile,zipfile,tkinter as tk
from pathlib import Path
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path('src').resolve()))
from PrismSkinPack import export_collection
from PrismSkinTools import SkinStudio,SketchButton
from PrismInstalledPacks import prism_pack

with tempfile.TemporaryDirectory(dir='work',prefix='multi_skin_') as temporary:
    base=Path(temporary).resolve();paths=[]
    for index,size in enumerate(((64,64),(128,128),(64,32))):
        folder=base/str(index);folder.mkdir();path=folder/'same-name.png'
        Image.new('RGBA',size,((index+1)*60,100,80,255)).save(path);paths.append(path)
    cape=base/'cape.png';Image.new('RGBA',(64,32),(30,70,200,255)).save(cape)
    root=tk.Tk();root.geometry('1000x960');studio=SkinStudio(root)
    try:
        studio.set_skin(paths[0]);studio.skin_name.set('Knight');studio.zombie.set(True)
        with patch('PrismSkinTools.filedialog.askopenfilename',return_value=str(cape)):studio.pick_cape()
        studio.name.set('My collection')
        studio.add_to_pack()
        assert len(studio.skins)==1 and studio.skin is None and studio.cape is None and studio.skin_name.get()==''
        assert not studio.zombie.get() and studio.model.get().startswith('Classic') and studio.name.get()=='My collection'
        studio.set_skin(paths[1]);assert not studio.zombie.get() and studio.cape is None
        studio.skin_name.set('Scout');studio.model.set('Slim (3-pixel arms)')
        studio.add_to_pack()
        studio.set_skin(paths[2]);studio.skin_name.set('Classic')
        studio.add_to_pack()
        studio.skin_list.selection_clear(0,'end');studio.skin_list.selection_set(0);studio.choose_skin()
        assert not studio.zombie.get() and studio.cape is not None and studio.skin_name.get()=='Knight'
        studio.skin_list.selection_clear(0,'end');studio.skin_list.selection_set(1);studio.choose_skin()
        assert not studio.zombie.get() and studio.cape is None and studio.model.get().startswith('Slim')
        root.update();studio.render()
        assert studio.canvas.winfo_rooty()+studio.canvas.winfo_height()<=root.winfo_rooty()+root.winfo_height()
        def descendants(widget):
            for child in widget.winfo_children():
                yield child;yield from descendants(child)
        for button in (w for w in descendants(root) if isinstance(w,SketchButton)):
            assert button.winfo_rooty()+button.winfo_height()<=root.winfo_rooty()+root.winfo_height(),button.text
        out=base/'collection.mcpack';notices=[]
        studio.experimental.set(True)
        with patch('PrismSkinTools.filedialog.asksaveasfilename',return_value=str(out)),patch('PrismSkinTools.messagebox.showinfo',side_effect=lambda *a,**k:notices.append(a)):
            studio.export()
        assert out.exists() and notices
        with zipfile.ZipFile(out) as z:
            assert z.testzip() is None
            definitions=json.loads(z.read('skins.json'));skins=definitions['skins']
            assert len(skins)==3 and len({s['localization_name'] for s in skins})==3
            assert len({s['texture'] for s in skins})==3
            assert skins[1]['geometry']=='geometry.humanoid.customSlim'
            assert Image.open(io.BytesIO(z.read(skins[1]['texture']))).size==(128,128)
            assert 'geometry.json' not in z.namelist()
            assert skins[0]['cape'] in z.namelist()
            assert all('animations' not in s for s in skins)
            for index,s in enumerate(skins):
                assert Image.open(io.BytesIO(z.read(s['texture']))).tobytes()==studio.skins[index]['skin'].tobytes()
            language=z.read('texts/en_US.lang').decode();assert all(n in language for n in ('Knight','Scout','Classic'))
            installed=base/'installed';z.extractall(installed)
            assert prism_pack(installed), 'Collection not recognized by pack manager'
        # Multiple enhanced skins stay separate without duplicate fallback entries.
        entries=[dict(item,zombie=True) for item in studio.skins]
        other=base/'customs.mcpack';export_collection(entries,other,'All custom',include_custom=True)
        with zipfile.ZipFile(other) as z:
            definitions=json.loads(z.read('skins.json'))['skins']
            assert len(definitions)==3 and all('animations' not in s for s in definitions)
            assert 'geometry.json' not in z.namelist()
        compatible=base/'compatible.mcpack';report=export_collection(studio.skins,compatible,'Compatible')
        assert report['preview_only']==1 and report['variants']==3
        with zipfile.ZipFile(compatible) as z:
            assert 'geometry.json' not in z.namelist()
            skins=json.loads(z.read('skins.json'))['skins'];assert len(skins)==3
            assert all(s['geometry'] in ('geometry.humanoid.custom','geometry.humanoid.customSlim') for s in skins)
            assert all('cape' not in s and 'animations' not in s for s in skins)
            for index,s in enumerate(skins):
                image=Image.open(io.BytesIO(z.read(s['texture'])))
                assert image.tobytes()==studio.skins[index]['skin'].tobytes()
        studio.remove_skin();assert len(studio.skins)==2
        studio.remove_skin();studio.remove_skin();assert not studio.skins and studio.skin is None
        studio.set_skin(paths[0]);assert not studio.skins and studio.draft is not None
        with patch('PrismSkinTools.messagebox.showerror') as error:studio.export();assert error.called
        studio.add_to_pack();assert len(studio.skins)==1 and not studio.zombie.get()
        invalid=base/'invalid.mcpack'
        try:export_collection([],invalid)
        except ValueError:pass
        else:raise AssertionError('Empty collection accepted')
        assert not invalid.exists()
        before=out.read_bytes()
        try:export_collection(studio.skins,out)
        except FileExistsError:pass
        else:raise AssertionError('Existing pack overwritten')
        assert out.read_bytes()==before and all(p.exists() for p in paths)
    finally:root.destroy()
print('Multi-skin passed: collection UI, per-skin settings, select/rename/remove, mixed sizes, separate cape metadata and retired pose inputs ignored, localization, manager recognition and overwrite protection.')
