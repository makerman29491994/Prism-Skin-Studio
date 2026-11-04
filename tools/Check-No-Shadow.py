import sys
from pathlib import Path
sys.path.insert(0,str(Path('src').resolve()))
from PrismSkinPack import preview_model
image=preview_model(None,None,(300,400),mesh=())
assert len(set(image.getdata()))==1
print('Skin Studio preview has no decorative shadow.')
