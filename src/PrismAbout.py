"""Standalone app identity."""
APP_NAME = 'Prism Skin Studio'
APP_VERSION = "1.3.7"

def show_about(parent):
    from tkinter import messagebox
    messagebox.showinfo("About "+APP_NAME, APP_NAME+"\nVersion "+APP_VERSION, parent=parent)
