#!/usr/bin/env python3
from pathlib import Path
import sys
import tempfile
import py_compile

if len(sys.argv) != 2:
    raise SystemExit("uso: patch-archive-no-range-fallback.py SOURCE_ROOT")

root = Path(sys.argv[1])
archive_py = root / "app" / "archive_import.py"
if not archive_py.exists():
    raise SystemExit("Archive no-range fallback: app/archive_import.py ausente")

src = archive_py.read_text(encoding="utf-8")
if "RM_ARCHIVE_NO_RANGE_FALLBACK_V1" in src:
    print("Archive no-range fallback: já aplicado")
    raise SystemExit(0)

if "RM_ARCHIVE_PARTIAL_RESUME_V1" not in src:
    raise SystemExit("Archive no-range fallback: partial resume V1 ausente")

old = """        if response.status_code != 206:
            if response.status_code >= 400:
                response.raise_for_status()
            raise RuntimeError(
                f'Servidor não aceitou retomada HTTP Range (respondeu HTTP {response.status_code}). '
                f'O parcial de {_rmpr_human(offset)} foi preservado; use Reiniciar apenas '
                f'se quiser baixar do zero.'
            )
"""

new = """        if response.status_code == 200 and offset > 0:
            return _rmnr_continue_from_full_response(
                jid, row, dest, target, response, offset
            )

        if response.status_code != 206:
            if response.status_code >= 400:
                response.raise_for_status()
            raise RuntimeError(
                f'Servidor não aceitou retomada HTTP Range (respondeu HTTP {response.status_code}). '
                f'O parcial de {_rmpr_human(offset)} foi preservado.'
            )
"""

if old not in src:
    raise SystemExit("Archive no-range fallback: bloco HTTP 206 esperado não encontrado")

src = src.replace(old, new, 1)

addon = r'''

# RM_ARCHIVE_NO_RANGE_FALLBACK_V1
# Fallback seguro quando a origem ignora Range e responde HTTP 200.
#
# Sem suporte a Range não existe como pedir somente o restante do arquivo.
# Para ainda reaproveitar o staging sem corromper o ZIP, recebemos o stream
# completo, comparamos byte a byte todo o prefixo remoto com o parcial local e
# somente depois do prefixo validado começamos a anexar os bytes restantes.
#
# Isso preserva o parcial e evita regravar o começo, mas NÃO economiza banda:
# a origem precisa retransmitir os bytes do prefixo. Se qualquer byte divergir,
# o arquivo local é preservado e nada novo é anexado.


def _rmnr_full_total(response):
    try:
        value = int(response.headers.get('Content-Length') or 0)
        return max(0, value)
    except Exception:
        return 0


def _rmnr_continue_from_full_response(job_id, row, dest, target, response, offset):
    jid = str(job_id or '')
    target = _RmprPath(target)
    offset = int(offset or 0)
    total = _rmnr_full_total(response)

    if total and offset > total:
        raise RuntimeError(
            f'A origem sem Range informou {_rmpr_human(total)}, menor que o parcial '
            f'local de {_rmpr_human(offset)}. Parcial preservado.'
        )

    if total and offset == total:
        _RM_PARTIAL_REMOTE_TOTALS[jid] = total
        _rmpr_update(
            jid,
            phase='downloading',
            status='running',
            current_item=target.name,
            downloaded_bytes=_rmpr_downloaded_total(dest),
            message=(
                'Origem não suporta Range, mas o tamanho remoto confirma que '
                'o arquivo local já está completo'
            ),
            error='',
        )
        return _rmpr_final_path(target)

    _rmpr_update(
        jid,
        phase='validating_prefix',
        status='running',
        current_item=target.name,
        downloaded_bytes=_rmpr_downloaded_total(dest),
        message=(
            f'Origem não suporta Range; revalidando {_rmpr_human(offset)} já '
            f'baixados antes de anexar o restante'
        ),
        error='',
    )

    chunk_size = 4 * 1024 * 1024
    verified = 0
    appended = 0
    network_bytes = 0
    start = _rmpr_time.time()
    last_update = start
    prefix_done_reported = False

    with target.open('rb') as local_read, target.open('ab') as local_append:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if not chunk:
                continue

            _rmpr_check_cancel(jid)
            network_bytes += len(chunk)
            pos = 0

            if verified < offset:
                need = min(len(chunk), offset - verified)
                local = local_read.read(need)
                remote_prefix = chunk[:need]

                if len(local) != need or local != remote_prefix:
                    raise RuntimeError(
                        f'Origem sem Range mudou de conteúdo no byte {verified}. '
                        f'O parcial de {_rmpr_human(offset)} foi preservado e '
                        f'não será misturado com outro arquivo.'
                    )

                verified += need
                pos = need

                if verified == offset and not prefix_done_reported:
                    prefix_done_reported = True
                    _rmpr_update(
                        jid,
                        phase='resuming_download',
                        status='running',
                        current_item=target.name,
                        downloaded_bytes=_rmpr_downloaded_total(dest),
                        message=(
                            f'Prefixo de {_rmpr_human(offset)} validado; '
                            f'anexando somente o restante ao arquivo local'
                        ),
                        error='',
                    )

            if pos < len(chunk):
                tail = chunk[pos:]
                local_append.write(tail)
                appended += len(tail)

            now = _rmpr_time.time()
            if now - last_update >= 1.5:
                current_local = offset + appended
                speed = network_bytes / max(0.001, now - start)
                remaining_network = max(0, total - network_bytes) if total else 0
                eta = int(remaining_network / speed) if remaining_network and speed > 1024 else 0

                dyn = globals().get('_RMQM_DYNAMIC')
                if isinstance(dyn, dict):
                    existing = dict(dyn.get(jid) or {})
                    existing.update({
                        'download_expected_bytes': total,
                        'downloaded_bytes_live': current_local,
                        'download_remaining_bytes': max(0, total - current_local) if total else 0,
                        'download_speed_bps': int(speed),
                        'download_eta_seconds': eta,
                        'download_progress_pct': (
                            min(100.0, current_local * 100.0 / total)
                            if total else 0.0
                        ),
                        'no_range_fallback': True,
                        'no_range_verified_bytes': verified,
                        'no_range_network_bytes': network_bytes,
                    })
                    dyn[jid] = existing

                phase = 'validating_prefix' if verified < offset else 'resuming_download'
                if verified < offset:
                    msg = (
                        f'Origem sem Range: validando prefixo '
                        f'{_rmpr_human(verified)} / {_rmpr_human(offset)}'
                    )
                else:
                    msg = (
                        f'Origem sem Range: prefixo validado; arquivo local agora '
                        f'{_rmpr_human(current_local)}'
                        + (f' / {_rmpr_human(total)}' if total else '')
                    )

                _rmpr_update(
                    jid,
                    phase=phase,
                    status='running',
                    current_item=target.name,
                    downloaded_bytes=_rmpr_downloaded_total(dest),
                    message=msg,
                    error='',
                )
                last_update = now

        local_append.flush()
        try:
            _rmpr_os.fsync(local_append.fileno())
        except Exception:
            pass

    if verified < offset:
        raise RuntimeError(
            f'A conexão terminou antes de validar o parcial: '
            f'{_rmpr_human(verified)} de {_rmpr_human(offset)}. '
            f'O parcial foi preservado.'
        )

    final_size = int(target.stat().st_size)
    if total and final_size != total:
        raise RuntimeError(
            f'A conexão terminou antes do arquivo completar: '
            f'{_rmpr_human(final_size)} de {_rmpr_human(total)}. '
            f'O parcial maior foi preservado para a próxima tentativa.'
        )

    if total:
        _RM_PARTIAL_REMOTE_TOTALS[jid] = total

    final_path = _rmpr_final_path(target)
    _RM_PARTIAL_LAST[jid] = {
        'resumed_from_bytes': offset,
        'final_bytes': final_size,
        'remote_total_bytes': total,
        'no_range_fallback': True,
        'network_replayed_prefix_bytes': offset,
        'finished_at': int(_rmpr_time.time()),
    }
    _rmpr_update(
        jid,
        phase='downloading',
        status='running',
        current_item=_RmprPath(final_path).name,
        downloaded_bytes=_rmpr_downloaded_total(dest),
        message=(
            f'Retomada sem Range concluída; parcial local de '
            f'{_rmpr_human(offset)} preservado e restante anexado'
        ),
        error='',
    )
    return final_path


_RMNR_ORIG_STATUS = globals().get('archive_partial_resume_status')
if callable(_RMNR_ORIG_STATUS):
    def archive_partial_resume_status():
        data = dict(_RMNR_ORIG_STATUS() or {})
        data['no_range_fallback'] = True
        data['prefix_byte_validation'] = True
        return data
'''

archive_py.write_text(src + addon, encoding="utf-8")

with tempfile.NamedTemporaryFile(suffix=".pyc") as tmp:
    py_compile.compile(str(archive_py), doraise=True, cfile=tmp.name)

print(
    "Archive no-range fallback OK: HTTP 200 valida prefixo local e anexa restante com segurança"
)
