"""Launch Prism Skin Studio, independently of the combined Prism application."""
import tkinter as tk
import sys
from tkinter import font as tkfont,ttk
from PrismAbout import APP_NAME,show_about

def main():
    root=tk.Tk();root.title(APP_NAME);root.geometry("1000x960");root.minsize(960,920)
    root.configure(background='#14221b')
    # Native Windows ttk themes ignore our custom field backgrounds.
    # Select a fully stylable theme before creating any app controls.
    style=ttk.Style(root);style.theme_use("clam")
    style.configure(".",background='#14221b',foreground='#e8f5e8')
    style.configure("TEntry",fieldbackground='#14221b',foreground='#e8f5e8',insertcolor='#e8f5e8')
    style.configure("TCombobox",fieldbackground='#14221b',foreground='#e8f5e8',background='#1d3025',arrowcolor='#a8dca0')
    root.option_add("*TCombobox*Listbox.background",'#14221b')
    root.option_add("*TCombobox*Listbox.foreground",'#e8f5e8')
    root.option_add("*TCombobox*Listbox.selectBackground",'#a8dca0')
    root.option_add("*TCombobox*Listbox.selectForeground",'#14221b')
    def theme_window(window):
        if sys.platform!="win32":return
        try:
            import ctypes
            from ctypes import wintypes
            get_parent=ctypes.windll.user32.GetParent
            get_parent.argtypes=[wintypes.HWND];get_parent.restype=wintypes.HWND
            hwnd=get_parent(window.winfo_id())
            attribute=ctypes.windll.dwmapi.DwmSetWindowAttribute
            attribute.argtypes=[wintypes.HWND,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]
            for key,value in ((20,1),(35,1778196),(36,15267304),(34,6917218)):
                setting=ctypes.c_int(value);attribute(hwnd,key,ctypes.byref(setting),ctypes.sizeof(setting))
        except (AttributeError,OSError,tk.TclError):pass
    root._prism_theme_window=theme_window
    root.bind("<Map>",lambda event:root.after_idle(lambda:theme_window(root)) if event.widget is root else None,add="+")
    families=set(tkfont.families(root))
    family="Ink Free" if "Ink Free" in families else "Segoe Print" if "Segoe Print" in families else "TkDefaultFont"
    for name in ("TkDefaultFont","TkTextFont","TkMenuFont","TkCaptionFont","TkSmallCaptionFont"):
        tkfont.nametofont(name,root=root).configure(family=family,size=13)
    from PrismSkinTools import SkinStudio,SketchButton
    topbar=tk.Frame(root,background='#14221b');topbar.pack(fill="x",padx=24,pady=(4,0))
    about=SketchButton(topbar,"About",lambda:show_about(root),78)
    about.configure(height=28);about.pack(side="right")
    root._skin_studio = app = SkinStudio(root)
    root.iconphoto(True,app._header_logo)
    root.mainloop()

if __name__=="__main__":main()
