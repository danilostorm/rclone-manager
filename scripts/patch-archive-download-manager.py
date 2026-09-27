#!/usr/bin/env python3
from pathlib import Path
import sys
import tempfile
import py_compile

if len(sys.argv) != 2:
    raise SystemExit("uso: patch-archive-download-manager.py SOURCE_ROOT")

root = Path(sys.argv[1])
appdir = root / "app"
archive_py = appdir / "archive_import.py"
app_py = appdir / "app.py"
tpl = appdir / "templates" / "api_manager.html"

if not archive_py.exists() or not app_py.exists():
    raise SystemExit("Archive download manager: archive_import.py/app.py ausente")

src = archive_py.read_text(encoding="utf-8")
if "RM_ARCHIVE_DOWNLOAD_MANAGER_V1" not in src:
    addon = r'''

# RM_ARCHIVE_DOWNLOAD_MANAGER_V1
# Fila persistente e serial para compactados. O objetivo é proteger disco
# limitado e transformar o importador em um download manager previsível:
# 1 job por vez por padrão, fila persistente, pausa global, bloqueio após erro,
# progresso por bytes/velocidade/ETA e suporte a pasta pública do Dropbox.
import json as _rmqm_json
import os as _rmqm_os
import shutil as _rmqm_shutil
import threading as _rmqm_threading
import time as _rmqm_time
import urllib.parse as _rmqm_urlparse
from pathlib import Path as _RmqmPath


_RMQM_STATE_FILE = DATA_DIR / 'archive-download-manager.json'
_RMQM_LOCK = _rmqm_threading.RLock()
_RMQM_WAKE = _rmqm_threading.Event()
_RMQM_DYNAMIC = {}
_RMQM_WATCHING = set()
_RMQM_DEFAULTS = {
    'max_concurrent_jobs': 1,
    'stop_queue_on_error': True,
    'min_free_gb': 10,
    'max_staging_gb': 0,
}

_RMQM_ORIG_START_JOB = _start_job
_RMQM_ORIG_LIST_JOBS = list_jobs
_RMQM_ORIG_ARCHIVE_CONTROL = archive_job_control
_RMQM_ORIG_DOWNLOAD_ONE = _download_one
_RMQM_ORIG_UPDATE_JOB = _update_job


def _rmqm_default_state():
    return {
        'queue': [],
        'paused': False,
        'blocked_by': '',
        'settings': dict(_RMQM_DEFAULTS),
    }


def _rmqm_load_state():
    state = _rmqm_default_state()
    try:
        if _RMQM_STATE_FILE.exists():
            raw = _rmqm_json.loads(_RMQM_STATE_FILE.read_text(encoding='utf-8'))
            if isinstance(raw, dict):
                state.update({k: raw.get(k, state[k]) for k in ('queue', 'paused', 'blocked_by')})
                cfg = raw.get('settings')
                if isinstance(cfg, dict):
                    state['settings'].update(cfg)
    except Exception:
        pass

    state['queue'] = [str(x) for x in (state.get('queue') or []) if str(x).strip()]
    state['queue'] = list(dict.fromkeys(state['queue']))
    state['paused'] = bool(state.get('paused'))
    state['blocked_by'] = str(state.get('blocked_by') or '')

    cfg = state['settings']
    try:
        cfg['max_concurrent_jobs'] = max(1, min(4, int(cfg.get('max_concurrent_jobs') or 1)))
    except Exception:
        cfg['max_concurrent_jobs'] = 1
    cfg['stop_queue_on_error'] = bool(cfg.get('stop_queue_on_error', True))
    try:
        cfg['min_free_gb'] = max(1, min(500, int(cfg.get('min_free_gb') or 10)))
    except Exception:
        cfg['min_free_gb'] = 10
    try:
        cfg['max_staging_gb'] = max(0, min(5000, int(cfg.get('max_staging_gb') or 0)))
    except Exception:
        cfg['max_staging_gb'] = 0
    return state


_RMQM_STATE = _rmqm_load_state()


def _rmqm_save_state():
    with _RMQM_LOCK:
        try:
            _RMQM_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = _RMQM_STATE_FILE.with_suffix('.tmp')
            tmp.write_text(
                _rmqm_json.dumps(_RMQM_STATE, ensure_ascii=False, separators=(',', ':')),
                encoding='utf-8',
            )
            try:
                _rmqm_os.chmod(tmp, 0o600)
            except Exception:
                pass
            tmp.replace(_RMQM_STATE_FILE)
            try:
                _rmqm_os.chmod(_RMQM_STATE_FILE, 0o600)
            except Exception:
                pass
        except Exception:
            pass


def _rmqm_worker_alive(job_id):
    jid = str(job_id or '')
    try:
        with _JOB_LOCK:
            th = _JOB_THREADS.get(jid)
            return bool(th and th.is_alive())
    except Exception:
        return False


def _rmqm_job_status(job_id):
    try:
        return str((get_job(str(job_id)) or {}).get('status') or '').lower()
    except Exception:
        return ''


def _rmqm_expected_bytes(job):
    if not isinstance(job, dict):
        return 0
    candidates = []
    for key in (
        'expected_download_bytes', 'source_size_bytes', 'total_size_bytes',
        'archive_bytes', 'content_length', 'size_bytes'
    ):
        try:
            value = int(job.get(key) or 0)
            if value > 0:
                candidates.append(value)
        except Exception:
            pass

    for key in ('links_json', 'items_json'):
        raw = job.get(key)
        if not raw:
            continue
        try:
            rows = _rmqm_json.loads(raw) if isinstance(raw, str) else raw
            total = sum(
                max(0, int(row.get('size_bytes') or row.get('content_length') or 0))
                for row in (rows or []) if isinstance(row, dict)
            )
            if total > 0:
                candidates.append(total)
        except Exception:
            pass
    return max(candidates) if candidates else 0


def _rmqm_download_dir(job_id):
    stage = STAGING_ROOT / ('job-' + str(job_id or ''))
    direct = stage / 'downloads'
    if direct.exists():
        return direct
    return stage


def _rmqm_dir_bytes(path):
    total = 0
    try:
        for p in _RmqmPath(path).rglob('*'):
            if p.is_file():
                try:
                    total += int(p.stat().st_size)
                except Exception:
                    pass
    except Exception:
        pass
    return total


def _rmqm_disk_stats(deep=False):
    try:
        usage = _rmqm_shutil.disk_usage(STAGING_ROOT)
        free = int(usage.free)
        total = int(usage.total)
    except Exception:
        free = total = 0
    if deep:
        staging = _rmqm_dir_bytes(STAGING_ROOT)
    else:
        staging = sum(
            max(0, int((row or {}).get('downloaded_bytes_live') or 0))
            for row in _RMQM_DYNAMIC.values()
        )
    return {
        'disk_total_bytes': total,
        'disk_free_bytes': free,
        'staging_bytes': staging,
    }


def _rmqm_can_start(job):
    cfg = _RMQM_STATE['settings']
    stats = _rmqm_disk_stats(deep=bool(int(cfg.get('max_staging_gb') or 0)))
    free = int(stats.get('disk_free_bytes') or 0)
    staging = int(stats.get('staging_bytes') or 0)
    expected = _rmqm_expected_bytes(job)
    min_free = int(cfg.get('min_free_gb') or 10) * 1024**3
    max_staging = int(cfg.get('max_staging_gb') or 0) * 1024**3

    if free and free <= min_free:
        return False, (
            f'Aguardando espaço: livre {free/1024**3:.1f} GB; '
            f'mínimo configurado {min_free/1024**3:.0f} GB'
        )

    if expected and free and free - expected < min_free:
        return False, (
            f'Aguardando espaço: tarefa precisa ~{expected/1024**3:.1f} GB; '
            f'livre {free/1024**3:.1f} GB'
        )

    if max_staging and staging + expected > max_staging:
        return False, (
            f'Aguardando limite de staging: uso {staging/1024**3:.1f} GB; '
            f'limite {max_staging/1024**3:.0f} GB'
        )
    return True, ''


def _rmqm_queue_add(job_id, front=False):
    jid = str(job_id or '').strip()
    if not jid:
        return
    with _RMQM_LOCK:
        q = [x for x in _RMQM_STATE['queue'] if x != jid]
        if front:
            q.insert(0, jid)
        else:
            q.append(jid)
        _RMQM_STATE['queue'] = q
        _rmqm_save_state()


def _rmqm_queue_remove(job_id):
    jid = str(job_id or '').strip()
    with _RMQM_LOCK:
        _RMQM_STATE['queue'] = [x for x in _RMQM_STATE['queue'] if x != jid]
        _rmqm_save_state()


def _rmqm_queue_move(job_id, delta):
    jid = str(job_id or '').strip()
    with _RMQM_LOCK:
        q = list(_RMQM_STATE['queue'])
        if jid not in q:
            return
        i = q.index(jid)
        j = max(0, min(len(q) - 1, i + int(delta)))
        if i != j:
            q.pop(i)
            q.insert(j, jid)
            _RMQM_STATE['queue'] = q
            _rmqm_save_state()
    _RMQM_WAKE.set()


def _rmqm_start_job(job_id):
    jid = str(job_id or '').strip()
    if not jid:
        return False
    if _rmqm_worker_alive(jid):
        return True

    _rmqm_queue_add(jid)
    try:
        _RMQM_ORIG_UPDATE_JOB(
            jid,
            status='queued',
            phase='queued',
            message='Aguardando vaga na fila de compactados',
            error='',
            finished_at='',
        )
    except Exception:
        pass
    _RMQM_WAKE.set()
    return True


_start_job = _rmqm_start_job


def _rmqm_progress_watch(job_id):
    jid = str(job_id or '').strip()
    with _RMQM_LOCK:
        _RMQM_WATCHING.add(jid)
    last_bytes = 0
    last_ts = _rmqm_time.time()
    smooth_speed = 0.0

    while _rmqm_worker_alive(jid):
        now = _rmqm_time.time()
        job = get_job(jid) or {}
        phase = str(job.get('phase') or '').lower()
        expected = _rmqm_expected_bytes(job)

        downloaded = int(job.get('downloaded_bytes') or 0)
        if phase in {
            'starting', 'downloading', 'download', 'download_retry', 'auto_retry',
            'analyzing', 'analysing', 'extracting_staging'
        }:
            stage_bytes = _rmqm_dir_bytes(_rmqm_download_dir(jid))
            downloaded = max(downloaded, stage_bytes)

        dt = max(0.001, now - last_ts)
        instant = max(0, downloaded - last_bytes) / dt
        smooth_speed = instant if smooth_speed <= 0 else (smooth_speed * 0.72 + instant * 0.28)

        remaining = max(0, expected - downloaded) if expected else 0
        eta = int(remaining / smooth_speed) if remaining and smooth_speed > 1024 else 0
        pct = min(100.0, downloaded * 100.0 / expected) if expected else 0.0

        _RMQM_DYNAMIC[jid] = {
            'download_expected_bytes': expected,
            'downloaded_bytes_live': downloaded,
            'download_remaining_bytes': remaining,
            'download_speed_bps': int(smooth_speed),
            'download_eta_seconds': eta,
            'download_progress_pct': pct,
        }

        try:
            if downloaded > int(job.get('downloaded_bytes') or 0):
                _RMQM_ORIG_UPDATE_JOB(jid, downloaded_bytes=downloaded)
        except Exception:
            pass

        last_bytes = downloaded
        last_ts = now
        _rmqm_time.sleep(1.5)

    _rmqm_time.sleep(0.25)
    job = get_job(jid) or {}
    status = str(job.get('status') or '').lower()
    cfg = _RMQM_STATE['settings']

    with _RMQM_LOCK:
        if status in {'error', 'failed'} and cfg.get('stop_queue_on_error', True):
            _RMQM_STATE['blocked_by'] = jid
        elif _RMQM_STATE.get('blocked_by') == jid and status not in {'error', 'failed'}:
            _RMQM_STATE['blocked_by'] = ''
        _rmqm_save_state()

    with _RMQM_LOCK:
        _RMQM_WATCHING.discard(jid)
    _RMQM_WAKE.set()


def _rmqm_dispatch_once():
    with _RMQM_LOCK:
        if _RMQM_STATE.get('paused'):
            return
        blocked = str(_RMQM_STATE.get('blocked_by') or '')
        if blocked:
            bstatus = _rmqm_job_status(blocked)
            if bstatus in {'error', 'failed', 'interrupted'}:
                return
            _RMQM_STATE['blocked_by'] = ''
            _rmqm_save_state()

        limit = int(_RMQM_STATE['settings'].get('max_concurrent_jobs') or 1)
        active_ids = {str(jid) for jid in list(_JOB_THREADS) if _rmqm_worker_alive(jid)}
        active_ids.update(_RMQM_WATCHING)
        slots = max(0, limit - len(active_ids))

        while slots > 0 and _RMQM_STATE['queue']:
            jid = _RMQM_STATE['queue'][0]
            job = get_job(jid) or {}
            status = str(job.get('status') or '').lower()

            if not job or status in {'deleted', 'done', 'completed', 'complete', 'success', 'canceled', 'cancelled'}:
                _RMQM_STATE['queue'].pop(0)
                _rmqm_save_state()
                continue

            if status in {'error', 'failed', 'interrupted'}:
                if _RMQM_STATE['settings'].get('stop_queue_on_error', True):
                    _RMQM_STATE['blocked_by'] = jid
                    _rmqm_save_state()
                    return
                _RMQM_STATE['queue'].pop(0)
                _rmqm_save_state()
                continue

            can_start, reason = _rmqm_can_start(job)
            if not can_start:
                try:
                    _RMQM_ORIG_UPDATE_JOB(
                        jid,
                        status='queued',
                        phase='waiting_space',
                        message=reason,
                    )
                except Exception:
                    pass
                return

            _RMQM_STATE['queue'].pop(0)
            _rmqm_save_state()

            try:
                _RMQM_ORIG_UPDATE_JOB(
                    jid,
                    status='queued',
                    phase='starting',
                    message='Iniciando pela fila de compactados',
                    error='',
                    finished_at='',
                )
            except Exception:
                pass

            _RMQM_WATCHING.add(jid)
            try:
                _RMQM_ORIG_START_JOB(jid)
                _rmqm_threading.Thread(
                    target=_rmqm_progress_watch,
                    args=(jid,),
                    name='archive-manager-watch-' + jid,
                    daemon=True,
                ).start()
                slots -= 1
            except Exception:
                _RMQM_WATCHING.discard(jid)
                _rmqm_queue_add(jid, front=True)
                raise


def _rmqm_dispatch_loop():
    while True:
        _RMQM_WAKE.wait(timeout=3.0)
        _RMQM_WAKE.clear()
        try:
            _rmqm_dispatch_once()
        except Exception:
            pass


def _rmqm_is_dropbox_folder(url):
    try:
        p = _rmqm_urlparse.urlparse(str(url or ''))
        host = (p.hostname or '').lower()
        path = p.path.lower()
        return (
            host.endswith('dropbox.com')
            and ('/scl/fo/' in path or path.startswith('/sh/'))
        )
    except Exception:
        return False


def _rmqm_dropbox_folder_download(url):
    p = _rmqm_urlparse.urlparse(str(url or ''))
    q = _rmqm_urlparse.parse_qs(p.query, keep_blank_values=True)
    q['dl'] = ['1']
    return _rmqm_urlparse.urlunparse(
        p._replace(query=_rmqm_urlparse.urlencode(q, doseq=True))
    )


def _download_one(job_id, row, dest, index, total):
    if isinstance(row, dict):
        url = str(row.get('url') or row.get('href') or '')
        if _rmqm_is_dropbox_folder(url):
            row = dict(row)
            row['url'] = _rmqm_dropbox_folder_download(url)
            label = str(row.get('label') or row.get('name') or 'Dropbox-folder').strip()
            if not label.lower().endswith('.zip'):
                label = label.rstrip('/ ') + '.zip'
            row['label'] = label
            row['name'] = label
            row['file_extension'] = 'ZIP'
            row['source_type'] = 'dropbox'
    return _RMQM_ORIG_DOWNLOAD_ONE(job_id, row, dest, index, total)


def list_jobs(limit=50):
    rows = _RMQM_ORIG_LIST_JOBS(limit) or []
    with _RMQM_LOCK:
        q = list(_RMQM_STATE['queue'])
        paused = bool(_RMQM_STATE.get('paused'))
        blocked = str(_RMQM_STATE.get('blocked_by') or '')

    out = []
    for row in rows:
        if not isinstance(row, dict):
            out.append(row)
            continue
        item = dict(row)
        jid = str(item.get('id') or item.get('job_id') or '')
        if jid in q:
            item['queue_position'] = q.index(jid) + 1
        else:
            item['queue_position'] = 0
        item['queue_paused'] = paused
        item['queue_blocked_by'] = blocked
        item.update(_RMQM_DYNAMIC.get(jid) or {})
        if not item.get('download_expected_bytes'):
            item['download_expected_bytes'] = _rmqm_expected_bytes(item)
        if not item.get('downloaded_bytes_live'):
            item['downloaded_bytes_live'] = int(item.get('downloaded_bytes') or 0)
        expected = int(item.get('download_expected_bytes') or 0)
        downloaded = int(item.get('downloaded_bytes_live') or 0)
        if expected:
            item['download_remaining_bytes'] = max(0, expected - downloaded)
            if not item.get('download_progress_pct'):
                item['download_progress_pct'] = min(100.0, downloaded * 100.0 / expected)
        out.append(item)
    return out


def archive_manager_status():
    stats = _rmqm_disk_stats(deep=False)
    with _RMQM_LOCK:
        state = {
            'queue': list(_RMQM_STATE['queue']),
            'paused': bool(_RMQM_STATE.get('paused')),
            'blocked_by': str(_RMQM_STATE.get('blocked_by') or ''),
            'settings': dict(_RMQM_STATE['settings']),
        }
    state.update(stats)
    state['active_jobs'] = [
        str(jid) for jid in list(_JOB_THREADS) if _rmqm_worker_alive(jid)
    ]
    state['queue_length'] = len(state['queue'])
    return state


def archive_manager_command(payload=None):
    payload = payload if isinstance(payload, dict) else {}
    action = str(payload.get('action') or '').strip().lower()

    with _RMQM_LOCK:
        if action == 'pause':
            _RMQM_STATE['paused'] = True
        elif action == 'resume':
            _RMQM_STATE['paused'] = False
        elif action == 'release_error':
            _RMQM_STATE['blocked_by'] = ''

        cfg = _RMQM_STATE['settings']
        if 'max_concurrent_jobs' in payload:
            cfg['max_concurrent_jobs'] = max(1, min(4, int(payload['max_concurrent_jobs'])))
        if 'stop_queue_on_error' in payload:
            cfg['stop_queue_on_error'] = bool(payload['stop_queue_on_error'])
        if 'min_free_gb' in payload:
            cfg['min_free_gb'] = max(1, min(500, int(payload['min_free_gb'])))
        if 'max_staging_gb' in payload:
            cfg['max_staging_gb'] = max(0, min(5000, int(payload['max_staging_gb'])))
        _rmqm_save_state()

    _RMQM_WAKE.set()
    return {'ok': True, **archive_manager_status()}


def archive_job_control(job_id, action, password='', cleanup=True):
    jid = str(job_id or '').strip()
    action = str(action or '').strip().lower()

    if action == 'move_up':
        _rmqm_queue_move(jid, -1)
        return {'id': jid, 'job_id': jid, 'status': _rmqm_job_status(jid), 'queue_action': action}
    if action == 'move_down':
        _rmqm_queue_move(jid, 1)
        return {'id': jid, 'job_id': jid, 'status': _rmqm_job_status(jid), 'queue_action': action}
    if action == 'start_now':
        with _RMQM_LOCK:
            _RMQM_STATE['blocked_by'] = ''
            _RMQM_STATE['paused'] = False
            _rmqm_save_state()
        _rmqm_queue_add(jid, front=True)
        _RMQM_WAKE.set()
        return {'id': jid, 'job_id': jid, 'status': _rmqm_job_status(jid), 'queue_action': action}

    if action in {'resume', 'retry', 'restart'}:
        with _RMQM_LOCK:
            if _RMQM_STATE.get('blocked_by') == jid:
                _RMQM_STATE['blocked_by'] = ''
                _rmqm_save_state()
        result = _RMQM_ORIG_ARCHIVE_CONTROL(jid, action, password, cleanup)
        _rmqm_queue_add(jid, front=True)
        _RMQM_WAKE.set()
        return result

    result = _RMQM_ORIG_ARCHIVE_CONTROL(jid, action, password, cleanup)

    if action in {'cancel', 'delete'}:
        _rmqm_queue_remove(jid)
        with _RMQM_LOCK:
            if _RMQM_STATE.get('blocked_by') == jid:
                _RMQM_STATE['blocked_by'] = ''
                _rmqm_save_state()
        _RMQM_WAKE.set()
    return result


def _rmqm_recover_queue():
    with _RMQM_LOCK:
        cleaned = []
        for jid in list(_RMQM_STATE['queue']):
            job = get_job(jid) or {}
            status = str(job.get('status') or '').lower()
            if not job or status in {'deleted', 'done', 'completed', 'success', 'canceled', 'cancelled'}:
                continue
            if status == 'interrupted':
                try:
                    _RMQM_ORIG_UPDATE_JOB(
                        jid,
                        status='queued',
                        phase='queued',
                        message='Fila restaurada após reinício do Manager',
                        finished_at='',
                    )
                except Exception:
                    pass
            cleaned.append(jid)
        _RMQM_STATE['queue'] = cleaned

        if not _RMQM_STATE.get('blocked_by'):
            # Uma tarefa que estava ativa durante restart não estava mais na
            # lista queue; mantenha a fila parada até o usuário decidir.
            for row in _RMQM_ORIG_LIST_JOBS(200) or []:
                if not isinstance(row, dict):
                    continue
                if str(row.get('status') or '').lower() == 'interrupted':
                    _RMQM_STATE['blocked_by'] = str(row.get('id') or row.get('job_id') or '')
                    break
        _rmqm_save_state()


_rmqm_recover_queue()
_rmqm_threading.Thread(
    target=_rmqm_dispatch_loop,
    name='archive-download-manager',
    daemon=True,
).start()
_RMQM_WAKE.set()
'''
    archive_py.write_text(src + addon, encoding="utf-8")
    with tempfile.NamedTemporaryFile(suffix=".pyc") as f:
        py_compile.compile(str(archive_py), doraise=True, cfile=f.name)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
app = app_py.read_text(encoding="utf-8")
if "RM_ARCHIVE_DOWNLOAD_MANAGER_ROUTES_V1" not in app:
    marker = "# RM_ARCHIVE_IMPORT_ROUTES_V1"
    pos = app.find(marker)
    if pos < 0:
        raise SystemExit("Archive download manager: marcador de rotas ausente")

    routes = r'''
# RM_ARCHIVE_DOWNLOAD_MANAGER_ROUTES_V1
@app.route('/api/v1/extension/archive/manager', methods=['GET', 'POST', 'OPTIONS'])
@extension_api_required
def extension_archive_manager_v1():
    from archive_import import archive_manager_status, archive_manager_command
    try:
        if request.method == 'POST':
            return jsonify(archive_manager_command(request.get_json(silent=True) or {}))
        return jsonify({'ok': True, 'manager': archive_manager_status()})
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400


'''
    app = app[:pos] + routes + app[pos:]

if "RM_ARCHIVE_DOWNLOAD_MANAGER_WEB_ROUTES_V1" not in app and "RM_ARCHIVE_WEB_ROUTES_V1" in app:
    marker = "# RM_ARCHIVE_IMPORT_ROUTES_V1"
    pos = app.find(marker)
    web = r'''
# RM_ARCHIVE_DOWNLOAD_MANAGER_WEB_ROUTES_V1
@app.route('/api/v1/archive/manager', methods=['GET', 'POST'])
def web_archive_manager_v1():
    from archive_import import archive_manager_status, archive_manager_command
    try:
        if request.method == 'POST':
            return jsonify(archive_manager_command(request.get_json(silent=True) or {}))
        return jsonify({'ok': True, 'manager': archive_manager_status()})
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400


'''
    app = app[:pos] + web + app[pos:]

app_py.write_text(app, encoding="utf-8")
with tempfile.NamedTemporaryFile(suffix=".pyc") as f:
    py_compile.compile(str(app_py), doraise=True, cfile=f.name)

# ---------------------------------------------------------------------------
# API Manager UI + external CSS
# ---------------------------------------------------------------------------
if tpl.exists():
    static_dir = appdir / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    css = static_dir / "archive-download-manager.css"
    css.write_text(r'''
#rmArchiveManagerV2 .rmqm-summary{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:8px;color:#9fb8d6;font-size:11px}
#rmArchiveManagerV2 .rmqm-pill{display:inline-flex;align-items:center;min-height:26px;padding:4px 8px;border:1px solid #34465e;border-radius:999px;background:#0c1522}
#rmArchiveManagerV2 .rmqm-pill.warn{border-color:#7c551f;background:#21180c;color:#ffd08a}
#rmArchiveManagerV2 .rmqm-pill.bad{border-color:#7f1d1d;background:#2b1117;color:#fecaca}
#rmArchiveManagerV2 .rmqm-manager-controls{display:flex;gap:7px;align-items:center;flex-wrap:wrap}
#rmArchiveManagerV2 .rmqm-manager-controls label{display:flex;gap:5px;align-items:center;color:#9fb8d6;font-size:11px}
#rmArchiveManagerV2 .rmqm-manager-controls select{min-height:32px;padding:5px 8px;border:1px solid #3b4b63;border-radius:8px;background:#0b1421;color:#eef4fb}
#rmArchiveManagerV2 .rmqm-download-info{grid-column:1/-1;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;padding:9px 10px;border-radius:9px;background:#0b1421;border:1px solid #223147}
#rmArchiveManagerV2 .rmqm-kpi{min-width:0}
#rmArchiveManagerV2 .rmqm-kpi span{display:block;color:#7896b9;font-size:9px;font-weight:700;letter-spacing:.04em}
#rmArchiveManagerV2 .rmqm-kpi b{display:block;margin-top:3px;color:#e8f0fa;font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#rmArchiveManagerV2 .rmqm-queue-actions{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
#rmArchiveManagerV2 .rmqm-queue-actions button{min-height:30px!important;padding:5px 8px!important;font-size:10px!important}
@media(max-width:850px){#rmArchiveManagerV2 .rmqm-download-info{grid-template-columns:1fr 1fr}}
@media(max-width:520px){#rmArchiveManagerV2 .rmqm-download-info{grid-template-columns:1fr}}
''', encoding="utf-8")

    page = tpl.read_text(encoding="utf-8")
    if "RM_ARCHIVE_DOWNLOAD_MANAGER_UI_V1" not in page:
        ui = r'''
<!-- RM_ARCHIVE_DOWNLOAD_MANAGER_UI_V1 -->
<script>
(() => {
  const fmtBytes = n => {
    n=Number(n||0); if(!n)return '—';
    const u=['B','KB','MB','GB','TB']; let i=0;
    while(n>=1024&&i<u.length-1){n/=1024;i++}
    return n.toFixed(i>=3?1:0)+' '+u[i];
  };
  const fmtTime = s => {
    s=Number(s||0); if(!s)return '—';
    if(s<60)return Math.ceil(s)+'s';
    if(s<3600)return Math.ceil(s/60)+'min';
    return (s/3600).toFixed(1)+'h';
  };
  const jobsById = () => new Map((window.__rmArchiveJobsV2||[]).map(j=>[String(j.id||j.job_id||''),j]));
  let manager=null;

  function cardId(card){
    const txt=Array.from(card.querySelectorAll('.rm-arc-meta')).map(x=>x.textContent||'').join(' ');
    const m=txt.match(/#([A-Za-z0-9_-]{6,64})/); return m?m[1]:'';
  }

  async function api(url, body){
    const r=await fetch(url,{method:body?'POST':'GET',credentials:'same-origin',cache:'no-store',
      headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});
    const d=await r.json().catch(()=>({}));
    if(!r.ok||d.ok===false)throw new Error(d.error||('HTTP '+r.status));
    return d;
  }

  async function managerCommand(body){
    try{await api('/api/v1/archive/manager',body); await refreshManager(); document.getElementById('rmArcRefreshV2')?.click();}
    catch(e){alert(e.message)}
  }

  async function jobAction(id, action){
    try{await api('/api/v1/archive/jobs/'+encodeURIComponent(id)+'/action',{action,cleanup:true}); document.getElementById('rmArcRefreshV2')?.click(); await refreshManager();}
    catch(e){alert(e.message)}
  }

  function ensureManagerUI(){
    const root=document.getElementById('rmArchiveManagerV2'); if(!root)return;
    const head=root.querySelector('.rm-arc-head'); if(!head)return;

    if(!root.querySelector('.rmqm-manager-controls')){
      const controls=document.createElement('div'); controls.className='rmqm-manager-controls';
      controls.innerHTML='<span id="rmqmQueueState" class="rmqm-pill">Fila</span><button id="rmqmPauseBtn" type="button">Pausar fila</button><label>Simultâneos <select id="rmqmConcurrent"><option>1</option><option>2</option><option>3</option></select></label><label><input id="rmqmStopOnError" type="checkbox"> parar em erro</label>';
      head.appendChild(controls);
      controls.querySelector('#rmqmPauseBtn').onclick=()=>managerCommand({action:manager?.paused?'resume':'pause'});
      controls.querySelector('#rmqmConcurrent').onchange=e=>managerCommand({max_concurrent_jobs:Number(e.target.value)});
      controls.querySelector('#rmqmStopOnError').onchange=e=>managerCommand({stop_queue_on_error:e.target.checked});
    }

    if(!root.querySelector('.rmqm-summary')){
      const stats=root.querySelector('.rm-arc-stats');
      const row=document.createElement('div'); row.className='rmqm-summary';
      row.innerHTML='<span id="rmqmQueued" class="rmqm-pill">Fila: —</span><span id="rmqmDisk" class="rmqm-pill">Disco: —</span><span id="rmqmStage" class="rmqm-pill">Staging: —</span><span id="rmqmBlock" class="rmqm-pill">Pronta</span>';
      stats?.insertAdjacentElement('afterend',row);
    }
  }

  function renderManager(){
    ensureManagerUI(); if(!manager)return;
    const root=document.getElementById('rmArchiveManagerV2'); if(!root)return;
    const cfg=manager.settings||{};
    const state=root.querySelector('#rmqmQueueState');
    if(state){state.textContent=manager.paused?'Fila pausada':(manager.blocked_by?'Fila bloqueada':'Fila ativa'); state.className='rmqm-pill '+(manager.blocked_by?'bad':manager.paused?'warn':'');}
    const pause=root.querySelector('#rmqmPauseBtn'); if(pause)pause.textContent=manager.paused?'Retomar fila':'Pausar fila';
    const conc=root.querySelector('#rmqmConcurrent'); if(conc)conc.value=String(cfg.max_concurrent_jobs||1);
    const stop=root.querySelector('#rmqmStopOnError'); if(stop)stop.checked=cfg.stop_queue_on_error!==false;
    const q=root.querySelector('#rmqmQueued'); if(q)q.textContent='Fila: '+Number(manager.queue_length||0)+' aguardando';
    const disk=root.querySelector('#rmqmDisk'); if(disk)disk.textContent='Livre: '+fmtBytes(manager.disk_free_bytes);
    const stage=root.querySelector('#rmqmStage'); if(stage)stage.textContent='Staging: '+fmtBytes(manager.staging_bytes);
    const block=root.querySelector('#rmqmBlock');
    if(block){
      block.textContent=manager.blocked_by?'Parada após erro #'+String(manager.blocked_by).slice(0,8):'Pronta para próximo';
      block.className='rmqm-pill '+(manager.blocked_by?'bad':'');
      block.onclick=manager.blocked_by?()=>managerCommand({action:'release_error'}):null;
      block.title=manager.blocked_by?'Clique para liberar a fila sem repetir a tarefa com erro':'';
    }
  }

  function decorateJobs(){
    const root=document.getElementById('rmArchiveManagerV2'); if(!root)return;
    const byId=jobsById();
    for(const card of root.querySelectorAll('.rm-arc-job')){
      const id=cardId(card), j=byId.get(id); if(!j)continue;
      const expected=Number(j.download_expected_bytes||j.archive_bytes||j.source_size_bytes||0);
      const downloaded=Number(j.downloaded_bytes_live||j.downloaded_bytes||0);
      const remaining=Number(j.download_remaining_bytes||(expected?Math.max(0,expected-downloaded):0));
      const speed=Number(j.download_speed_bps||0), eta=Number(j.download_eta_seconds||0);
      const pos=Number(j.queue_position||0);
      let info=card.querySelector('.rmqm-download-info');
      if(!info){info=document.createElement('div');info.className='rmqm-download-info';card.appendChild(info)}
      info.innerHTML='<div class="rmqm-kpi"><span>BAIXADO</span><b>'+fmtBytes(downloaded)+'</b></div><div class="rmqm-kpi"><span>TOTAL</span><b>'+fmtBytes(expected)+'</b></div><div class="rmqm-kpi"><span>FALTA</span><b>'+fmtBytes(remaining)+'</b></div><div class="rmqm-kpi"><span>VELOCIDADE / ETA</span><b>'+fmtBytes(speed)+'/s · '+fmtTime(eta)+'</b></div><div class="rmqm-kpi"><span>FILA</span><b>'+(pos?'#'+pos:'—')+'</b></div>';

      if(expected && downloaded>=0){
        const pct=Math.max(0,Math.min(100,downloaded*100/expected));
        const bar=card.querySelector('.rm-arc-progress>i'); if(bar)bar.style.width=pct.toFixed(1)+'%';
        const meta=card.querySelector('.rm-arc-progress')?.nextElementSibling;
        if(meta && String(j.phase||'').match(/download|retry|starting|queued|waiting_space/i))meta.textContent=pct.toFixed(1)+'% · '+fmtBytes(downloaded)+' / '+fmtBytes(expected);
      }

      if(pos){
        let qa=card.querySelector('.rmqm-queue-actions');
        if(!qa){qa=document.createElement('div');qa.className='rmqm-queue-actions';card.appendChild(qa)}
        qa.innerHTML='<button data-q="start_now">▶ Agora</button><button data-q="move_up">↑</button><button data-q="move_down">↓</button>';
        qa.querySelectorAll('button').forEach(b=>b.onclick=()=>jobAction(id,b.dataset.q));
      }
    }
  }

  async function refreshManager(){
    try{const d=await api('/api/v1/archive/manager'); manager=d.manager||d; renderManager(); decorateJobs()}catch(_){}
  }

  function ensureCss(){
    const href='/static/archive-download-manager.css?v=ha4.7.4.13';
    let link=document.querySelector('link[data-rm-archive-manager-css]');
    if(!link){link=document.createElement('link');link.rel='stylesheet';link.dataset.rmArchiveManagerCss='1';document.head.appendChild(link)}
    if(link.getAttribute('href')!==href)link.setAttribute('href',href);
  }

  ensureCss(); ensureManagerUI(); refreshManager();
  document.addEventListener('rm-archive-jobs',()=>{decorateJobs();refreshManager()});
  setInterval(refreshManager,5000);
})();
</script>
'''
        end = page.rfind("{% endblock %}")
        if end >= 0:
            page = page[:end] + ui + "\n" + page[end:]
        else:
            page += "\n" + ui
        tpl.write_text(page, encoding="utf-8")

print("Archive download manager OK: fila serial + progresso/ETA + espaço + Dropbox folder")
