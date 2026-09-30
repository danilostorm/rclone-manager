#!/usr/bin/env python3
from pathlib import Path
import sys
import tempfile
import py_compile

if len(sys.argv) != 2:
    raise SystemExit("uso: patch-archive-partial-resume.py SOURCE_ROOT")

root = Path(sys.argv[1])
archive_py = root / "app" / "archive_import.py"
if not archive_py.exists():
    raise SystemExit("Archive partial resume: app/archive_import.py ausente")

src = archive_py.read_text(encoding="utf-8")
if "RM_ARCHIVE_PARTIAL_RESUME_V1" in src:
    print("Archive partial resume: já aplicado")
    raise SystemExit(0)

addon = r'''

# RM_ARCHIVE_PARTIAL_RESUME_V1
# Retomada real de downloads parciais por HTTP Range.
#
# Este overlay é carregado DEPOIS do resilience/download-manager. Em vez de
# substituir a fila, ele troca o callable interno usado por cada tentativa do
# resilience. Assim, tanto retry automático quanto "Continuar" reutilizam os
# bytes já gravados no staging.
#
# Regra de segurança principal: se existe um parcial e o servidor NÃO confirma
# 206 + Content-Range iniciando exatamente no byte salvo, o Manager NÃO
# sobrescreve o arquivo. O parcial é preservado e a tarefa para com uma
# mensagem clara; "Reiniciar" continua sendo a ação explícita para descartar.
import os as _rmpr_os
import re as _rmpr_re
import time as _rmpr_time
from pathlib import Path as _RmprPath
from urllib.parse import urlparse as _rmpr_urlparse

try:
    import requests as _rmpr_requests
except Exception:
    _rmpr_requests = None


_RM_PARTIAL_REMOTE_TOTALS = {}
_RM_PARTIAL_LAST = {}

# O resilience captura o wrapper de UI em _RM_RES_ORIG_DOWNLOAD_ONE.
# Guarde esse callable antes de substituí-lo para evitar recursão.
_RMPR_BASE_DOWNLOAD = globals().get('_RM_RES_ORIG_DOWNLOAD_ONE')
if not callable(_RMPR_BASE_DOWNLOAD):
    _RMPR_BASE_DOWNLOAD = globals().get('_download_one')


def _rmpr_human(value):
    try:
        n = float(value or 0)
    except Exception:
        n = 0.0
    units = ('B', 'KB', 'MB', 'GB', 'TB')
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024.0
        i += 1
    return f'{n:.1f} {units[i]}' if i >= 3 else f'{n:.0f} {units[i]}'


def _rmpr_normal_name(value):
    name = _RmprPath(str(value or '').split('?', 1)[0]).name.strip().lower()
    for suffix in ('.crdownload', '.download', '.partial', '.part', '.tmp'):
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return name


def _rmpr_files(dest):
    rows = []
    try:
        for p in _RmprPath(dest).iterdir():
            if not p.is_file():
                continue
            try:
                size = int(p.stat().st_size)
                mtime = float(p.stat().st_mtime)
            except Exception:
                continue
            if size > 0:
                rows.append((p, size, mtime))
    except Exception:
        pass
    return rows


def _rmpr_pick_partial(row, dest, index, total):
    files = _rmpr_files(dest)
    if not files:
        return None

    label = ''
    url = ''
    if isinstance(row, dict):
        label = str(row.get('name') or row.get('label') or '').strip()
        url = str(row.get('url') or row.get('download_url') or row.get('href') or '').strip()

    wanted = {
        x for x in (
            _rmpr_normal_name(label),
            _rmpr_normal_name(_rmpr_urlparse(url).path if url else ''),
        ) if x
    }

    # 1) Nome exato, ignorando sufixos temporários.
    if wanted:
        exact = [x for x in files if _rmpr_normal_name(x[0].name) in wanted]
        if exact:
            return max(exact, key=lambda x: (x[1], x[2]))[0]

    # 2) Nome contido (alguns providers acrescentam token/prefixo).
    if wanted:
        fuzzy = []
        for item in files:
            got = _rmpr_normal_name(item[0].name)
            if any(w in got or got in w for w in wanted if len(w) >= 6 and len(got) >= 6):
                fuzzy.append(item)
        if fuzzy:
            return max(fuzzy, key=lambda x: (x[1], x[2]))[0]

    # 3) Job de um único arquivo: o maior arquivo do diretório de download é o
    # candidato seguro. É exatamente o caso de ZIP de pasta Dropbox.
    try:
        if int(total or 1) == 1:
            return max(files, key=lambda x: (x[1], x[2]))[0]
    except Exception:
        pass

    # 4) Multipart: prefira o arquivo mais recentemente alterado. Não use
    # ordenação alfabética porque partes concluídas anteriores permanecem.
    return max(files, key=lambda x: x[2])[0]


def _rmpr_expected_from_row(row):
    if not isinstance(row, dict):
        return 0
    for key in ('size_bytes', 'content_length', 'total_size_bytes', 'source_size_bytes'):
        try:
            value = int(row.get(key) or 0)
            if value > 0:
                return value
        except Exception:
            pass
    return 0


def _rmpr_downloaded_total(dest):
    total = 0
    for _p, size, _mtime in _rmpr_files(dest):
        total += max(0, int(size))
    return total


def _rmpr_update(job_id, **fields):
    fn = globals().get('_update_job')
    if callable(fn):
        try:
            fn(str(job_id), **fields)
            return
        except Exception:
            pass
    fn = globals().get('_ARCHIVE_ORIG_UPDATE_JOB') or globals().get('_RM_RES_ORIG_UPDATE_JOB')
    if callable(fn):
        try:
            fn(str(job_id), **fields)
        except Exception:
            pass


def _rmpr_check_cancel(job_id):
    fn = globals().get('_archive_check_cancel')
    if callable(fn):
        fn(str(job_id))


def _rmpr_url(row):
    if not isinstance(row, dict):
        return ''
    return str(row.get('url') or row.get('download_url') or row.get('href') or '').strip()


def _rmpr_headers(row, offset):
    headers = {
        'Range': f'bytes={int(offset)}-',
        'Accept-Encoding': 'identity',
        'User-Agent': 'Mozilla/5.0 Rclone-Manager-Archive-Resume/1.0',
    }
    if isinstance(row, dict):
        supplied = row.get('headers')
        if isinstance(supplied, dict):
            for key, value in supplied.items():
                key = str(key or '').strip()
                if key and value is not None and key.lower() not in {'range', 'content-length'}:
                    headers[key] = str(value)
        referer = str(row.get('referer') or row.get('referrer') or '').strip()
        if referer:
            headers['Referer'] = referer
    return headers


def _rmpr_content_range(response):
    value = str(response.headers.get('Content-Range') or '').strip()
    # bytes 123-999/1000
    m = _rmpr_re.match(r'^bytes\s+(\d+)-(\d+)/(\d+|\*)$', value, _rmpr_re.I)
    if m:
        return int(m.group(1)), int(m.group(2)), (0 if m.group(3) == '*' else int(m.group(3)))
    # bytes */1000 (comum no 416 quando já terminou)
    m = _rmpr_re.match(r'^bytes\s+\*/(\d+)$', value, _rmpr_re.I)
    if m:
        return -1, -1, int(m.group(1))
    return None


def _rmpr_final_path(path):
    p = _RmprPath(path)
    low = p.name.lower()
    for suffix in ('.crdownload', '.download', '.partial', '.part', '.tmp'):
        if low.endswith(suffix):
            candidate = p.with_name(p.name[:-len(suffix)])
            # Só retire sufixo temporário se restar um nome real.
            if candidate.name and candidate.name != p.name:
                try:
                    if candidate.exists() and candidate != p:
                        return p
                    p.replace(candidate)
                    return candidate
                except Exception:
                    return p
    return p


def _rmpr_resume_http(job_id, row, dest, target):
    if _rmpr_requests is None:
        raise RuntimeError(
            'Download parcial preservado, mas requests não está disponível para retomada HTTP Range'
        )

    jid = str(job_id or '')
    url = _rmpr_url(row)
    if not url.lower().startswith(('http://', 'https://')):
        raise RuntimeError(
            f'Download parcial preservado em {target}; a origem não é HTTP e não pode ser retomada por Range'
        )

    try:
        offset = int(_RmprPath(target).stat().st_size)
    except Exception:
        offset = 0
    if offset <= 0:
        return None

    expected_hint = _rmpr_expected_from_row(row)
    if expected_hint and offset == expected_hint:
        _RM_PARTIAL_REMOTE_TOTALS[jid] = expected_hint
        _rmpr_update(
            jid,
            phase='downloading',
            status='running',
            current_item=_RmprPath(target).name,
            downloaded_bytes=_rmpr_downloaded_total(dest),
            message=f'Download já completo no staging ({_rmpr_human(offset)}); reutilizando',
        )
        return _rmpr_final_path(target)
    if expected_hint and offset > expected_hint:
        raise RuntimeError(
            f'Parcial preservado ({_rmpr_human(offset)}), mas é maior que o tamanho esperado '
            f'({_rmpr_human(expected_hint)}). Use Reiniciar somente se quiser descartá-lo.'
        )

    _rmpr_check_cancel(jid)
    _rmpr_update(
        jid,
        phase='resuming_download',
        status='running',
        current_item=_RmprPath(target).name,
        downloaded_bytes=_rmpr_downloaded_total(dest),
        message=f'Retomando download a partir de {_rmpr_human(offset)}',
        error='',
    )

    response = None
    try:
        response = _rmpr_requests.get(
            url,
            headers=_rmpr_headers(row, offset),
            stream=True,
            allow_redirects=True,
            timeout=(25, 120),
        )

        cr = _rmpr_content_range(response)

        if response.status_code == 416:
            if cr and cr[2] > 0 and cr[2] == offset:
                _RM_PARTIAL_REMOTE_TOTALS[jid] = cr[2]
                _rmpr_update(
                    jid,
                    phase='downloading',
                    status='running',
                    current_item=_RmprPath(target).name,
                    downloaded_bytes=_rmpr_downloaded_total(dest),
                    message='Servidor confirmou que o parcial já contém 100% do arquivo',
                    error='',
                )
                return _rmpr_final_path(target)
            raise RuntimeError(
                f'Servidor recusou a faixa de retomada (HTTP 416). '
                f'O parcial de {_rmpr_human(offset)} foi preservado.'
            )

        if response.status_code != 206:
            if response.status_code >= 400:
                response.raise_for_status()
            raise RuntimeError(
                f'Servidor não aceitou retomada HTTP Range (respondeu HTTP {response.status_code}). '
                f'O parcial de {_rmpr_human(offset)} foi preservado; use Reiniciar apenas '
                f'se quiser baixar do zero.'
            )

        if not cr or cr[0] != offset:
            got = response.headers.get('Content-Range') or 'ausente'
            raise RuntimeError(
                f'Content-Range inválido na retomada: esperado início {offset}, recebido {got}. '
                f'O parcial foi preservado.'
            )

        remote_total = int(cr[2] or 0)
        if remote_total > 0:
            if offset > remote_total:
                raise RuntimeError(
                    f'Parcial local ({_rmpr_human(offset)}) é maior que a origem '
                    f'({_rmpr_human(remote_total)}); arquivo preservado.'
                )
            _RM_PARTIAL_REMOTE_TOTALS[jid] = remote_total

        ctype = str(response.headers.get('Content-Type') or '').lower()
        dispo = str(response.headers.get('Content-Disposition') or '').lower()
        if 'text/html' in ctype and 'attachment' not in dispo:
            raise RuntimeError(
                f'A origem retornou HTML em vez dos bytes do arquivo; parcial de '
                f'{_rmpr_human(offset)} preservado.'
            )

        start = _rmpr_time.time()
        last_update = start
        last_size = offset
        speed = 0.0
        target = _RmprPath(target)

        with target.open('ab') as fh:
            for chunk in response.iter_content(chunk_size=4 * 1024 * 1024):
                if not chunk:
                    continue
                _rmpr_check_cancel(jid)
                fh.write(chunk)

                now = _rmpr_time.time()
                if now - last_update >= 1.5:
                    try:
                        current = int(target.stat().st_size)
                    except Exception:
                        current = last_size + len(chunk)

                    dt = max(0.001, now - last_update)
                    instant = max(0, current - last_size) / dt
                    speed = instant if speed <= 0 else (speed * 0.70 + instant * 0.30)
                    total_downloaded = _rmpr_downloaded_total(dest)
                    remaining = max(0, remote_total - current) if remote_total else 0
                    eta = int(remaining / speed) if remaining and speed > 1024 else 0

                    dyn = globals().get('_RMQM_DYNAMIC')
                    if isinstance(dyn, dict):
                        existing = dict(dyn.get(jid) or {})
                        existing.update({
                            'download_expected_bytes': remote_total,
                            'downloaded_bytes_live': total_downloaded,
                            'download_remaining_bytes': remaining,
                            'download_speed_bps': int(speed),
                            'download_eta_seconds': eta,
                            'download_progress_pct': (
                                min(100.0, current * 100.0 / remote_total)
                                if remote_total else 0.0
                            ),
                        })
                        dyn[jid] = existing

                    _rmpr_update(
                        jid,
                        phase='resuming_download',
                        status='running',
                        current_item=target.name,
                        downloaded_bytes=total_downloaded,
                        message=(
                            f'Retomando de {_rmpr_human(offset)} · '
                            f'agora {_rmpr_human(current)}'
                            + (f' / {_rmpr_human(remote_total)}' if remote_total else '')
                        ),
                        error='',
                    )
                    last_update = now
                    last_size = current

            fh.flush()
            try:
                _rmpr_os.fsync(fh.fileno())
            except Exception:
                pass

        final_size = int(target.stat().st_size)
        if remote_total and final_size != remote_total:
            raise RuntimeError(
                f'Conexão terminou antes do arquivo completar: '
                f'{_rmpr_human(final_size)} de {_rmpr_human(remote_total)}. '
                f'O parcial foi preservado para a próxima tentativa.'
            )

        final_path = _rmpr_final_path(target)
        _RM_PARTIAL_LAST[jid] = {
            'resumed_from_bytes': offset,
            'final_bytes': final_size,
            'remote_total_bytes': remote_total,
            'finished_at': int(_rmpr_time.time()),
        }
        _rmpr_update(
            jid,
            phase='downloading',
            status='running',
            current_item=_RmprPath(final_path).name,
            downloaded_bytes=_rmpr_downloaded_total(dest),
            message=(
                f'Retomada concluída: preservados {_rmpr_human(offset)} '
                f'e baixado somente o restante'
            ),
            error='',
        )
        return final_path
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def _rmpr_download_one(job_id, row, dest, index, total):
    jid = str(job_id or '')
    target = _rmpr_pick_partial(row, dest, index, total)

    if target is None:
        return _RMPR_BASE_DOWNLOAD(job_id, row, dest, index, total)

    try:
        size = int(_RmprPath(target).stat().st_size)
    except Exception:
        size = 0
    if size <= 0:
        return _RMPR_BASE_DOWNLOAD(job_id, row, dest, index, total)

    # Nunca deixe o downloader legado truncar silenciosamente um parcial.
    # Se a origem suportar Range, continue. Se não suportar, pare preservando.
    return _rmpr_resume_http(jid, row, dest, target)


# O retry antigo apagava exatamente o arquivo modificado pela tentativa que
# falhava. Isso tornava impossível retomar: 94 GB viravam 0 GB antes do retry.
# A partir daqui erros transitórios preservam staging.
if '_rm_res_cleanup_failed_attempt' in globals():
    def _rm_res_cleanup_failed_attempt(dest, before):
        return None


# Faça TODAS as tentativas internas do resilience passarem pelo resumidor.
if '_RM_RES_ORIG_DOWNLOAD_ONE' in globals() and callable(_RMPR_BASE_DOWNLOAD):
    _RM_RES_ORIG_DOWNLOAD_ONE = _rmpr_download_one
elif callable(_RMPR_BASE_DOWNLOAD):
    # Compatibilidade para instalações sem o overlay resilience.
    _download_one = _rmpr_download_one


# O Download Manager calcula TOTAL/ETA por esta função. Inclua o total remoto
# descoberto pelo Content-Range para jobs em que a extensão não conhecia o
# tamanho (ex.: ZIP dinâmico de pasta Dropbox).
_RMPR_ORIG_EXPECTED_BYTES = globals().get('_rmqm_expected_bytes')
if callable(_RMPR_ORIG_EXPECTED_BYTES):
    def _rmqm_expected_bytes(job):
        base = 0
        try:
            base = int(_RMPR_ORIG_EXPECTED_BYTES(job) or 0)
        except Exception:
            base = 0
        jid = ''
        if isinstance(job, dict):
            jid = str(job.get('id') or job.get('job_id') or '')
        try:
            remote = int(_RM_PARTIAL_REMOTE_TOTALS.get(jid) or 0)
        except Exception:
            remote = 0
        return max(base, remote)


def archive_partial_resume_status():
    return {
        'enabled': True,
        'range_resume': True,
        'preserve_partial_on_failure': True,
        'known_remote_totals': dict(_RM_PARTIAL_REMOTE_TOTALS),
        'last_resumes': dict(_RM_PARTIAL_LAST),
    }
'''

archive_py.write_text(src + addon, encoding="utf-8")

with tempfile.NamedTemporaryFile(suffix=".pyc") as f:
    py_compile.compile(str(archive_py), doraise=True, cfile=f.name)

print(
    "Archive partial resume OK: HTTP Range + parcial preservado + retry sem truncar"
)
