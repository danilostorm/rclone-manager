#!/usr/bin/env python3
# Source SHA-256: 28c9e8cc21a9f1f34e328c6054f377d36591cf15f35cd281e35ad75c27f78aac
# Archive importer overlay payload is split so GitHub updates remain reliable.
from pathlib import Path
import base64, hashlib, zlib

here = Path(__file__).resolve().parent
parts = sorted(here.glob("patch-archive-import.b64.part-*"))
if not parts:
    raise SystemExit("Archive overlay: payload parts missing")
packed = "".join(p.read_text(encoding="utf-8").strip() for p in parts)
try:
    source = zlib.decompress(base64.b64decode(packed)).decode("utf-8")
except Exception as exc:
    raise SystemExit(f"Archive overlay: payload corrupt/incomplete: {exc}")
expected = "28c9e8cc21a9f1f34e328c6054f377d36591cf15f35cd281e35ad75c27f78aac"
actual = hashlib.sha256(source.encode("utf-8")).hexdigest()
if actual != expected:
    raise SystemExit(f"Archive overlay: SHA256 mismatch: {actual}")
exec(compile(source, __file__, "exec"))
