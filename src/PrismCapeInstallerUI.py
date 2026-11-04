"""Direct native cape installation, with an original-slot backup and undo."""
import json,tempfile,tkinter as tk,zipfile
from tkinter import filedialog,messagebox
from pathlib import Path
from PrismCapeInstall import game_skin_roots,checked_root,install_pack,undo_install,latest_receipt
from PrismSkinPack import export_collection
from PrismSkinTools import BG,CARD,INK,MUTED,MINT,SketchButton


class CapeInstaller:
    def __init__(self,studio):
        self.studio=studio
        self.window=w=tk.Toplevel(studio.parent);w.title("Prism | Direct install")
        x=max(0,(w.winfo_screenwidth()-640)//2);y=max(0,(w.winfo_screenheight()-420)//2-20)
        w.geometry(f"640x420+{x}+{y}");w.minsize(620,400);w.configure(bg=BG)
        w.transient(studio.parent.winfo_toplevel());w.iconphoto(False,studio._header_logo)
        theme=getattr(studio.parent.winfo_toplevel(),"_prism_theme_window",None)
        if theme:w.after(100,lambda:theme(w))
        outer=tk.Frame(w,bg=BG,padx=20,pady=16);outer.pack(fill="both",expand=True)
        outer.columnconfigure(0,weight=1);outer.rowconfigure(2,weight=1)
        tk.Label(outer,text="Direct install",font=("Ink Free",24,"bold"),bg=BG,fg=INK,anchor="w").grid(row=0,column=0,sticky="ew")
        tk.Label(outer,text="Use Minecraft's custom skin slot. The previous slot is backed up.",font=("Ink Free",12),bg=BG,fg=MUTED,anchor="w").grid(row=1,column=0,sticky="ew",pady=(3,8))
        card=studio.paper(outer);card.master.grid(row=2,column=0,sticky="nsew")
        roots=game_skin_roots();self.root_path=tk.StringVar(w,value=str(roots[0]) if roots else "")
        self.game_status=tk.StringVar(w)
        self.root_path.trace_add("write",lambda *args:self.game_status.set("Minecraft folder selected" if self.root_path.get() else "Choose your Minecraft game folder"))
        self.game_status.set("Minecraft found" if roots else "Choose your Minecraft game folder")
        tk.Label(card,textvariable=self.game_status,font=("Ink Free",15,"bold"),bg=CARD,fg=MINT,anchor="w").pack(fill="x",pady=(0,5))
        tk.Label(card,text="Installs your saved Studio skins, or lets you pick a pack file.\nClose Minecraft before installing.",font=("Ink Free",12),bg=CARD,fg=MUTED,justify="left",anchor="w",wraplength=530).pack(fill="x")
        SketchButton(card,"Choose game folderâ€¦",self.browse,220).pack(anchor="w",pady=(6,0))
        actions=tk.Frame(outer,bg=BG);actions.grid(row=3,column=0,sticky="ew",pady=(8,4))
        SketchButton(actions,"Undo last install",self.undo,180).pack(side="left")
        SketchButton(actions,"Install skinsâ€¦",self.install,210,True).pack(side="right")
        SketchButton(actions,"Restore old packs…",self.marketplace,185).pack(side="left",padx=4)
        self.status=tk.StringVar(w,value="Game updates may reset direct installs.")
        tk.Label(outer,textvariable=self.status,font=("Ink Free",11),bg=BG,fg=MUTED,justify="left",wraplength=590,height=2,anchor="w").grid(row=4,column=0,sticky="ew")

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
            if self.studio.draft is not None:raise ValueError("Click Add to pack for the current skin before installing.")
            self.studio.save_current()
            archive=None
            if not self.studio.skins:
                archive=filedialog.askopenfilename(parent=self.window,title="Choose a Prism cape pack",filetypes=[("Skin packs","*.mcpack")])
                if not archive:return
            if archive:
                with zipfile.ZipFile(archive) as z:definitions=json.loads(z.read("skins.json"))["skins"]
                count=len(definitions);poses=sum(s.get("animations",{}).get("move.arms")=="animation.player.move.arms.zombie" for s in definitions)
            else:count=len(self.studio.skins);poses=sum(bool(s.get("zombie")) for s in self.studio.skins)
            if not messagebox.askyesno("Install this cape pack?",f"Install into:\n{root/'custom'}\n\n{count} skins Â· {poses} with zombie arms\n\nPrism will keep the original slot in a backup before replacing it. Other built-in packs stay in place.\n\nClose Minecraft first. Continue?",parent=self.window):return
            with tempfile.TemporaryDirectory(prefix="prism_cape_install_") as temporary:
                if archive is None:
                    archive=Path(temporary)/"pack.mcpack"
                    export_collection(self.studio.skins,archive,self.studio.name.get(),include_custom=True)
                receipt=install_pack(archive,root)
            self.status.set("Installed! Open Minecraft â†’ Dressing Room â†’ Classic Skins â†’ Owned, then select your Prism pack.")
            messagebox.showinfo("Cape pack installed",f"Open Minecraft and select your pack under Classic Skins / Owned.\n\nBackup receipt:\n{receipt}\n\nIf a server filters custom skins, it may hide the cape. Use Undo last install to restore the previous slot.",parent=self.window)
        except (OSError,ValueError) as exc:messagebox.showerror("Couldn't install cape pack",str(exc),parent=self.window)

    def undo(self):
        try:
            root=checked_root(self.root_path.get());receipt=latest_receipt(root)
            if receipt is None:self.status.set("No active Prism cape installation to undo in that folder.");return
            if not messagebox.askyesno("Undo cape installation?","Restore the previous custom skin slot? Your Prism pack will stay in the backup.",parent=self.window):return
            undo_install(receipt);self.status.set("Previous skin slot restored. Reopen Minecraft to refresh it.")
        except (OSError,ValueError) as exc:messagebox.showerror("Couldn't undo cape install",str(exc),parent=self.window)
