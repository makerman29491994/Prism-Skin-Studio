"""Temporary fixtures only. Never changes installed Minecraft content."""
import base64
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
from unittest.mock import patch
import uuid
import zipfile

from PIL import Image
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
from cryptography.hazmat.decrepit.ciphers.modes import CFB8
sys.path.insert(0, str(Path('src').resolve()))
import PrismMarketplaceInstall as market
from PrismSkinPack import export_collection


def decrypt(key, data):
    decoder = Cipher(algorithms.AES(key), CFB8(key[:16])).decryptor()
    return decoder.update(data)+decoder.finalize()


def read(path, name):
    if path.is_dir():
        return (path/name).read_bytes()
    with zipfile.ZipFile(path) as z:
        return z.read(name)


def make_host(root, name, archive=False):
    path = root/name
    manifest = json.dumps({'format_version': 1, 'header': {'name': 'pack.name', 'uuid': str(uuid.uuid4()), 'version': [1, 2, 3]},
                           'modules': [{'type': 'skin_pack', 'uuid': str(uuid.uuid4()), 'version': [1, 2, 3]}]}).encode()
    files = {'manifest.json': manifest, 'skins.json': b'opaque purchased data', 'texts/en_US.lang': ('pack.name='+name+'\n').encode(), 'old.png': b'original'}
    if archive:
        with zipfile.ZipFile(path, 'w') as z:
            for entry, data in files.items():
                z.writestr(entry, data)
    else:
        path.mkdir()
        for entry, data in files.items():
            file = path/entry; file.parent.mkdir(exist_ok=True); file.write_bytes(data)
        (path/'empty').mkdir()
    return path


# NIST SP800-38A AES-256 CFB8 first plaintext block. Independent known vector.
key = bytes.fromhex('603deb1015ca71be2b73aef0857d77811f352c073b6108d72d9810a30914dff4')
iv = bytes.fromhex('000102030405060708090a0b0c0d0e0f')
plain = bytes.fromhex('6bc1bee22e409f96e93d7e117393172a')
encoder = Cipher(algorithms.AES(key), CFB8(iv)).encryptor()
assert (encoder.update(plain)+encoder.finalize()).hex() == 'dc1f1a8520a64db55fcc8ac554844e88'

with tempfile.TemporaryDirectory(dir='work', prefix='market_install_') as temporary:
    base = Path(temporary).resolve(); root = base/'premium_cache/skin_packs'; root.mkdir(parents=True)
    first = make_host(root, 'My Owned Pack'); second = make_host(root, 'Another Pack', archive=True)
    (root/'not-a-pack').mkdir(); (root/'lru.json').write_text('{}')
    packs, warnings = market.scan_marketplace([root])
    assert not warnings and {p['name'] for p in packs} == {'My Owned Pack', 'Another Pack'}
    skins = [{'name': 'Knight', 'skin': Image.new('RGBA', (64, 64), (120, 60, 20, 255)),
              'cape': Image.new('RGBA', (64, 32), (30, 180, 50, 255)), 'zombie': True},
             {'name': 'Other', 'skin': Image.new('RGBA', (64, 64), (40, 50, 100, 255)), 'slim': True}]
    archive = base/'studio.mcpack'; export_collection(skins, archive, 'My Studio Pack', include_custom=True)
    with zipfile.ZipFile(archive) as z:
        raw = {n: z.read(n) for n in z.namelist()}
    originals = {p: market._fingerprint(p) for p in (first, second)}
    # Validate both extracted Marketplace caches and extensionless ZIP caches.
    for target in (first, second):
        selected = market.cached_pack(target); manifest = read(target, 'manifest.json')
        with patch.object(market, 'minecraft_running', return_value=True):
            try: market.replace_pack(archive, selected)
            except ValueError: pass
            else: raise AssertionError('Replaced a pack with Minecraft running')
        with patch.object(market, 'minecraft_running', return_value=False):
            receipt = market.replace_pack(archive, selected)
            assert market._fingerprint(receipt.parent/'original') == originals[target]
            assert read(target, 'manifest.json') == manifest
            data = read(target, 'contents.json')
            assert struct.unpack_from('<IIQ', data) == (0, 0x9bcfb9fc, 0)
            assert data[17:17+data[16]].decode() == selected['uuid']
            contents = json.loads(decrypt(market.PERSONA_KEY, data[256:]).rstrip(b'\0'))
            entries = {e['path']: e for e in contents['content']}
            decoded = {}
            for name, entry in entries.items():
                if name.endswith('/'): continue
                file = read(target, name)
                decoded[name] = decrypt(entry['key'].encode(), file).rstrip(b'\0') if 'key' in entry else file
            assert 'key' not in entries['manifest.json'] and 'key' not in entries['texts/en_US.lang']
            assert 'key' in entries['skins.json'] and 'key' in entries['skin_1_cape.png']
            for name in ('skins.json', 'skin_1_skin.png', 'skin_1_cape.png', 'skin_2_skin.png'):
                # PNGs can end in zero bytes: use their original lengths, not JSON trimming.
                value = decrypt(entries[name]['key'].encode(), read(target, name))[:len(raw[name])]
                assert value == raw[name], name
            definitions = json.loads(decoded['skins.json'])['skins']
            assert len(definitions) == 2 and 'animations' not in definitions[0]
            signature = json.loads(decoded['signatures.json'])
            assert signature[0]['hash'] == base64.b64encode(hashlib.sha256(manifest).digest()).decode()
            assert b'pack.name=My Studio Pack' in decoded['texts/en_US.lang']
            packs, warnings = market.scan_marketplace([root]); assert not warnings
            assert next(p for p in packs if p['path'] == target)['receipt'] == receipt
            try: market.replace_pack(archive, market.cached_pack(target))
            except ValueError: pass
            else: raise AssertionError('Overwrote a host with a pending original backup')
            market.restore_pack(receipt)
            assert market._fingerprint(target) == originals[target]
            assert market.active_receipt(market.cached_pack(target)) is None
    with patch.object(market, 'minecraft_running', return_value=False):
        # Failed swap automatically puts the original back.
        selected = market.cached_pack(first); real_move = market._move_directory
        def fail_stage(source, destination):
            if source.name == 'prepared': raise PermissionError('fixture locked')
            return real_move(source, destination)
        with patch.object(market, '_move_directory', side_effect=fail_stage):
            try: market.replace_pack(archive, selected)
            except PermissionError: pass
            else: raise AssertionError('Expected simulated swap failure')
        assert market._fingerprint(first) == originals[first]
        # Refuse changed active files, retain the original backup.
        receipt = market.replace_pack(archive, market.cached_pack(first))
        current = (first/'skins.json').read_bytes(); (first/'skins.json').write_bytes(b'changed')
        try: market.restore_pack(receipt)
        except ValueError: pass
        else: raise AssertionError('Overwrote modified replacement')
        assert market._fingerprint(receipt.parent/'original') == originals[first]
        (first/'skins.json').write_bytes(current)
        # Missing cached target is still discoverable and restorable.
        saved = first.with_name('held-outside-scan'); market._move_directory(first,saved)
        packs, warnings = market.scan_marketplace([root])
        missing = next(p for p in packs if p['path'] == first)
        assert missing['missing'] and missing['receipt'] == receipt
        market.restore_pack(receipt); assert market._fingerprint(first) == originals[first]
        # Stale selection and traversal are rejected before changes.
        stale = dict(market.cached_pack(second), manifest_hash='stale')
        try: market.replace_pack(archive, stale)
        except ValueError: pass
        else: raise AssertionError('Accepted stale selection')
        bad = base/'bad.mcpack'
        with zipfile.ZipFile(bad, 'w') as z:
            for name, data in raw.items(): z.writestr(name, data)
            z.writestr('../escape', b'bad')
        try: market.replace_pack(bad, market.cached_pack(second))
        except ValueError: pass
        else: raise AssertionError('Accepted traversal')
        assert market._fingerprint(second) == originals[second]
        # Forged receipt cannot redirect restoration outside its selected cache.
        record = json.loads(receipt.read_text()); record['target'] = str(base/'elsewhere')
        receipt.write_text(json.dumps(record))
        try: market.restore_pack(receipt)
        except ValueError: pass
        else: raise AssertionError('Accepted outside-cache target')
print('Marketplace installer passed: discovery, two skins/cape/pose encryption, exact manifest preservation, folder/ZIP replacement, restore, closed-game/stale guards, rollback, changed/missing target handling and path refusal.')
