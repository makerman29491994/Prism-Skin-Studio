"""Asymmetric artwork catches flipped UVs and rear-shell bleed-through."""
import sys
from pathlib import Path
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path('src').resolve()))
from PrismSkinPack import prepare_model,preview_model

red=(255,30,30,255);blue=(30,80,255,255);green=(30,255,80,255)
skin=Image.new('RGBA',(64,64))
draw=ImageDraw.Draw(skin)
# Asymmetric outer head front; no opaque core to conceal back-facing faces.
draw.rectangle((40,8,43,15),fill=red)
draw.rectangle((44,8,47,15),fill=blue)
draw.rectangle((42,10,43,11),fill=(0,0,0,0))
draw.rectangle((56,8,63,15),fill=green)
atlas,geometry=prepare_model(skin)
front=preview_model(atlas,geometry,yaw=0)
assert front.getpixel((145,87))==red[:3], 'Outer front left was mirrored'
assert front.getpixel((190,87))==blue[:3], 'Outer front right was mirrored'
skin_without_back=skin.copy()
ImageDraw.Draw(skin_without_back).rectangle((56,8,63,15),fill=(0,0,0,0))
a,g=prepare_model(skin_without_back)
assert preview_model(a,g,yaw=0).tobytes()==front.tobytes(), 'Rear overlay leaked through front'
back=preview_model(atlas,geometry,yaw=180)
assert back.getpixel((170,87))==green[:3]

cape=Image.new('RGBA',(64,32))
draw=ImageDraw.Draw(cape)
draw.rectangle((1,1,5,16),fill=red)
draw.rectangle((6,1,10,16),fill=blue)
draw.rectangle((12,1,21,16),fill=green)
panels=[]
for scale in (1,2):
    for slim in (False,True):
        for zombie in (False,True):
            atlas,geometry=prepare_model(skin.resize((64*scale,64*scale),Image.Resampling.NEAREST),cape,slim,zombie)
            bone=next(b for b in geometry['bones'] if b['name']=='prism_cape')
            uv=bone['cubes'][0]['uv']
            assert uv['south']['uv']==[scale,65*scale]
            assert uv['north']['uv']==[12*scale,65*scale]
            # Isolate the cape to check both panels without body occlusion.
            only_cape={'bones':[bone]}
            rear=preview_model(atlas,only_cape,yaw=180)
            inside=preview_model(atlas,only_cape,yaw=0)
            assert rear.getpixel((145,200))==red[:3], 'Cape outward artwork reversed'
            assert rear.getpixel((195,200))==blue[:3]
            assert inside.getpixel((170,200))==green[:3]
            if scale==1 and not slim and not zombie:panels=[front,back,rear,inside]
sheet=Image.new('RGB',(340*4,400))
for i,panel in enumerate(panels):sheet.paste(panel,(340*i,0))
sheet.save('work/skin-orientation-check.png')
print('Orientation passed: asymmetric outer layer, hidden rear faces, cape outward/inside panels, classic/slim, zombie and HD.')
