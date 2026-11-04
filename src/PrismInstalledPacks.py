"""Discover Prism skin packs and move them out of Minecraft with undo."""
import io,json,os,re,shutil,uuid,zipfile
from pathlib import Path


def _io_path(path):
    """Keep Minecraft's trailing-dot folder names intact through Windows IO."""
    path=Path(path).absolute()
    if os.name!="nt":return path
    text=str(path)
    if text.startswith("\\\\?\\"):return path
    return Path("\\\\?\\UNC\\"+text[2:] if text.startswith("\\\\") else "\\\\?\\"+text)


def _display_path(path):
    text=str(path)
    if text.startswith("\\\\?\\UNC\\"):return Path("\\\\"+text[8:])
    return Path(text[4:] if text.startswith("\\\\?\\") else text)


def minecraft_skin_roots():
    roots=[]
    roaming=Path(os.environ.get("APPDATA",Path.home()/"AppData/Roaming"))
    local=Path(os.environ.get("LOCALAPPDATA",Path.home()/"AppData/Local"))
    for base in (roaming/"Minecraft Bedrock",roaming/"Minecraft Bedrock Preview"):
        roots.append(base/"games/com.mojang/skin_packs")
        users=base/"Users"
        if users.is_dir():roots.extend(p/"games/com.mojang/skin_packs" for p in users.iterdir() if p.is_dir())
    packages=local/"Packages"
    if packages.is_dir():
        for package in packages.glob("*Minecraft*"):
            roots.append(package/"LocalState/games/com.mojang/skin_packs")
    from PrismCapeInstall import game_skin_roots
    roots.extend(game_skin_roots())
    return sorted({p.absolute() for p in roots if p.is_dir()},key=str)


def _plain_directory(path):
    # Junctions and symlinks must never redirect a removal or restore.
    path=_io_path(path)
    for part in (path,*path.parents):
        if part.is_symlink() or (hasattr(part,"is_junction") and part.is_junction()):
            raise ValueError("Linked folders cannot be managed here.")
    return _display_path(path.resolve())


def prism_pack(path):
    try:
        path=_plain_directory(path)
        if _io_path(path).is_file():
            with zipfile.ZipFile(_io_path(path)) as archive:
                for name in ("manifest.json","skins.json"):
                    if archive.getinfo(name).file_size>4*1024*1024:raise ValueError("Pack metadata is too large.")
                manifest=json.loads(archive.read("manifest.json").decode("utf-8-sig"))
                skins=json.loads(archive.read("skins.json").decode("utf-8-sig"))
        else:
            manifest=json.loads((_io_path(path)/"manifest.json").read_text(encoding="utf-8-sig"))
            skins=json.loads((_io_path(path)/"skins.json").read_text(encoding="utf-8-sig"))
        header=manifest["header"]
        if header.get("description")!="Created with Prism Skin Studio":return None
        if not any(m.get("type")=="skin_pack" for m in manifest.get("modules",[])):return None
        if not re.fullmatch(r"prism_[0-9a-f]{32}",skins.get("serialize_name","")):return None
        pack_id=str(uuid.UUID(header["uuid"]))
        definitions=skins.get("skins",[])
        return {"name":str(header["name"]),"uuid":pack_id,"path":path,"skin_count":len(definitions),"cape_count":sum(bool(s.get("cape")) for s in definitions),"zombie_count":sum(s.get("animations",{}).get("move.arms")=="animation.player.move.arms.zombie" for s in definitions),"archive":_io_path(path).is_file()}
    except (OSError,ValueError,KeyError,TypeError,AttributeError,zipfile.BadZipFile):return None


def scan_packs(roots):
    packs=[];warnings=[]
    for candidate in dict.fromkeys(map(Path,roots)):
        try:
            root=_plain_directory(candidate)
            if root.name!="skin_packs":raise ValueError("Choose Minecraft's skin_packs folder.")
            if root.is_dir():
                for child in root.iterdir():
                    pack=prism_pack(child)
                    if pack:
                        native=root.parent.name=="data" and child.name=="custom"
                        packs.append(dict(pack,root=root,removed=False,native=native))
            if root.parent.name=="data":
                storage=root.parent/"prism_cape_backups"
                if storage.is_dir():
                    _plain_directory(storage)
                    for receipt in storage.glob("*/receipt.json"):
                        try:
                            _plain_directory(receipt.parent)
                            record=json.loads(receipt.read_text(encoding="utf-8"))
                            if Path(record["target"])!=root/"custom":continue
                            for saved in receipt.parent.glob("removed_*"):
                                pack=prism_pack(saved)
                                if pack and pack["uuid"]==record["installed_uuid"]:
                                    packs.append(dict(pack,root=root,removed=True,native=True,receipt=receipt))
                        except (OSError,ValueError,KeyError,TypeError):continue
            backup=root.parent/"prism_removed_skin_packs"
            if backup.is_dir():
                _plain_directory(backup)
                for entry in backup.iterdir():
                    try:
                        _plain_directory(entry)
                        record=json.loads((entry/"record.json").read_text(encoding="utf-8"))
                        pack=prism_pack(entry/"pack")
                        if pack and pack["uuid"]==record["uuid"] and Path(record["original"]).parent==root:
                            packs.append(dict(pack,root=root,removed=True,record=entry/"record.json",original=Path(record["original"])))
                    except (OSError,ValueError,KeyError,TypeError):continue
        except (OSError,ValueError) as exc:warnings.append(f"{candidate}: {exc}")
    return sorted(packs,key=lambda p:(p["removed"],p["name"].lower(),str(p["path"]))),warnings


def remove_pack(pack):
    root=_plain_directory(pack["root"]);source=_plain_directory(pack["path"])
    current=prism_pack(source)
    if root.name!="skin_packs" or source.parent!=root or not current or current["uuid"]!=pack["uuid"]:
        raise ValueError("This is no longer a verified installed Prism pack. Refresh the list.")
    if root.parent.name=="data" and source.name=="custom":
        from PrismCapeInstall import latest_receipt,undo_install
        receipt=latest_receipt(root)
        if receipt is None:raise ValueError("No verified original-slot backup was found for this direct installation.")
        return undo_install(receipt)
    backup=root.parent/"prism_removed_skin_packs"
    _plain_directory(backup)
    entry=backup/uuid.uuid4().hex
    entry.mkdir(parents=True)
    record=entry/"record.json"
    try:
        record.write_text(json.dumps({"original":str(source),"uuid":current["uuid"]},indent=2),encoding="utf-8")
        _io_path(source).rename(_io_path(entry/"pack"))
    except Exception:
        record.unlink(missing_ok=True);entry.rmdir()
        raise
    return entry


def restore_pack(pack):
    root=_plain_directory(pack["root"]);source=_plain_directory(pack["path"])
    if pack.get("native"):
        from PrismCapeInstall import checked_root,install_pack,_snapshot
        checked_root(root)
        storage=_plain_directory(root.parent/"prism_cape_backups")
        if source.parent.parent!=storage or not source.name.startswith("removed_"):
            raise ValueError("This is not a direct-install pack backup.")
        record=json.loads((source.parent/"receipt.json").read_text(encoding="utf-8"))
        current=prism_pack(source)
        if Path(record["target"])!=root/"custom" or not current or current["uuid"]!=pack["uuid"] or current["uuid"]!=record["installed_uuid"] or _snapshot(source)!=record["installed_files"]:
            raise ValueError("The direct-install backup no longer matches its receipt.")
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,"w",zipfile.ZIP_DEFLATED) as archive:
            for file in source.rglob("*"):
                if file.is_file():archive.write(file,file.relative_to(source).as_posix())
        stream.seek(0)
        return install_pack(stream,root)
    backup=_plain_directory(root.parent/"prism_removed_skin_packs")
    if source.name!="pack" or source.parent.parent!=backup:
        raise ValueError("This is not a Prism pack backup.")
    record_path=source.parent/"record.json"
    record=json.loads(record_path.read_text(encoding="utf-8"))
    destination=Path(record["original"])
    _plain_directory(destination)
    current=prism_pack(source)
    if root.name!="skin_packs" or destination.parent!=root or not current or current["uuid"]!=record["uuid"] or current["uuid"]!=pack["uuid"]:
        raise ValueError("The backup no longer matches this pack. Refresh the list.")
    if _io_path(destination).exists():raise FileExistsError("A pack already uses that folder. Nothing was overwritten.")
    root.mkdir(parents=True,exist_ok=True)
    _io_path(source).rename(_io_path(destination))
    # Retain the small receipt; scans ignore receipts without a pack folder.
    return destination


def purge_removed(packs):
    """Permanently delete only the explicitly supplied verified removed backups."""
    verified=[]
    for pack in packs:
        if not pack.get("removed"):raise ValueError("Installed packs cannot be permanently deleted here.")
        root=_plain_directory(pack["root"]);source=_plain_directory(pack["path"])
        current=prism_pack(source)
        if not current or current["uuid"]!=pack["uuid"]:raise ValueError("A removed pack changed. Refresh before deleting.")
        if pack.get("native"):
            from PrismCapeInstall import _snapshot
            storage=_plain_directory(root.parent/"prism_cape_backups")
            if source.parent.parent!=storage or not re.fullmatch(r"removed_[0-9a-f]{32}",source.name):raise ValueError("This is not a removed cape-pack backup.")
            record=json.loads((source.parent/"receipt.json").read_text(encoding="utf-8"))
            if source.parent.parent!=storage or not re.fullmatch(r"removed_[0-9a-f]{32}",source.name) or Path(record["target"])!=root/"custom" or current["uuid"]!=record["installed_uuid"] or _snapshot(source)!=record["installed_files"]:
                raise ValueError("This is not a verified removed cape pack.")
        else:
            storage=_plain_directory(root.parent/"prism_removed_skin_packs")
            if source.name!="pack" or source.parent.parent!=storage or not re.fullmatch(r"[0-9a-f]{32}",source.parent.name):raise ValueError("This is not a removed pack backup.")
            record=json.loads((source.parent/"record.json").read_text(encoding="utf-8"))
            if source.name!="pack" or source.parent.parent!=storage or not re.fullmatch(r"[0-9a-f]{32}",source.parent.name) or Path(record["original"]).parent!=root or current["uuid"]!=record["uuid"]:
                raise ValueError("This is not a verified removed pack.")
            if source.is_dir():
                from PrismCapeInstall import _snapshot
                _snapshot(source)  # Reject nested links before recursive removal.
        if source not in verified:verified.append(source)
    deleted=0
    for source in verified:
        try:
            if _io_path(source).is_file():_io_path(source).unlink()
            else:shutil.rmtree(_io_path(source))
            deleted+=1
        except OSError as exc:raise OSError(f"Deleted {deleted} backups before an error: {exc}") from exc
    return deleted
