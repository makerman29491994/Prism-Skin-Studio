
<img width="1254" height="1254" alt="Skin-Studio-logo" src="https://github.com/user-attachments/assets/94b29410-cfb9-41f6-86e9-55381f523ba1" />

# Prism Skin Studio

Windows app for creating and installing Minecraft Bedrock skin packs. Current version: **1.3.16**.

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
python -m PyInstaller --noconfirm --clean app.spec
python tools/verify-packaging.py . "dist/Prism Skin Studio.exe"
```

The executable is written to `dist/Prism Skin Studio.exe`. Alternatively, run **Build Windows app** manually from GitHub Actions; it uploads a downloadable build artifact and does not publish a release automatically.

The build excludes Pillow's optional NumPy integration, which Skin Studio does not use. All Pillow image codecs and the cryptography runtime remain included. Packaging verification runs the fixture suite against modules extracted from the executable, with installed third-party packages and application source imports disabled.

## Licensing and public release

The application source is licensed under the [Apache License 2.0](LICENSE). Third-party dependencies retain their own licenses; see [third-party notices](THIRD_PARTY_NOTICES.md). User-provided models and textures remain subject to their respective licenses. This is not an official Minecraft or Mine-imator product.

## AI Usage
Ai was used as the main programmer for this project. I don't really know how to code :( 

Skin PNGs now suggest Slim or Classic arms automatically from transparent arm padding. Legacy and ambiguous skins default to Classic. Arm size remains editable, and each skin retains its manual choice.

Picking another PNG replaces the displayed draft or selected pack skin in place. Custom names and capes stay attached, arm size is suggested again, and invalid files or cancelled picks leave the skin unchanged.
