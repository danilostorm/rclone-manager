#!/usr/bin/env python3
from pathlib import Path
import ast
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
if "RM_DRIVE_LINK_QUOTA_WAIT_V1" in src:
    print("Drive Link quota wait: já aplicado")
    raise SystemExit(0)

tree = ast.parse(src)

# O worker normal é identificado estruturalmente pelo ponto em que confirma um
# item concluído ("completed += 1"). Isto evita depender do nome histórico da
# função, que mudou entre builds.
workers = []
for node in ast.walk(tree):
    if not isinstance(node, ast.FunctionDef):
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
        workers.append((node, hits[0]))

if not workers:
    raise SystemExit("Drive Link quota wait: worker com completed += 1 não encontrado")

# Prefira a função mais estreita que contém o marcador.
workers.sort(key=lambda pair: (getattr(pair[0], "end_lineno", 10**9) - pair[0].lineno))
worker, completed_node = workers[0]

if not worker.args.args:
    raise SystemExit("Drive Link quota wait: worker sem job_id")
job_arg = worker.args.args[0].arg
worker_name = worker.name

# Ache o try/except de item que envolve o completed += 1 e captura Exception.
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
insert_line = handler.lineno  # índice 0-based = linha imediatamente após except
body_indent = " " * (
    handler.body[0].col_offset if handler.body else handler.col_offset + 4
)
guard = (
    f"{body_indent}if _rm_dl_quota_is_error({exc_name}):\n"
    f"{body_indent}    raise _RmDriveLinkQuotaWait(str({exc_name}))\n"
)
lines.insert(insert_line, guard)
src = "".join(lines)

addon = f'''

# RM_DRIVE_LINK_QUOTA_WAIT_V1
# Cotas/rate limits são estado temporário, não falha definitiva. O worker
# normal é reiniciado a partir de completed_items após backoff, sem clique em
# "Tentar novamente". Como o mesmo worker permanece vivo durante a espera, a
# ordem da fila e a concorrência existente continuam respeitadas.
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
    # 403 sozinho pode ser autenticação/permissão. Só trate como cota quando a
    # própria mensagem também indicar rate/quota/limite.
    if ('403' in text) and any(
        token in text for token in ('quota', 'rate limit', 'cota', 'limite', 'bandwidth')
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
        return {str(row[1]) for row in db.execute('PRAGMA table_info(drive_link_jobs)')}
    except Exception:
        return set()


def _rm_dl_quota_update(job_id, message):
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
    # 1m, 2m, 5m, 10m e depois 15m. O teto curto permite recuperar sozinho
    # assim que a cota voltar, sem martelar o provider.
    schedule = (60, 120, 300, 600, 900)
    try:
        override = int(_rm_dl_quota_os.environ.get('RM_QUOTA_RETRY_SECONDS', '0') or 0)
    except Exception:
        override = 0
    if override > 0:
        return max(30, min(3600, override))
    return schedule[min(max(0, int(attempt) - 1), len(schedule) - 1)]


_RM_DL_QUOTA_ORIG_WORKER = {worker_name}


def {worker_name}(*args, **kwargs):
    job_id = args[0] if args else kwargs.get({job_arg!r})
    attempt = 0
    while True:
        try:
            return _RM_DL_QUOTA_ORIG_WORKER(*args, **kwargs)
        except _RmDriveLinkQuotaWait as exc:
            attempt += 1
            delay = _rm_dl_quota_delay(attempt)
            mins = max(1, int(round(delay / 60.0)))
            _rm_dl_quota_update(
                job_id,
                (
                    f'Cota temporariamente excedida; aguardando {mins} min '
                    f'para tentar novamente automaticamente · {str(exc)[:500]}'
                ),
            )

            # Sono cooperativo: Cancelar/Excluir encerra a espera em poucos
            # segundos em vez de aguardar o backoff inteiro.
            remaining = delay
            while remaining > 0:
                if _rm_dl_quota_cancelled(job_id):
                    return None
                step = min(10, remaining)
                _rm_dl_quota_time.sleep(step)
                remaining -= step

            _rm_dl_quota_update(
                job_id,
                f'Cota: iniciando tentativa automática {attempt + 1}',
            )
'''

src += addon
drive_py.write_text(src, encoding="utf-8")

with tempfile.NamedTemporaryFile(suffix=".pyc") as f:
    py_compile.compile(str(drive_py), doraise=True, cfile=f.name)

print(
    f"Drive Link quota wait OK: worker {worker_name} aguarda e retoma "
    "automaticamente em 429/quota/rate-limit"
)
