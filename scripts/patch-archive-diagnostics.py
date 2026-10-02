#!/usr/bin/env python3
from pathlib import Path
import sys
import tempfile
import py_compile

if len(sys.argv) != 2:
    raise SystemExit("uso: patch-archive-diagnostics.py SOURCE_ROOT")

root = Path(sys.argv[1])
appdir = root / "app"
archive_py = appdir / "archive_import.py"
app_py = appdir / "app.py"
tpl = appdir / "templates" / "api_manager.html"

if not archive_py.exists() or not app_py.exists():
    raise SystemExit("Archive diagnostics: archive_import.py/app.py ausente")

src = archive_py.read_text(encoding="utf-8")

if "RM_ARCHIVE_DIAGNOSTICS_V1" not in src:
    addon = r'''

# RM_ARCHIVE_DIAGNOSTICS_V1
# Diagnóstico persistente por job. O objetivo é tornar erros de downloads
# grandes acionáveis sem SSH: estado atual, mensagem/erro concreto, staging,
# HTTP Range conhecido e uma trilha curta de eventos ficam acessíveis pela UI.
#
# Não registra senhas, headers, cookies nem URLs completas.
import json as _rmdi_json
import os as _rmdi_os
import time as _rmdi_time
import traceback as _rmdi_traceback
from pathlib import Path as _RmdiPath


_RMDI_DIR = DATA_DIR / 'archive-job-logs'
_RMDI_MAX_FILE = 1024 * 1024
_RMDI_KEEP_EVENTS = 120

_RMDI_ORIG_UPDATE_JOB = globals().get('_update_job')
_RMDI_ORIG_RUN_JOB = globals().get('_run_job')
_RMDI_ORIG_LIST_JOBS = globals().get('list_jobs')


def _rmdi_safe_text(value, limit=3000):
    text = str(value or '')
    # Evite gravar segredos comuns por acidente em mensagens de exceção.
    for needle in ('Authorization:', 'Cookie:', 'Set-Cookie:'):
        if needle.lower() in text.lower():
            return '[conteúdo sensível omitido]'
    return text[:limit]


def _rmdi_path(job_id):
    jid = ''.join(c for c in str(job_id or '') if c.isalnum() or c in '-_')[:128]
    return _RMDI_DIR / (jid + '.jsonl')


def _rmdi_rotate(path):
    try:
        if path.exists() and path.stat().st_size > _RMDI_MAX_FILE:
            old = path.with_suffix('.jsonl.1')
            try:
                old.unlink(missing_ok=True)
            except Exception:
                pass
            path.replace(old)
    except Exception:
        pass


def _rmdi_log(job_id, event, **fields):
    jid = str(job_id or '').strip()
    if not jid:
        return
    try:
        _RMDI_DIR.mkdir(parents=True, exist_ok=True)
        path = _rmdi_path(jid)
        _rmdi_rotate(path)
        row = {
            'ts': int(_rmdi_time.time()),
            'event': _rmdi_safe_text(event, 120),
        }
        allowed = (
            'status', 'phase', 'message', 'error', 'current_item',
            'downloaded_bytes', 'archive_bytes', 'uploaded_bytes',
            'unpacked_bytes', 'attempt'
        )
        for key in allowed:
            if key in fields and fields.get(key) not in (None, ''):
                value = fields.get(key)
                if key.endswith('_bytes') or key == 'attempt':
                    try:
                        row[key] = int(value)
                        continue
                    except Exception:
                        pass
                row[key] = _rmdi_safe_text(value)
        with path.open('a', encoding='utf-8') as fh:
            fh.write(_rmdi_json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
        try:
            _rmdi_os.chmod(path, 0o600)
        except Exception:
            pass
    except Exception:
        pass


def _rmdi_tail(job_id, limit=_RMDI_KEEP_EVENTS):
    path = _rmdi_path(job_id)
    if not path.exists():
        return []
    rows = []
    try:
        # Arquivo limitado a ~1 MiB, leitura completa é barata e simples.
        for line in path.read_text(encoding='utf-8', errors='replace').splitlines()[-max(1, int(limit)):]:
            try:
                item = _rmdi_json.loads(line)
            except Exception:
                continue
            if isinstance(item, dict):
                rows.append(item)
    except Exception:
        return []
    return rows


def _rmdi_stage_files(job_id, limit=80):
    stage = STAGING_ROOT / ('job-' + str(job_id or ''))
    rows = []
    if not stage.exists():
        return rows
    try:
        for p in stage.rglob('*'):
            if not p.is_file():
                continue
            try:
                st = p.stat()
                rows.append({
                    'name': str(p.relative_to(stage)),
                    'bytes': int(st.st_size),
                    'mtime': int(st.st_mtime),
                })
            except Exception:
                pass
    except Exception:
        pass
    rows.sort(key=lambda x: x.get('bytes', 0), reverse=True)
    return rows[:max(1, int(limit))]


def _rmdi_job(job_id):
    jid = str(job_id or '')
    try:
        row = get_job(jid) or {}
        return dict(row) if isinstance(row, dict) else {}
    except Exception:
        return {}


def _rmdi_public_job(row):
    row = dict(row or {})
    # Whitelist: não exponha links/headers/cookies/passwords no diagnóstico.
    keys = (
        'id', 'job_id', 'filename', 'archive_name', 'name',
        'status', 'phase', 'message', 'error', 'current_item',
        'created_at', 'updated_at', 'finished_at',
        'downloaded_bytes', 'archive_bytes', 'source_size_bytes',
        'expected_download_bytes', 'download_expected_bytes',
        'downloaded_bytes_live', 'download_remaining_bytes',
        'download_progress_pct', 'download_speed_bps',
        'download_eta_seconds', 'estimated_unpacked_bytes',
        'unpacked_bytes', 'uploaded_bytes', 'total_files',
        'completed_files', 'queue_position', 'worker_alive',
        'stage_bytes', 'stage_files'
    )
    return {key: row.get(key) for key in keys if key in row}


def _update_job(job_id, **fields):
    result = None
    if callable(_RMDI_ORIG_UPDATE_JOB):
        result = _RMDI_ORIG_UPDATE_JOB(job_id, **fields)

    interesting = {
        key: fields.get(key)
        for key in (
            'status', 'phase', 'message', 'error', 'current_item',
            'downloaded_bytes', 'archive_bytes', 'uploaded_bytes',
            'unpacked_bytes'
        )
        if key in fields
    }
    if any(
        key in interesting
        for key in ('status', 'phase', 'message', 'error')
    ):
        _rmdi_log(job_id, 'update', **interesting)
    return result


def _run_job(job_id):
    jid = str(job_id or '')
    _rmdi_log(jid, 'worker_start')
    try:
        if callable(_RMDI_ORIG_RUN_JOB):
            result = _RMDI_ORIG_RUN_JOB(job_id)
        else:
            result = None
        row = _rmdi_job(jid)
        _rmdi_log(
            jid,
            'worker_end',
            status=row.get('status'),
            phase=row.get('phase'),
            message=row.get('message'),
            error=row.get('error'),
            downloaded_bytes=row.get('downloaded_bytes'),
            archive_bytes=row.get('archive_bytes'),
        )
        return result
    except Exception as exc:
        row = _rmdi_job(jid)
        tb = ''.join(_rmdi_traceback.format_exception_only(type(exc), exc)).strip()
        _rmdi_log(
            jid,
            'worker_exception',
            status=row.get('status'),
            phase=row.get('phase'),
            message=row.get('message'),
            error=tb,
            downloaded_bytes=row.get('downloaded_bytes'),
            archive_bytes=row.get('archive_bytes'),
        )
        raise


def archive_job_diagnostics(job_id):
    jid = str(job_id or '').strip()
    if not jid:
        raise ValueError('job_id inválido')

    # Use list_jobs para incorporar dados dinâmicos do Download Manager.
    live = {}
    if callable(_RMDI_ORIG_LIST_JOBS):
        try:
            for row in (_RMDI_ORIG_LIST_JOBS(500) or []):
                if not isinstance(row, dict):
                    continue
                rid = str(row.get('id') or row.get('job_id') or '')
                if rid == jid:
                    live = dict(row)
                    break
        except Exception:
            live = {}
    if not live:
        live = _rmdi_job(jid)
    if not live:
        raise ValueError('Tarefa de compactado não encontrada')

    stage_files = _rmdi_stage_files(jid)
    stage_bytes = sum(max(0, int(x.get('bytes') or 0)) for x in stage_files)

    partial = {}
    try:
        known = globals().get('_RM_PARTIAL_REMOTE_TOTALS')
        last = globals().get('_RM_PARTIAL_LAST')
        if isinstance(known, dict):
            partial['known_remote_total_bytes'] = int(known.get(jid) or 0)
        if isinstance(last, dict) and isinstance(last.get(jid), dict):
            partial['last_resume'] = dict(last.get(jid) or {})
    except Exception:
        partial = {}

    manager = {}
    try:
        fn = globals().get('archive_manager_status')
        if callable(fn):
            state = fn() or {}
            manager = {
                'paused': bool(state.get('paused')),
                'blocked_by': str(state.get('blocked_by') or ''),
                'queue_length': int(state.get('queue_length') or 0),
                'disk_free_bytes': int(state.get('disk_free_bytes') or 0),
                'staging_bytes': int(state.get('staging_bytes') or 0),
            }
    except Exception:
        manager = {}

    return {
        'ok': True,
        'job_id': jid,
        'job': _rmdi_public_job(live),
        'manager': manager,
        'partial_resume': partial,
        'stage_total_bytes': stage_bytes,
        'stage_files': stage_files,
        'events': _rmdi_tail(jid),
    }


# Registre um snapshot na primeira consulta/listagem depois do upgrade para
# jobs que já estavam em erro antes de o diagnóstico existir.
try:
    for _row in (list_jobs(500) or []):
        if not isinstance(_row, dict):
            continue
        _jid = str(_row.get('id') or _row.get('job_id') or '')
        _status = str(_row.get('status') or '').lower()
        if _jid and _status in {'error', 'failed', 'interrupted'}:
            _rmdi_log(
                _jid,
                'startup_existing_error',
                status=_row.get('status'),
                phase=_row.get('phase'),
                message=_row.get('message'),
                error=_row.get('error'),
                downloaded_bytes=_row.get('downloaded_bytes'),
                archive_bytes=_row.get('archive_bytes'),
            )
except Exception:
    pass
'''
    archive_py.write_text(src + addon, encoding="utf-8")

with tempfile.NamedTemporaryFile(suffix=".pyc") as f:
    py_compile.compile(str(archive_py), doraise=True, cfile=f.name)

# ---------------------------------------------------------------------------
# Endpoints de diagnóstico — painel e extensão.
# ---------------------------------------------------------------------------
app = app_py.read_text(encoding="utf-8")
if "RM_ARCHIVE_DIAGNOSTICS_ROUTES_V1" not in app:
    marker = "# RM_ARCHIVE_IMPORT_ROUTES_V1"
    pos = app.find(marker)
    if pos < 0:
        raise SystemExit("Archive diagnostics: marcador de rotas ausente")

    routes = r'''
# RM_ARCHIVE_DIAGNOSTICS_ROUTES_V1
@app.route('/api/v1/extension/archive/jobs/<job_id>/diagnostics', methods=['GET', 'OPTIONS'])
@extension_api_required
def extension_archive_job_diagnostics_v1(job_id):
    from archive_import import archive_job_diagnostics
    try:
        return jsonify(archive_job_diagnostics(job_id))
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400


'''
    app = app[:pos] + routes + app[pos:]

if (
    "RM_ARCHIVE_DIAGNOSTICS_WEB_ROUTES_V1" not in app
    and "RM_ARCHIVE_WEB_ROUTES_V1" in app
):
    marker = "# RM_ARCHIVE_IMPORT_ROUTES_V1"
    pos = app.find(marker)

    # Reaproveite o guard do endpoint web de jobs quando existir.
    guard = ""
    import re as _rmdi_patch_re
    m = _rmdi_patch_re.search(
        r"@app\.route\('/api/v1/archive/jobs'.*?\)\n(?P<guard>(?:@[^\n]+\n)*)def web_archive_jobs\(",
        app,
    )
    if not m:
        m = _rmdi_patch_re.search(
            r'@app\.route\("/api/v1/archive/jobs".*?\)\n(?P<guard>(?:@[^\n]+\n)*)def web_archive_jobs\(',
            app,
        )
    if m:
        guard = m.group('guard') or ""

    web = r'''
# RM_ARCHIVE_DIAGNOSTICS_WEB_ROUTES_V1
@app.route('/api/v1/archive/jobs/<job_id>/diagnostics', methods=['GET'])
__GUARD__def web_archive_job_diagnostics_v1(job_id):
    from archive_import import archive_job_diagnostics
    try:
        return jsonify(archive_job_diagnostics(job_id))
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400


'''.replace('__GUARD__', guard)
    app = app[:pos] + web + app[pos:]

app_py.write_text(app, encoding="utf-8")
with tempfile.NamedTemporaryFile(suffix=".pyc") as f:
    py_compile.compile(str(app_py), doraise=True, cfile=f.name)

# ---------------------------------------------------------------------------
# UI — erro concreto inline + modal "Detalhes / Logs" + copiar diagnóstico.
# ---------------------------------------------------------------------------
if tpl.exists():
    page = tpl.read_text(encoding="utf-8")
    if "RM_ARCHIVE_DIAGNOSTICS_UI_V1" not in page:
        ui = r'''
<!-- RM_ARCHIVE_DIAGNOSTICS_UI_V1 -->
<style>
#rmArchiveManagerV2 .rmdi-error{
  grid-column:1/-1;padding:9px 11px;border:1px solid #7f1d1d;border-radius:9px;
  background:#32131a;color:#fecaca;font-size:11px;line-height:1.45;white-space:pre-wrap;
  overflow-wrap:anywhere
}
#rmdiModal[hidden]{display:none!important}
#rmdiModal{
  position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.72);
  display:flex;align-items:center;justify-content:center;padding:20px
}
#rmdiModal .rmdi-box{
  width:min(1000px,96vw);max-height:90vh;overflow:auto;background:#0d1725;color:#e5edf7;
  border:1px solid #34465e;border-radius:14px;padding:16px;box-shadow:0 20px 60px rgba(0,0,0,.5)
}
#rmdiModal .rmdi-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px}
#rmdiModal .rmdi-actions{display:flex;gap:8px;flex-wrap:wrap}
#rmdiModal button{padding:7px 10px;border:1px solid #475569;border-radius:8px;background:#172233;color:#e5edf7;cursor:pointer}
#rmdiModal pre{
  margin:0;padding:12px;background:#08111d;border:1px solid #26354a;border-radius:10px;
  color:#dbeafe;font:12px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace;
  white-space:pre-wrap;overflow-wrap:anywhere
}
</style>
<div id="rmdiModal" hidden>
  <div class="rmdi-box">
    <div class="rmdi-head">
      <strong>Diagnóstico da tarefa</strong>
      <div class="rmdi-actions">
        <button type="button" id="rmdiCopy">Copiar diagnóstico</button>
        <button type="button" id="rmdiClose">Fechar</button>
      </div>
    </div>
    <pre id="rmdiText">Carregando...</pre>
  </div>
</div>
<script>
(() => {
  let jobs = [];
  let lastText = '';

  const root = () => document.getElementById('rmArchiveManagerV2');
  const esc = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = n => {
    n=Number(n||0); if(!n)return '0 B';
    const u=['B','KB','MB','GB','TB'];let i=0;
    while(n>=1024&&i<u.length-1){n/=1024;i++}
    return n.toFixed(i>=3?1:0)+' '+u[i];
  };

  function cardId(card){
    const txt=Array.from(card.querySelectorAll('.rm-arc-meta')).map(x=>x.textContent||'').join(' ');
    const m=txt.match(/#([A-Za-z0-9_-]{6,128})/);
    return m?m[1]:'';
  }

  function exactJob(id){
    if(!id)return null;
    return jobs.find(j=>{
      const jid=String(j.id||j.job_id||'');
      return jid===id || jid.startsWith(id) || id.startsWith(jid);
    })||null;
  }

  function decorate(){
    const box=root(); if(!box)return;
    for(const card of box.querySelectorAll('.rm-arc-job')){
      const shortId=cardId(card);
      const job=exactJob(shortId);
      if(!job)continue;
      const id=String(job.id||job.job_id||shortId);

      const error=String(job.error||'').trim();
      const message=String(job.message||'').trim();
      const status=String(job.status||'').toLowerCase();

      let err=card.querySelector('.rmdi-error');
      if((status==='error'||status==='failed') && (error||message)){
        if(!err){
          err=document.createElement('div');
          err.className='rmdi-error';
          card.appendChild(err);
        }
        err.textContent='ERRO: '+(error||message);
      }else if(err){
        err.remove();
      }

      const actions=card.querySelector('.rm-arc-actions');
      if(actions && !actions.querySelector('[data-rmdi]')){
        const btn=document.createElement('button');
        btn.type='button';
        btn.dataset.rmdi='1';
        btn.textContent='📋 Detalhes / Logs';
        btn.onclick=()=>openDiagnostics(id);
        actions.appendChild(btn);
      }
    }
  }

  async function openDiagnostics(id){
    const modal=document.getElementById('rmdiModal');
    const pre=document.getElementById('rmdiText');
    modal.hidden=false;
    pre.textContent='Carregando diagnóstico...';
    try{
      const r=await fetch('/api/v1/archive/jobs/'+encodeURIComponent(id)+'/diagnostics',{
        credentials:'same-origin',cache:'no-store'
      });
      const d=await r.json().catch(()=>({}));
      if(!r.ok||d.ok===false)throw new Error(d.error||('HTTP '+r.status));

      const j=d.job||{}, p=d.partial_resume||{}, m=d.manager||{};
      const lines=[];
      lines.push('JOB: '+String(d.job_id||id));
      lines.push('STATUS: '+String(j.status||'')+' / '+String(j.phase||''));
      if(j.message) lines.push('MENSAGEM: '+j.message);
      if(j.error) lines.push('ERRO: '+j.error);
      lines.push('');
      lines.push('DOWNLOAD: '+fmt(j.downloaded_bytes_live||j.downloaded_bytes)+' / '+fmt(j.download_expected_bytes||j.expected_download_bytes||j.archive_bytes));
      lines.push('STAGING: '+fmt(d.stage_total_bytes));
      lines.push('LIVRE: '+fmt(m.disk_free_bytes));
      if(p.known_remote_total_bytes) lines.push('TOTAL REMOTO (Range): '+fmt(p.known_remote_total_bytes));
      if(p.last_resume) lines.push('ÚLTIMA RETOMADA: '+JSON.stringify(p.last_resume));
      lines.push('');
      lines.push('ARQUIVOS NO STAGING:');
      for(const f of (d.stage_files||[])){
        lines.push('  - '+String(f.name||'')+' · '+fmt(f.bytes));
      }
      lines.push('');
      lines.push('EVENTOS RECENTES:');
      for(const ev of (d.events||[])){
        const when=ev.ts?new Date(Number(ev.ts)*1000).toLocaleString():'';
        const parts=[when,ev.event,ev.status,ev.phase,ev.message,ev.error].filter(Boolean);
        lines.push('  '+parts.join(' | '));
      }
      lastText=lines.join('\n');
      pre.textContent=lastText;
    }catch(e){
      lastText='Falha ao obter diagnóstico: '+e.message;
      pre.textContent=lastText;
    }
  }

  document.getElementById('rmdiClose')?.addEventListener('click',()=>{
    document.getElementById('rmdiModal').hidden=true;
  });
  document.getElementById('rmdiCopy')?.addEventListener('click',async()=>{
    try{
      await navigator.clipboard.writeText(lastText||document.getElementById('rmdiText')?.textContent||'');
      alert('Diagnóstico copiado.');
    }catch(e){
      alert('Não foi possível copiar automaticamente. Selecione o texto do diagnóstico.');
    }
  });
  document.getElementById('rmdiModal')?.addEventListener('click',ev=>{
    if(ev.target===ev.currentTarget)ev.currentTarget.hidden=true;
  });

  jobs=Array.isArray(window.__rmArchiveJobsV2)?window.__rmArchiveJobsV2:[];
  decorate();
  document.addEventListener('rm-archive-jobs',ev=>{
    jobs=Array.isArray(ev.detail)?ev.detail:[];
    setTimeout(decorate,0);
  });
})();
</script>
'''
        end = page.rfind("{% endblock %}")
        if end >= 0:
            page = page[:end] + ui + "\n" + page[end:]
        else:
            page += "\n" + ui
        tpl.write_text(page, encoding="utf-8")

print(
    "Archive diagnostics OK: erro inline + detalhes/logs por job + copiar diagnóstico"
)
