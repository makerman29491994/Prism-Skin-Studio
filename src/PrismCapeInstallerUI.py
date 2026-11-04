"""Direct native cape installation, with an original-slot backup and undo."""
import json,tempfile,tkinter as tk,zipfile
from tkinter import filedialog,messagebox
from pathlib import Path
from PrismCapeInstall import game_skin_roots,checked_root,install_pack,undo_install,latest_receipt
from PrismSkinPack import export_collection
from PrismInstalledPacks import prism_pack
from PrismSkinTools import BG,CARD,INK,MUTED,MINT,SketchButton


class CapeInstaller:
    def __init__(self,studio):
        self.studio=studio;self.pack_path=None;self.options_window=None
        roots=game_skin_roots()
        height=400 if roots else 460
        self.window=w=tk.Toplevel(studio.parent);w.title("Prism | Install skins")
        x=max(0,(w.winfo_screenwidth()-560)//2);y=max(0,(w.winfo_screenheight()-height)//2-20)
        w.geometry(f"560x{height}+{x}+{y}");w.minsize(540,height-20);w.configure(bg=BG)
        w.transient(studio.parent.winfo_toplevel());w.iconphoto(False,studio._header_logo)
        self.theme=getattr(studio.parent.winfo_toplevel(),"_prism_theme_window",None)
        if self.theme:w.after(100,lambda:self.theme(w))
        outer=tk.Frame(w,bg=BG,padx=20,pady=16);outer.pack(fill="both",expand=True)
        outer.columnconfigure(0,weight=1);outer.rowconfigure(2,weight=1)
        tk.Label(outer,text="Install skins",font=("Ink Free",24,"bold"),bg=BG,fg=INK,anchor="w").grid(row=0,column=0,sticky="ew")
        tk.Label(outer,text="Your whole pack, including capes.",font=("Ink Free",12),bg=BG,fg=MUTED,anchor="w").grid(row=1,column=0,sticky="ew",pady=(3,8))
        card=studio.paper(outer);card.master.grid(row=2,column=0,sticky="nsew")
        self.root_path=tk.StringVar(w,value=str(roots[0]) if roots else "")
        self.game_status=tk.StringVar(w)
        self.root_path.trace_add("write",self.refresh_game)
        self.pack_status=tk.StringVar(w)
        tk.Label(card,textvariable=self.pack_status,font=("Ink Free",14,"bold"),bg=CARD,fg=MINT,justify="left",anchor="w",wraplength=450).pack(fill="x",pady=(2,8))
        sources=tk.Frame(card,bg=CARD);sources.pack(fill="x",pady=(0,8))
        SketchButton(sources,"Choose .mcpack\u2026",self.choose_pack,195).pack(side="left")
        self.studio_button=SketchButton(sources,"Use Studio pack",self.use_studio,165)
        tk.Label(card,textvariable=self.game_status,font=("Ink Free",11),bg=CARD,fg=MUTED,anchor="w").pack(fill="x")
        self.folder_button=SketchButton(card,"Choose game folder\u2026",self.browse,220)
        self.refresh_game();self.use_studio()
        actions=tk.Frame(outer,bg=BG);actions.grid(row=3,column=0,sticky="ew",pady=(8,4))
        SketchButton(actions,"More options\u2026",self.more_options,165).pack(side="left")
        SketchButton(actions,"Install skins\u2026",self.install,210,True).pack(side="right")
        self.status=tk.StringVar(w,value="Close Minecraft before installing.")
        tk.Label(outer,textvariable=self.status,font=("Ink Free",11),bg=BG,fg=MUTED,justify="left",wraplength=510,height=2,anchor="w").grid(row=4,column=0,sticky="ew")

    def refresh_game(self,*args):
        found=bool(self.root_path.get())
        self.game_status.set("Minecraft found" if found else "Choose your Minecraft game folder")
        if found:self.folder_button.pack_forget()
        else:self.folder_button.pack(anchor="w",pady=(6,0))

    def more_options(self):
        if self.options_window is not None and self.options_window.winfo_exists():self.options_window.lift();return
        w=self.options_window=tk.Toplevel(self.window);w.title("Prism | More options")
        w.geometry("600x300");w.minsize(580,280);w.configure(bg=BG);w.transient(self.window)
        w.iconphoto(False,self.studio._header_logo)
        if self.theme:w.after(100,lambda:self.theme(w))
        frame=tk.Frame(w,bg=BG,padx=20,pady=16);frame.pack(fill="both",expand=True)
        tk.Label(frame,text="More options",font=("Ink Free",22,"bold"),bg=BG,fg=INK,anchor="w").pack(fill="x")
        tk.Label(frame,textvariable=self.root_path,font=("Ink Free",11),bg=BG,fg=MUTED,anchor="w",justify="left",wraplength=550).pack(fill="x",pady=(8,12))
        buttons=tk.Frame(frame,bg=BG);buttons.pack(fill="x")
        for row,column,text,command in ((0,0,"Choose game folder\u2026",self.browse),(0,1,"Save Studio copy\u2026",self.studio.export),(1,0,"Undo last install",self.undo),(1,1,"Restore old packs\u2026",self.marketplace)):
            SketchButton(buttons,text,command,260).grid(row=row,column=column,padx=3,pady=4)

    def use_studio(self):
        self.pack_path=None
        self.studio_button.pack_forget()
        self.studio.save_current()
        count=len(self.studio.skins);capes=sum(s.get("cape") is not None for s in self.studio.skins)
        self.pack_status.set(f"Studio pack: {count} skins \u00b7 {capes} capes")

    def choose_pack(self):
        path=filedialog.askopenfilename(parent=self.window,title="Open a saved Prism skin pack",filetypes=[("Prism skin packs","*.mcpack")])
        if not path:return
        try:
            if not prism_pack(Path(path)):raise ValueError("Choose a .mcpack created by Prism Skin Studio.")
            with zipfile.ZipFile(path) as z:skins=json.loads(z.read("skins.json"))["skins"]
            self.pack_path=path
            self.studio_button.pack(side="left",padx=4)
            name=Path(path).name
            if len(name)>48:name=name[:45]+"\u2026"
            self.pack_status.set(f"{name}\n{len(skins)} skins \u00b7 {sum(bool(s.get('cape')) for s in skins)} capes")
        except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile) as exc:messagebox.showerror("Check the skin pack",str(exc),parent=self.window)

    def marketplace(self):
        from PrismMarketplaceUI import MarketplaceInstaller
        MarketplaceInstaller(self.studio)

    def browse(self):
        path=filedialog.askdirectory(parent=self.window,title="Choose Minecraft's Content/data/skin_packs folder")
        if not path:return
        try:self.root_path.set(str(checked_root(path)))
        except (OSError,ValueError) as exc:messagebox.showerror("Check the game folder",str(exc),parent=self.window)

    def install(self):
        try:
            root=checked_root(self.root_path.get())
            if self.pack_path is None and self.studio.draft is not None:raise ValueError("Click Add to pack for the current skin before installing.")
            self.studio.save_current()
            archive=self.pack_path
            if not archive and not self.studio.skins:
                self.choose_pack();archive=self.pack_path
                if not archive:return
            if archive:
                with zipfile.ZipFile(archive) as z:definitions=json.loads(z.read("skins.json"))["skins"]
                count=len(definitions);capes=sum(bool(s.get("cape")) for s in definitions)
            else:count=len(self.studio.skins);capes=sum(s.get("cape") is not None for s in self.studio.skins)
            if not messagebox.askyesno("Install this skin pack?",f"Install {count} skins and {capes} capes?\n\nMinecraft folder:\n{root}\n\nYour previous custom pack will be backed up.\nClose Minecraft before continuing.",parent=self.window):return
            with tempfile.TemporaryDirectory(prefix="prism_cape_install_") as temporary:
                if archive is None:
                    archive=Path(temporary)/"pack.mcpack"
                    export_collection(self.studio.skins,archive,self.studio.name.get(),include_custom=True)
                receipt=install_pack(archive,root)
            self.status.set("Installed! Open Minecraft \u2192 Dressing Room \u2192 Classic Skins \u2192 Owned, then select your Prism pack.")
            messagebox.showinfo("Pack installed","Reopen Minecraft and select your pack under Dressing Room / Classic Skins / Owned.\n\nTo undo: More options / Undo last install.",parent=self.window)
        except (OSError,ValueError) as exc:messagebox.showerror("Couldn't install cape pack",str(exc),parent=self.window)

    def undo(self):
        try:
            root=checked_root(self.root_path.get());receipt=latest_receipt(root)
            if receipt is None:self.status.set("No active Prism cape installation to undo in that folder.");return
            if not messagebox.askyesno("Undo cape installation?","Restore the previous custom skin slot? Your Prism pack will stay in the backup.",parent=self.window):return
            undo_install(receipt);self.status.set("Previous skin slot restored. Reopen Minecraft to refresh it.")
        except (OSError,ValueError) as exc:messagebox.showerror("Couldn't undo cape install",str(exc),parent=self.window)
