#!/usr/bin/env python3
from pathlib import Path
import re, sys, py_compile, tempfile

if len(sys.argv) != 2:
    raise SystemExit('uso: patch-archive-ui-v2.py SOURCE_ROOT')
root = Path(sys.argv[1])
appdir = root / 'app'
app_py = appdir / 'app.py'
tpl = appdir / 'templates' / 'api_manager.html'
if not app_py.exists():
    raise SystemExit('Archive UI v2: app/app.py ausente')

s = app_py.read_text(encoding='utf-8')
if 'RM_ARCHIVE_IMPORT_ROUTES_V1' not in s:
    raise SystemExit('Archive UI v2: Archive Import não está aplicado')

if 'RM_ARCHIVE_STATUS_API_V2' not in s:
    marker = '# RM_ARCHIVE_IMPORT_ROUTES_V1'
    pos = s.find(marker)
    if pos < 0:
        raise SystemExit('Archive UI v2: marcador de rotas não encontrado')
    block = r'''
# RM_ARCHIVE_STATUS_API_V2
def _archive_public_job_id(row):
    if not isinstance(row, dict):
        return ''
    return str(row.get('job_id') or row.get('id') or row.get('uuid') or '').strip()


def _archive_status_payload(row):
    row = dict(row or {})
    jid = _archive_public_job_id(row)
    status = str(row.get('status') or row.get('state') or row.get('phase') or 'queued')
    phase = str(row.get('phase') or status)
    try:
        current = int(row.get('completed_files') or row.get('completed_items') or row.get('progress_current') or 0)
    except Exception:
        current = 0
    try:
        total = int(row.get('total_files') or row.get('total_items') or row.get('progress_total') or 0)
    except Exception:
        total = 0
    try:
        pct = float(row.get('progress_pct') or row.get('progress_percent') or 0)
    except Exception:
        pct = 0.0
    if not pct and total > 0:
        pct = max(0.0, min(100.0, (current * 100.0) / total))
    payload = dict(row)
    payload.update({
        'id': jid,
        'job_id': jid,
        'status': status,
        'phase': phase,
        'completed_items': current,
        'total_items': total,
        'progress_current': current,
        'progress_total': total,
        'progress_pct': pct,
        'archive_job': True,
    })
    payload['job'] = dict(row)
    return payload


@app.route('/api/v1/extension/archive/status', methods=['GET', 'OPTIONS'])
@extension_api_required
def extension_archive_status_list_v2():
    try:
        limit = max(1, min(200, int(request.args.get('limit', '50'))))
    except Exception:
        limit = 50
    jobs = [dict(x) for x in (archive_list_jobs(limit) or []) if isinstance(x, dict)]
    counts = {'queued': 0, 'running': 0, 'waiting_password': 0, 'done': 0, 'error': 0, 'other': 0}
    for row in jobs:
        status = str(row.get('status') or row.get('state') or row.get('phase') or '').lower()
        if status in {'queued', 'pending', 'waiting'}:
            counts['queued'] += 1
        elif status in {'running', 'downloading', 'download', 'analyzing', 'analysing', 'extracting', 'streaming', 'uploading', 'cleanup', 'cleaning'}:
            counts['running'] += 1
        elif status in {'waiting_password', 'password', 'needs_password'}:
            counts['waiting_password'] += 1
        elif status in {'completed', 'complete', 'done', 'success'}:
            counts['done'] += 1
        elif status in {'error', 'failed', 'cancelled', 'canceled'}:
            counts['error'] += 1
        else:
            counts['other'] += 1
    return jsonify({'ok': True, 'jobs': jobs, 'counts': counts})


@app.route('/api/v1/extension/archive/status/<job_id>', methods=['GET', 'OPTIONS'])
@extension_api_required
def extension_archive_status_one_v2(job_id):
    needle = str(job_id or '').strip()
    jobs = archive_list_jobs(200) or []
    for row in jobs:
        if isinstance(row, dict) and _archive_public_job_id(row) == needle:
            return jsonify({'ok': True, **_archive_status_payload(row)})
    return jsonify({'ok': False, 'error': 'Tarefa de compactado não encontrada', 'job_id': needle}), 404

'''
    s = s[:pos] + block + s[pos:]
    app_py.write_text(s, encoding='utf-8')

with tempfile.NamedTemporaryFile(suffix='.pyc') as f:
    py_compile.compile(str(app_py), doraise=True, cfile=f.name)

if tpl.exists():
    text = tpl.read_text(encoding='utf-8')
    text = text.replace('Drive Link API v11', 'Drive Link API v14')
    # Jinja treats "{#" as the start of a template comment. CSS such as
    # "@media(...){#rmArchiveManagerV2" therefore breaks /api-manager with
    # TemplateSyntaxError before any JavaScript can run. Keep whitespace
    # between "{" and the CSS id selector, and repair HA4.7.4.3 templates.
    text = text.replace('{#rmArchiveManagerV2', '{ #rmArchiveManagerV2')
    text = text.replace("if(['queued','pending','waiting'].includes(s)) queued++;", "if(['queued','pending','waiting','interrupted'].includes(s)) queued++;")
    # Repair HA4.7.4.5 legacy-card hider in already-patched live templates.
    old_hide = """  function hideLegacyPanel() {
    const heads = Array.from(document.querySelectorAll('h1,h2,h3,h4,strong,b'));
    const old = heads.find(el => el.id !== 'rmArcV2Title' && (el.textContent || '').trim() === 'Compactados');
    if (!old) return;
    const box = old.closest('.card,.panel,section') || old.parentElement;
    if (box && !box.closest('#'+MARK)) box.style.display='none';
  }
"""
    new_hide = """  function hideLegacyPanel() {
    const all = Array.from(document.querySelectorAll('section,article,div'));
    const candidates = all.filter(el => {
      if (el.closest('#'+MARK)) return false;
      const txt = (el.textContent || '').replace(/\\s+/g, ' ').trim();
      return txt.includes('Compactados')
        && txt.includes('Download')
        && txt.includes('extração/streaming')
        && txt.includes('Drive')
        && txt.includes('limpeza')
        && (txt.includes('Carregando') || txt.includes('Atualizar'));
    });
    if (!candidates.length) return;
    candidates.sort((a,b) => (a.textContent || '').length - (b.textContent || '').length);
    let box = candidates[0];
    const semantic = box.closest('section,article,.card,.panel,[class*="card"],[class*="panel"]');
    if (semantic && !semantic.closest('#'+MARK)) box = semantic;
    const txt = (box.textContent || '').replace(/\\s+/g, ' ').trim();
    if (txt.length < 1200 && txt.includes('Compactados')) {
      box.style.display='none';
      box.setAttribute('data-rm-legacy-archive-hidden','1');
    }
  }
"""
    if old_hide in text:
        text = text.replace(old_hide, new_hide)
    text = text.replace(
        "    hideLegacyPanel();\\n    return box;",
        "    hideLegacyPanel();\\n    setTimeout(hideLegacyPanel, 250);\\n    setTimeout(hideLegacyPanel, 1000);\\n    return box;"
    )
    if 'RM_ARCHIVE_MANAGER_V2' not in text:
        overlay = r'''
<!-- RM_ARCHIVE_MANAGER_V2 -->
<style id="rm-archive-manager-v2-style">
  #rmArchiveManagerV2{margin:14px 0;padding:14px;border:1px solid #334155;border-radius:12px;background:#0b1220;color:#e5e7eb;box-sizing:border-box;max-width:100%;overflow:hidden}
  #rmArchiveManagerV2 *{box-sizing:border-box}
  #rmArchiveManagerV2 .rm-arc-head{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:10px}
  #rmArchiveManagerV2 .rm-arc-title{font-weight:800;font-size:15px}
  #rmArchiveManagerV2 .rm-arc-sub{font-size:11px;color:#94a3b8;margin-top:2px}
  #rmArchiveManagerV2 .rm-arc-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-bottom:10px}
  #rmArchiveManagerV2 .rm-arc-stat{padding:9px 10px;border:1px solid #263449;border-radius:9px;background:#101827;min-width:0}
  #rmArchiveManagerV2 .rm-arc-stat b{display:block;font-size:16px;margin-top:2px}
  #rmArchiveManagerV2 .rm-arc-stat span{font-size:10px;color:#94a3b8}
  #rmArchiveManagerV2 .rm-arc-list{display:grid;gap:8px;max-height:480px;overflow:auto;padding-right:2px}
  #rmArchiveManagerV2 .rm-arc-job{display:grid;grid-template-columns:minmax(220px,2fr) minmax(130px,.9fr) minmax(110px,.7fr);gap:10px;align-items:center;padding:10px;border:1px solid #253247;border-radius:9px;background:#0f172a;min-width:0}
  #rmArchiveManagerV2 .rm-arc-file{font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  #rmArchiveManagerV2 .rm-arc-meta{font-size:10px;color:#94a3b8;margin-top:3px;overflow-wrap:anywhere}
  #rmArchiveManagerV2 .rm-arc-status{font-weight:700;font-size:11px}
  #rmArchiveManagerV2 .rm-arc-progress{height:6px;border-radius:999px;background:#1f2937;overflow:hidden;margin-top:5px}
  #rmArchiveManagerV2 .rm-arc-progress>i{display:block;height:100%;background:#3b82f6;width:0}
  #rmArchiveManagerV2 .rm-arc-empty{padding:14px;text-align:center;color:#94a3b8;border:1px dashed #334155;border-radius:9px}
  #rmArchiveManagerV2 button{padding:7px 10px;border-radius:8px;border:1px solid #475569;background:#172033;color:#e5e7eb;cursor:pointer}
  @media(max-width:900px){ #rmArchiveManagerV2 .rm-arc-job{grid-template-columns:1fr}#rmArchiveManagerV2 .rm-arc-stats{grid-template-columns:1fr 1fr 1fr}}
  @media(max-width:520px){ #rmArchiveManagerV2 .rm-arc-stats{grid-template-columns:1fr}}
</style>
<script>
(() => {
  const MARK = 'rmArchiveManagerV2';
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num = (v) => { const n = Number(v || 0); return Number.isFinite(n) ? n : 0; };
  const bytes = (n) => { n=num(n); if(!n)return '0 B'; const u=['B','KB','MB','GB','TB']; let i=0; while(n>=1024&&i<u.length-1){n/=1024;i++;} return `${n.toFixed(i?1:0)} ${u[i]}`; };
  const jobId = j => String(j.job_id || j.id || j.uuid || '');
  const statusOf = j => String(j.status || j.state || j.phase || 'queued');
  const terminal = s => ['completed','complete','done','success','error','failed','cancelled','canceled'].includes(String(s).toLowerCase());

  function hideLegacyPanel() {
    // HA4.7.4 originally injected a second "Compactados" card at the end of
    // api_manager.html. Its title is not always an h1/h2/strong, so the old
    // selector missed it and users saw a duplicate card stuck below the
    // normal API queue. Find the small legacy card by its own unique copy.
    const all = Array.from(document.querySelectorAll('section,article,div'));
    const candidates = all.filter(el => {
      if (el.closest('#'+MARK)) return false;
      const txt = (el.textContent || '').replace(/\\s+/g, ' ').trim();
      return txt.includes('Compactados')
        && txt.includes('Download')
        && txt.includes('extração/streaming')
        && txt.includes('Drive')
        && txt.includes('limpeza')
        && (txt.includes('Carregando') || txt.includes('Atualizar'));
    });
    if (!candidates.length) return;

    // Prefer the smallest matching container so we never hide the whole page.
    candidates.sort((a,b) => (a.textContent || '').length - (b.textContent || '').length);
    let box = candidates[0];
    const semantic = box.closest('section,article,.card,.panel,[class*="card"],[class*="panel"]');
    if (semantic && !semantic.closest('#'+MARK)) box = semantic;

    const txt = (box.textContent || '').replace(/\\s+/g, ' ').trim();
    if (txt.length < 1200 && txt.includes('Compactados')) {
      box.style.display='none';
      box.setAttribute('data-rm-legacy-archive-hidden','1');
    }
  }

  function mount() {
    if (document.getElementById(MARK)) return document.getElementById(MARK);
    const box = document.createElement('section');
    box.id=MARK;
    box.innerHTML=`<div class="rm-arc-head"><div><div id="rmArcV2Title" class="rm-arc-title">📦 Fila de compactados</div><div class="rm-arc-sub">Separada da fila normal: download → análise → extração/streaming → Google Drive → limpeza.</div></div><button id="rmArcRefreshV2" type="button">Atualizar</button></div><div class="rm-arc-stats"><div class="rm-arc-stat"><span>EM ANDAMENTO</span><b id="rmArcRunV2">0</b></div><div class="rm-arc-stat"><span>AGUARDANDO</span><b id="rmArcQueueV2">0</b></div><div class="rm-arc-stat"><span>AGUARDANDO SENHA</span><b id="rmArcPwdV2">0</b></div></div><div id="rmArcListV2" class="rm-arc-list"><div class="rm-arc-empty">Nenhum compactado ativo.</div></div>`;
    const normalHeading = Array.from(document.querySelectorAll('h1,h2,h3,h4,strong')).find(el => /Fila e tarefas da API/i.test(el.textContent || ''));
    const normalBox = normalHeading?.closest('.card,.panel,section');
    if (normalBox?.parentElement) normalBox.parentElement.insertBefore(box, normalBox);
    else (document.querySelector('main') || document.querySelector('.main-content') || document.body).appendChild(box);
    box.querySelector('#rmArcRefreshV2')?.addEventListener('click', refresh);
    hideLegacyPanel();
    setTimeout(hideLegacyPanel, 250);
    setTimeout(hideLegacyPanel, 1000);
    return box;
  }

  async function refresh(){
    const box=mount();
    try{
      const r=await fetch('/api/v1/archive/jobs?limit=50',{credentials:'same-origin',cache:'no-store'});
      if(!r.ok) throw new Error(`HTTP ${r.status}`);
      const data=await r.json();
      const jobs=Array.isArray(data.jobs)?data.jobs:[];
      let running=0, queued=0, pwd=0;
      for(const j of jobs){
        const s=statusOf(j).toLowerCase();
        if(['queued','pending','waiting','interrupted'].includes(s)) queued++;
        else if(['waiting_password','password','needs_password'].includes(s)) pwd++;
        else if(!terminal(s)) running++;
      }
      box.querySelector('#rmArcRunV2').textContent=running;
      box.querySelector('#rmArcQueueV2').textContent=queued;
      box.querySelector('#rmArcPwdV2').textContent=pwd;
      const active=jobs.filter(j=>!terminal(statusOf(j))).concat(jobs.filter(j=>terminal(statusOf(j))).slice(0,5));
      const list=box.querySelector('#rmArcListV2');
      if(!active.length){list.innerHTML='<div class="rm-arc-empty">Nenhum compactado ativo. As tarefas normais continuam na fila acima.</div>';return;}
      list.innerHTML=active.map(j=>{
        const id=jobId(j), s=statusOf(j), phase=String(j.phase||s);
        const name=String(j.filename||j.archive_name||j.name||j.source_name||j.url||'Compactado');
        const dest=[j.destination_slug,j.destination_path].filter(Boolean).join(' / ') || j.destination || '-';
        const cur=num(j.completed_files||j.completed_items||j.progress_current), tot=num(j.total_files||j.total_items||j.progress_total);
        let pct=num(j.progress_pct||j.progress_percent); if(!pct&&tot>0)pct=(cur*100/tot); pct=Math.max(0,Math.min(100,pct));
        const dl=num(j.downloaded_bytes||j.archive_bytes||j.source_size_bytes), unpack=num(j.unpacked_bytes||j.extracted_bytes||j.unpacked_size_bytes);
        return `<article class="rm-arc-job"><div><div class="rm-arc-file" title="${esc(name)}">${esc(name)}</div><div class="rm-arc-meta">#${esc(id.slice(0,16))} · destino: ${esc(dest)}</div></div><div><div class="rm-arc-status">${esc(s)} · ${esc(phase)}</div><div class="rm-arc-progress"><i style="width:${pct.toFixed(1)}%"></i></div><div class="rm-arc-meta">${pct.toFixed(1)}% · ${cur}/${tot||'?'} arquivo(s)</div></div><div><div>${esc(bytes(dl))} → ${esc(bytes(unpack))}</div><div class="rm-arc-meta">${esc(j.updated_at||j.created_at||'')}</div></div></article>`;
      }).join('');
    }catch(e){
      box.querySelector('#rmArcListV2').innerHTML=`<div class="rm-arc-empty">Não foi possível atualizar compactados: ${esc(e.message)}</div>`;
    }
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',()=>{mount();refresh();setInterval(refresh,3000);},{once:true});
  else {mount();refresh();setInterval(refresh,3000);}
})();
</script>
'''
        end = text.rfind('{% endblock %}')
        if end >= 0:
            text = text[:end] + overlay + '\n' + text[end:]
        else:
            text += '\n' + overlay
    tpl.write_text(text, encoding='utf-8')

print('Archive UI v2 OK: status API estável + fila compactados responsiva')



# RM_ARCHIVE_CONTROLS_PATCH_V1
# Lifecycle controls for persistent archive jobs. This is appended by the
# deploy overlay so old HA live-source installations gain the same behavior.
archive_py = appdir / 'archive_import.py'
if archive_py.exists():
    arc = archive_py.read_text(encoding='utf-8')
    if 'RM_ARCHIVE_CONTROLS_V1' not in arc:
        arc += r'''

# RM_ARCHIVE_CONTROLS_V1
import shutil as _archive_shutil
import threading as _archive_threading


class ArchiveJobCancelled(Exception):
    pass


_ARCHIVE_CANCEL_REQUESTS = set()
_ARCHIVE_RESUME_REQUESTED = set()
_ARCHIVE_CANCEL_DEFER = _archive_threading.local()

_ARCHIVE_ORIG_LIST_JOBS = list_jobs
_ARCHIVE_ORIG_UPDATE_JOB = _update_job
_ARCHIVE_ORIG_RUN_JOB = _run_job
_ARCHIVE_ORIG_DOWNLOAD_ONE = _download_one
_ARCHIVE_ORIG_RCAT = _rcat
_ARCHIVE_ORIG_EXTRACT_FULL = _extract_full_and_upload
_ARCHIVE_ORIG_UPLOAD_ORIGINAL = _upload_original_archives


def _archive_worker_alive(job_id):
    job_id = str(job_id or '')
    try:
        with _JOB_LOCK:
            th = _JOB_THREADS.get(job_id)
            return bool(th and th.is_alive())
    except Exception:
        return False


def _archive_stage_path(job_id):
    return STAGING_ROOT / ('job-' + str(job_id or ''))


def _archive_stage_info(job_id):
    stage = _archive_stage_path(job_id)
    total = 0
    files = 0
    if stage.exists():
        try:
            for child in stage.rglob('*'):
                if child.is_file():
                    files += 1
                    try:
                        total += int(child.stat().st_size)
                    except Exception:
                        pass
        except Exception:
            pass
    return {
        'stage_exists': stage.exists(),
        'stage_path': str(stage),
        'stage_files': files,
        'stage_bytes': total,
    }


def _archive_cleanup_stage(job_id):
    stage = _archive_stage_path(job_id)
    if stage.exists():
        _archive_shutil.rmtree(stage, ignore_errors=True)


def _archive_check_cancel(job_id):
    if str(job_id or '') in _ARCHIVE_CANCEL_REQUESTS:
        raise ArchiveJobCancelled('Cancelada pelo usuário')


def _update_job(job_id, **fields):
    jid = str(job_id or '')
    worker_name = 'archive-import-' + jid
    if (
        jid in _ARCHIVE_CANCEL_REQUESTS
        and _archive_threading.current_thread().name == worker_name
        and not getattr(_ARCHIVE_CANCEL_DEFER, 'value', False)
    ):
        raise ArchiveJobCancelled('Cancelada pelo usuário')
    return _ARCHIVE_ORIG_UPDATE_JOB(job_id, **fields)


def _run_job(job_id):
    jid = str(job_id or '')
    try:
        return _ARCHIVE_ORIG_RUN_JOB(job_id)
    except ArchiveJobCancelled:
        _ARCHIVE_CANCEL_REQUESTS.discard(jid)
        _ARCHIVE_RESUME_REQUESTED.discard(jid)
        _ARCHIVE_ORIG_UPDATE_JOB(
            jid,
            status='canceled',
            phase='canceled',
            message='Cancelada pelo usuário',
            error='',
            finished_at=_now(),
        )
        return None


def _archive_download_candidates(dest):
    try:
        return sorted(
            [
                p for p in dest.iterdir()
                if p.is_file()
                and p.stat().st_size > 0
                and not p.name.lower().endswith(('.part', '.tmp', '.download', '.crdownload'))
            ],
            key=lambda p: p.name.lower(),
        )
    except Exception:
        return []


def _download_one(job_id, row, dest, index, total):
    jid = str(job_id or '')
    _archive_check_cancel(jid)

    if jid in _ARCHIVE_RESUME_REQUESTED:
        job = get_job(jid) or {}
        expected_total = int(job.get('archive_bytes') or 0)
        candidates = _archive_download_candidates(dest)
        actual_total = sum(int(p.stat().st_size) for p in candidates) if candidates else 0

        # Reuse only a previously completed download set. archive_bytes is
        # filled after all link downloads complete, so partial files are never
        # mistaken for resumable archives.
        if expected_total > 0 and actual_total == expected_total and len(candidates) >= int(total or 1):
            chosen = None
            label = str((row or {}).get('label') or (row or {}).get('name') or '').strip()
            if label:
                for p in candidates:
                    if p.name == label or p.name in label or label in p.name:
                        chosen = p
                        break
            if chosen is None:
                pos = max(0, min(len(candidates) - 1, int(index or 1) - 1))
                chosen = candidates[pos]
            _ARCHIVE_ORIG_UPDATE_JOB(
                jid,
                phase='downloading',
                status='running',
                current_item=chosen.name,
                downloaded_bytes=actual_total,
                message='Reutilizando download completo já presente no staging',
            )
            _archive_check_cancel(jid)
            return chosen

    result = _ARCHIVE_ORIG_DOWNLOAD_ONE(job_id, row, dest, index, total)
    _archive_check_cancel(jid)
    return result


def _rcat(job_id, *args, **kwargs):
    _archive_check_cancel(job_id)
    _ARCHIVE_CANCEL_DEFER.value = True
    try:
        result = _ARCHIVE_ORIG_RCAT(job_id, *args, **kwargs)
    finally:
        _ARCHIVE_CANCEL_DEFER.value = False
    _archive_check_cancel(job_id)
    return result


def _extract_full_and_upload(job_id, *args, **kwargs):
    _archive_check_cancel(job_id)
    _ARCHIVE_CANCEL_DEFER.value = True
    try:
        result = _ARCHIVE_ORIG_EXTRACT_FULL(job_id, *args, **kwargs)
    finally:
        _ARCHIVE_CANCEL_DEFER.value = False
    _archive_check_cancel(job_id)
    return result


def _upload_original_archives(job_id, *args, **kwargs):
    _archive_check_cancel(job_id)
    _ARCHIVE_CANCEL_DEFER.value = True
    try:
        result = _ARCHIVE_ORIG_UPLOAD_ORIGINAL(job_id, *args, **kwargs)
    finally:
        _ARCHIVE_CANCEL_DEFER.value = False
    _archive_check_cancel(job_id)
    return result


def _archive_mark_orphans():
    try:
        rows = _ARCHIVE_ORIG_LIST_JOBS(500) or []
    except Exception:
        return
    for row in rows:
        if not isinstance(row, dict):
            continue
        jid = str(row.get('id') or row.get('job_id') or '')
        status = str(row.get('status') or '').lower()
        if jid and status in {'queued', 'running'} and not _archive_worker_alive(jid):
            _ARCHIVE_ORIG_UPDATE_JOB(
                jid,
                status='interrupted',
                phase='interrupted',
                message='Interrompida por reinício/atualização; use Continuar ou Reiniciar',
                finished_at='',
            )


def list_jobs(limit=50):
    rows = _ARCHIVE_ORIG_LIST_JOBS(limit) or []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            out.append(row)
            continue
        if str(row.get('status') or '').lower() == 'deleted':
            continue
        item = dict(row)
        jid = str(item.get('id') or item.get('job_id') or '')
        item['worker_alive'] = _archive_worker_alive(jid)
        item.update(_archive_stage_info(jid))
        out.append(item)
    return out


def archive_job_control(job_id, action, password='', cleanup=True):
    jid = str(job_id or '').strip()
    action = str(action or '').strip().lower()
    job = get_job(jid)
    if not job or str(job.get('status') or '').lower() == 'deleted':
        raise ValueError('Tarefa de compactado não encontrada')

    alive = _archive_worker_alive(jid)
    status = str(job.get('status') or '').lower()

    if action == 'cancel':
        if alive:
            _ARCHIVE_CANCEL_REQUESTS.add(jid)
            _ARCHIVE_ORIG_UPDATE_JOB(
                jid,
                phase='canceling',
                message='Cancelamento solicitado; aguardando ponto seguro',
            )
        else:
            _ARCHIVE_ORIG_UPDATE_JOB(
                jid,
                status='canceled',
                phase='canceled',
                message='Cancelada pelo usuário',
                error='',
                finished_at=_now(),
            )
        return {**(get_job(jid) or {}), **_archive_stage_info(jid), 'worker_alive': alive}

    if action in {'resume', 'retry'}:
        if alive:
            raise ValueError('A tarefa ainda possui worker ativo')
        _ARCHIVE_CANCEL_REQUESTS.discard(jid)
        _ARCHIVE_RESUME_REQUESTED.add(jid)
        if password:
            _JOB_PASSWORDS[jid] = str(password)
        if status == 'waiting_password' and not password:
            raise ValueError('Informe a senha do arquivo compactado')
        _ARCHIVE_ORIG_UPDATE_JOB(
            jid,
            status='queued',
            phase='queued',
            message='Retomando; downloads completos no staging serão reutilizados',
            error='',
            finished_at='',
        )
        _start_job(jid)
        return {**(get_job(jid) or {}), **_archive_stage_info(jid), 'worker_alive': True}

    if action == 'restart':
        if alive:
            raise ValueError('Cancele a tarefa ativa antes de reiniciar')
        _ARCHIVE_CANCEL_REQUESTS.discard(jid)
        _ARCHIVE_RESUME_REQUESTED.discard(jid)
        _archive_cleanup_stage(jid)
        if password:
            _JOB_PASSWORDS[jid] = str(password)
        _ARCHIVE_ORIG_UPDATE_JOB(
            jid,
            status='queued',
            phase='queued',
            message='Reiniciando do zero',
            error='',
            downloaded_bytes=0,
            archive_bytes=0,
            estimated_unpacked_bytes=0,
            unpacked_bytes=0,
            uploaded_bytes=0,
            total_files=0,
            completed_files=0,
            progress=0,
            current_item='',
            finished_at='',
        )
        _start_job(jid)
        return {**(get_job(jid) or {}), **_archive_stage_info(jid), 'worker_alive': True}

    if action == 'delete':
        if alive:
            raise ValueError('Cancele a tarefa ativa antes de excluir')
        if cleanup:
            _archive_cleanup_stage(jid)
        _ARCHIVE_CANCEL_REQUESTS.discard(jid)
        _ARCHIVE_RESUME_REQUESTED.discard(jid)
        _JOB_PASSWORDS.pop(jid, None)
        _ARCHIVE_ORIG_UPDATE_JOB(
            jid,
            status='deleted',
            phase='deleted',
            message='Removida do histórico',
            error='',
            finished_at=_now(),
        )
        return {'id': jid, 'job_id': jid, 'status': 'deleted', **_archive_stage_info(jid)}

    raise ValueError('Ação inválida')


def archive_jobs_maintenance(action, cleanup=True):
    action = str(action or '').strip().lower()
    rows = list_jobs(500) or []
    changed = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        jid = str(row.get('id') or row.get('job_id') or '')
        status = str(row.get('status') or '').lower()
        if not jid or _archive_worker_alive(jid):
            continue
        should_delete = (
            action == 'clear_finished' and status in {'done', 'completed', 'complete', 'success', 'canceled', 'cancelled'}
        ) or (
            action == 'clear_orphans' and status == 'interrupted'
        )
        if should_delete:
            archive_job_control(jid, 'delete', cleanup=cleanup)
            changed.append(jid)
    if action not in {'clear_finished', 'clear_orphans'}:
        raise ValueError('Ação de manutenção inválida')
    return {'ok': True, 'changed': changed, 'count': len(changed)}


_archive_mark_orphans()
'''
        archive_py.write_text(arc, encoding='utf-8')
        with tempfile.NamedTemporaryFile(suffix='.pyc') as f:
            py_compile.compile(str(archive_py), doraise=True, cfile=f.name)

# Action endpoints for extension API and authenticated panel.
app_text = app_py.read_text(encoding='utf-8')
if 'RM_ARCHIVE_CONTROL_ROUTES_V1' not in app_text:
    marker = '# RM_ARCHIVE_STATUS_API_V2'
    pos = app_text.find(marker)
    if pos < 0:
        marker = '# RM_ARCHIVE_IMPORT_ROUTES_V1'
        pos = app_text.find(marker)
    if pos < 0:
        raise SystemExit('Archive controls: marcador de rotas não encontrado')

    routes = r'''
# RM_ARCHIVE_CONTROL_ROUTES_V1
@app.route('/api/v1/extension/archive/jobs/<job_id>/action', methods=['POST', 'OPTIONS'])
@extension_api_required
def extension_archive_job_action_v1(job_id):
    from archive_import import archive_job_control
    payload = request.get_json(silent=True) or {}
    try:
        result = archive_job_control(
            job_id,
            payload.get('action') or '',
            payload.get('password') or '',
            bool(payload.get('cleanup', True)),
        )
        return jsonify({'ok': True, 'job': result})
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400


@app.route('/api/v1/extension/archive/maintenance', methods=['POST', 'OPTIONS'])
@extension_api_required
def extension_archive_maintenance_v1():
    from archive_import import archive_jobs_maintenance
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(archive_jobs_maintenance(
            payload.get('action') or '',
            bool(payload.get('cleanup', True)),
        ))
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400


'''
    app_text = app_text[:pos] + routes + app_text[pos:]

if 'RM_ARCHIVE_WEB_CONTROL_ROUTES_V1' not in app_text and 'RM_ARCHIVE_WEB_ROUTES_V1' in app_text:
    guard = ''
    m = re.search(
        r"@app\.route\('/api/v1/archive/jobs'.*?\)\n(?P<guard>(?:@[^\n]+\n)*)def web_archive_jobs\(",
        app_text,
    )
    if not m:
        m = re.search(
            r'@app\.route\("/api/v1/archive/jobs".*?\)\n(?P<guard>(?:@[^\n]+\n)*)def web_archive_jobs\(',
            app_text,
        )
    if m:
        guard = m.group('guard') or ''

    marker = '# RM_ARCHIVE_IMPORT_ROUTES_V1'
    pos = app_text.find(marker)
    web_routes = r'''
# RM_ARCHIVE_WEB_CONTROL_ROUTES_V1
@app.route('/api/v1/archive/jobs/<job_id>/action', methods=['POST'])
__GUARD__def web_archive_job_action_v1(job_id):
    from archive_import import archive_job_control
    payload = request.get_json(silent=True) or {}
    try:
        result = archive_job_control(
            job_id,
            payload.get('action') or '',
            payload.get('password') or '',
            bool(payload.get('cleanup', True)),
        )
        return jsonify({'ok': True, 'job': result})
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400


@app.route('/api/v1/archive/maintenance', methods=['POST'])
__GUARD__def web_archive_maintenance_v1():
    from archive_import import archive_jobs_maintenance
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(archive_jobs_maintenance(
            payload.get('action') or '',
            bool(payload.get('cleanup', True)),
        ))
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400


'''.replace('__GUARD__', guard)
    app_text = app_text[:pos] + web_routes + app_text[pos:]

app_py.write_text(app_text, encoding='utf-8')
with tempfile.NamedTemporaryFile(suffix='.pyc') as f:
    py_compile.compile(str(app_py), doraise=True, cfile=f.name)

# Responsive action buttons on the existing archive cards.
if tpl.exists():
    page = tpl.read_text(encoding='utf-8')
    if 'RM_ARCHIVE_CONTROLS_UI_V1' not in page and 'RM_ARCHIVE_MANAGER_V2' in page and 'RM_ARCHIVE_WEB_CONTROL_ROUTES_V1' in app_text:
        controls_ui = r'''
<!-- RM_ARCHIVE_CONTROLS_UI_V1 -->
<style id="rm-archive-controls-v1-style">
  #rmArchiveManagerV2 .rm-arc-actions{display:flex;gap:6px;align-items:center;justify-content:flex-end;flex-wrap:wrap;margin-top:7px}
  #rmArchiveManagerV2 .rm-arc-actions button{font-size:11px;padding:6px 9px}
  #rmArchiveManagerV2 .rm-arc-actions .danger{border-color:#7f1d1d;background:#3f1218;color:#fecaca}
  #rmArchiveManagerV2 .rm-arc-actions .primary{border-color:#1d4ed8;background:#173a77;color:#dbeafe}
  #rmArchiveManagerV2 .rm-arc-actions input{min-width:160px;max-width:230px;padding:7px 9px;border:1px solid #475569;border-radius:8px;background:#0b1220;color:#e5e7eb}
  #rmArchiveManagerV2 .rm-arc-toolbar{display:flex;gap:6px;flex-wrap:wrap}
  #rmArchiveManagerV2 .rm-arc-interrupted{border-color:#92400e;background:#1d160d}
  @media(max-width:900px){ #rmArchiveManagerV2 .rm-arc-actions{justify-content:flex-start} }
</style>
<script>
(() => {
  const ROOT = '#rmArchiveManagerV2';
  const terminal = s => ['done','completed','complete','success','canceled','cancelled','error','failed','deleted'].includes(String(s||'').toLowerCase());
  let jobs = [];

  async function callJson(url, body) {
    const r = await fetch(url, {
      method: body ? 'POST' : 'GET',
      credentials: 'same-origin',
      cache: 'no-store',
      headers: body ? {'Content-Type':'application/json'} : {},
      body: body ? JSON.stringify(body) : undefined
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok || data.ok === false) throw new Error(data.error || ('HTTP ' + r.status));
    return data;
  }

  async function action(id, name, extra={}) {
    if (name === 'delete' && !confirm('Excluir esta tarefa do histórico e apagar os temporários?')) return;
    if (name === 'restart' && !confirm('Reiniciar do zero? O staging será apagado e o download recomeçará.')) return;
    try {
      await callJson('/api/v1/archive/jobs/' + encodeURIComponent(id) + '/action', {action:name, cleanup:true, ...extra});
      await load();
    } catch (e) {
      alert(e.message);
    }
  }

  async function maintenance(name) {
    const label = name === 'clear_finished' ? 'finalizadas/canceladas' : 'interrompidas';
    if (!confirm('Remover tarefas ' + label + ' e apagar seus temporários?')) return;
    try {
      await callJson('/api/v1/archive/maintenance', {action:name, cleanup:true});
      await load();
    } catch (e) {
      alert(e.message);
    }
  }

  function cardId(card) {
    const txt = Array.from(card.querySelectorAll('.rm-arc-meta')).map(x => x.textContent || '').join(' ');
    const m = txt.match(/#([A-Za-z0-9_-]{6,64})/);
    return m ? m[1] : '';
  }

  function actionHtml(job) {
    const status = String(job.status || job.state || '').toLowerCase();
    if (status === 'waiting_password') {
      return '<input class="rm-arc-pwd" type="password" autocomplete="new-password" placeholder="Senha do compactado"><button class="primary" data-a="resume">Continuar</button><button class="danger" data-a="delete">Excluir</button>';
    }
    if (status === 'interrupted') {
      return '<button class="primary" data-a="resume">▶ Continuar</button><button data-a="restart">↻ Reiniciar</button><button class="danger" data-a="delete">Excluir</button>';
    }
    if (status === 'error' || status === 'failed') {
      return '<button class="primary" data-a="retry">Tentar novamente</button><button data-a="restart">↻ Reiniciar</button><button class="danger" data-a="delete">Excluir</button>';
    }
    if (status === 'running' || status === 'queued') {
      return '<button class="danger" data-a="cancel">Cancelar</button>';
    }
    if (terminal(status)) {
      return '<button class="danger" data-a="delete">Excluir</button>';
    }
    return '<button class="primary" data-a="resume">Continuar</button><button class="danger" data-a="delete">Excluir</button>';
  }

  function decorate() {
    const root = document.querySelector(ROOT);
    if (!root) return;
    const byId = new Map(jobs.map(j => [String(j.id || j.job_id || ''), j]));

    for (const card of root.querySelectorAll('.rm-arc-job')) {
      const id = cardId(card);
      const job = byId.get(id);
      if (!job) continue;
      const status = String(job.status || '').toLowerCase();
      if (status === 'interrupted') card.classList.add('rm-arc-interrupted');

      const file = card.querySelector('.rm-arc-file');
      const better = job.current_item || job.filename || job.archive_name || job.name;
      if (file && better && better !== 'Compactado') {
        file.textContent = better;
        file.title = better;
      }

      let actions = card.querySelector('.rm-arc-actions');
      if (!actions) {
        actions = document.createElement('div');
        actions.className = 'rm-arc-actions';
        card.appendChild(actions);
      }
      const signature = status + '|' + String(job.worker_alive) + '|' + String(job.stage_bytes || 0);
      if (actions.dataset.signature !== signature) {
        actions.dataset.signature = signature;
        actions.innerHTML = actionHtml(job);
        actions.querySelectorAll('button[data-a]').forEach(btn => {
          btn.onclick = () => {
            const pwd = actions.querySelector('.rm-arc-pwd')?.value || '';
            action(id, btn.dataset.a, {password:pwd});
          };
        });
      }
    }

    const head = root.querySelector('.rm-arc-head');
    if (head && !root.querySelector('.rm-arc-toolbar')) {
      const toolbar = document.createElement('div');
      toolbar.className = 'rm-arc-toolbar';
      toolbar.innerHTML = '<button type="button" data-m="clear_finished">Limpar finalizados</button><button type="button" data-m="clear_orphans">Limpar interrompidos</button>';
      toolbar.querySelectorAll('button[data-m]').forEach(btn => {
        btn.onclick = () => maintenance(btn.dataset.m);
      });
      head.appendChild(toolbar);
    }

    let running = 0, waiting = 0, pwd = 0;
    for (const j of jobs) {
      const st = String(j.status || j.state || '').toLowerCase();
      if (st === 'waiting_password') pwd++;
      else if (st === 'interrupted' || st === 'queued' || st === 'pending' || st === 'waiting') waiting++;
      else if (!terminal(st)) running++;
    }
    const a = root.querySelector('#rmArcRunV2');
    const q = root.querySelector('#rmArcQueueV2');
    const p = root.querySelector('#rmArcPwdV2');
    if (a) a.textContent = running;
    if (q) q.textContent = waiting;
    if (p) p.textContent = pwd;
  }

  async function load() {
    try {
      const data = await callJson('/api/v1/archive/jobs?limit=100');
      jobs = Array.isArray(data.jobs) ? data.jobs : [];
      decorate();
    } catch (_) {}
  }

  new MutationObserver(() => decorate()).observe(document.documentElement, {subtree:true, childList:true});
  load();
  setInterval(load, 2500);
})();
</script>
'''
        end = page.rfind('{% endblock %}')
        if end >= 0:
            page = page[:end] + controls_ui + '\n' + page[end:]
        else:
            page += '\n' + controls_ui
        tpl.write_text(page, encoding='utf-8')

print('Archive controls OK: cancelar/continuar/reiniciar/excluir + limpeza + retomada segura')


# RM_ARCHIVE_STYLE_V3
# Strong visual override for the V2 archive queue. Some live-source templates
# carry old inline blocks in an order that can leave the V2 markup effectively
# unstyled. This final block is appended last and wins by specificity.
if tpl.exists():
    page = tpl.read_text(encoding='utf-8')
    if 'RM_ARCHIVE_STYLE_V3' not in page:
        style_v3 = r'''
<!-- RM_ARCHIVE_STYLE_V3 -->
<style id="rm-archive-manager-v3-style">
  #rmArchiveManagerV2{
    display:block !important;
    width:100% !important;
    margin:16px 0 18px !important;
    padding:16px !important;
    border:1px solid #26354a !important;
    border-radius:14px !important;
    background:#0f1724 !important;
    color:#e7edf6 !important;
    box-shadow:0 1px 0 rgba(255,255,255,.02) inset !important;
    overflow:hidden !important;
  }
  #rmArchiveManagerV2 *{box-sizing:border-box !important}
  #rmArchiveManagerV2 .rm-arc-head{
    display:flex !important;
    align-items:flex-start !important;
    justify-content:space-between !important;
    gap:14px !important;
    flex-wrap:wrap !important;
    margin:0 0 14px !important;
  }
  #rmArchiveManagerV2 .rm-arc-title{
    display:block !important;
    margin:0 !important;
    font-size:18px !important;
    line-height:1.25 !important;
    font-weight:800 !important;
    letter-spacing:-.01em !important;
    color:#f4f7fb !important;
  }
  #rmArchiveManagerV2 .rm-arc-sub{
    margin-top:4px !important;
    font-size:12px !important;
    line-height:1.45 !important;
    color:#8fb0d6 !important;
  }
  #rmArchiveManagerV2 .rm-arc-toolbar{
    display:flex !important;
    align-items:center !important;
    gap:8px !important;
    flex-wrap:wrap !important;
    margin-left:auto !important;
  }
  #rmArchiveManagerV2 #rmArcRefreshV2,
  #rmArchiveManagerV2 .rm-arc-toolbar button,
  #rmArchiveManagerV2 .rm-arc-actions button{
    appearance:none !important;
    min-height:34px !important;
    padding:7px 11px !important;
    border:1px solid #3b4b63 !important;
    border-radius:9px !important;
    background:#172233 !important;
    color:#eaf1fb !important;
    font-size:12px !important;
    font-weight:700 !important;
    line-height:1 !important;
    cursor:pointer !important;
    transition:background .15s ease,border-color .15s ease,transform .15s ease !important;
  }
  #rmArchiveManagerV2 #rmArcRefreshV2:hover,
  #rmArchiveManagerV2 .rm-arc-toolbar button:hover,
  #rmArchiveManagerV2 .rm-arc-actions button:hover{
    background:#1d2b40 !important;
    border-color:#536987 !important;
  }
  #rmArchiveManagerV2 .rm-arc-stats{
    display:grid !important;
    grid-template-columns:repeat(3,minmax(0,1fr)) !important;
    gap:10px !important;
    margin:0 0 12px !important;
  }
  #rmArchiveManagerV2 .rm-arc-stat{
    display:flex !important;
    flex-direction:column !important;
    justify-content:center !important;
    min-height:66px !important;
    padding:11px 13px !important;
    border:1px solid #26354a !important;
    border-radius:11px !important;
    background:#111c2c !important;
    min-width:0 !important;
  }
  #rmArchiveManagerV2 .rm-arc-stat span{
    display:block !important;
    font-size:10px !important;
    line-height:1.2 !important;
    font-weight:700 !important;
    letter-spacing:.04em !important;
    color:#83a7d0 !important;
  }
  #rmArchiveManagerV2 .rm-arc-stat b{
    display:block !important;
    margin-top:5px !important;
    font-size:20px !important;
    line-height:1 !important;
    color:#f8fbff !important;
  }
  #rmArchiveManagerV2 .rm-arc-list{
    display:grid !important;
    gap:9px !important;
    width:100% !important;
    max-height:520px !important;
    overflow:auto !important;
    padding:0 !important;
  }
  #rmArchiveManagerV2 .rm-arc-empty{
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    min-height:58px !important;
    padding:14px !important;
    border:1px dashed #34465e !important;
    border-radius:10px !important;
    background:#0c1522 !important;
    color:#8fa6c1 !important;
    font-size:12px !important;
    text-align:center !important;
  }
  #rmArchiveManagerV2 .rm-arc-job{
    display:grid !important;
    grid-template-columns:minmax(240px,1.8fr) minmax(190px,1fr) minmax(150px,.7fr) !important;
    gap:14px !important;
    align-items:center !important;
    width:100% !important;
    padding:12px 13px !important;
    border:1px solid #29394f !important;
    border-radius:11px !important;
    background:#101a29 !important;
    min-width:0 !important;
  }
  #rmArchiveManagerV2 .rm-arc-interrupted{
    border-color:#6f4d1f !important;
    background:#1b160f !important;
  }
  #rmArchiveManagerV2 .rm-arc-file{
    min-width:0 !important;
    overflow:hidden !important;
    text-overflow:ellipsis !important;
    white-space:nowrap !important;
    font-size:13px !important;
    font-weight:800 !important;
    color:#f0f5fb !important;
  }
  #rmArchiveManagerV2 .rm-arc-meta{
    margin-top:4px !important;
    font-size:10px !important;
    line-height:1.35 !important;
    color:#7f9bbd !important;
    overflow-wrap:anywhere !important;
  }
  #rmArchiveManagerV2 .rm-arc-status{
    font-size:11px !important;
    line-height:1.3 !important;
    font-weight:800 !important;
    color:#dce8f6 !important;
  }
  #rmArchiveManagerV2 .rm-arc-progress{
    width:100% !important;
    height:7px !important;
    margin-top:7px !important;
    border-radius:999px !important;
    background:#1b2a3e !important;
    overflow:hidden !important;
  }
  #rmArchiveManagerV2 .rm-arc-progress>i{
    display:block !important;
    height:100% !important;
    min-width:0 !important;
    border-radius:999px !important;
    background:#3f8cff !important;
  }
  #rmArchiveManagerV2 .rm-arc-actions{
    grid-column:1/-1 !important;
    display:flex !important;
    align-items:center !important;
    justify-content:flex-end !important;
    gap:7px !important;
    flex-wrap:wrap !important;
    margin-top:0 !important;
    padding-top:9px !important;
    border-top:1px solid #223147 !important;
  }
  #rmArchiveManagerV2 .rm-arc-actions .primary{
    border-color:#275aa8 !important;
    background:#173c77 !important;
    color:#eaf3ff !important;
  }
  #rmArchiveManagerV2 .rm-arc-actions .danger{
    border-color:#78303a !important;
    background:#401821 !important;
    color:#ffdce1 !important;
  }
  #rmArchiveManagerV2 .rm-arc-actions input{
    min-height:34px !important;
    min-width:220px !important;
    max-width:320px !important;
    padding:7px 10px !important;
    border:1px solid #3b4b63 !important;
    border-radius:9px !important;
    background:#0b1421 !important;
    color:#eef4fb !important;
    outline:none !important;
  }
  @media(max-width:980px){ #rmArchiveManagerV2 .rm-arc-job{grid-template-columns:1fr 1fr !important} }
  @media(max-width:760px){
    #rmArchiveManagerV2{padding:13px !important}
    #rmArchiveManagerV2 .rm-arc-stats{grid-template-columns:1fr !important}
    #rmArchiveManagerV2 .rm-arc-job{grid-template-columns:1fr !important}
    #rmArchiveManagerV2 .rm-arc-actions{justify-content:flex-start !important}
    #rmArchiveManagerV2 .rm-arc-actions input{min-width:100% !important;max-width:100% !important}
  }
</style>
'''
        end = page.rfind('{% endblock %}')
        if end >= 0:
            page = page[:end] + style_v3 + '\n' + page[end:]
        else:
            page += '\n' + style_v3
        tpl.write_text(page, encoding='utf-8')

print('Archive style v3 OK: fila de compactados com card/stats/ações responsivos')


# RM_ARCHIVE_EXTERNAL_CSS_V1
# Some deployments serve the panel with a CSP/style policy that leaves injected
# inline <style> blocks unapplied. Publish the archive queue stylesheet as a
# normal Flask static asset and link it from the template.
if tpl.exists():
    static_dir = appdir / 'static'
    static_dir.mkdir(parents=True, exist_ok=True)
    css_file = static_dir / 'archive-manager-v3.css'
    css_file.write_text(r'''
#rmArchiveManagerV2{
  display:block!important;width:100%!important;margin:16px 0 18px!important;padding:16px!important;
  border:1px solid #26354a!important;border-radius:14px!important;background:#0f1724!important;
  color:#e7edf6!important;box-shadow:0 1px 0 rgba(255,255,255,.02) inset!important;overflow:hidden!important
}
#rmArchiveManagerV2 *{box-sizing:border-box!important}
#rmArchiveManagerV2 .rm-arc-head{
  display:flex!important;align-items:flex-start!important;justify-content:space-between!important;
  gap:14px!important;flex-wrap:wrap!important;margin:0 0 14px!important
}
#rmArchiveManagerV2 .rm-arc-title{
  display:block!important;margin:0!important;font-size:18px!important;line-height:1.25!important;
  font-weight:800!important;letter-spacing:-.01em!important;color:#f4f7fb!important
}
#rmArchiveManagerV2 .rm-arc-sub{
  margin-top:4px!important;font-size:12px!important;line-height:1.45!important;color:#8fb0d6!important
}
#rmArchiveManagerV2 .rm-arc-toolbar{
  display:flex!important;align-items:center!important;gap:8px!important;flex-wrap:wrap!important;margin-left:auto!important
}
#rmArchiveManagerV2 #rmArcRefreshV2,
#rmArchiveManagerV2 .rm-arc-toolbar button,
#rmArchiveManagerV2 .rm-arc-actions button{
  appearance:none!important;min-height:34px!important;padding:7px 11px!important;
  border:1px solid #3b4b63!important;border-radius:9px!important;background:#172233!important;
  color:#eaf1fb!important;font-size:12px!important;font-weight:700!important;line-height:1!important;
  cursor:pointer!important
}
#rmArchiveManagerV2 #rmArcRefreshV2:hover,
#rmArchiveManagerV2 .rm-arc-toolbar button:hover,
#rmArchiveManagerV2 .rm-arc-actions button:hover{background:#1d2b40!important;border-color:#536987!important}
#rmArchiveManagerV2 .rm-arc-stats{
  display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;
  gap:10px!important;margin:0 0 12px!important
}
#rmArchiveManagerV2 .rm-arc-stat{
  display:flex!important;flex-direction:column!important;justify-content:center!important;
  min-height:66px!important;padding:11px 13px!important;border:1px solid #26354a!important;
  border-radius:11px!important;background:#111c2c!important;min-width:0!important
}
#rmArchiveManagerV2 .rm-arc-stat span{
  display:block!important;font-size:10px!important;line-height:1.2!important;font-weight:700!important;
  letter-spacing:.04em!important;color:#83a7d0!important
}
#rmArchiveManagerV2 .rm-arc-stat b{
  display:block!important;margin-top:5px!important;font-size:20px!important;line-height:1!important;color:#f8fbff!important
}
#rmArchiveManagerV2 .rm-arc-list{
  display:grid!important;gap:9px!important;width:100%!important;max-height:520px!important;
  overflow:auto!important;padding:0!important
}
#rmArchiveManagerV2 .rm-arc-empty{
  display:flex!important;align-items:center!important;justify-content:center!important;min-height:58px!important;
  padding:14px!important;border:1px dashed #34465e!important;border-radius:10px!important;
  background:#0c1522!important;color:#8fa6c1!important;font-size:12px!important;text-align:center!important
}
#rmArchiveManagerV2 .rm-arc-job{
  display:grid!important;grid-template-columns:minmax(240px,1.8fr) minmax(190px,1fr) minmax(150px,.7fr)!important;
  gap:14px!important;align-items:center!important;width:100%!important;padding:12px 13px!important;
  border:1px solid #29394f!important;border-radius:11px!important;background:#101a29!important;min-width:0!important
}
#rmArchiveManagerV2 .rm-arc-interrupted{border-color:#6f4d1f!important;background:#1b160f!important}
#rmArchiveManagerV2 .rm-arc-file{
  min-width:0!important;overflow:hidden!important;text-overflow:ellipsis!important;white-space:nowrap!important;
  font-size:13px!important;font-weight:800!important;color:#f0f5fb!important
}
#rmArchiveManagerV2 .rm-arc-meta{
  margin-top:4px!important;font-size:10px!important;line-height:1.35!important;color:#7f9bbd!important;
  overflow-wrap:anywhere!important
}
#rmArchiveManagerV2 .rm-arc-status{
  font-size:11px!important;line-height:1.3!important;font-weight:800!important;color:#dce8f6!important
}
#rmArchiveManagerV2 .rm-arc-progress{
  width:100%!important;height:7px!important;margin-top:7px!important;border-radius:999px!important;
  background:#1b2a3e!important;overflow:hidden!important
}
#rmArchiveManagerV2 .rm-arc-progress>i{
  display:block!important;height:100%!important;min-width:0!important;border-radius:999px!important;background:#3f8cff!important
}
#rmArchiveManagerV2 .rm-arc-actions{
  grid-column:1/-1!important;display:flex!important;align-items:center!important;justify-content:flex-end!important;
  gap:7px!important;flex-wrap:wrap!important;margin-top:0!important;padding-top:9px!important;
  border-top:1px solid #223147!important
}
#rmArchiveManagerV2 .rm-arc-actions .primary{
  border-color:#275aa8!important;background:#173c77!important;color:#eaf3ff!important
}
#rmArchiveManagerV2 .rm-arc-actions .danger{
  border-color:#78303a!important;background:#401821!important;color:#ffdce1!important
}
#rmArchiveManagerV2 .rm-arc-actions input{
  min-height:34px!important;min-width:220px!important;max-width:320px!important;padding:7px 10px!important;
  border:1px solid #3b4b63!important;border-radius:9px!important;background:#0b1421!important;
  color:#eef4fb!important;outline:none!important
}
@media(max-width:980px){
  #rmArchiveManagerV2 .rm-arc-job{grid-template-columns:1fr 1fr!important}
}
@media(max-width:760px){
  #rmArchiveManagerV2{padding:13px!important}
  #rmArchiveManagerV2 .rm-arc-stats{grid-template-columns:1fr!important}
  #rmArchiveManagerV2 .rm-arc-job{grid-template-columns:1fr!important}
  #rmArchiveManagerV2 .rm-arc-actions{justify-content:flex-start!important}
  #rmArchiveManagerV2 .rm-arc-actions input{min-width:100%!important;max-width:100%!important}
}
''', encoding='utf-8')

    page = tpl.read_text(encoding='utf-8')
    link = '<link rel="stylesheet" href="/static/archive-manager-v3.css?v=ha4.7.4.9" data-rm-archive-css="v3">'
    if 'data-rm-archive-css="v3"' not in page:
        anchor = '<!-- RM_ARCHIVE_MANAGER_V2 -->'
        if anchor in page:
            page = page.replace(anchor, link + '\n' + anchor, 1)
        else:
            end = page.rfind('{% endblock %}')
            if end >= 0:
                page = page[:end] + link + '\n' + page[end:]
            else:
                page += '\n' + link
        tpl.write_text(page, encoding='utf-8')

print('Archive external CSS OK: /static/archive-manager-v3.css vinculado ao painel')


# RM_ARCHIVE_REMOVE_LEGACY_PANEL_V1
# Remove the old server-rendered Compactados card at deploy time. The previous
# JS hider was inherently racy: the legacy card could be rendered again later
# and appear at the page footer. We now delete only the legacy block that
# contains the original exact flow copy (capital "Download" and no "Google"),
# while keeping the V2 queue whose subtitle is different.
if tpl.exists():
    page = tpl.read_text(encoding='utf-8')

    legacy_needles = [
        'Download → análise → extração/streaming → Drive → limpeza',
        'Download -> análise -> extração/streaming -> Drive -> limpeza',
    ]

    def _remove_legacy_archive_card(text):
        removed = 0
        while True:
            positions = [text.find(n) for n in legacy_needles if text.find(n) >= 0]
            if not positions:
                break
            pos = min(positions)

            # Prefer semantic containers first. Walk backwards to the nearest
            # opening tag and remove through its matching closing tag using a
            # small depth counter. This avoids touching the V2 panel.
            candidates = []
            for tag in ('section', 'article', 'div'):
                start = text.rfind('<' + tag, 0, pos)
                if start >= 0:
                    candidates.append((start, tag))
            if not candidates:
                # Last-resort: remove only the legacy heading/subtitle area.
                line_start = text.rfind('\n', 0, pos)
                line_end = text.find('\n', pos)
                if line_start < 0: line_start = 0
                if line_end < 0: line_end = len(text)
                text = text[:line_start] + '\n<!-- RM_LEGACY_ARCHIVE_REMOVED -->\n' + text[line_end:]
                removed += 1
                continue

            start, tag = max(candidates, key=lambda x: x[0])

            token_re = re.compile(r'</?' + re.escape(tag) + r'\b[^>]*>', re.I)
            depth = 0
            end = None
            for m in token_re.finditer(text, start):
                token = m.group(0)
                if token.startswith('</'):
                    depth -= 1
                    if depth == 0:
                        end = m.end()
                        break
                elif not token.rstrip().endswith('/>'):
                    depth += 1

            if end is None or end <= pos or (end - start) > 20000:
                # Do not risk deleting a huge page region. Replace the legacy
                # subtitle so it can no longer be mistaken for a live panel,
                # then stop; the V2 JS hider remains as a fallback.
                for needle in legacy_needles:
                    text = text.replace(needle, 'RM_LEGACY_ARCHIVE_REMOVED', 1)
                removed += 1
                break

            block = text[start:end]
            # Safety check: this must be the legacy card, never the V2 queue.
            if (
                'Compactados' not in block
                or 'RM_ARCHIVE_MANAGER_V2' in block
                or 'Fila de compactados' in block
                or len(block) > 20000
            ):
                for needle in legacy_needles:
                    text = text.replace(needle, 'RM_LEGACY_ARCHIVE_REMOVED', 1)
                removed += 1
                break

            text = text[:start] + '\n<!-- RM_LEGACY_ARCHIVE_REMOVED -->\n' + text[end:]
            removed += 1

        return text, removed

    page, legacy_removed = _remove_legacy_archive_card(page)
    tpl.write_text(page, encoding='utf-8')
    print(f'Archive legacy panel cleanup OK: {legacy_removed} bloco(s) legado(s) removido(s)')
