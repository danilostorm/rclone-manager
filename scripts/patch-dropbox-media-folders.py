#!/usr/bin/env python3
from pathlib import Path
import sys
import tempfile
import py_compile

if len(sys.argv) != 2:
    raise SystemExit("uso: patch-dropbox-media-folders.py SOURCE_ROOT")

root = Path(sys.argv[1])
drive_py = root / "app" / "drive_links.py"
if not drive_py.exists():
    raise SystemExit("Dropbox media folders: app/drive_links.py ausente")

src = drive_py.read_text(encoding="utf-8")
if "RM_DROPBOX_MEDIA_FOLDER_EXPAND_V1" in src:
    print("Dropbox media folders: já aplicado")
    raise SystemExit(0)

marker = "    if len(result) > 2000:\n"
limit_pos = src.find(marker)
if limit_pos < 0:
    raise SystemExit("Dropbox media folders: fim de normalize_items não encontrado")

def_start = src.rfind("\ndef ", 0, limit_pos)
if def_start < 0:
    raise SystemExit("Dropbox media folders: normalize_items não encontrado")
sig_end = src.find("\n", def_start + 1)
if sig_end < 0:
    raise SystemExit("Dropbox media folders: assinatura normalize_items inválida")
signature = src[def_start + 1:sig_end]
if "links" not in signature:
    raise SystemExit("Dropbox media folders: normalize_items não recebe links")

helper = r'''

# RM_DROPBOX_MEDIA_FOLDER_EXPAND_V1
# Pastas públicas do Dropbox que contêm mídia são enumeradas antes da
# normalização. Assim MKV/MP4/etc entram na fila normal arquivo por arquivo em
# vez de o Dropbox fabricar um ZIP gigante que exige download + extração local.
#
# Segurança/fallback: se a enumeração falhar, ficar incompleta ou não encontrar
# mídia, o link original é mantido. O comportamento ZIP do Archive Import
# continua disponível para pastas que realmente devem ser tratadas como pacote.
import base64 as _rm_dbx_base64
import html as _rm_dbx_html
import re as _rm_dbx_re
from pathlib import Path as _RmDbxPath
from urllib.parse import (
    parse_qs as _rm_dbx_parse_qs,
    urlencode as _rm_dbx_urlencode,
    urlsplit as _rm_dbx_urlsplit,
    urlunsplit as _rm_dbx_urlunsplit,
)

_RM_DBX_MEDIA_EXTS = {
    '.mkv', '.mp4', '.m4v', '.avi', '.mov', '.wmv', '.webm', '.ts', '.m2ts',
    '.mpg', '.mpeg', '.flv', '.ogv', '.vob', '.iso',
    '.mp3', '.m4a', '.aac', '.flac', '.wav', '.ogg', '.opus', '.wma',
}
_RM_DBX_FILE_EXTS = _RM_DBX_MEDIA_EXTS | {
    '.srt', '.ass', '.ssa', '.sub', '.idx', '.vtt', '.nfo',
    '.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp',
    '.zip', '.rar', '.7z', '.tar', '.gz', '.tgz', '.bz2', '.xz',
    '.txt', '.pdf', '.xml', '.json',
}
_RM_DBX_MAX_ITEMS = 1800
_RM_DBX_MAX_PAGES = 120
_RM_DBX_MAX_DEPTH = 12
_RM_DBX_BROWSER_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.7',
}


def _rm_dbx_is_public_folder(raw_url):
    try:
        p = _rm_dbx_urlsplit(str(raw_url or '').strip())
        host = (p.hostname or '').lower().rstrip('.')
        path = p.path or ''
        return host.endswith('dropbox.com') and (
            '/scl/fo/' in path or path.startswith('/sh/')
        )
    except Exception:
        return False


def _rm_dbx_rlkey(raw_url):
    try:
        q = _rm_dbx_parse_qs(_rm_dbx_urlsplit(str(raw_url or '')).query)
        return str((q.get('rlkey') or [''])[0] or '').strip()
    except Exception:
        return ''


def _rm_dbx_clean_folder_url(raw_url):
    p = _rm_dbx_urlsplit(str(raw_url or '').strip())
    q = _rm_dbx_parse_qs(p.query, keep_blank_values=True)
    out = {}
    rlkey = str((q.get('rlkey') or [''])[0] or '').strip()
    if rlkey:
        out['rlkey'] = rlkey
    out['dl'] = '0'
    return _rm_dbx_urlunsplit((
        'https',
        p.netloc or 'www.dropbox.com',
        p.path,
        _rm_dbx_urlencode(out),
        '',
    ))


def _rm_dbx_download_url(raw_url):
    p = _rm_dbx_urlsplit(str(raw_url or '').strip())
    q = _rm_dbx_parse_qs(p.query, keep_blank_values=True)
    out = {}
    rlkey = str((q.get('rlkey') or [''])[0] or '').strip()
    if rlkey:
        out['rlkey'] = rlkey
    out['dl'] = '1'
    return _rm_dbx_urlunsplit((
        'https',
        p.netloc or 'www.dropbox.com',
        p.path,
        _rm_dbx_urlencode(out),
        '',
    ))


def _rm_dbx_path_tail(raw_url):
    try:
        parts = [x for x in _rm_dbx_urlsplit(str(raw_url or '')).path.split('/') if x]
    except Exception:
        return []
    # /scl/fo/<root-id>/<entry-token>/<path...>
    if len(parts) >= 4 and parts[0:2] == ['scl', 'fo']:
        return parts[4:]
    # Legacy /sh/<token>/<path...>
    if len(parts) >= 2 and parts[0] == 'sh':
        return parts[2:]
    return []


def _rm_dbx_relative_path(child_url, root_url):
    child = _rm_dbx_path_tail(child_url)
    base = _rm_dbx_path_tail(root_url)
    if base and child[:len(base)] == base:
        child = child[len(base):]
    return '/'.join(child).strip('/')


def _rm_dbx_read_page(url):
    response = None
    try:
        response, _final_url = _public_request(
            'GET',
            _rm_dbx_clean_folder_url(url),
            headers=dict(_RM_DBX_BROWSER_HEADERS),
            stream=True,
            timeout=(20, 60),
        )
        if response.status_code != 200:
            raise RuntimeError(f'Dropbox respondeu HTTP {response.status_code}')
        chunks = []
        total = 0
        max_bytes = 8 * 1024 * 1024
        for chunk in response.iter_content(128 * 1024):
            if not chunk:
                continue
            remain = max_bytes - total
            if remain <= 0:
                break
            chunks.append(chunk[:remain])
            total += min(len(chunk), remain)
            if total >= max_bytes:
                break
        return b''.join(chunks).decode(response.encoding or 'utf-8', errors='replace')
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def _rm_dbx_extract_child_urls(page_text, parent_url):
    parent_key = _rm_dbx_rlkey(parent_url)
    raw_page = str(page_text or '')
    blobs = [raw_page.encode('utf-8', errors='ignore')]

    # Dropbox embute os metadados/URLs dos itens em prefetches protobuf
    # codificados em Base64. Decodificar somente tokens razoáveis e que de fato
    # contêm referências Dropbox mantém a análise barata.
    seen_tokens = 0
    for token in _rm_dbx_re.findall(r'[A-Za-z0-9+/]{120,}={0,2}', raw_page):
        if seen_tokens >= 800:
            break
        seen_tokens += 1
        if len(token) > 2_000_000:
            continue
        try:
            padded = token + ('=' * ((-len(token)) % 4))
            data = _rm_dbx_base64.b64decode(padded, validate=False)
        except Exception:
            continue
        if b'dropbox.com' in data and (b'/scl/fo/' in data or b'/sh/' in data):
            blobs.append(data)

    # Deliberadamente termina antes de "?" e reconstrói somente os parâmetros
    # necessários. Isso evita engolir bytes do protobuf que às vezes são ASCII.
    url_rx = _rm_dbx_re.compile(
        rb'https://(?:www\.)?dropbox\.com/'
        rb'(?:scl/fo/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+|sh/[A-Za-z0-9_-]+)'
        rb'(?:/[A-Za-z0-9._~!$&()*+,;=:@%+\-]+)*'
    )

    parent_path = _rm_dbx_urlsplit(_rm_dbx_clean_folder_url(parent_url)).path.rstrip('/')
    found = []
    seen = set()
    for blob in blobs:
        for match in url_rx.finditer(blob):
            base = _rm_dbx_html.unescape(match.group(0).decode('utf-8', errors='ignore'))
            try:
                p = _rm_dbx_urlsplit(base)
            except Exception:
                continue
            if not p.path:
                continue
            key = parent_key
            if not key:
                tail = blob[match.end():match.end() + 300].decode('latin1', errors='ignore')
                km = _rm_dbx_re.search(r'rlkey=([A-Za-z0-9_-]{16,64})', tail)
                if km:
                    key = km.group(1)
            q = {'dl': '0'}
            if key:
                q['rlkey'] = key
            clean = _rm_dbx_urlunsplit(('https', p.netloc or 'www.dropbox.com', p.path, _rm_dbx_urlencode(q), ''))
            clean_path = p.path.rstrip('/')
            if clean_path == parent_path:
                continue
            canonical = (clean_path, key)
            if canonical in seen:
                continue
            seen.add(canonical)
            found.append(clean)
    return found


def _rm_dbx_suffix(raw_url):
    rel = _rm_dbx_path_tail(raw_url)
    if not rel:
        return ''
    try:
        return _RmDbxPath(rel[-1]).suffix.lower()
    except Exception:
        return ''


def _rm_dbx_enumerate_media_folder(root_url):
    queue = [(root_url, 0)]
    visited = set()
    files = []
    failed = False
    truncated = False
    pages = 0

    while queue:
        current, depth = queue.pop(0)
        clean = _rm_dbx_clean_folder_url(current)
        key = _rm_dbx_urlsplit(clean).path.rstrip('/')
        if key in visited:
            continue
        visited.add(key)

        if depth > _RM_DBX_MAX_DEPTH or pages >= _RM_DBX_MAX_PAGES:
            truncated = True
            break

        try:
            page = _rm_dbx_read_page(clean)
            pages += 1
            children = _rm_dbx_extract_child_urls(page, clean)
        except Exception:
            failed = True
            break

        # Uma URL sem extensão que não possui filhos pode ser um arquivo com
        # nome incomum; preserve-a como item, exceto a própria raiz.
        if not children and clean != _rm_dbx_clean_folder_url(root_url):
            files.append(clean)
            continue

        for child in children:
            ext = _rm_dbx_suffix(child)
            if ext in _RM_DBX_FILE_EXTS:
                files.append(child)
            elif depth + 1 <= _RM_DBX_MAX_DEPTH:
                queue.append((child, depth + 1))
            else:
                truncated = True

            if len(files) >= _RM_DBX_MAX_ITEMS:
                truncated = True
                break
        if truncated:
            break

    if failed or truncated:
        return []

    # Só muda o modo da pasta quando existe mídia real. Pastas sem vídeo/áudio
    # continuam no fallback antigo de ZIP do Dropbox/Archive Import.
    if not any(_rm_dbx_suffix(url) in _RM_DBX_MEDIA_EXTS for url in files):
        return []

    deduped = []
    seen = set()
    for url in files:
        p = _rm_dbx_urlsplit(url)
        ident = p.path.rstrip('/')
        if ident in seen:
            continue
        seen.add(ident)
        deduped.append(url)
    return deduped


def _rm_dbx_expand_public_folders(links):
    expanded = []
    for entry in (links or []):
        original = dict(entry) if isinstance(entry, dict) else {'url': str(entry or '')}
        raw_url = str(original.get('url') or original.get('href') or '').strip()

        if not _rm_dbx_is_public_folder(raw_url):
            expanded.append(entry)
            continue

        try:
            children = _rm_dbx_enumerate_media_folder(raw_url)
        except Exception:
            children = []

        if not children:
            # Fallback conservador: o Archive Import ainda pode baixar a pasta
            # como ZIP exatamente como nas versões anteriores.
            expanded.append(entry)
            continue

        for child_url in children:
            rel = _rm_dbx_relative_path(child_url, raw_url)
            if not rel:
                rel = _RmDbxPath(_rm_dbx_urlsplit(child_url).path).name
            filename = _RmDbxPath(rel).name
            ext = _RmDbxPath(filename).suffix.lower()

            child = dict(original)
            child.update({
                'url': _rm_dbx_download_url(child_url),
                'source_type': 'dropbox',
                'name': filename,
                'label': rel,
                'relative_path': rel,
                'file_extension': ext.lstrip('.').upper()[:12],
                'dropbox_folder_expanded': True,
                'dropbox_parent_url': raw_url,
            })
            expanded.append(child)

    return expanded
'''

src = src[:def_start] + helper + src[def_start:]

# Re-localize normalize_items after inserting helper, then expand input once.
limit_pos = src.find(marker)
def_start = src.rfind("\ndef ", 0, limit_pos)
sig_end = src.find("\n", def_start + 1)
inject = "    links = _rm_dbx_expand_public_folders(links)\n"
if inject not in src[def_start:limit_pos]:
    src = src[:sig_end + 1] + inject + src[sig_end + 1:]

drive_py.write_text(src, encoding="utf-8")
with tempfile.NamedTemporaryFile(suffix=".pyc") as f:
    py_compile.compile(str(drive_py), doraise=True, cfile=f.name)

print(
    "Dropbox media folders OK: pasta pública com mídia -> itens normais; "
    "fallback ZIP preservado"
)
