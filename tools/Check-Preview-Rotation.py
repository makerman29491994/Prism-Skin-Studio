"""Exercise mouse orbit controls and full vertical preview rotation."""
import sys
import tkinter as tk
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path("src").resolve()))
from PrismSkinTools import SkinStudio
from PrismSkinPack import prepare_model, preview_model

root = tk.Tk()
root.geometry("1000x960")
studio = SkinStudio(root)
try:
    root.update()
    studio.canvas.event_generate("<ButtonPress-1>", x=50, y=50)
    assert studio._drag_position is None
    skin = Image.new("RGBA", (64, 64), (80, 150, 120, 255))
    studio.select_skin(None, draft={"skin": skin, "name": "Orbit test"})
    root.update()
    canvas = studio.canvas
    canvas.event_generate("<ButtonPress-1>", x=50, y=50)
    canvas.event_generate("<B1-Motion>", x=150, y=100)
    assert (studio.yaw, studio.pitch) == (330, 44)
    pending = studio._preview_job
    canvas.event_generate("<B1-Motion>", x=200, y=150)
    assert studio._preview_job == pending, "Motion postponed the pending frame"
    studio.render()
    assert studio._image.width() > 0
    cached = studio._preview_model
    studio.yaw += 10
    studio.render()
    assert studio._preview_model is cached, "Orbit rebuilt the textured model"
    studio.model.set("Slim (3-pixel arms)")
    studio.render()
    assert studio._preview_model is not cached, "Arm changes reused stale geometry"
    cached = studio._preview_model
    studio.cape = Image.new("RGBA", (64, 32), (120, 60, 200, 255))
    studio.render()
    assert studio._preview_model is not cached, "Cape changes reused stale texture"
    cached = studio._preview_model
    studio.skin = skin.copy()
    studio.render()
    assert studio._preview_model is not cached, "Skin changes reused stale texture"
    canvas.event_generate("<ButtonRelease-1>", x=200, y=150)
    assert studio._drag_position is None and canvas.cget("cursor") == "hand2"
    studio.reset_view()
    assert (studio.yaw, studio.pitch) == (30, 14)
    atlas, geometry = prepare_model(skin)
    views = [preview_model(atlas, geometry, yaw=30, pitch=p).tobytes()
             for p in (0, 90, 180, 270)]
    assert len(set(views)) == 4, "Vertical orbit did not change the view"
    assert studio.draft["skin"] is skin, "Orbit changed the skin draft"
finally:
    root.destroy()
print("Mouse orbit passed: reversed axes, full vertical rotation, frame scheduling, reset and model cache invalidation.")
