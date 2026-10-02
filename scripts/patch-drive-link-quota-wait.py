#!/usr/bin/env python3
from pathlib import Path
import re
import sys
import tempfile
import py_compile

if len(sys.argv) != 2:
    raise SystemExit("uso: patch-drive-link-quota-wait.py SOURCE_ROOT")

root = Path(sys.argv[1])
drive_py = root / "app" / "drive_links.py"
if not drive_py.exists():
    raise SystemExit("Drive Link quota recovery: app/drive_links.py ausente")

src = drive_py.read_text(encoding="utf-8")
original = src

# HA4.7.4.19 recovery:
# .17 adicionou um wrapper de quota no escopo global para um _run_job que não
# existe globalmente em algumas bases HA, causando NameError no import.
# .18 tentou reposicionar o wrapper, mas abortava antes de escrever em algumas
# árvores antigas. Para recuperar produção com segurança, remova somente o
# overlay de quota .17/.18 e mantenha todo o restante (Dropbox/staging/archive).

# 1) Bloco helper global da .17/.18 foi acrescentado no fim do arquivo.
marker = "# RM_DRIVE_LINK_QUOTA_WAIT_V1"
pos = src.find("\n" + marker)
if pos < 0:
    pos = src.find(marker)
if pos >= 0:
    src = src[:pos].rstrip() + "\n"

# 2) Guard inserido dentro do worker na .17.
src = re.sub(
    r"(?m)^(?P<i>[ \t]*)if _rm_dl_quota_is_error\((?P<e>[A-Za-z_][A-Za-z0-9_]*)\):\n"
    r"(?P=i)[ \t]+raise _RmDriveLinkQuotaWait\(str\((?P=e)\)\)\n",
    "",
    src,
)

# 3) Se alguma tentativa .18 chegou a gravar wrapper V2 local antes de abortar,
# retire esse bloco também. O wrapper sempre começa no marcador abaixo e termina
# antes da próxima linha no mesmo nível de indentação.
lines = src.splitlines(keepends=True)
out = []
i = 0
while i < len(lines):
    line = lines[i]
    if "RM_DRIVE_LINK_QUOTA_WAIT_WRAPPER_V2" not in line:
        out.append(line)
        i += 1
        continue

    indent = len(line) - len(line.lstrip(" "))
    i += 1
    while i < len(lines):
        cur = lines[i]
        stripped = cur.strip()
        if not stripped:
            i += 1
            continue
        cur_indent = len(cur) - len(cur.lstrip(" "))
        # Próxima instrução real no mesmo nível ou acima encerra o wrapper.
        if cur_indent <= indent and not cur.lstrip().startswith("#"):
            break
        i += 1
src = "".join(out)

drive_py.write_text(src, encoding="utf-8")

with tempfile.NamedTemporaryFile(suffix=".pyc") as tmp:
    py_compile.compile(str(drive_py), doraise=True, cfile=tmp.name)

if "_RM_DL_QUOTA_ORIG_WORKER = _run_job" in src:
    raise SystemExit("Drive Link quota recovery: alias global quebrado ainda presente")
if "RM_DRIVE_LINK_QUOTA_WAIT_V1" in src:
    raise SystemExit("Drive Link quota recovery: helper legado ainda presente")

changed = src != original
print(
    "Drive Link quota recovery OK: overlay de quota experimental removido; "
    + ("fonte reparada" if changed else "fonte já limpa")
)
