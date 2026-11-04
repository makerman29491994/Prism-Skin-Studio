"""Green, hand-drawn Skin Studio; usable inside Prism or as its own window."""
import sys
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
from PIL import Image,ImageTk
from PrismSkinPack import load_skin,load_cape,prepare_model,prepare_preview_mesh,preview_model,export_collection

BG="#14221b";CARD="#1d3025";INK="#e8f5e8";MUTED="#aac8ad";MINT="#a8dca0";EDGE="#628c69"


class SketchButton(tk.Canvas):
    def __init__(self,parent,text,command,width=130,primary=False):
        super().__init__(parent,width=width,height=44,bg=parent.cget("background"),highlightthickness=0,takefocus=1,cursor="hand2")
        self.text,self.command,self.primary=text,command,primary
        self.bind("<Configure>",self.draw);self.bind("<FocusIn>",self.draw);self.bind("<FocusOut>",self.draw)
        self.bind("<Button-1>",lambda e:self.invoke());self.bind("<Return>",lambda e:self.invoke());self.bind("<space>",lambda e:self.invoke())
    def invoke(self):self.focus_set();self.command()
    def draw(self,event=None):
        self.delete("all");w=self.winfo_width();h=self.winfo_height()
        self.create_polygon(12,3,w*.5,5,w-12,3,w-3,12,w-5,h-11,w-12,h-3,12,h-4,3,h-12,4,12,fill=MINT if self.primary else "#294333",outline="#c4efb4" if str(self.tk.call("focus"))==str(self) else EDGE,width=2,smooth=True,splinesteps=16)
        self.create_text(w/2,h/2,text=self.text,font=("Ink Free",13,"bold"),fill=BG if self.primary else INK)


class SketchCheck(tk.Canvas):
    def __init__(self,parent,text,variable):
        super().__init__(parent,height=35,bg=CARD,highlightthickness=0,takefocus=1,cursor="hand2")
        self.text,self.variable=text,variable
        self.bind("<Configure>",self.draw);self.bind("<Button-1>",lambda e:self.toggle());self.bind("<space>",lambda e:self.toggle())
        self.variable.trace_add("write",self.draw)
    def toggle(self):self.focus_set();self.variable.set(not self.variable.get())
    def draw(self,*args):
        self.delete("all");self.create_polygon(5,7,23,6,24,25,6,26,fill=MINT if self.variable.get() else BG,outline=EDGE,width=2,smooth=True)
        if self.variable.get():self.create_line(9,16,13,21,21,11,fill=BG,width=3,capstyle="round",joinstyle="round")
        self.create_text(36,17,text=self.text,anchor="w",font=("Ink Free",14),fill=INK)


class SkinStudio:
    def __init__(self,parent):
        self.parent=parent;self.skin=None;self.cape=None;self._image=None;self.yaw=30;self._preview_job=None
        self.pitch=14;self._drag_position=None
        self._preview_source=None;self._preview_model=None
        self.skins=[];self.selected_index=None;self.draft=None;self._loading=False
        self.skin_name=tk.StringVar(parent)
        self.skin_path=tk.StringVar(parent);self.cape_path=tk.StringVar(parent);self.name=tk.StringVar(parent,value="My Skin Pack")
        self.model=tk.StringVar(parent,value="Classic (4-pixel arms)");self.zombie=tk.BooleanVar(parent,value=False)
        self.experimental=tk.BooleanVar(parent,value=True)
        self.status=tk.StringVar(parent,value="Pick a skin → Add to pack → Install in Minecraft")
        style=ttk.Style(parent)
        style.configure("Skin.TEntry",fieldbackground=BG,foreground=INK,insertcolor=INK,bordercolor=EDGE,lightcolor=EDGE,darkcolor=EDGE,padding=8,font=("Ink Free",13))
        style.map("Skin.TEntry",fieldbackground=[("readonly",BG)],foreground=[("readonly",INK)],bordercolor=[("focus",MINT)])
        style.configure("Skin.TCombobox",fieldbackground=BG,foreground=INK,background=CARD,arrowcolor=MINT,bordercolor=EDGE,lightcolor=EDGE,darkcolor=EDGE,padding=6,font=("Ink Free",13))
        style.map("Skin.TCombobox",fieldbackground=[("readonly",BG)],foreground=[("readonly",INK)])
        parent.configure(background=BG)
        outer=tk.Frame(parent,bg=BG,padx=28,pady=24);outer.pack(fill="both",expand=True)
        head=tk.Canvas(outer,bg=BG,height=88,highlightthickness=0);head.pack(fill="x")
        resource_dir=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parent))
        with Image.open(resource_dir/"Skin-Studio-logo.png") as source:
            logo=source.convert("RGBA")
        # Use the available header height and crisp sampling for flat artwork.
        bounds=logo.getchannel("A").point(lambda a:255 if a>128 else 0).getbbox()
        if bounds:logo=logo.crop(bounds)
        logo.thumbnail((88,88),Image.Resampling.NEAREST)
        self._header_logo=ImageTk.PhotoImage(logo,master=head)
        head.create_image(44,44,image=self._header_logo)
        head.create_text(104,28,text="Skin Studio",anchor="w",font=("Ink Free",30,"bold"),fill=INK)
        head.create_text(106,62,text="a little green skin magic",anchor="w",font=("Ink Free",14),fill=MUTED)
        head.create_line(104,78,165,75,224,79,282,76,fill=MINT,width=3,smooth=True)
        packs_button=SketchButton(head,"Installed packs…",self.installed_packs,180)
        packs_window=head.create_window(720,44,window=packs_button,anchor="e")
        install_button=SketchButton(head,"Install skins…",self.install_skins,160,True)
        install_window=head.create_window(530,44,window=install_button,anchor="e")
        def place_header_actions(event):
            head.coords(packs_window,event.width-4,44);head.coords(install_window,event.width-194,44)
        head.bind("<Configure>",place_header_actions)
        body=tk.Frame(outer,bg=BG);body.pack(fill="both",expand=True,pady=(16,12));body.columnconfigure(0,weight=3);body.columnconfigure(1,weight=2);body.rowconfigure(0,weight=1)
        form=self.paper(body);form.master.grid(row=0,column=0,sticky="nsew",padx=(0,18));form.columnconfigure(0,weight=1)
        preview=self.paper(body);preview.master.grid(row=0,column=1,sticky="nsew");preview.columnconfigure(0,weight=1);preview.rowconfigure(3,weight=1)
        def label(text,row):tk.Label(form,text=text,bg=CARD,fg=MINT,font=("Ink Free",15,"bold"),anchor="w").grid(row=row,column=0,columnspan=2,sticky="ew",pady=(12,5))
        label("Skin name",0)
        ttk.Entry(form,textvariable=self.skin_name,style="Skin.TEntry",width=22).grid(row=1,column=0,sticky="ew",padx=(0,8))
        SketchButton(form,"Pick PNG…",self.pick_skin,112).grid(row=1,column=1)
        label("Cape (optional)",2)
        ttk.Entry(form,textvariable=self.cape_path,state="readonly",style="Skin.TEntry",width=22).grid(row=3,column=0,sticky="ew",padx=(0,8))
        SketchButton(form,"Pick cape…",self.pick_cape,112).grid(row=3,column=1)
        SketchButton(form,"No cape",self.clear_cape,100).grid(row=4,column=1,sticky="e",pady=(4,0))
        label("Pack name",5)
        ttk.Entry(form,textvariable=self.name,style="Skin.TEntry").grid(row=6,column=0,columnspan=2,sticky="ew")
        label("Arm size",7)
        combo=ttk.Combobox(form,textvariable=self.model,values=("Classic (4-pixel arms)","Slim (3-pixel arms)"),state="readonly",style="Skin.TCombobox")
        combo.grid(row=8,column=0,columnspan=2,sticky="ew");combo.bind("<<ComboboxSelected>>",lambda e:self.update_preview())
        self.zombie.trace_add("write",lambda *args:self.update_preview())
        self.model.trace_add("write",lambda *args:self.update_preview())
        self.skin_name.trace_add("write",self.rename_skin)
        tk.Label(form,text="Add this skin to your pack, or save your pack file below.",bg=CARD,fg=MUTED,font=("Ink Free",11),justify="left",wraplength=385).grid(row=10,column=0,columnspan=2,sticky="ew",pady=(8,6))
        actions=tk.Frame(form,bg=CARD);actions.grid(row=12,column=0,columnspan=2,sticky="ew",pady=(8,12))
        actions.columnconfigure(0,weight=3);actions.columnconfigure(1,weight=2)
        SketchButton(actions,"Add to pack",self.add_to_pack,205,True).grid(row=0,column=0,sticky="ew",padx=(0,6))
        SketchButton(actions,"Save .mcpack…",self.export,155).grid(row=0,column=1,sticky="ew")
        SketchButton(actions,"Clear",self.start_over,155).grid(row=1,column=0,columnspan=2,sticky="ew",pady=(5,0))
        self.pack_count=tk.StringVar(parent,value="Your pack · 0 skins")
        tk.Label(preview,textvariable=self.pack_count,bg=CARD,fg=MINT,font=("Ink Free",18,"bold")).grid(row=0,column=0,sticky="w",pady=(8,8))
        self.skin_list=tk.Listbox(preview,height=3,bg=BG,fg=INK,selectbackground=MINT,selectforeground=BG,font=("Ink Free",13),exportselection=False,activestyle="none",highlightthickness=0,borderwidth=0)
        self.skin_list.grid(row=1,column=0,sticky="ew")
        self.skin_list.bind("<<ListboxSelect>>",self.choose_skin)
        SketchButton(preview,"Remove skin",self.remove_skin,140).grid(row=2,column=0,sticky="e",pady=(4,8))
        self.canvas=tk.Canvas(preview,bg="#17251f",highlightthickness=0,width=300,height=230);self.canvas.grid(row=3,column=0,sticky="nsew")
        self.canvas.bind("<Configure>",lambda e:self.update_preview())
        self.canvas.configure(cursor="hand2")
        self.canvas.bind("<ButtonPress-1>",self.begin_rotate)
        self.canvas.bind("<B1-Motion>",self.drag_rotate)
        self.canvas.bind("<ButtonRelease-1>",self.end_rotate)
        self.canvas.create_text(150,180,text="Your skin goes here",fill=MUTED,font=("Ink Free",16))
        turns=tk.Frame(preview,bg=CARD);turns.grid(row=4,column=0,pady=12)
        SketchButton(turns,"Turn left",lambda:self.turn(-45),110).pack(side="left",padx=4)
        SketchButton(turns,"Turn right",lambda:self.turn(45),110).pack(side="left",padx=4)
        SketchButton(turns,"Reset view",self.reset_view,110).pack(side="left",padx=4)
        tk.Label(preview,text="Drag the preview to rotate",bg=CARD,fg=MUTED,font=("Ink Free",11)).grid(row=5,column=0,pady=(0,4))
        tk.Label(outer,textvariable=self.status,bg=BG,fg=MUTED,font=("Ink Free",13),anchor="w",justify="left",wraplength=900).pack(fill="x",pady=(4,0))
        parent.bind("<Destroy>",self.destroyed,add="+")

    def paper(self,parent):
        canvas=tk.Canvas(parent,bg=BG,highlightthickness=0,borderwidth=0)
        content=tk.Frame(canvas,bg=CARD,padx=18,pady=12);window=canvas.create_window(12,12,window=content,anchor="nw")
        def draw(event=None):
            w,h=canvas.winfo_width(),canvas.winfo_height();canvas.itemconfigure(window,width=max(1,w-24),height=max(content.winfo_reqheight(),h-24));canvas.delete("sketch")
            canvas.create_polygon(20,4,w*.4,7,w-22,5,w-5,22,w-7,h-22,w-22,h-5,20,h-7,5,h-22,7,22,fill=CARD,outline=EDGE,width=2,smooth=True,splinesteps=20,tags="sketch")
            canvas.create_line(24,7,w*.2,5,w*.4,8,fill=MINT,width=2,smooth=True,tags="sketch");canvas.tag_lower("sketch")
        canvas.bind("<Configure>",draw)
        return content

    def pick_skin(self):
        path=filedialog.askopenfilename(parent=self.parent,title="Choose your next skin",filetypes=[("PNG skin","*.png")])
        if not path:return
        try:self.set_skin(path)
        except (OSError,ValueError) as exc:messagebox.showerror("Check your skin",str(exc),parent=self.parent)
    def installed_packs(self):
        previous=getattr(self,"_pack_manager",None)
        if previous is not None and previous.window.winfo_exists():
            previous.window.lift();return
        from PrismPackManager import InstalledPacks
        self._pack_manager=InstalledPacks(self)
    def cape_installer(self):
        previous=getattr(self,"_cape_installer",None)
        if previous is not None and previous.window.winfo_exists():previous.window.lift();return
        from PrismCapeInstallerUI import CapeInstaller
        self._cape_installer=CapeInstaller(self)
    def install_skins(self):
        # A single skin can go straight to installation without a separate save step.
        if self.draft is not None:
            self.add_to_pack()
            if self.draft is not None:return
        self.save_current()
        self.cape_installer()
    def set_skin(self,path):
        if self.draft is not None:raise ValueError("Click Add to pack to save the current skin, or Remove skin to clear it, before picking another PNG.")
        skin=load_skin(path)
        self.save_current()
        self.select_skin(None,draft={"skin":skin,"skin_path":str(path),"name":Path(path).stem,"cape":None,"cape_path":"","slim":False,"zombie":False})
        self.status.set("Set this skin's name, cape and pose, then click Add to pack.")
    def add_to_pack(self):
        if self.draft is None:
            self.status.set("Pick a PNG to add a new skin. Saved skins update as you edit them.");return
        self.save_current()
        name=self.draft["name"].strip()
        if not name or len(name)>80 or any(c in name for c in "\r\n="):
            self.status.set("Give this skin a name of 1–80 characters without line breaks or =.");return
        self.draft["name"]=name;self.skins.append(self.draft)
        self.select_skin(None)
        self.status.set(f"Added {name} to your pack. Pick the next PNG, or export all {len(self.skins)} skins.")
    def save_current(self):
        if self._loading:return
        item=self.draft if self.draft is not None else self.skins[self.selected_index] if self.selected_index is not None else None
        if item is not None:item.update(name=self.skin_name.get(),cape=self.cape,cape_path=self.cape_path.get(),slim=self.model.get().startswith("Slim"),zombie=False)
    def start_over(self):
        self.yaw=30;self.pitch=14
        self.select_skin(None)
        self.status.set("Fresh start. Pick a skin PNG. Skins already added to your pack are kept.")
    def refresh_skin_list(self):
        self.skin_list.delete(0,"end")
        for index,item in enumerate(self.skins):
            effects=(" · cape" if item.get("cape") is not None else "")+(" · zombie arms" if item.get("zombie") else "")
            self.skin_list.insert("end",f"{index+1}. {item['name'] or '(name your skin)'}{effects}")
        if self.selected_index is not None:
            self.skin_list.selection_set(self.selected_index);self.skin_list.see(self.selected_index)
        count=len(self.skins);self.pack_count.set(f"Your pack · {count} skin"+("s" if count!=1 else ""))
    def rename_skin(self,*args):
        if self._loading:return
        self.save_current();self.refresh_skin_list()
    def choose_skin(self,event=None):
        selection=self.skin_list.curselection()
        if selection and selection[0]!=self.selected_index:
            if self.draft is not None:
                self.refresh_skin_list();self.status.set("Click Add to pack for this skin first, or Remove skin to clear the draft.");return
            self.save_current();self.select_skin(selection[0])
    def select_skin(self,index,draft=None):
        self._loading=True
        try:
            self.selected_index=index;self.draft=draft
            item=draft if draft is not None else self.skins[index] if index is not None else {}
            self.skin=item.get("skin");self.cape=item.get("cape")
            self.skin_path.set(item.get("skin_path",""));self.skin_name.set(item.get("name",""));self.cape_path.set(item.get("cape_path",""))
            self.model.set("Slim (3-pixel arms)" if item.get("slim") else "Classic (4-pixel arms)");self.zombie.set(False)
            self.refresh_skin_list()
        finally:self._loading=False
        self.update_preview()
    def remove_skin(self):
        if self.draft is not None:
            self.select_skin(None);self.status.set("Draft cleared. Pick another PNG to start a skin.");return
        if self.selected_index is None:return
        index=self.selected_index;self.skins.pop(index)
        self.select_skin(min(index,len(self.skins)-1) if self.skins else None)
        self.status.set("Skin removed from this pack. Its original PNG is unchanged.")
    def pick_cape(self):
        path=filedialog.askopenfilename(parent=self.parent,title="Choose a cape PNG or picture",filetypes=[("PNG cape","*.png")])
        if not path:return
        try:self.cape=load_cape(path);self.cape_path.set(path);self.status.set("Cape added to the preview and experimental custom model.");self.update_preview()
        except (OSError,ValueError) as exc:messagebox.showerror("Check your cape",str(exc),parent=self.parent)
    def clear_cape(self):self.cape=None;self.cape_path.set("");self.update_preview()
    def turn(self,amount):self.yaw=(self.yaw+amount)%360;self.update_preview()
    def reset_view(self):
        self.yaw=30;self.pitch=14;self.queue_rotation()
    def begin_rotate(self,event):
        if self.skin is None:return
        self._drag_position=(event.x,event.y)
        self.canvas.configure(cursor="fleur")
    def drag_rotate(self,event):
        if self._drag_position is None:return
        x,y=self._drag_position
        self.yaw=(self.yaw-(event.x-x)*.6)%360
        self.pitch=(self.pitch+(event.y-y)*.6)%360
        self._drag_position=(event.x,event.y)
        self.queue_rotation()
    def end_rotate(self,event):
        self._drag_position=None
        self.canvas.configure(cursor="hand2")
    def queue_rotation(self):
        # Keep rendering during a drag instead of waiting for motion to stop.
        if self._preview_job is None:self._preview_job=self.parent.after(16,self.render)
    def update_preview(self):
        if self._loading:return
        self.save_current()
        if self.selected_index is not None:self.refresh_skin_list()
        if self._preview_job is not None:self.parent.after_cancel(self._preview_job)
        self._preview_job=self.parent.after(80,self.render)
    def render(self):
        self._preview_job=None
        if self.skin is None:
            self._preview_source=None;self._preview_model=None
            self.canvas.delete("all")
            self.canvas.create_text(self.canvas.winfo_width()/2,self.canvas.winfo_height()/2,text="Your skin goes here",fill=MUTED,font=("Ink Free",16))
            return
        slim=self.model.get().startswith("Slim")
        cached=self._preview_source
        if cached is None or cached[0] is not self.skin or cached[1] is not self.cape or cached[2]!=slim:
            atlas,geometry=prepare_model(self.skin,self.cape,slim,False)
            self._preview_model=(atlas,geometry,prepare_preview_mesh(atlas,geometry))
            self._preview_source=(self.skin,self.cape,slim)
        atlas,geometry,mesh=self._preview_model
        size=max(150,self.canvas.winfo_width()),max(180,self.canvas.winfo_height())
        image=preview_model(atlas,geometry,size,self.yaw,self.pitch,mesh);self._image=ImageTk.PhotoImage(image,master=self.canvas)
        self.canvas.delete("all");self.canvas.create_image(size[0]/2,size[1]/2,image=self._image)
    def export(self):
        if self.draft is not None:messagebox.showerror("Add this skin first","Click Add to pack before exporting, or Remove skin to clear the draft.",parent=self.parent);return
        if not self.skins:messagebox.showerror("Add a skin first","Add one or more skin PNGs before making your pack.",parent=self.parent);return
        path=filedialog.asksaveasfilename(parent=self.parent,title="Save your skin pack",defaultextension=".mcpack",filetypes=[("Minecraft skin pack","*.mcpack")],initialfile="My-Skin-Pack.mcpack")
        if not path:return
        try:
            self.save_current()
            result=export_collection(self.skins,path,self.name.get(),include_custom=True)
            self.status.set(f"Ta-da! All {result['skins']} skins are in one pack ({result['variants']} versions). Open the .mcpack in Minecraft to import it.")
            note="\n\nCapes and zombie poses were kept in the preview. This export uses standard player models." if result["preview_only"] else ""
            if result["enhanced_skins"]:note="\n\nCape textures are included. For Minecraft to load them, use Install skins in Skin Studio instead of normal importing."
            poses=sum(bool(s.get("zombie")) for s in self.skins)
            messagebox.showinfo("Skin pack ready",f"Saved {result['skins']} skins in one pack:\n{path}"+note,parent=self.parent)
        except (OSError,ValueError) as exc:messagebox.showerror("Couldn't make the pack",str(exc),parent=self.parent)
    def destroyed(self,event):
        if event.widget==self.parent and self._preview_job is not None:
            self.parent.after_cancel(self._preview_job);self._preview_job=None


if __name__=="__main__":
    root=tk.Tk();root.title("Prism Skin Studio");root.geometry("1000x900");root.configure(bg=BG)
    from PrismAbout import show_about
    menu=tk.Menu(root)
    menu.add_command(label="About Prism",command=lambda:show_about(root))
    root.configure(menu=menu)
    SkinStudio(root);root.mainloop()
