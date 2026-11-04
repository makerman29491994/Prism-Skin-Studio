"""Green handwritten installed-pack manager, opened from Skin Studio."""
import tkinter as tk
from tkinter import filedialog,messagebox
from pathlib import Path
from PrismInstalledPacks import minecraft_skin_roots,scan_packs,remove_pack,restore_pack,purge_removed
from PrismSkinTools import BG,CARD,INK,MUTED,MINT,EDGE,SketchButton


class InstalledPacks:
    def __init__(self,studio):
        self.studio=studio;self.roots=minecraft_skin_roots();self.packs=[]
        self.window=window=tk.Toplevel(studio.parent)
        window.title("Prism | Installed Skin Packs");window.geometry("820x640");window.minsize(700,560)
        window.configure(bg=BG);window.transient(studio.parent.winfo_toplevel())
        window.iconphoto(False,studio._header_logo)
        theme=getattr(studio.parent.winfo_toplevel(),"_prism_theme_window",None)
        if theme:window.after(100,lambda:theme(window))
        outer=tk.Frame(window,bg=BG,padx=24,pady=20);outer.pack(fill="both",expand=True)
        heading=tk.Frame(outer,bg=BG);heading.pack(fill="x")
        tk.Label(heading,text="Your installed packs",font=("Ink Free",26,"bold"),bg=BG,fg=INK,anchor="w").pack(side="left")
        tk.Label(outer,text="Finished testing? Make a little room.",font=("Ink Free",14),bg=BG,fg=MUTED,anchor="w").pack(fill="x",pady=(3,12))
        card=studio.paper(outer);card.master.pack(fill="both",expand=True)
        tk.Label(card,text="Packs made with Prism Skin Studio",font=("Ink Free",16,"bold"),bg=CARD,fg=MINT,anchor="w").pack(fill="x",pady=(0,8))
        listing=tk.Frame(card,bg=CARD);listing.pack(fill="both",expand=True)
        self.list=tk.Listbox(listing,height=6,bg=BG,fg=INK,selectbackground=MINT,selectforeground=BG,font=("Ink Free",15),activestyle="none",exportselection=False,highlightthickness=1,highlightbackground=EDGE,highlightcolor=MINT,borderwidth=0)
        self.list.pack(side="left",fill="both",expand=True)
        self.details=tk.StringVar(window)
        tk.Label(card,textvariable=self.details,font=("Ink Free",11),bg=CARD,fg=MUTED,anchor="w",justify="left",wraplength=690,height=4).pack(fill="x",pady=(8,2))
        self.list.bind("<<ListboxSelect>>",self.selected)
        actions=tk.Frame(outer,bg=BG);actions.pack(fill="x",pady=(12,8))
        SketchButton(actions,"Refresh",self.refresh,105).pack(side="left",padx=3)
        SketchButton(actions,"Find folder…",self.find_folder,135).pack(side="left",padx=3)
        SketchButton(actions,"Remove selected",self.remove,180,True).pack(side="right",padx=3)
        SketchButton(actions,"Restore selected",self.restore,170).pack(side="right",padx=3)
        self.status=tk.StringVar(window)
        tk.Label(outer,textvariable=self.status,font=("Ink Free",12),bg=BG,fg=MUTED,anchor="w",justify="left",wraplength=740).pack(fill="x")
        tk.Label(outer,text="Close Minecraft first. Remove selected permanently deletes that pack.\nExported pack files and original game-slot backups are kept.",font=("Ink Free",11),bg=BG,fg=MUTED,anchor="w",justify="left").pack(fill="x",pady=(8,0))
        self.refresh()

    def refresh(self):
        self.roots=list(dict.fromkeys(self.roots+minecraft_skin_roots()))
        self.packs,warnings=scan_packs(self.roots)
        self.list.delete(0,"end")
        for pack in self.packs:self.list.insert("end",("Removed · " if pack["removed"] else "Installed cape pack · " if pack.get("native") else "Installed · ")+pack["name"])
        self.details.set("Select a pack to see where it is stored.")
        installed=sum(not p["removed"] for p in self.packs)
        self.status.set(f"{installed} installed · {len(self.packs)-installed} backed up" if self.packs else "No Prism skin packs found. Import a Prism .mcpack, then refresh, or choose your skin_packs folder.")
        if warnings:self.status.set(self.status.get()+"\nSome folders could not be read: "+warnings[0])

    def chosen(self):
        selection=self.list.curselection()
        return self.packs[selection[0]] if selection else None

    def selected(self,event=None):
        pack=self.chosen()
        if pack:self.details.set(str(pack["path"])+f"\n{pack.get('skin_count',0)} skins · {pack.get('cape_count',0)} capes"+("\nAn old backup: restore it or remove it permanently." if pack["removed"] else "\nRemoval restores the previous custom slot and deletes this pack." if pack.get("native") else "\nReady to remove permanently."))

    def find_folder(self):
        folder=filedialog.askdirectory(parent=self.window,title="Choose Minecraft's skin_packs folder")
        if not folder:return
        path=Path(folder)
        if path.name!="skin_packs":
            messagebox.showerror("Choose skin_packs","Select Minecraft's skin_packs folder, in com.mojang or Content/data.",parent=self.window);return
        self.roots.append(path);self.refresh()

    def remove(self):
        pack=self.chosen()
        if not pack:
            self.status.set("Select a pack to remove.");return
        if not messagebox.askyesno("Remove selected pack?",f"Permanently remove {pack['name']}?\n\nThis cannot be undone. Exported .mcpack files stay where you saved them.\n\nClose Minecraft first.",parent=self.window):return
        try:
            from PrismCapeInstall import minecraft_running
            if minecraft_running():raise ValueError("Close Minecraft before removing packs.")
            if pack["removed"]:purge_removed([pack])
            else:
                before,_=scan_packs([pack["root"]]);known={p["path"] for p in before if p["removed"]}
                remove_pack(pack)
                after,_=scan_packs([pack["root"]])
                removed=[p for p in after if p["removed"] and p["uuid"]==pack["uuid"] and p["path"] not in known]
                if len(removed)!=1:raise ValueError("Pack was removed, but its backup could not be uniquely verified for deletion. Refresh the list.")
                purge_removed(removed)
            self.refresh();self.status.set(f"Removed {pack['name']} permanently.")
        except (OSError,ValueError) as exc:messagebox.showerror("Couldn't remove pack",str(exc),parent=self.window)

    def restore(self):
        pack=self.chosen()
        if not pack or not pack["removed"]:
            self.status.set("Select a removed pack to restore.");return
        try:
            restore_pack(pack);self.refresh();self.status.set(f"Restored {pack['name']}. Reopen Minecraft to see it.")
        except (OSError,ValueError) as exc:messagebox.showerror("Couldn't restore pack",str(exc),parent=self.window)

    def delete_removed(self):
        self.refresh()
        removed=[pack for pack in self.packs if pack["removed"]]
        if not removed:self.status.set("There are no removed packs to delete.");return
        if not messagebox.askyesno("Permanently delete removed packs?",f"Delete all {len(removed)} removed pack backups?\n\nThese packs can no longer be restored afterward. Installed packs and original-slot backups needed for Undo stay in place.",parent=self.window):return
        try:
            count=purge_removed(removed);self.refresh();self.status.set(f"Permanently deleted {count} removed pack backups.")
        except (OSError,ValueError) as exc:
            self.refresh();messagebox.showerror("Couldn't delete all removed packs",str(exc),parent=self.window)
