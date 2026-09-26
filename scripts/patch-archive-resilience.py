#!/usr/bin/env python3
from pathlib import Path
import sys
import tempfile
import py_compile

if len(sys.argv) != 2:
    raise SystemExit("uso: patch-archive-resilience.py SOURCE_ROOT")

root = Path(sys.argv[1])
archive_py = root / "app" / "archive_import.py"
if not archive_py.exists():
    raise SystemExit("Archive resilience: app/archive_import.py ausente")

src = archive_py.read_text(encoding="utf-8")
if "RM_ARCHIVE_RESILIENCE_V1" in src:
    print("Archive resilience: já aplicado")
    raise SystemExit(0)

addon = r'''

# RM_ARCHIVE_RESILIENCE_V1
# Robustez para downloads grandes de compactados:
# - retry automático com backoff em falhas transitórias de rede/provedor;
# - não exige clicar "Tentar novamente" para cada timeout/reset/5xx/429/403;
# - mantém a senha do job criptografada em /data somente enquanto necessária,
#   para que restart do Manager não faça o usuário digitá-la novamente.
import base64 as _rm_res_base64
import hashlib as _rm_res_hashlib
import json as _rm_res_json
import os as _rm_res_os
import time as _rm_res_time
from pathlib import Path as _RmResPath

try:
    from cryptography.fernet import Fernet as _RmResFernet
except Exception:
    _RmResFernet = None


_RM_RES_PASSWORD_FILE = DATA_DIR / 'archive-import-passwords.json'
_RM_RES_DOWNLOAD_ATTEMPTS = max(1, int(_rm_res_os.environ.get('RM_ARCHIVE_DOWNLOAD_ATTEMPTS', '6') or 6))
_RM_RES_BACKOFF = (2, 5, 10, 20, 30, 45)

_RM_RES_ORIG_CREATE_JOB = create_job
_RM_RES_ORIG_RESUME_WITH_PASSWORD = resume_with_password
_RM_RES_ORIG_DOWNLOAD_ONE = _download_one
_RM_RES_ORIG_UPDATE_JOB = _update_job
_RM_RES_ORIG_ARCHIVE_JOB_CONTROL = globals().get('archive_job_control')


def _rm_res_secret_key():
    secret = str(_rm_res_os.environ.get('APP_SECRET') or '').encode('utf-8')
    if not secret:
        return None
    digest = _rm_res_hashlib.sha256(secret).digest()
    return _rm_res_base64.urlsafe_b64encode(digest)


def _rm_res_fernet():
    key = _rm_res_secret_key()
    if not key or _RmResFernet is None:
        return None
    try:
        return _RmResFernet(key)
    except Exception:
        return None


def _rm_res_load_password_map():
    try:
        if not _RM_RES_PASSWORD_FILE.exists():
            return {}
        raw = _rm_res_json.loads(_RM_RES_PASSWORD_FILE.read_text(encoding='utf-8'))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _rm_res_save_password_map(data):
    try:
        _RM_RES_PASSWORD_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = _RM_RES_PASSWORD_FILE.with_suffix('.tmp')
        tmp.write_text(
            _rm_res_json.dumps(data, ensure_ascii=False, separators=(',', ':')),
            encoding='utf-8',
        )
        try:
            _rm_res_os.chmod(tmp, 0o600)
        except Exception:
            pass
        tmp.replace(_RM_RES_PASSWORD_FILE)
        try:
            _rm_res_os.chmod(_RM_RES_PASSWORD_FILE, 0o600)
        except Exception:
            pass
    except Exception:
        pass


def _rm_res_store_password(job_id, password):
    jid = str(job_id or '').strip()
    password = str(password or '')
    if not jid or not password:
        return
    f = _rm_res_fernet()
    if f is None:
        # Fail closed: do not persist plaintext if encryption is unavailable.
        return
    try:
        data = _rm_res_load_password_map()
        data[jid] = f.encrypt(password.encode('utf-8')).decode('ascii')
        _rm_res_save_password_map(data)
    except Exception:
        pass


def _rm_res_load_password(job_id):
    jid = str(job_id or '').strip()
    if not jid:
        return ''
    f = _rm_res_fernet()
    if f is None:
        return ''
    try:
        token = _rm_res_load_password_map().get(jid)
        if not token:
            return ''
        return f.decrypt(str(token).encode('ascii')).decode('utf-8')
    except Exception:
        return ''


def _rm_res_forget_password(job_id):
    jid = str(job_id or '').strip()
    if not jid:
        return
    try:
        data = _rm_res_load_password_map()
        if jid in data:
            data.pop(jid, None)
            _rm_res_save_password_map(data)
    except Exception:
        pass


def _rm_res_restore_password(job_id):
    jid = str(job_id or '').strip()
    if not jid:
        return ''
    current = str(_JOB_PASSWORDS.get(jid) or '')
    if current:
        return current
    saved = _rm_res_load_password(jid)
    if saved:
        _JOB_PASSWORDS[jid] = saved
    return saved


def create_job(payload):
    job = _RM_RES_ORIG_CREATE_JOB(payload)
    try:
        jid = str((job or {}).get('id') or (job or {}).get('job_id') or '')
        password = str(_JOB_PASSWORDS.get(jid) or '')
        if jid and password:
            _rm_res_store_password(jid, password)
    except Exception:
        pass
    return job


def resume_with_password(job_id, password):
    jid = str(job_id or '').strip()
    if password:
        _rm_res_store_password(jid, password)
    elif jid:
        password = _rm_res_restore_password(jid)
    return _RM_RES_ORIG_RESUME_WITH_PASSWORD(jid, password)


def _update_job(job_id, **fields):
    result = _RM_RES_ORIG_UPDATE_JOB(job_id, **fields)
    status = str(fields.get('status') or '').lower()
    if status in {'done', 'completed', 'complete', 'success', 'deleted'}:
        _rm_res_forget_password(job_id)
    return result


def _rm_res_transient_download_error(exc):
    text = (type(exc).__name__ + ': ' + str(exc)).lower()

    # Password/format/CRC failures need user action or a valid archive; retrying
    # the network download blindly only wastes bandwidth.
    permanent = (
        'password', 'senha', 'encrypted', 'crc', 'checksum',
        'unsupported archive', 'formato', 'not an archive',
        'arquivo compactado não reconhecido', 'no space', 'espaço livre',
    )
    if any(x in text for x in permanent):
        return False

    transient = (
        'timeout', 'timed out', 'connection', 'reset by peer', 'broken pipe',
        'temporary failure', 'temporarily unavailable', 'remote end closed',
        'incomplete read', 'chunkedencoding', 'contentdecoding',
        'network is unreachable', 'name or service not known',
        '429', '403', '408', '425', '500', '502', '503', '504',
        'bad gateway', 'service unavailable', 'gateway timeout',
        'too many requests', 'unexpected eof', 'eof',
    )
    return any(x in text for x in transient)


def _rm_res_snapshot(dest):
    out = {}
    try:
        for p in _RmResPath(dest).iterdir():
            if p.is_file():
                try:
                    st = p.stat()
                    out[str(p)] = (int(st.st_size), int(st.st_mtime_ns))
                except Exception:
                    pass
    except Exception:
        pass
    return out


def _rm_res_cleanup_failed_attempt(dest, before):
    # Preserve files completed by previous links. Remove only files created or
    # modified by the failed attempt so the next retry starts cleanly.
    try:
        for p in _RmResPath(dest).iterdir():
            if not p.is_file():
                continue
            try:
                st = p.stat()
                old = before.get(str(p))
                changed = old is None or old != (int(st.st_size), int(st.st_mtime_ns))
                if changed:
                    p.unlink(missing_ok=True)
            except Exception:
                pass
    except Exception:
        pass


def _download_one(job_id, row, dest, index, total):
    jid = str(job_id or '').strip()
    last_exc = None

    for attempt in range(1, _RM_RES_DOWNLOAD_ATTEMPTS + 1):
        before = _rm_res_snapshot(dest)
        try:
            # Password belongs to the archive phase, but restoring it here
            # guarantees it is back in memory after a process restart before
            # the job reaches analysis/extraction.
            _rm_res_restore_password(jid)
            return _RM_RES_ORIG_DOWNLOAD_ONE(job_id, row, dest, index, total)
        except Exception as exc:
            last_exc = exc
            if not _rm_res_transient_download_error(exc):
                raise

            _rm_res_cleanup_failed_attempt(dest, before)

            if attempt >= _RM_RES_DOWNLOAD_ATTEMPTS:
                break

            wait_s = _RM_RES_BACKOFF[min(attempt - 1, len(_RM_RES_BACKOFF) - 1)]
            label = ''
            if isinstance(row, dict):
                label = str(row.get('label') or row.get('name') or row.get('url') or '')[:180]

            try:
                _RM_RES_ORIG_UPDATE_JOB(
                    jid,
                    status='running',
                    phase='download_retry',
                    current_item=label,
                    message=(
                        f'Falha transitória no download; tentativa '
                        f'{attempt + 1}/{_RM_RES_DOWNLOAD_ATTEMPTS} em {wait_s}s'
                    ),
                    error=str(exc)[:1000],
                )
            except Exception:
                pass

            _rm_res_time.sleep(wait_s)

    raise last_exc


if callable(_RM_RES_ORIG_ARCHIVE_JOB_CONTROL):
    def archive_job_control(job_id, action, password='', cleanup=True):
        jid = str(job_id or '').strip()
        action = str(action or '').strip().lower()

        if password:
            _JOB_PASSWORDS[jid] = str(password)
            _rm_res_store_password(jid, password)
        elif action in {'resume', 'retry', 'restart'}:
            _rm_res_restore_password(jid)

        result = _RM_RES_ORIG_ARCHIVE_JOB_CONTROL(
            jid, action, password or _JOB_PASSWORDS.get(jid, ''), cleanup
        )

        if action == 'delete':
            _rm_res_forget_password(jid)
        return result


# Restore secrets for unfinished persisted jobs at process start. We never
# restart jobs automatically here; this only prevents password loss when the
# user clicks Continuar/Tentar novamente after a Manager restart.
try:
    for _rm_job in list_jobs(500) or []:
        if not isinstance(_rm_job, dict):
            continue
        _rm_jid = str(_rm_job.get('id') or _rm_job.get('job_id') or '')
        _rm_status = str(_rm_job.get('status') or '').lower()
        if _rm_jid and _rm_status not in {'done', 'completed', 'success', 'deleted'}:
            _rm_res_restore_password(_rm_jid)
except Exception:
    pass
'''

archive_py.write_text(src + addon, encoding="utf-8")

with tempfile.NamedTemporaryFile(suffix=".pyc") as f:
    py_compile.compile(str(archive_py), doraise=True, cfile=f.name)

print(
    "Archive resilience OK: retry automático de download + senha criptografada "
    "persistente até conclusão/exclusão"
)
