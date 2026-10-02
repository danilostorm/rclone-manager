#!/usr/bin/env python3
from pathlib import Path
import sys
import tempfile
import py_compile

if len(sys.argv) != 2:
    raise SystemExit("uso: patch-archive-pause-ready.py SOURCE_ROOT")

root = Path(sys.argv[1])
appdir = root / "app"
archive_py = appdir / "archive_import.py"
app_py = appdir / "app.py"
tpl = appdir / "templates" / "api_manager.html"

if not archive_py.exists():
    raise SystemExit("Archive pause/ready: archive_import.py ausente")

src = archive_py.read_text(encoding="utf-8")

# Paused jobs are intentionally retained by the archive GC.
src = src.replace(
    "'cleaning', 'canceling', 'waiting_space',",
    "'cleaning', 'canceling', 'waiting_space', 'paused', 'pausing',",
)

if "RM_ARCHIVE_PAUSE_READY_V1" not in src:
    addon = r'''

# RM_ARCHIVE_PAUSE_READY_V1
# Pausa cooperativa para tarefas de compactados + correção de fila quando o
# download já está 100% no staging.
#
# Pausar preserva todo o staging. Continuar volta pela fila e reutiliza o
# arquivo parcial/completo. A pausa é aplicada nos checkpoints já existentes
# (download, HTTP Range, análise, extração/upload em ponto seguro).
import shutil as _rmpf_shutil
import threading as _rmpf_threading


class ArchiveJobPaused(Exception):
    pass


_ARCHIVE_PAUSE_REQUESTS = set()

_RMPF_ORIG_CHECK_CANCEL = globals().get('_archive_check_cancel')
_RMPF_ORIG_UPDATE_JOB = globals().get('_update_job')
_RMPF_ORIG_RUN_JOB = globals().get('_run_job')
_RMPF_ORIG_CONTROL = globals().get('archive_job_control')
_RMPF_ORIG_LIST_JOBS = globals().get('list_jobs')
_RMPF_RAW_UPDATE = (
    globals().get('_ARCHIVE_ORIG_UPDATE_JOB')
    or globals().get('_RM_RES_ORIG_UPDATE_JOB')
    or globals().get('_RMQM_ORIG_UPDATE_JOB')
)
_RMPF_ORIG_CAN_START = globals().get('_rmqm_can_start')


def _rmpf_raw_update(job_id, **fields):
    fn = _RMPF_RAW_UPDATE
    if callable(fn):
        return fn(str(job_id), **fields)
    fn = _RMPF_ORIG_UPDATE_JOB
    if callable(fn):
        return fn(str(job_id), **fields)
    return None


def _rmpf_worker_alive(job_id):
    fn = globals().get('_rmqm_worker_alive') or globals().get('_archive_worker_alive')
    if callable(fn):
        try:
            return bool(fn(str(job_id)))
        except Exception:
            pass
    try:
        with _JOB_LOCK:
            th = _JOB_THREADS.get(str(job_id))
            return bool(th and th.is_alive())
    except Exception:
        return False


def _rmpf_queue_remove(job_id):
    fn = globals().get('_rmqm_queue_remove')
    if callable(fn):
        try:
            fn(str(job_id))
        except Exception:
            pass


def _rmpf_wake_queue():
    ev = globals().get('_RMQM_WAKE')
    try:
        if ev is not None:
            ev.set()
    except Exception:
        pass


def _rmpf_download_dir(job_id):
    fn = globals().get('_rmqm_download_dir')
    if callable(fn):
        try:
            return fn(str(job_id))
        except Exception:
            pass
    return STAGING_ROOT / ('job-' + str(job_id))


def _rmpf_dir_bytes(path):
    fn = globals().get('_rmqm_dir_bytes')
    if callable(fn):
        try:
            return max(0, int(fn(path) or 0))
        except Exception:
            pass
    total = 0
    try:
        for p in path.rglob('*'):
            if p.is_file():
                try:
                    total += max(0, int(p.stat().st_size))
                except Exception:
                    pass
    except Exception:
        pass
    return total


def _rmpf_expected(job):
    fn = globals().get('_rmqm_expected_bytes')
    if callable(fn):
        try:
            return max(0, int(fn(job) or 0))
        except Exception:
            pass
    if isinstance(job, dict):
        for key in (
            'expected_download_bytes', 'archive_bytes', 'source_size_bytes',
            'total_size_bytes', 'content_length', 'size_bytes'
        ):
            try:
                value = int(job.get(key) or 0)
                if value > 0:
                    return value
            except Exception:
                pass
    return 0


def _rmpf_staged_bytes(job_id):
    return _rmpf_dir_bytes(_rmpf_download_dir(job_id))


def _archive_check_cancel(job_id):
    jid = str(job_id or '')
    if callable(_RMPF_ORIG_CHECK_CANCEL):
        _RMPF_ORIG_CHECK_CANCEL(jid)
    if jid in _ARCHIVE_PAUSE_REQUESTS:
        raise ArchiveJobPaused('Pausada pelo usuário')


def _update_job(job_id, **fields):
    jid = str(job_id or '')
    worker_name = 'archive-import-' + jid
    if (
        jid in _ARCHIVE_PAUSE_REQUESTS
        and _rmpf_threading.current_thread().name == worker_name
        and not getattr(globals().get('_ARCHIVE_CANCEL_DEFER'), 'value', False)
    ):
        raise ArchiveJobPaused('Pausada pelo usuário')
    if callable(_RMPF_ORIG_UPDATE_JOB):
        return _RMPF_ORIG_UPDATE_JOB(job_id, **fields)
    return None


def _run_job(job_id):
    jid = str(job_id or '')
    try:
        if callable(_RMPF_ORIG_RUN_JOB):
            return _RMPF_ORIG_RUN_JOB(job_id)
        return None
    except ArchiveJobPaused:
        _ARCHIVE_PAUSE_REQUESTS.discard(jid)
        _rmpf_raw_update(
            jid,
            status='paused',
            phase='paused',
            message='Pausada pelo usuário; staging preservado. Use Continuar para retomar.',
            error='',
            finished_at='',
        )
        _rmpf_wake_queue()
        return None


def archive_job_control(job_id, action, password='', cleanup=True):
    jid = str(job_id or '').strip()
    action = str(action or '').strip().lower()

    if action == 'pause':
        job = get_job(jid)
        if not job or str(job.get('status') or '').lower() == 'deleted':
            raise ValueError('Tarefa de compactado não encontrada')

        alive = _rmpf_worker_alive(jid)
        if alive:
            _ARCHIVE_PAUSE_REQUESTS.add(jid)
            _rmpf_raw_update(
                jid,
                phase='pausing',
                message='Pausa solicitada; aguardando checkpoint seguro. Staging será preservado.',
                error='',
                finished_at='',
            )
        else:
            _ARCHIVE_PAUSE_REQUESTS.discard(jid)
            _rmpf_queue_remove(jid)
            _rmpf_raw_update(
                jid,
                status='paused',
                phase='paused',
                message='Pausada; staging preservado. Use Continuar para retomar.',
                error='',
                finished_at='',
            )
        _rmpf_wake_queue()
        row = get_job(jid) or {}
        return {**row, 'worker_alive': alive}

    if action in {'resume', 'retry', 'restart', 'cancel', 'delete', 'start_now'}:
        _ARCHIVE_PAUSE_REQUESTS.discard(jid)

    if not callable(_RMPF_ORIG_CONTROL):
        raise ValueError('Controle de tarefa indisponível')
    return _RMPF_ORIG_CONTROL(jid, action, password, cleanup)


# O Download Manager antigo reservava novamente o tamanho TOTAL do download
# mesmo quando esses bytes já existiam no staging. Isso pode manter um job de
# 137 GB em waiting_space apesar de os 137 GB já estarem baixados.
#
# A partir daqui só reserve o que AINDA FALTA baixar. A etapa de extração
# continua protegida pelo space guard próprio do Archive Import.
if callable(_RMPF_ORIG_CAN_START):
    def _rmqm_can_start(job):
        cfg = {}
        state = globals().get('_RMQM_STATE')
        if isinstance(state, dict):
            cfg = state.get('settings') or {}

        stats_fn = globals().get('_rmqm_disk_stats')
        if callable(stats_fn):
            try:
                stats = stats_fn(deep=bool(int(cfg.get('max_staging_gb') or 0)))
            except Exception:
                stats = {}
        else:
            stats = {}

        try:
            free = int(stats.get('disk_free_bytes') or _rmpf_shutil.disk_usage(STAGING_ROOT).free)
        except Exception:
            free = 0
        try:
            staging = int(stats.get('staging_bytes') or 0)
        except Exception:
            staging = 0

        expected = _rmpf_expected(job)
        jid = ''
        if isinstance(job, dict):
            jid = str(job.get('id') or job.get('job_id') or '')
        staged = _rmpf_staged_bytes(jid) if jid else 0
        remaining = max(0, expected - staged) if expected else 0

        try:
            min_free = max(1, int(cfg.get('min_free_gb') or 10)) * 1024**3
        except Exception:
            min_free = 10 * 1024**3
        try:
            max_staging = max(0, int(cfg.get('max_staging_gb') or 0)) * 1024**3
        except Exception:
            max_staging = 0

        # Preserve the GC behavior before refusing due to genuinely low disk.
        if free and free <= min_free:
            gc_fn = globals().get('archive_gc_run')
            if callable(gc_fn):
                try:
                    gc_fn(reason='low_disk', include_old=False)
                    free = int(_rmpf_shutil.disk_usage(STAGING_ROOT).free)
                except Exception:
                    pass

        if free and free <= min_free:
            return False, (
                f'Aguardando espaço: livre {free/1024**3:.1f} GB; '
                f'mínimo configurado {min_free/1024**3:.0f} GB'
            )

        if remaining and free and free - remaining < min_free:
            return False, (
                f'Aguardando espaço: faltam ~{remaining/1024**3:.1f} GB do download; '
                f'livre {free/1024**3:.1f} GB'
            )

        if max_staging and staging + remaining > max_staging:
            return False, (
                f'Aguardando limite de staging: uso {staging/1024**3:.1f} GB; '
                f'faltam {remaining/1024**3:.1f} GB; '
                f'limite {max_staging/1024**3:.0f} GB'
            )

        return True, ''


def list_jobs(limit=50):
    rows = _RMPF_ORIG_LIST_JOBS(limit) if callable(_RMPF_ORIG_LIST_JOBS) else []
    out = []
    for row in (rows or []):
        if not isinstance(row, dict):
            out.append(row)
            continue

        item = dict(row)
        jid = str(item.get('id') or item.get('job_id') or '')
        status = str(item.get('status') or '').lower()
        expected = _rmpf_expected(item)
        staged = _rmpf_staged_bytes(jid) if jid else 0

        if expected > 0:
            downloaded = max(
                staged,
                int(item.get('downloaded_bytes_live') or 0),
                int(item.get('downloaded_bytes') or 0),
            )
            item['download_expected_bytes'] = expected
            item['downloaded_bytes_live'] = downloaded
            item['download_remaining_bytes'] = max(0, expected - downloaded)
            item['download_progress_pct'] = min(100.0, downloaded * 100.0 / expected)

            if status == 'queued' and downloaded >= expected:
                item['download_complete_in_staging'] = True
                phase = str(item.get('phase') or '').lower()
                if phase in {'queued', 'waiting_space', 'starting', ''}:
                    item['phase'] = 'queued_ready'
                item['message'] = (
                    'Download 100% no staging; aguardando vaga para analisar/extrair. '
                    'Não será baixado novamente.'
                )

        out.append(item)
    return out
'''
    archive_py.write_text(src + addon, encoding="utf-8")
else:
    archive_py.write_text(src, encoding="utf-8")

with tempfile.NamedTemporaryFile(suffix=".pyc") as f:
    py_compile.compile(str(archive_py), doraise=True, cfile=f.name)

# UI: Pausar em running/queued; Continuar em paused. Também conta paused como
# aguardando, e exibe "queued_ready" para deixar claro que 100% significa
# download pronto, não job finalizado.
if tpl.exists():
    page = tpl.read_text(encoding="utf-8")

    page = page.replace(
        "if(['queued','pending','waiting','interrupted'].includes(s)) queued++;",
        "if(['queued','pending','waiting','interrupted','paused'].includes(s)) queued++;",
    )

    old_actions = """    if (status === 'running' || status === 'queued') {
      return '<button class=\"danger\" data-a=\"cancel\">Cancelar</button>';
    }
"""
    new_actions = """    if (status === 'paused') {
      return '<button class=\"primary\" data-a=\"resume\">▶ Continuar</button><button data-a=\"restart\">↻ Reiniciar</button><button class=\"danger\" data-a=\"delete\">Excluir</button>';
    }
    if (status === 'running') {
      return '<button data-a=\"pause\">⏸ Pausar</button><button class=\"danger\" data-a=\"cancel\">Cancelar</button>';
    }
    if (status === 'queued') {
      return '<button data-a=\"pause\">⏸ Pausar</button><button class=\"danger\" data-a=\"cancel\">Cancelar</button>';
    }
"""
    if old_actions in page:
        page = page.replace(old_actions, new_actions, 1)

    page = page.replace(
        "else if (st === 'interrupted' || st === 'queued' || st === 'pending' || st === 'waiting') waiting++;",
        "else if (st === 'interrupted' || st === 'paused' || st === 'queued' || st === 'pending' || st === 'waiting') waiting++;",
    )

    if "RM_ARCHIVE_PAUSE_READY_UI_V1" not in page:
        ui = r'''
<!-- RM_ARCHIVE_PAUSE_READY_UI_V1 -->
<script>
(() => {
  function labelReady() {
    const jobs = Array.isArray(window.__rmArchiveJobsV2) ? window.__rmArchiveJobsV2 : [];
    const byId = new Map(jobs.map(j => [String(j.id || j.job_id || ''), j]));
    const root = document.getElementById('rmArchiveManagerV2');
    if (!root) return;
    for (const card of root.querySelectorAll('.rm-arc-job')) {
      const txt = Array.from(card.querySelectorAll('.rm-arc-meta')).map(x => x.textContent || '').join(' ');
      const m = txt.match(/#([A-Za-z0-9_-]{6,64})/);
      if (!m) continue;
      const j = byId.get(m[1]);
      if (!j) continue;
      if (j.download_complete_in_staging) {
        const st = card.querySelector('.rm-arc-status');
        if (st) st.textContent = 'queued · download pronto, aguardando processamento';
      }
    }
  }
  document.addEventListener('rm-archive-jobs', () => setTimeout(labelReady, 0));
  setTimeout(labelReady, 250);
})();
</script>
'''
        end = page.rfind("{% endblock %}")
        if end >= 0:
            page = page[:end] + ui + "\n" + page[end:]
        else:
            page += "\n" + ui

    tpl.write_text(page, encoding="utf-8")

# API counters: paused is a waiting state.
if app_py.exists():
    app = app_py.read_text(encoding="utf-8")
    app = app.replace(
        "if status in {'queued', 'pending', 'waiting'}:",
        "if status in {'queued', 'pending', 'waiting', 'paused'}:",
    )
    app_py.write_text(app, encoding="utf-8")
    with tempfile.NamedTemporaryFile(suffix=".pyc") as f:
        py_compile.compile(str(app_py), doraise=True, cfile=f.name)

print(
    "Archive pause/ready OK: pausar/continuar + staging 100% reutilizado "
    "+ espaço calculado só pelo restante do download"
)
