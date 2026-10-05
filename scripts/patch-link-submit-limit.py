#!/usr/bin/env python3
from pathlib import Path
import re
import sys
import tempfile
import py_compile

if len(sys.argv) != 2:
    raise SystemExit("uso: patch-link-submit-limit.py SOURCE_ROOT")

root = Path(sys.argv[1])
limit = 2000
marker = "RM_LINK_SUBMIT_LIMIT_V1"

candidates = []
for base in (root / "app", root / "extension", root / "browser-extension"):
    if not base.exists():
        continue
    for p in base.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".py", ".js", ".html", ".htm"}:
            candidates.append(p)

changed = []
hits = 0

literal_replacements = [
    ("Máximo de 250 links por envio", f"Máximo de {limit} links por envio"),
    ("Maximo de 250 links por envio", f"Maximo de {limit} links por envio"),
    ("máximo de 250 links por envio", f"máximo de {limit} links por envio"),
    ("maximo de 250 links por envio", f"maximo de {limit} links por envio"),
    ("Maximum of 250 links per submission", f"Maximum of {limit} links per submission"),
    ("Maximum 250 links per submission", f"Maximum {limit} links per submission"),
]

patterns = [
    # JS/Python constants whose names clearly represent a link/item submission cap.
    (
        re.compile(
            r"(?i)\b((?:MAX|LIMIT)[A-Z0-9_]*(?:LINK|ITEM|SELECT|IMPORT)[A-Z0-9_]*\s*=\s*)250\b"
        ),
        lambda m: m.group(1) + str(limit),
    ),
    (
        re.compile(
            r"(?i)\b((?:max|limit)[A-Za-z0-9_]*(?:Link|Item|Select|Import)[A-Za-z0-9_]*\s*=\s*)250\b"
        ),
        lambda m: m.group(1) + str(limit),
    ),
    # Client-side guards such as selected.length > 250 / links.length >= 250.
    (
        re.compile(
            r"(?i)(\b(?:selected(?:Links|Items)?|links|items|selected_links|selected_items)"
            r"\.length\s*(?:>|>=)\s*)250\b"
        ),
        lambda m: m.group(1) + str(limit),
    ),
    # Python guards such as len(links) > 250.
    (
        re.compile(
            r"(?i)(len\([^\n)]*(?:link|item|selected)[^\n)]*\)\s*(?:>|>=)\s*)250\b"
        ),
        lambda m: m.group(1) + str(limit),
    ),
    # Flask/API messages that interpolate the same hard cap nearby.
    (
        re.compile(
            r"(?i)((?:max(?:imum|imo)?|limite)[^\n]{0,45}(?:link|item)[^\n]{0,30})250\b"
        ),
        lambda m: m.group(1) + str(limit),
    ),
]

for p in candidates:
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        continue

    original = text
    local_hits = 0

    for old, new in literal_replacements:
        count = text.count(old)
        if count:
            text = text.replace(old, new)
            local_hits += count

    for rx, repl in patterns:
        text, count = rx.subn(repl, text)
        local_hits += count

    if text != original:
        p.write_text(text, encoding="utf-8")
        changed.append(str(p.relative_to(root)))
        hits += local_hits

# Keep backend normalization aligned with the UI. Existing HA source currently
# has a 2000-item hard stop; if an older source still has 250, raise only that
# exact normalize_items guard, not previews such as [:250].
drive_py = root / "app" / "drive_links.py"
if drive_py.exists():
    text = drive_py.read_text(encoding="utf-8")
    old = text
    text = re.sub(
        r"(?m)^(\s*)if\s+len\(result\)\s*>\s*250\s*:",
        lambda m: m.group(1) + f"if len(result) > {limit}:",
        text,
    )
    if marker not in text:
        text += f"\n# {marker}: max_links_per_submission={limit}\n"
    if text != old:
        drive_py.write_text(text, encoding="utf-8")
        if "app/drive_links.py" not in changed:
            changed.append("app/drive_links.py")

# Validate Python files we touched.
for rel in changed:
    p = root / rel
    if p.suffix.lower() == ".py":
        with tempfile.NamedTemporaryFile(suffix=".pyc") as tmp:
            py_compile.compile(str(p), doraise=True, cfile=tmp.name)

print(
    f"Link submit limit OK: até {limit} links por envio; "
    f"{hits} limite(s)/mensagem(ns) ajustado(s) em {len(changed)} arquivo(s)"
)
