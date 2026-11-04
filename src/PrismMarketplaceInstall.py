"""Local Marketplace host selection and reversible Skin Studio replacement.

Encryption interoperability reference (Unlicense):
https://github.com/FurDra64/McTools.rs (header.rs, crypto.rs, index.html).
This encodes the user's own textures; it does not decrypt purchased content or
change account entitlements. A cache entry is not proof of ownership.
"""
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import string
import struct
import uuid
import zipfile

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
from cryptography.hazmat.decrepit.ciphers.modes import CFB8
from PrismCapeInstall import minecraft_running, _move_directory
from PrismInstalledPacks import _plain_directory, prism_pack

LIMIT = 100 * 1024 * 1024
PERSONA_KEY = b"s5s5ejuDru4uchuF2drUFuthaspAbepE".ljust(32, b"\0")


def marketplace_roots():
    roaming = Path(os.environ.get("APPDATA", Path.home()/"AppData/Roaming"))
    local = Path(os.environ.get("LOCALAPPDATA", Path.home()/"AppData/Local"))
    candidates = []
    for base in (roaming/"Minecraft Bedrock", roaming/"Minecraft Bedrock Preview"):
        candidates.extend((base/"premium_cache/skin_packs", base/"games/com.mojang/premium_cache/skin_packs"))
        users = base/"Users"
        if users.is_dir():
            for user in users.iterdir():
                if user.is_dir():
                    candidates.extend((user/"premium_cache/skin_packs", user/"games/com.mojang/premium_cache/skin_packs"))
    packages = local/"Packages"
    if packages.is_dir():
        for package in packages.glob("*Minecraft*"):
            candidates.extend((package/"LocalState/premium_cache/skin_packs", package/"LocalState/games/com.mojang/premium_cache/skin_packs"))
    return sorted({p.absolute() for p in candidates if p.is_dir()}, key=str)


def checked_root(path):
    root = _plain_directory(path)
    if root.name != "skin_packs" or root.parent.name != "premium_cache" or not root.is_dir():
        raise ValueError("Choose Minecraft's premium_cache/skin_packs folder.")
    return root


def _json(data):
    return json.loads(data.decode("utf-8-sig"))


def _read(path, name, limit=4*1024*1024):
    if path.is_dir():
        file = _plain_directory(path/name)
        if file.stat().st_size > limit:
            raise ValueError("Pack metadata is too large.")
        return file.read_bytes()
    with zipfile.ZipFile(path) as archive:
        if archive.getinfo(name).file_size > limit:
            raise ValueError("Pack metadata is too large.")
        return archive.read(name)


def cached_pack(path):
    try:
        path = _plain_directory(path)
        checked_root(path.parent)
        manifest_bytes = _read(path, "manifest.json")
        manifest = _json(manifest_bytes)
        if not any(m.get("type") == "skin_pack" for m in manifest["modules"]):
            return None
        pack_id = str(uuid.UUID(manifest["header"]["uuid"]))
        name = str(manifest["header"].get("name", pack_id))
        # Marketplace language files are normally plaintext. Never decrypt the host.
        try:
            language = _read(path, "texts/en_US.lang").decode("utf-8-sig")
            names = dict(line.split("=", 1) for line in language.splitlines() if "=" in line and not line.lstrip().startswith("#"))
            resolved = names.get(name, names.get("skinpack."+name))
            if resolved:
                name = resolved
            elif name in ("pack.name", "pack.description", "TemplateSkinPack"):
                titles = [value for key, value in names.items() if key.startswith("skinpack.") and not key.endswith(".by")]
                if len(titles) == 1:
                    name = titles[0]
        except (OSError, ValueError, KeyError, zipfile.BadZipFile):
            pass
        name = " ".join(name.split())[:160] or pack_id
        return {"name": name, "uuid": pack_id, "path": path, "root": path.parent,
                "manifest_hash": hashlib.sha256(manifest_bytes).hexdigest(), "archive": path.is_file()}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, zipfile.BadZipFile):
        return None


def scan_marketplace(roots):
    packs, warnings = [], []
    for path in dict.fromkeys(map(Path, roots)):
        try:
            root = checked_root(path)
            for child in root.iterdir():
                pack = cached_pack(child)
                if pack:
                    receipt = active_receipt(pack)
                    if receipt:
                        pack["receipt"] = receipt
                        pack["name"] = _json(receipt.read_bytes())["host_name"]
                    packs.append(pack)
            # Keep Restore available even if Minecraft removed the replacement.
            storage = _storage(root)
            if storage.is_dir():
                for receipt in storage.glob("*/receipt.json"):
                    try:
                        _plain_directory(receipt)
                        record = _json(receipt.read_bytes())
                        target = _plain_directory(record["target"])
                        if record["root"] == str(root) and target.parent == root and not target.exists() and (receipt.parent/"original").exists():
                            packs.append({"name": record["host_name"], "uuid": record["host_uuid"], "path": target,
                                          "root": root, "receipt": receipt, "missing": True})
                    except (OSError, ValueError, KeyError, TypeError):
                        continue
        except (OSError, ValueError) as exc:
            warnings.append(f"{path}: {exc}")
    return sorted(packs, key=lambda p: (p["name"].casefold(), str(p["path"]))), warnings


def _fingerprint(path):
    path = _plain_directory(path)
    if path.is_file():
        if path.stat().st_size > LIMIT:
            raise ValueError("This pack is larger than 100 MiB.")
        return {"archive": hashlib.sha256(path.read_bytes()).hexdigest()}
    if not path.is_dir():
        raise ValueError("The pack folder is missing. Refresh the list.")
    result = {}; total = 0
    for file in path.rglob("*"):
        _plain_directory(file)
        if file.is_file():
            total += file.stat().st_size
            if total > LIMIT or len(result) >= 10000:
                raise ValueError("This pack is too large to replace here (100 MiB / 10,000 files).")
            result[file.relative_to(path).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
        elif file.is_dir():
            result[file.relative_to(path).as_posix()+"/"] = "directory"
    return result


def _crypt(key, data):
    """Minecraft's CFB8 format uses the first 16 key bytes as IV and zero padding."""
    padded = data + b"\0" * (-len(data) % 16)
    encoder = Cipher(algorithms.AES(key), CFB8(key[:16])).encryptor()
    return encoder.update(padded) + encoder.finalize()


def _encode(files, manifest_bytes):
    """Encrypt only Prism-authored assets using the public persona content format."""
    studio_name = _json(files["manifest.json"])["header"]["name"]
    files = dict(files, **{"manifest.json": manifest_bytes})
    manifest = _json(manifest_bytes)
    # Retained Marketplace manifests commonly use pack.name / pack.description.
    language = files["texts/en_US.lang"].decode("utf-8-sig")
    for field, value in (("name", studio_name), ("description", "Made with Prism Skin Studio")):
        key = manifest["header"].get(field, "")
        if re.fullmatch(r"[A-Za-z0-9_.-]+", key):
            language += f"\n{key}={value}\n"
    files["texts/en_US.lang"] = language.encode()
    pack_id = str(uuid.UUID(manifest["header"]["uuid"]))
    signature = [{"hash": base64.b64encode(hashlib.sha256(manifest_bytes).digest()).decode(), "path": "manifest.json"}]
    files["signatures.json"] = json.dumps(signature, separators=(",", ":")).encode()
    entries = []; encoded = {}
    directories = {str(p)+"/" for name in files for p in PurePosixPath(name).parents if str(p) != "."}
    for name in sorted(set(files) | directories):
        entry = {"path": name}
        if name not in directories:
            data = files[name]
            if not set(PurePosixPath(name).parts) & {"manifest.json", "texts", "pack_icon.png"}:
                key = "".join(secrets.choice(string.ascii_letters+string.digits) for _ in range(32))
                entry["key"] = key
                data = _crypt(key.encode(), data)
            encoded[name] = data
        entries.append(entry)
    contents = json.dumps({"version": 1, "content": entries}, separators=(",", ":"), ensure_ascii=False).encode()
    header = bytearray(256)
    struct.pack_into("<IIQ", header, 0, 0, 0x9bcfb9fc, 0)
    header[16] = len(pack_id); header[17:17+len(pack_id)] = pack_id.encode()
    encoded["contents.json"] = bytes(header)+_crypt(PERSONA_KEY, contents)
    return encoded


def _prism_files(archive):
    if not prism_pack(archive):
        raise ValueError("Choose a pack exported by Prism Skin Studio.")
    files = {}; names = set()
    with zipfile.ZipFile(archive) as z:
        if len(z.infolist()) > 10000 or sum(i.file_size for i in z.infolist()) > LIMIT:
            raise ValueError("The Studio pack is too large (100 MiB / 10,000 files).")
        for info in z.infolist():
            path = PurePosixPath(info.filename)
            if path.is_absolute() or not path.parts or any(p in ("..", ".") or not re.fullmatch(r"[A-Za-z0-9_.-]+", p) or p.endswith((".", " ")) for p in path.parts):
                raise ValueError("Unsafe Studio pack path.")
            name = path.as_posix()
            if name.casefold() in names or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Duplicate or linked Studio pack file.")
            names.add(name.casefold())
            if info.is_dir():
                continue
            if name not in ("manifest.json", "skins.json", "pack_icon.png", "README.txt", "texts/en_US.lang", "texts/languages.json") and not re.fullmatch(r"(?:skin_\d+_)?(?:skin|cape)\.png", name):
                raise ValueError("This Studio pack contains an unsupported file.")
            files[name] = z.read(info)
    definitions = _json(files["skins.json"])["skins"]
    if not isinstance(definitions, list) or not definitions:
        raise ValueError("Add at least one skin to the Studio pack.")
    for skin in definitions:
        if skin["geometry"] not in ("geometry.humanoid.custom", "geometry.humanoid.customSlim"):
            raise ValueError("This installer supports Studio's standard player models.")
        for field in ("texture", "cape"):
            if field in skin and (skin[field] not in files or not skin[field].endswith(".png")):
                raise ValueError("A skin or cape texture is missing.")
    return files


def _storage(root):
    return _plain_directory(root.parent.parent/"prism_marketplace_backups")


def active_receipt(pack):
    root = checked_root(pack["root"])
    storage = _storage(root)
    if not storage.is_dir():
        return None
    for receipt in sorted(storage.glob("*/receipt.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            run = _plain_directory(receipt.parent)
            data = _json(receipt.read_bytes())
            if data["target"] == str(pack["path"]) and (run/"original").exists():
                return receipt
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return None


def replace_pack(archive, selected):
    if minecraft_running():
        raise ValueError("Close Minecraft before replacing a Marketplace pack.")
    root = checked_root(selected["root"])
    target = _plain_directory(selected["path"])
    current = cached_pack(target)
    if target.parent != root or not current or current["uuid"] != selected["uuid"] or current["manifest_hash"] != selected["manifest_hash"]:
        raise ValueError("The selected Marketplace pack changed. Refresh the list.")
    if active_receipt(current):
        raise ValueError("Restore this pack's original files before replacing it again.")
    original_files = _fingerprint(target)
    manifest_bytes = _read(target, "manifest.json")
    files = _encode(_prism_files(archive), manifest_bytes)
    storage = _storage(root); run = storage/uuid.uuid4().hex
    run.mkdir(parents=True)
    stage = run/"prepared"
    if current["archive"]:
        with zipfile.ZipFile(stage, "x", zipfile.ZIP_DEFLATED) as z:
            for name, data in files.items():
                z.writestr(name, data)
    else:
        stage.mkdir()
        for name, data in files.items():
            destination = stage/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
    record = {"version": 1, "target": str(target), "root": str(root), "host_uuid": current["uuid"],
              "host_name": current["name"], "archive": current["archive"],
              "studio_name": prism_pack(archive)["name"],
              "original_files": original_files, "installed_files": _fingerprint(stage)}
    receipt = run/"receipt.json"
    receipt.write_text(json.dumps(record, indent=2), encoding="utf-8")
    if minecraft_running() or _fingerprint(target) != original_files:
        raise ValueError("Minecraft opened or the pack changed during preparation. Nothing was replaced.")
    _move_directory(target, run/"original")
    try:
        _move_directory(stage, target)
    except Exception:
        _move_directory(run/"original", target)
        raise
    return receipt


def restore_pack(receipt_path):
    if minecraft_running():
        raise ValueError("Close Minecraft before restoring a Marketplace pack.")
    receipt_path = _plain_directory(receipt_path)
    record = _json(receipt_path.read_bytes())
    root = checked_root(record["root"])
    target = _plain_directory(record["target"])
    run = receipt_path.parent
    if receipt_path.name != "receipt.json" or run.parent != _storage(root) or not re.fullmatch(r"[0-9a-f]{32}", run.name) or target.parent != root:
        raise ValueError("Invalid Marketplace backup receipt.")
    original = _plain_directory(run/"original")
    if not original.exists() or _fingerprint(original) != record["original_files"]:
        raise ValueError("The original Marketplace backup is missing or changed. Nothing was replaced.")
    if str(uuid.UUID(_json(_read(original, "manifest.json"))["header"]["uuid"])) != record["host_uuid"]:
        raise ValueError("The original backup's identity doesn't match its receipt.")
    if target.exists() and _fingerprint(target) == record["original_files"]:
        # Minecraft may already have downloaded the original again. Keep the backup.
        _move_directory(original, run/"retained_original")
        return target
    if target.exists() and _fingerprint(target) != record["installed_files"]:
        raise ValueError("Minecraft changed this pack after installation. The original backup is safe; Prism will not overwrite the changed files.")
    removed = run/("removed_"+uuid.uuid4().hex)
    moved = target.exists()
    if moved:
        _move_directory(target, removed)
    try:
        _move_directory(original, target)
    except Exception:
        if moved:
            _move_directory(removed, target)
        raise
    return target
