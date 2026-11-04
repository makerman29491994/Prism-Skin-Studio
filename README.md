
<img width="1254" height="1254" alt="Skin-Studio-logo" src="https://github.com/user-attachments/assets/94b29410-cfb9-41f6-86e9-55381f523ba1" />
# Prism Skin Studio

Windows app for creating and installing Minecraft Bedrock skin packs. Current version: **1.3.14**.

Create multi-skin Minecraft Bedrock `.mcpack` files from PNG skins, preview classic/slim models and capes with mouse orbit, manage Prism installations, and use reversible local cape installation. Close Minecraft before any install or restore operation.

## Features

- Build packs with multiple PNG skins and individual capes.
- Preview classic and slim skins with mouse rotation.
- Name and organize skins within a pack.
- Install Studio collections or saved Prism `.mcpack` files through **Install skins**.
- Save pack copies, manage installed Prism packs and undo installations.

For capes, use **Install skins**; ordinary Minecraft `.mcpack` import may ignore cape data. Close Minecraft before installing or restoring a pack.

## Run from source (Windows)

Use Python 3.12 with Tkinter installed (the standard python.org Windows installer includes it).

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python src/main.py
```

## Test

From the repository root:

```powershell
python tools/check-startup.py
python tools/check.py
```

Tests use generated temporary fixtures. They do not modify a real Minecraft installation.

## Build a Windows executable

```powershell
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm app.spec
```

The executable is written to `dist/Prism Skin Studio.exe`. Alternatively, run **Build Windows app** manually from GitHub Actions; it uploads a downloadable build artifact and does not publish a release automatically.

## Licensing and public release

This repository is public. No open-source license has been selected for the application's source; public visibility does not grant a license to reuse or redistribute it. Third-party code remains under its own licenses; see [notices](THIRD_PARTY_NOTICES.md). Not an official Minecraft or Mine-imator product.

## AI Usage
Ai was used as the main programmer for this project. I don't really know how to code :( 
