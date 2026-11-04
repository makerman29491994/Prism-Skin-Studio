import sys,json,uuid,zipfile,tempfile,hashlib
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path("src").resolve()))
from PrismSkinPack import load_skin,load_cape,prepare_model,preview_model,export_pack
with tempfile.TemporaryDirectory(dir="work",prefix="skin_checks_") as temporary:
    root=Path(temporary)
    skin=root/"skin.png";cape=root/"cape.png"
    image=Image.new("RGBA",(64,64),(70,140,80,255));image.putpixel((8,8),(255,0,0,255));image.save(skin)
    Image.new("RGBA",(64,32),(120,30,180,255)).save(cape)
    original=hashlib.sha256(skin.read_bytes()).hexdigest()
    for slim in (False,True):
        for zombie in (False,True):
            for with_cape in (False,True):
                out=root/f"{slim}-{zombie}-{with_cape}.mcpack"
                report=export_pack(skin,out,"Test Pack",slim,zombie,cape if with_cape else None,include_custom=True)
                with zipfile.ZipFile(out) as archive:
                    assert archive.testzip() is None
                    manifest=json.loads(archive.read("manifest.json"));uuid.UUID(manifest["header"]["uuid"])
                    assert manifest["modules"][0]["type"]=="skin_pack"
                    definitions=json.loads(archive.read("skins.json"));entries=definitions["skins"]
                    assert len(entries)==1
                    assert entries[0]["geometry"]==("geometry.humanoid.customSlim" if slim else "geometry.humanoid.custom")
                    assert all(entry["texture"] in archive.namelist() for entry in entries)
                    language=archive.read("texts/en_US.lang").decode()
                    assert all(f"skin.{definitions['serialize_name']}.{entry['localization_name']}=" in language for entry in entries)
                    assert "geometry.json" not in archive.namelist() and "custom_skin.png" not in archive.namelist()
                    with archive.open(entries[0]["texture"]) as stream, Image.open(stream) as texture:
                        assert texture.size==(64,64) and texture.getpixel((8,8))==(255,0,0,255)
                    assert ("cape" in entries[0])==with_cape
                    if with_cape:assert entries[0]["cape"] in archive.namelist()
                    assert "animations" not in entries[0]  # Retired pose inputs are ignored.
                old=out.read_bytes()
                try:export_pack(skin,out)
                except FileExistsError:pass
                else:raise AssertionError("Existing pack overwritten")
                assert old==out.read_bytes()
    assert hashlib.sha256(skin.read_bytes()).hexdigest()==original
    legacy=root/"legacy.png";Image.new("RGBA",(64,32),(40,80,120,255)).save(legacy);assert load_skin(legacy).size==(64,64)
    hd=root/"hd.png";Image.new("RGBA",(128,128),(20,60,90,255)).save(hd)
    atlas,geometry=prepare_model(load_skin(hd),load_cape(cape),True,True)
    assert atlas.size==(256,256)
    assert preview_model(atlas,geometry,(200,250)).size==(200,250)
    wrong=root/"wrong.png";Image.new("RGB",(32,32)).save(wrong)
    try:load_skin(wrong)
    except ValueError:pass
    else:raise AssertionError("Invalid skin size accepted")
print("Skin packs passed: classic/slim, separate cape PNGs, retired pose inputs ignored, unchanged body textures, HD/legacy PNGs and no overwrite.")
