#!/usr/bin/env python3
import struct
import json
import base64
import hashlib
import zipfile
from pathlib import Path
from typing import List, Tuple, Dict

try:
    import xxhash
except ImportError:
    xxhash = None

TARGET_BASE64 = {"battlesystemconfig.xml", "systemconfig.xml"}


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def xxhash_6digit(data: bytes) -> str:
    """Pure Python xxhash → 6 digit style seperti original."""
    if xxhash is None:
        # fallback sederhana jika lib tidak ada
        return hashlib.md5(data).hexdigest()[-6:]
    full = xxhash.xxh64(data).hexdigest()
    last6 = full[-6:]
    pairs = [last6[i:i+2] for i in range(0, 6, 2)]
    return "".join(reversed(pairs))


def get_hashes_bytes(data: bytes) -> Tuple[str, str, int]:
    return md5_bytes(data), xxhash_6digit(data), len(data)


def detect_type(data: bytes) -> str:
    if not data:
        return "empty"
    sample = data[:64]
    if sample[:3] == b"\xef\xbb\xbf":
        return "text"
    if sample[:1] in (b"{", b"["):
        return "json"
    printable = sum(1 for b in sample if 32 <= b < 127 or b in (9, 10, 13))
    if printable / max(len(sample), 1) >= 0.90:
        return "text"
    first = data[0]
    wire = first & 0x07
    field = first >> 3
    if wire in (0, 1, 2, 5) and field > 0:
        return "protobuf"
    return "binary"


def parse_toc(raw: bytes) -> Tuple[int, List[Tuple[str, int, int]]]:
    if len(raw) < 8 or raw[:4] != b"MLBB":
        raise ValueError("Bukan MLBB bundle valid")
    count = struct.unpack_from("<I", raw, 4)[0]
    pos = 8
    entries = []
    for i in range(count):
        if pos + 4 > len(raw):
            raise ValueError(f"TOC corrupt entry {i}")
        nl = struct.unpack_from("<I", raw, pos)[0]
        pos += 4
        if pos + nl > len(raw):
            raise ValueError(f"name_len OOB entry {i}")
        name = raw[pos:pos + nl].decode("utf-8", errors="replace")
        pos += nl
        if pos + 8 > len(raw):
            raise ValueError(f"size/offset OOB entry {i}")
        size = struct.unpack_from("<I", raw, pos)[0]
        pos += 4
        offset = struct.unpack_from("<I", raw, pos)[0]
        pos += 4
        entries.append((name, size, offset))
    return pos, entries


def extract_to_zip(input_bytes: bytes, zip_path: Path) -> Dict:
    """Extract dari bytes langsung ke zip (cocok serverless)."""
    data_start, entries = parse_toc(input_bytes)
    total = len(entries)
    ok = 0
    errors = []
    manifest = []

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, size, offset in entries:
            try:
                start = data_start + offset
                end = start + size
                if end > len(input_bytes):
                    raise ValueError(f"size OOB ({size})")
                data = input_bytes[start:end]

                if name.lower() in TARGET_BASE64:
                    try:
                        data = base64.b64decode(data.strip())
                    except Exception as e:
                        errors.append(f"{name}: b64 {e}")
                        continue

                md5_val, xx_val, _ = get_hashes_bytes(data)
                manifest.append({
                    "name": name,
                    "size": len(data),
                    "offset": offset,
                    "type": detect_type(data),
                    "md5": md5_val,
                    "xxhash": xx_val,
                })
                zf.writestr(name, data)
                ok += 1
            except Exception as e:
                errors.append(f"{name}: {e}")

        zf.writestr("_manifest.json", json.dumps(manifest, indent=2))

    zip_md5 = md5_file(zip_path)
    return {
        "ok": ok,
        "total": total,
        "errors": errors[:10],
        "zip_size": zip_path.stat().st_size,
        "zip_md5": zip_md5,
    }
