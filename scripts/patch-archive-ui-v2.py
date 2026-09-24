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
  @media(max-width:900px){#rmArchiveManagerV2 .rm-arc-job{grid-template-columns:1fr}#rmArchiveManagerV2 .rm-arc-stats{grid-template-columns:1fr 1fr 1fr}}
  @media(max-width:520px){#rmArchiveManagerV2 .rm-arc-stats{grid-template-columns:1fr}}
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
    const heads = Array.from(document.querySelectorAll('h1,h2,h3,h4,strong,b'));
    const old = heads.find(el => el.id !== 'rmArcV2Title' && (el.textContent || '').trim() === 'Compactados');
    if (!old) return;
    const box = old.closest('.card,.panel,section') || old.parentElement;
    if (box && !box.closest('#'+MARK)) box.style.display='none';
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
        if(['queued','pending','waiting'].includes(s)) queued++;
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
