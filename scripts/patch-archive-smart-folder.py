#!/usr/bin/env python3
from pathlib import Path
import ast
import re
import sys
import tempfile
import py_compile

if len(sys.argv) != 2:
    raise SystemExit("uso: patch-archive-smart-folder.py SOURCE_ROOT")

root = Path(sys.argv[1])
archive_py = root / "app" / "archive_import.py"
if not archive_py.exists():
    raise SystemExit("Archive smart folder: app/archive_import.py ausente")

src = archive_py.read_text(encoding="utf-8")
if "RM_ARCHIVE_SMART_FOLDER_V1" in src:
    print("Archive smart folder: já aplicado")
    raise SystemExit(0)

try:
    tree = ast.parse(src)
except SyntaxError as exc:
    raise SystemExit(f"Archive smart folder: archive_import.py inválido antes do patch: {exc}")

run_fn = next(
    (node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_run_job"),
    None,
)
if run_fn is None:
    raise SystemExit("Archive smart folder: def _run_job não encontrada")

dest_assign = None
for node in ast.walk(run_fn):
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(t, ast.Name) and t.id == "dest_prefix" for t in targets):
            dest_assign = node
            break

if dest_assign is None:
    raise SystemExit("Archive smart folder: atribuição dest_prefix não encontrada em _run_job")

helper = r'''
# RM_ARCHIVE_SMART_FOLDER_V1
# "Pasta: automático" deve proteger organização sem criar uma pasta
# desnecessária para um filme único. Regras:
# - uma raiz real já presente no arquivo é preservada exatamente;
# - filme único (+ legenda/NFO/imagens auxiliares) vai direto ao destino;
# - série/pack com múltiplos vídeos soltos mantém a pasta automática existente;
# - modos/pastas manuais não são alterados.
import re as _rm_arc_re


_RM_ARC_VIDEO_EXTS = {
    '.mkv', '.mp4', '.m4v', '.avi', '.mov', '.wmv', '.ts', '.m2ts',
    '.mpg', '.mpeg', '.webm', '.vob'
}
_RM_ARC_SIDECAR_EXTS = {
    '.srt', '.ass', '.ssa', '.sub', '.idx', '.vtt',
    '.nfo', '.txt', '.jpg', '.jpeg', '.png', '.webp', '.gif',
    '.xml', '.json'
}


def _rm_arc_entry_name(entry):
    if not isinstance(entry, dict):
        return ''
    return str(
        entry.get('name')
        or entry.get('path')
        or entry.get('filename')
        or entry.get('file')
        or ''
    ).replace('\\', '/').lstrip('./')


def _rm_arc_entry_is_dir(entry, name):
    if not isinstance(entry, dict):
        return False
    if entry.get('is_dir') is True or entry.get('dir') is True:
        return True
    kind = str(entry.get('type') or '').lower()
    return kind in {'dir', 'directory', 'folder'} or name.endswith('/')


def _rm_arc_package_stem(primary):
    name = str(getattr(primary, 'name', primary) or '').split('/')[-1]
    low = name.lower()

    # Multipart endings first.
    name = _rm_arc_re.sub(r'(?i)\.part\d+\.rar$', '', name)
    name = _rm_arc_re.sub(r'(?i)\.(?:7z|zip)\.\d{3}$', '', name)
    name = _rm_arc_re.sub(r'(?i)\.\d{3}$', '', name)

    # Compound/simple archive suffixes.
    for suffix in ('.tar.gz', '.tar.bz2', '.tar.xz', '.tgz', '.tbz2', '.txz',
                   '.rar', '.zip', '.7z', '.tar', '.gz', '.bz2', '.xz'):
        if name.lower().endswith(suffix):
            name = name[:-len(suffix)]
            break
    return name.strip(' ._-')


def _rm_arc_norm_folder(value):
    return _rm_arc_re.sub(r'[^a-z0-9]+', '', str(value or '').lower())


def _rm_arc_is_auto_generated_dest(dest_prefix, base_destination, primary):
    dest = str(dest_prefix or '').rstrip('/')
    base = str(base_destination or '').rstrip('/')
    if not dest or dest == base:
        return False
    if base and not (dest == base or dest.startswith(base + '/')):
        return False

    tail = dest.rsplit('/', 1)[-1]
    package = _rm_arc_package_stem(primary)
    a = _rm_arc_norm_folder(tail)
    b = _rm_arc_norm_folder(package)
    if not a or not b:
        return False
    return a == b or (len(a) >= 8 and len(b) >= 8 and (a in b or b in a))


def _rm_archive_smart_dest(dest_prefix, base_destination, primary, entries):
    # If the existing logic did not create an automatic child folder, keep it.
    if not _rm_arc_is_auto_generated_dest(dest_prefix, base_destination, primary):
        return dest_prefix

    files = []
    top_files = []
    top_dirs = set()
    videos = []

    for entry in (entries or []):
        name = _rm_arc_entry_name(entry)
        if not name or name.startswith('../') or '/..' in name:
            continue
        clean = name.rstrip('/')
        if not clean:
            continue

        parts = [p for p in clean.split('/') if p and p != '.']
        if not parts:
            continue

        is_dir = _rm_arc_entry_is_dir(entry, name)
        if len(parts) > 1:
            top_dirs.add(parts[0])
        elif is_dir:
            top_dirs.add(parts[0])

        if is_dir:
            continue

        files.append(name)
        if len(parts) == 1:
            top_files.append(name)

        ext = Path(parts[-1]).suffix.lower()
        if ext in _RM_ARC_VIDEO_EXTS:
            videos.append(name)

    # Archive already contains exactly one real root folder and no loose
    # top-level files: do not wrap it in another archive-name folder.
    # Uploading against base_destination preserves the internal root as-is.
    if len(top_dirs) == 1 and not top_files:
        return base_destination

    # A movie package should not create "Filme/Filme.mkv". One video plus
    # ordinary subtitles/NFO/artwork stays directly in the selected folder.
    if len(videos) == 1:
        allowed = True
        for name in files:
            ext = Path(name.split('/')[-1]).suffix.lower()
            if name == videos[0]:
                continue
            if ext not in _RM_ARC_SIDECAR_EXTS:
                allowed = False
                break
        if allowed:
            return base_destination

    # Series/packs/multiple loose media files remain isolated inside the
    # automatic archive/package folder selected by the original logic.
    return dest_prefix
'''

lines = src.splitlines(keepends=True)
fn_line = run_fn.lineno - 1
assign_end = getattr(dest_assign, "end_lineno", dest_assign.lineno)
assign_idx = assign_end
indent_match = re.match(r"^(\s*)", lines[dest_assign.lineno - 1])
indent = indent_match.group(1) if indent_match else "    "

# Insert helper before _run_job as real source lines. Account for the shifted
# assignment index using list entries, not the number of newlines inside one
# string item.
helper_lines = (helper + "\n").splitlines(keepends=True)
lines[fn_line:fn_line] = helper_lines
assign_idx += len(helper_lines)

inject = (
    f"{indent}dest_prefix = _rm_archive_smart_dest("
    "dest_prefix, base_destination, primary, entries)\n"
)
lines.insert(assign_idx, inject)

patched = "".join(lines)
archive_py.write_text(patched, encoding="utf-8")

with tempfile.NamedTemporaryFile(suffix=".pyc") as f:
    py_compile.compile(str(archive_py), doraise=True, cfile=f.name)

print(
    "Archive smart folder OK: filme único direto; raiz interna preservada; "
    "série/pack continua em pasta automática"
)
