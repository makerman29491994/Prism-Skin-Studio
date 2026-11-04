"""Reversible native skin-pack installation into Minecraft's empty custom slot."""
import csv,hashlib,json,subprocess,sys,time,uuid,zipfile
from pathlib import Path,PurePosixPath
from PrismInstalledPacks import _plain_directory,prism_pack


def game_skin_roots():
    candidates=[Path(f"{drive}:/XboxGames/Minecraft for Windows/Content/data/skin_packs") for drive in "CDEFGHIJKLMNOPQRSTUVWXYZ"]
    roots=[]
    for path in candidates:
        try:
            if path.is_dir():roots.append(path)
        except OSError:
            # Other XboxGames drives can exist but deny this process access.
            continue
    return roots


def checked_root(path):
    root=_plain_directory(path)
    if root.name!="skin_packs" or root.parent.name!="data":
        raise ValueError("Choose Minecraft's Content/data/skin_packs folder.")
    if not (root/"vanilla").is_dir() or not (root/"persona").is_dir():
        raise ValueError("This folder is missing Minecraft's vanilla and persona packs.")
    return root


def minecraft_running():
    if sys.platform!="win32":return False
    try:result=subprocess.run(["tasklist","/FO","CSV","/NH"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
    except (OSError,subprocess.CalledProcessError) as exc:raise ValueError("Couldn't check whether Minecraft is closed. Close Minecraft and try again.") from exc
    return any(row and row[0].lower() in ("minecraft.windows.exe","minecraftpreview.exe") for row in csv.reader(result.stdout.splitlines()))


def _snapshot(path):
    result={}
    for file in path.rglob("*"):
        if file.is_symlink() or (hasattr(file,"is_junction") and file.is_junction()):
            raise ValueError("Linked files or folders cannot be backed up.")
        if file.is_file():result[str(file.relative_to(path))]=hashlib.sha256(file.read_bytes()).hexdigest()
    return result


def _move_directory(source,destination):
    # Windows scanners can briefly retain a directory handle after verification.
    for attempt in range(5):
        try:return source.rename(destination)
        except PermissionError as exc:
            if getattr(exc,"winerror",None) not in (5,32,33) or attempt==4:raise
            time.sleep(.05*2**attempt)


def install_pack(archive,root):
    if minecraft_running():raise ValueError("Close Minecraft before installing your cape pack.")
    root=checked_root(root);target=_plain_directory(root/"custom")
    if target.exists() and not prism_pack(target):
        try:skins=json.loads((target/"skins.json").read_text(encoding="utf-8-sig"))["skins"]
        except (OSError,ValueError,KeyError,TypeError):raise ValueError("The custom slot is not an empty Minecraft pack or a Prism pack.")
        if skins:raise ValueError("The custom slot contains another tool's skins. Back them up and clear that slot before installing with Prism.")
    before=_snapshot(target) if target.exists() else None
    storage=_plain_directory(root.parent/"prism_cape_backups")
    run=storage/uuid.uuid4().hex;run.mkdir(parents=True)
    stage=run/"prepared";stage.mkdir()
    with zipfile.ZipFile(archive) as z:
        if sum(i.file_size for i in z.infolist())>100*1024*1024:raise ValueError("Pack is larger than 100 MiB.")
        names=set()
        for info in z.infolist():
            name=PurePosixPath(info.filename)
            if name.is_absolute() or any(p in ("..","") or ":" in p or "\\" in p for p in name.parts):raise ValueError("Unsafe pack path.")
            key=str(name).lower()
            if key in names:raise ValueError("Duplicate pack path.")
            names.add(key)
            if info.is_dir():continue
            if (info.external_attr>>16)&0o170000==0o120000:raise ValueError("Linked pack files are not supported.")
            destination=stage.joinpath(*name.parts);destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(z.read(info))
    pack=prism_pack(stage)
    if not pack:raise ValueError("Install a pack created by Prism Skin Studio.")
    definitions=json.loads((stage/"skins.json").read_text())
    for skin in definitions["skins"]:
        if skin["geometry"] not in ("geometry.humanoid.custom","geometry.humanoid.customSlim"):raise ValueError("Unsupported player model.")
        for field in ("texture","cape"):
            if field in skin:
                file=stage/skin[field]
                if file.parent!=stage or not file.is_file():raise ValueError("A skin or cape texture is missing.")
    receipt={"target":str(target),"installed_uuid":pack["uuid"],"original_files":before,"installed_files":_snapshot(stage)}
    (run/"receipt.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
    # Recheck immediately before the two same-volume directory renames.
    if (target.exists() and _snapshot(target)!=before) or (not target.exists() and before is not None):
        raise ValueError("The custom slot changed during preparation. Try again.")
    if target.exists():_move_directory(target,run/"original")
    try:_move_directory(stage,target)
    except Exception:
        if (run/"original").exists():_move_directory(run/"original",target)
        raise
    return run/"receipt.json"


def undo_install(receipt_path):
    if minecraft_running():raise ValueError("Close Minecraft before undoing the cape installation.")
    receipt_path=Path(receipt_path);receipt=json.loads(receipt_path.read_text(encoding="utf-8"))
    target=_plain_directory(receipt["target"]);root=checked_root(target.parent)
    run=_plain_directory(receipt_path.parent)
    if target.name!="custom" or run.parent!=root.parent/"prism_cape_backups":raise ValueError("Invalid installation receipt.")
    pack=prism_pack(target)
    if not pack or pack["uuid"]!=receipt["installed_uuid"] or _snapshot(target)!=receipt["installed_files"]:
        raise ValueError("The installed pack changed. Nothing was replaced.")
    original=run/"original"
    _plain_directory(original)
    if receipt["original_files"] is not None and (not original.exists() or _snapshot(original)!=receipt["original_files"]):
        raise ValueError("The original backup did not pass its file check.")
    saved=run/("removed_"+uuid.uuid4().hex)
    _move_directory(target,saved)
    try:
        if original.exists():_move_directory(original,target)
    except Exception:
        _move_directory(saved,target);raise
    return target


def latest_receipt(root):
    root=checked_root(root);pack=prism_pack(root/"custom")
    if not pack:return None
    storage=root.parent/"prism_cape_backups"
    if not storage.is_dir():return None
    for receipt in sorted(storage.glob("*/receipt.json"),key=lambda p:p.stat().st_mtime,reverse=True):
        try:
            data=json.loads(receipt.read_text(encoding="utf-8"))
            if data["installed_uuid"]==pack["uuid"] and Path(data["target"])==root/"custom":return receipt
        except (OSError,ValueError,KeyError):continue
    return None
