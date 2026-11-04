"""The Skin Studio Marketplace host picker. No account or purchase changes."""
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox

from PrismSkinTools import BG, CARD, INK, MUTED, MINT, EDGE, SketchButton, SketchCheck
from PrismSkinPack import export_collection
from PrismMarketplaceInstall import marketplace_roots, checked_root, scan_marketplace, replace_pack, restore_pack


class MarketplaceInstaller:
    def __init__(self, studio):
        self.studio = studio
        self.roots = marketplace_roots(); self.packs = []; self.visible = []
        self.window = w = tk.Toplevel(studio.parent)
        w.title("Prism | Restore original packs")
        height=min(660,max(620,w.winfo_screenheight()-100))
        x=max(0,(w.winfo_screenwidth()-840)//2)
        y=max(0,(w.winfo_screenheight()-height)//2-20)
        w.geometry(f"840x{height}+{x}+{y}"); w.minsize(780, 620)
        w.configure(bg=BG); w.transient(studio.parent.winfo_toplevel())
        w.iconphoto(False, studio._header_logo)
        theme = getattr(studio.parent.winfo_toplevel(), "_prism_theme_window", None)
        if theme:
            w.after(100, lambda: theme(w))
        outer = tk.Frame(w, bg=BG, padx=20, pady=16); outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1); outer.rowconfigure(2, weight=1)
        tk.Label(outer, text="Restore original packs", font=("Ink Free", 24, "bold"), bg=BG, fg=INK, anchor="w").grid(row=0,column=0,sticky="ew")
        tk.Label(outer, text="Restore packs previously replaced with Prism.", font=("Ink Free", 13), bg=BG, fg=MUTED, anchor="w").grid(row=1,column=0,sticky="ew",pady=(2,8))
        # Only the search/list panel flexes. Required controls live outside the
        # paper canvas, whose requested content height can exceed its viewport.
        card = studio.paper(outer); card.master.grid(row=2,column=0,sticky="nsew")
        tk.Label(card, text="Search earlier Prism replacements", font=("Ink Free", 15, "bold"), bg=CARD, fg=MINT, anchor="w").pack(fill="x", pady=(0, 5))
        self.search = tk.StringVar(w)
        search = tk.Entry(card, textvariable=self.search, bg=BG, fg=INK, insertbackground=INK,
                          relief="flat", highlightthickness=1, highlightbackground=EDGE, highlightcolor=MINT, font=("Ink Free", 14))
        search.pack(fill="x", pady=(0, 8))
        self.search.trace_add("write", lambda *args: self.filter())
        self.list = tk.Listbox(card, height=4, bg=BG, fg=INK, selectbackground=MINT, selectforeground=BG,
                               font=("Ink Free", 14), activestyle="none", exportselection=False, borderwidth=0,
                               highlightthickness=1, highlightbackground=EDGE, highlightcolor=MINT)
        self.list.pack(fill="both", expand=True)
        self.list.bind("<<ListboxSelect>>", self.selected)
        self.details = tk.StringVar(w, value="Select a pack. Type above to find its name.")
        self.details_label = tk.Label(outer, textvariable=self.details, font=("Ink Free", 11), bg=BG, fg=MUTED, anchor="w", justify="left", height=2)
        self.details_label.grid(row=3,column=0,sticky="ew",pady=(5,0))
        self.owns = tk.BooleanVar(w, value=False)
        self.ownership_check = SketchCheck(outer, "I own the selected Marketplace pack", self.owns)
        self.ownership_check.configure(bg=BG)
        
        actions = tk.Frame(outer, bg=BG); actions.grid(row=5,column=0,sticky="ew",pady=(2,4))
        SketchButton(actions, "Refresh", self.refresh, 105).pack(side="left")
        SketchButton(actions, "Find folder…", self.browse, 140).pack(side="left", padx=5)
        SketchButton(actions, "Install my skins…", self.install, 235, True).pack(side="right")
        SketchButton(actions, "Restore original", self.restore, 175).pack(side="right", padx=5)
        self.status = tk.StringVar(w)
        tk.Label(outer, textvariable=self.status, bg=BG, fg=MINT, font=("Ink Free", 11), height=2, justify="left", anchor="w").grid(row=6,column=0,sticky="ew")
        footer=tk.Frame(outer,bg=BG);footer.grid(row=7,column=0,sticky="ew",pady=(3,0));footer.columnconfigure(0,weight=1)
        note=tk.Label(footer, text="Restore earlier Prism replacements.\nClose Minecraft first. Backups are kept.", bg=BG, fg=MUTED, font=("Ink Free", 10), justify="left", anchor="w")
        note.grid(row=0,column=0,sticky="ew",padx=(0,8))
        SketchButton(footer, "Other install options…", studio.cape_installer, 230).grid(row=0,column=1,sticky="e")
        def fit_text(event):
            self.details_label.configure(wraplength=max(100,event.width-40))
            note.configure(wraplength=max(100,event.width-290))
        outer.bind("<Configure>",fit_text)
        self.refresh()

    def chosen(self):
        selection = self.list.curselection()
        return self.visible[selection[0]] if selection else None

    def filter(self, keep=None):
        query = self.search.get().strip().casefold()
        self.visible = [p for p in self.packs if query in p["name"].casefold()]
        self.list.delete(0, "end"); self.owns.set(False)
        self.details.set("Select a pack. Type above to find its name.")
        for index, pack in enumerate(self.visible):
            label = "Original backed up · " if pack.get("receipt") else ""
            duplicate = sum(p["name"] == pack["name"] for p in self.packs) > 1
            self.list.insert("end", label+pack["name"]+(" · "+pack["uuid"][:8] if duplicate else ""))
            if keep and pack["path"] == keep:
                self.list.selection_set(index); self.list.see(index); self.selected()

    def refresh(self, keep=None):
        self.roots = list(dict.fromkeys(self.roots+marketplace_roots()))
        self.packs, warnings = scan_marketplace(self.roots)
        self.packs = [p for p in self.packs if p.get("receipt")]
        self.filter(keep)
        self.status.set(f"{len(self.packs)} backed-up replacements found." if self.packs else "No earlier Prism replacements found.")
        if warnings:
            self.status.set(self.status.get()+" Some folders couldn't be read: "+warnings[0])

    def selected(self, event=None):
        self.owns.set(False)
        pack = self.chosen()
        if pack:
            self.details.set(pack["name"]+("\nOriginal backed up. Restore it before replacing again." if pack.get("receipt") else "\nYour saved Studio skins will replace this pack. The original is backed up."))

    def browse(self):
        folder = filedialog.askdirectory(parent=self.window, title="Choose Minecraft's premium_cache/skin_packs folder")
        if not folder:
            return
        try:
            self.roots.append(checked_root(folder)); self.refresh()
        except (OSError, ValueError) as exc:
            messagebox.showerror("Check the Marketplace folder", str(exc), parent=self.window)

    def install(self):
        self.status.set("Marketplace replacement has been removed. Use Restore original to recover an older pack."); return
        pack = self.chosen()
        if not pack:
            self.status.set("Select the Marketplace pack you want to replace."); return
        if pack.get("receipt"):
            self.status.set("Restore this pack's original files before replacing it again."); return
        if not self.owns.get():
            self.status.set("Confirm that you own the selected Marketplace pack first."); return
        try:
            if self.studio.draft is not None:
                raise ValueError("Click Add to pack for your current skin before installing.")
            self.studio.save_current()
            archive = None
            if not self.studio.skins:
                archive = filedialog.askopenfilename(parent=self.window, title="Choose an exported Prism pack", filetypes=[("Prism skin packs", "*.mcpack")])
                if not archive:
                    return
            contents = f"{len(self.studio.skins)} saved Studio skins" if not archive else Path(archive).name
            if not messagebox.askyesno("Replace this Marketplace pack?", f"Replace all skins in {pack['name']} with:\n{contents}\n\n{pack['path']}\n\nThe complete original pack will be backed up. Restore original puts it back.\n\nClose Minecraft first. Hive zombie-arm compatibility is still unverified. Continue?", parent=self.window):
                return
            with tempfile.TemporaryDirectory(prefix="prism_marketplace_") as temporary:
                if not archive:
                    archive = Path(temporary)/"pack.mcpack"
                    export_collection(self.studio.skins, archive, self.studio.name.get(), include_custom=True)
                receipt = replace_pack(archive, pack)
            self.refresh(pack["path"])
            self.status.set(f"Replaced {pack['name']}. Open Minecraft's Dressing Room and select your pack under Owned.")
            messagebox.showinfo("Marketplace pack replaced", f"Your Studio skins are installed through {pack['name']}.\n\nOpen Dressing Room → Classic Skins → Owned to select them.\nUse Restore original here to undo the replacement.\n\nBackup receipt:\n{receipt}\n\nThis confirms installation; visibility to other players on Hive still needs testing.", parent=self.window)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            messagebox.showerror("Couldn't replace Marketplace pack", str(exc), parent=self.window)

    def restore(self):
        pack = self.chosen()
        if not pack or not pack.get("receipt"):
            self.status.set("Select a pack marked Original backed up to restore it."); return
        if not messagebox.askyesno("Restore this Marketplace pack?", f"Put the original {pack['name']} files back?\n\nYour installed Studio version will be kept in the backup folder. Close Minecraft first.", parent=self.window):
            return
        try:
            restore_pack(pack["receipt"]); self.refresh(pack["path"])
            self.status.set(f"Original {pack['name']} restored. Reopen Minecraft to refresh it.")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            messagebox.showerror("Couldn't restore Marketplace pack", str(exc), parent=self.window)
