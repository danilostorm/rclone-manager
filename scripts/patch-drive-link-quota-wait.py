#!/usr/bin/env python3
from pathlib import Path
import ast
import re
import sys
import tempfile
import py_compile

if len(sys.argv) != 2:
    raise SystemExit("uso: patch-drive-link-quota-wait.py SOURCE_ROOT")

root = Path(sys.argv[1])
drive_py = root / "app" / "drive_links.py"
if not drive_py.exists():
    raise SystemExit("Drive Link quota wait: app/drive_links.py ausente")

src = drive_py.read_text(encoding="utf-8")

# HA4.7.4.18 repair:
# .17 gerou corretamente o código, porém tentou referenciar o worker interno
# _run_job no escopo global. Em builds HA ele é uma função aninhada dentro do
# importador, então o módulo falhava no import com NameError.
#
# Torne o patch auto-reparável: se encontrar a implementação .17, remova
# somente o bloco/guard adicionados por ela e reaplique a versão corrigida.
marker = "# RM_DRIVE_LINK_QUOTA_WAIT_V1"
if marker in src:
    marker_pos = src.find("\n" + marker)
    if marker_pos < 0:
        marker_pos = src.find(marker)
    if marker_pos >= 0:
        src = src[:marker_pos].rstrip() + "\n"

    src = re.sub(
        r"(?m)^(?P<i>[ \t]*)if _rm_dl_quota_is_error\((?P<e>[A-Za-z_][A-Za-z0-9_]*)\):\n"
        r"(?P=i)[ \t]+raise _RmDriveLinkQuotaWait\(str\((?P=e)\)\)\n",
        "",
        src,
    )

tree = ast.parse(src)

# Mapeie pais AST para saber em qual escopo o worker vive.
parents = {}
for node in ast.walk(tree):
    for child in ast.iter_child_nodes(node):
        parents[child] = node

# O worker normal é identificado estruturalmente pelo ponto em que confirma um
# item concluído ("completed += 1"). Isto evita depender do nome histórico.
workers = []
for node in ast.walk(tree):
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        continue
    hits = []
    for sub in ast.walk(node):
        if (
            isinstance(sub, ast.AugAssign)
            and isinstance(sub.target, ast.Name)
            and sub.target.id == "completed"
            and isinstance(sub.op, ast.Add)
        ):
            hits.append(sub)
    if hits:
        span = getattr(node, "end_lineno", 10**9) - node.lineno
        workers.append((span, node, hits[0]))

if not workers:
    raise SystemExit("Drive Link quota wait: worker com completed += 1 não encontrado")

workers.sort(key=lambda x: x[0])
_worker_span, worker, completed_node = workers[0]
worker_name = worker.name

if not worker.args.args:
    raise SystemExit("Drive Link quota wait: worker sem job_id")
job_arg = worker.args.args[0].arg

# Em HA4.x esse worker é aninhado. O wrapper precisa ser criado no MESMO
# escopo, depois da definição original e antes de ele ser entregue à Thread.
scope = parents.get(worker)
while scope is not None and not isinstance(
    scope, (ast.FunctionDef, ast.AsyncFunctionDef)
):
    scope = parents.get(scope)
if not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
    raise SystemExit(
        "Drive Link quota wait: worker não está em escopo de função; "
        "não é seguro aplicar wrapper"
    )

# Ache o try/except do item que envolve completed += 1.
choices = []
for sub in ast.walk(worker):
    if not isinstance(sub, ast.Try):
        continue
    body_start = min((getattr(x, "lineno", 10**9) for x in sub.body), default=10**9)
    body_end = max(
        (getattr(x, "end_lineno", getattr(x, "lineno", 0)) for x in sub.body),
        default=0,
    )
    if not (body_start <= completed_node.lineno <= body_end):
        continue
    for handler in sub.handlers:
        catches_exception = (
            handler.type is None
            or (
                isinstance(handler.type, ast.Name)
                and handler.type.id in {"Exception", "BaseException"}
            )
        )
        if catches_exception and handler.name:
            span = getattr(sub, "end_lineno", sub.lineno) - sub.lineno
            choices.append((span, sub, handler))

if not choices:
    raise SystemExit("Drive Link quota wait: except Exception do item não encontrado")

choices.sort(key=lambda x: x[0])
handler = choices[0][2]
exc_name = handler.name

lines = src.splitlines(keepends=True)

# 1) No erro do item, converta somente quota/rate-limit em sinal temporário.
insert_line = handler.lineno
body_indent = " " * (
    handler.body[0].col_offset if handler.body else handler.col_offset + 4
)
guard = (
    f"{body_indent}if _rm_dl_quota_is_error({exc_name}):\n"
    f"{body_indent}    raise _RmDriveLinkQuotaWait(str({exc_name}))\n"
)
guard_lines = guard.splitlines(keepends=True)
lines[insert_line:insert_line] = guard_lines

# A inserção acima desloca as linhas posteriores pelo número real de linhas
# físicas adicionadas.
worker_end_index = worker.end_lineno + len(guard_lines)

scope_indent = " " * worker.col_offset
inner = scope_indent + "    "
wrapper = (
    "\n"
    f"{scope_indent}# RM_DRIVE_LINK_QUOTA_WAIT_WRAPPER_V2\n"
    f"{scope_indent}_rm_dl_quota_orig_worker = {worker_name}\n"
    f"{scope_indent}def {worker_name}(*args, **kwargs):\n"
    f"{inner}job_id = args[0] if args else kwargs.get({job_arg!r})\n"
    f"{inner}attempt = 0\n"
    f"{inner}while True:\n"
    f"{inner}    try:\n"
    f"{inner}        return _rm_dl_quota_orig_worker(*args, **kwargs)\n"
    f"{inner}    except _RmDriveLinkQuotaWait as exc:\n"
    f"{inner}        attempt += 1\n"
    f"{inner}        delay = _rm_dl_quota_delay(attempt)\n"
    f"{inner}        mins = max(1, int(round(delay / 60.0)))\n"
    f"{inner}        _rm_dl_quota_update(\n"
    f"{inner}            job_id,\n"
    f"{inner}            'Cota temporariamente excedida; aguardando '\n"
    f"{inner}            + str(mins)\n"
    f"{inner}            + ' min para tentar novamente automaticamente · '\n"
    f"{inner}            + str(exc)[:500],\n"
    f"{inner}        )\n"
    f"{inner}        remaining = delay\n"
    f"{inner}        while remaining > 0:\n"
    f"{inner}            if _rm_dl_quota_cancelled(job_id):\n"
    f"{inner}                return None\n"
    f"{inner}            step = min(10, remaining)\n"
    f"{inner}            _rm_dl_quota_time.sleep(step)\n"
    f"{inner}            remaining -= step\n"
    f"{inner}        _rm_dl_quota_update(\n"
    f"{inner}            job_id,\n"
    f"{inner}            'Cota: iniciando tentativa automática ' + str(attempt + 1),\n"
    f"{inner}        )\n"
)

lines.insert(worker_end_index, wrapper)
src = "".join(lines)

helpers = r'''

# RM_DRIVE_LINK_QUOTA_WAIT_V1
# Cotas/rate limits são estado temporário, não falha definitiva. O wrapper é
# instalado no mesmo escopo do worker aninhado; assim não existe referência
# global inválida a _run_job.
import os as _rm_dl_quota_os
import sqlite3 as _rm_dl_quota_sqlite3
import time as _rm_dl_quota_time
from datetime import datetime as _RmDlQuotaDateTime, timezone as _RmDlQuotaTimezone


class _RmDriveLinkQuotaWait(Exception):
    pass


def _rm_dl_quota_is_error(exc):
    text = (type(exc).__name__ + ': ' + str(exc)).lower()
    hard_tokens = (
        'quota exceeded',
        'cota excedida',
        'download quota',
        'downloadquotaexceeded',
        'userratelimitexceeded',
        'ratelimitexceeded',
        'dailylimitexceeded',
        'storagequotaexceeded',
        'bandwidth limit',
        'bandwidth exceeded',
        'limite de banda',
        'limite de download',
        'too many requests',
        'http 429',
        'status 429',
        '429 too many',
        'http 509',
        'status 509',
        '509 bandwidth',
        'temporarily unavailable due to traffic',
        'muitas solicitações',
    )
    if any(token in text for token in hard_tokens):
        return True
    if ('403' in text) and any(
        token in text
        for token in ('quota', 'rate limit', 'cota', 'limite', 'bandwidth')
    ):
        return True
    return False


def _rm_dl_quota_db():
    return str(
        _rm_dl_quota_os.environ.get('DB_PATH')
        or _rm_dl_quota_os.path.join(
            _rm_dl_quota_os.environ.get('DATA_DIR', '/data'),
            'rclone-manager.db',
        )
    )


def _rm_dl_quota_columns(db):
    try:
        return {str(row[1]) for row in db.execute(
            'PRAGMA table_info(drive_link_jobs)'
        )}
    except Exception:
        return set()


def _rm_dl_quota_update(job_id, message):
    if job_id is None:
        return
    path = _rm_dl_quota_db()
    try:
        db = _rm_dl_quota_sqlite3.connect(path, timeout=15)
        try:
            cols = _rm_dl_quota_columns(db)
            values = {}
            if 'status' in cols:
                values['status'] = 'queued'
            if 'phase' in cols:
                values['phase'] = 'waiting_quota'
            elif 'stage' in cols:
                values['stage'] = 'waiting_quota'
            if 'message' in cols:
                values['message'] = str(message)[:1000]
            elif 'error' in cols:
                values['error'] = str(message)[:1000]
            if 'updated_at' in cols:
                values['updated_at'] = _RmDlQuotaDateTime.now(
                    _RmDlQuotaTimezone.utc
                ).isoformat()
            if not values:
                return
            set_sql = ', '.join(f'{key}=?' for key in values)
            db.execute(
                f'UPDATE drive_link_jobs SET {set_sql} WHERE id=?',
                [*values.values(), int(job_id)],
            )
            db.commit()
        finally:
            db.close()
    except Exception:
        pass


def _rm_dl_quota_cancelled(job_id):
    if job_id is None:
        return False
    try:
        db = _rm_dl_quota_sqlite3.connect(_rm_dl_quota_db(), timeout=10)
        try:
            row = db.execute(
                'SELECT status FROM drive_link_jobs WHERE id=?',
                (int(job_id),),
            ).fetchone()
        finally:
            db.close()
        if not row:
            return True
        return str(row[0] or '').lower() in {
            'cancelled', 'canceled', 'deleted', 'done', 'completed', 'success'
        }
    except Exception:
        return False


def _rm_dl_quota_delay(attempt):
    schedule = (60, 120, 300, 600, 900)
    try:
        override = int(
            _rm_dl_quota_os.environ.get('RM_QUOTA_RETRY_SECONDS', '0') or 0
        )
    except Exception:
        override = 0
    if override > 0:
        return max(30, min(3600, override))
    return schedule[
        min(max(0, int(attempt) - 1), len(schedule) - 1)
    ]
'''

src += helpers
drive_py.write_text(src, encoding="utf-8")

with tempfile.NamedTemporaryFile(suffix=".pyc") as f:
    py_compile.compile(str(drive_py), doraise=True, cfile=f.name)

# Validação estrutural extra: o alias quebrado da .17 não pode existir no
# escopo global; o wrapper V2 precisa estar no código final.
check = drive_py.read_text(encoding="utf-8")
if "\n_RM_DL_QUOTA_ORIG_WORKER =" in check:
    raise SystemExit("Drive Link quota wait: alias global legado ainda presente")
if "RM_DRIVE_LINK_QUOTA_WAIT_WRAPPER_V2" not in check:
    raise SystemExit("Drive Link quota wait: wrapper V2 não foi inserido")

print(
    f"Drive Link quota wait OK: worker {worker_name} em escopo local; "
    "429/quota/rate-limit aguardam e retomam automaticamente"
)
