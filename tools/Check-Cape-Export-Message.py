"""Cape data survives export; UI distinguishes packaging from Minecraft import."""
import json,sys,tempfile,tkinter as tk,zipfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path('src').resolve()))
from PrismSkinTools import SkinStudio
with tempfile.TemporaryDirectory(dir='work',prefix='cape-message-') as tmp:
    base=Path(tmp);skin=base/'skin.png';cape=base/'cape.png';out=base/'test.mcpack'
    Image.new('RGBA',(64,64),(60,140,90,255)).save(skin)
    Image.new('RGBA',(64,32),(170,40,160,255)).save(cape)
    root=tk.Tk();studio=SkinStudio(root)
    try:
        studio.set_skin(skin)
        with patch('PrismSkinTools.filedialog.askopenfilename',return_value=str(cape)):studio.pick_cape()
        studio.add_to_pack();notices=[]
        with patch('PrismSkinTools.filedialog.asksaveasfilename',return_value=str(out)),patch('PrismSkinTools.messagebox.showinfo',side_effect=lambda *a,**k:notices.append(a)):
            studio.export()
        with zipfile.ZipFile(out) as z:
            entry=json.loads(z.read('skins.json'))['skins'][0]
            assert entry['cape']=='cape.png' and z.read('cape.png')==cape.read_bytes()
            assert z.read('skin.png')==skin.read_bytes()
            assert 'Install skins' in z.read('README.txt').decode()
            assert 'Marketplace' not in z.read('README.txt').decode()
        assert '1 capes included' in studio.status.get() and 'Install skins' in studio.status.get()
        assert notices and 'verified in the saved file' in notices[0][1]
    finally:root.destroy()
print('Cape export passed: original skin/cape PNGs, native cape reference, verified count and direct-install guidance.')
