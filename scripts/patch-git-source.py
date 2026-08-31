#!/usr/bin/env python3
from pathlib import Path
import re, sys, py_compile, tempfile

if len(sys.argv) < 2:
    raise SystemExit('uso: patch-git-source.py SOURCE_ROOT [VERSION]')
root = Path(sys.argv[1])
version = sys.argv[2] if len(sys.argv) > 2 else ''
appdir = root / 'app'

def need(cond, msg):
    if not cond:
        raise SystemExit(msg)

# --- drive_links.py: providers + metadata hints ---
p = appdir / 'drive_links.py'
need(p.exists(), 'Git overlay: app/drive_links.py ausente')
s = p.read_text(encoding='utf-8')

if 'AKIRABOX_SUFFIXES' not in s:
    m = re.search(r'(?m)^PIXELDRAIN_SUFFIXES\s*=.*\n', s)
    need(m, 'Git overlay: PIXELDRAIN_SUFFIXES ausente')
    s = s[:m.end()] + 'AKIRABOX_SUFFIXES = ("akirabox.to", "akirabox.com")\nBUZZHEAVIER_SUFFIXES = ("buzzheavier.com", "bzzhr.co", "bzzhr.to")\n' + s[m.end():]

if 'return "akirabox"' not in s:
    pat = re.compile(r'(?m)^(\s*)if _host_matches\(host, PIXELDRAIN_SUFFIXES\):\n\1    return "pixeldrain"\n')
    m = pat.search(s)
    need(m, 'Git overlay: classify pixeldrain ausente')
    indent = m.group(1)
    extra = (
        f'{indent}if _host_matches(host, AKIRABOX_SUFFIXES):\n{indent}    return "akirabox"\n'
        f'{indent}if _host_matches(host, BUZZHEAVIER_SUFFIXES):\n{indent}    return "buzzheavier"\n'
    )
    s = s[:m.end()] + extra + s[m.end():]

s = s.replace(
    'Link não reconhecido como Google Drive, OneDrive/SharePoint, MediaFire, Dropbox, Pixeldrain ou arquivo direto',
    'Link não reconhecido como Google Drive, OneDrive/SharePoint, MediaFire, Dropbox, Pixeldrain, AkiraBox, BuzzHeavier ou arquivo direto',
)

resolver_code = r'''

def _read_html_preview(response, max_bytes=2 * 1024 * 1024):
    chunks, total = [], 0
    for chunk in response.iter_content(64 * 1024):
        if not chunk:
            continue
        remain = max_bytes - total
        if remain <= 0:
            break
        chunks.append(chunk[:remain])
        total += min(len(chunk), remain)
        if total >= max_bytes:
            break
    return b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")


def _resolve_buzzheavier(url):
    response, page_url = _public_request("GET", url, stream=True, timeout=(25, 75))
    try:
        if response.status_code != 200:
            raise RuntimeError(f"BuzzHeavier respondeu HTTP {response.status_code}")
        text = _read_html_preview(response)
    finally:
        response.close()

    patterns = [
        r'hx-get=["\']([^"\']*/download[^"\']*)["\']',
        r'href=["\']([^"\']*/download[^"\']*)["\'][^>]*hx-',
    ]
    download_href = ""
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.S)
        if match:
            download_href = html.unescape(match.group(1)).strip()
            break
    if not download_href:
        raise RuntimeError("Não foi possível localizar o endpoint de download do BuzzHeavier")

    endpoint = _validate_public_http_url(urljoin(page_url, download_href))
    headers = {
        "HX-Request": "true",
        "HX-Current-URL": page_url,
        "Referer": page_url,
        "Range": "bytes=0-0",
    }
    response, final_url = _public_request("GET", endpoint, headers=headers, stream=True, timeout=(25, 90))
    try:
        hx_redirect = (response.headers.get("HX-Redirect") or response.headers.get("Hx-Redirect") or "").strip()
        if hx_redirect:
            return _validate_public_http_url(urljoin(page_url, hx_redirect))
        if response.status_code not in {200, 206}:
            raise RuntimeError(f"BuzzHeavier download respondeu HTTP {response.status_code}")
        ctype = (response.headers.get("Content-Type") or "").lower()
        dispo = (response.headers.get("Content-Disposition") or "").lower()
        if "text/html" in ctype and "attachment" not in dispo:
            raise RuntimeError("BuzzHeavier não retornou o redirect do arquivo")
        return _validate_public_http_url(final_url)
    finally:
        response.close()


def _resolve_akirabox(url):
    response, page_url = _public_request("GET", url, stream=True, timeout=(25, 75))
    try:
        if response.status_code != 200:
            raise RuntimeError(f"AkiraBox respondeu HTTP {response.status_code}")
        text = _read_html_preview(response)
    finally:
        response.close()

    patterns = [
        r'id=["\']download-button["\'][^>]*href=["\']([^"\']+)',
        r'href=["\']([^"\']+)["\'][^>]*id=["\']download-button["\']',
    ]
    download_href = ""
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.S)
        if match:
            download_href = html.unescape(match.group(1)).strip()
            break
    if not download_href:
        if "cf-chl-" in text.lower() or "just a moment" in text.lower() or "um momento" in text.lower():
            raise RuntimeError("AkiraBox exigiu verificação Cloudflare; abra o arquivo no navegador e tente novamente")
        raise RuntimeError("Não foi possível localizar o botão de download público do AkiraBox")

    referer = page_url
    fm = re.search(r'fileUrl\s*[:=]\s*["\']([^"\']+)', text, re.I)
    if fm:
        try:
            referer = _validate_public_http_url(urljoin(page_url, html.unescape(fm.group(1))))
        except Exception:
            referer = page_url

    download_url = _validate_public_http_url(urljoin(page_url, download_href))
    response, final_url = _public_request(
        "GET", download_url,
        headers={"Referer": referer, "Range": "bytes=0-0"},
        stream=True, timeout=(25, 90),
    )
    try:
        if response.status_code not in {200, 206}:
            raise RuntimeError(f"AkiraBox download respondeu HTTP {response.status_code}")
        ctype = (response.headers.get("Content-Type") or "").lower()
        dispo = (response.headers.get("Content-Disposition") or "").lower()
        if "text/html" in ctype and "attachment" not in dispo:
            raise RuntimeError("AkiraBox abriu uma página HTML em vez do arquivo")
        return _validate_public_http_url(final_url)
    finally:
        response.close()
'''

if 'def _resolve_buzzheavier(' not in s:
    marker = '\ndef _probe_download_url('
    pos = s.find(marker)
    need(pos >= 0, 'Git overlay: _probe_download_url ausente')
    s = s[:pos] + resolver_code + s[pos:]

if 'source_type == "akirabox"' not in s:
    pat = re.compile(r'(?m)^(\s*)elif source_type == "pixeldrain":\n\1    source_url = _rewrite_pixeldrain\(source_url\)\n')
    m = pat.search(s)
    need(m, 'Git overlay: branch pixeldrain em _remote_probe ausente')
    indent = m.group(1)
    extra = (
        f'{indent}elif source_type == "akirabox":\n{indent}    source_url = _resolve_akirabox(source_url)\n'
        f'{indent}elif source_type == "buzzheavier":\n{indent}    source_url = _resolve_buzzheavier(source_url)\n'
    )
    s = s[:m.end()] + extra + s[m.end():]

if 'RM_EXTENSION_METADATA_HINTS_V1' not in s:
    marker = '    if len(result) > 2000:\n'
    need(marker in s, 'Git overlay: fim de normalize_items ausente')
    block = '''    # RM_EXTENSION_METADATA_HINTS_V1\n    _extension_hints = {}\n    for _row in links:\n        if not isinstance(_row, dict):\n            continue\n        _url = str(_row.get("url") or "").strip()\n        if not _url:\n            continue\n        try:\n            _size = max(0, int(_row.get("size_bytes") or 0))\n        except (TypeError, ValueError):\n            _size = 0\n        _size_text = str(_row.get("size_text") or "").strip()[:80]\n        _ext = re.sub(r"[^A-Za-z0-9]", "", str(_row.get("file_extension") or ""))[:12].upper()\n        _extension_hints[_url] = (_size, _size_text, _ext)\n    for _item in result:\n        if not isinstance(_item, dict):\n            continue\n        _hint = _extension_hints.get(str(_item.get("url") or "").strip())\n        if not _hint:\n            continue\n        _size, _size_text, _ext = _hint\n        if _size and not int(_item.get("size_bytes") or 0):\n            _item["size_bytes"] = _size\n        if _size_text:\n            _item["size_text"] = _size_text\n        if _ext:\n            _item["file_extension"] = _ext\n        elif not _item.get("file_extension"):\n            _name = str(_item.get("name") or _item.get("label") or "")\n            _item["file_extension"] = Path(_name).suffix.lstrip(".").upper()[:12]\n\n'''
    s = s.replace(marker, block + marker, 1)

p.write_text(s, encoding='utf-8')

# --- app.py: expose metadata in task manager and align visible version ---
p = appdir / 'app.py'
need(p.exists(), 'Git overlay: app/app.py ausente')
s = p.read_text(encoding='utf-8')
if version:
    s = re.sub(r'(?m)^APP_VERSION\s*=\s*["\'][^"\']+["\']', f'APP_VERSION = "{version}"', s, count=1)

if 'RM_TASK_METADATA_V1' not in s:
    marker = '    row.pop("items_json", None)\n'
    if marker in s:
        block = '''    # RM_TASK_METADATA_V1\n    _valid_items = [x for x in items if isinstance(x, dict)]\n    def _rm_item_meta(x):\n        _label = (x.get("name") or x.get("label") or x.get("url") or "item")[:220]\n        try:\n            _size = max(0, int(x.get("size_bytes") or 0))\n        except (TypeError, ValueError):\n            _size = 0\n        _ext = re.sub(r"[^A-Za-z0-9]", "", str(x.get("file_extension") or ""))[:12].upper()\n        if not _ext:\n            _ext = Path(_label).suffix.lstrip(".").upper()[:12]\n        return {\n            "label": _label,\n            "source_type": x.get("source_type") or "google_drive",\n            "url": (x.get("url") or "")[:2000],\n            "size_bytes": _size,\n            "size_text": str(x.get("size_text") or "")[:80],\n            "file_extension": _ext,\n        }\n    if include_items:\n        row["items_preview"] = [_rm_item_meta(x) for x in _valid_items[:250]]\n    row["total_size_bytes"] = sum(_rm_item_meta(x)["size_bytes"] for x in _valid_items)\n    row["known_size_items"] = sum(1 for x in _valid_items if _rm_item_meta(x)["size_bytes"] > 0)\n    row["extensions"] = sorted({m["file_extension"] for m in (_rm_item_meta(x) for x in _valid_items) if m["file_extension"]})\n'''
        s = s.replace(marker, block + marker, 1)

p.write_text(s, encoding='utf-8')

# --- API manager template: individual + total metadata, best effort/idempotent ---
p = appdir / 'templates' / 'api_manager.html'
if p.exists():
    t = p.read_text(encoding='utf-8')
    t = t.replace(
        'Google Drive usa cópia server-side. OneDrive/SharePoint/MediaFire/links diretos usam download → upload → confirmação → limpeza.',
        'Google Drive usa cópia server-side. OneDrive/SharePoint/MediaFire/Dropbox/Pixeldrain/AkiraBox/BuzzHeavier e links diretos usam download → upload → confirmação → limpeza.'
    )
    if 'j.total_size_bytes' not in t:
        old = '{% if j.items_preview %}<details class="api-details"><summary>{{ j.total_items }} link(s)</summary><div class="api-link-list">{% for item in j.items_preview %}<div><span class="type">{{ item.source_type }}</span> {{ item.label }}</div>{% endfor %}</div></details>{% endif %}'
        new = '{% if j.items_preview %}<details class="api-details"><summary>{{ j.total_items }} item(s){% if j.total_size_bytes %} · {{ \'%.2f\'|format(j.total_size_bytes/1073741824) }} GB{% endif %}</summary><div class="muted" style="margin:5px 0">Tamanho conhecido: {{ j.known_size_items }}/{{ j.total_items }}{% if j.extensions %} · Extensões: {{ j.extensions|join(\', \') }}{% endif %}</div><div class="api-link-list">{% for item in j.items_preview %}<div><span class="type">{{ item.source_type }}</span>{% if item.file_extension %} <span class="type">{{ item.file_extension }}</span>{% endif %} {{ item.label }}{% if item.size_bytes %} <span class="muted">· {{ \'%.1f\'|format(item.size_bytes/1048576) }} MiB</span>{% elif item.size_text %} <span class="muted">· {{ item.size_text }}</span>{% endif %}</div>{% endfor %}</div></details>{% endif %}'
        if old in t:
            t = t.replace(old, new, 1)
    p.write_text(t, encoding='utf-8')

p = appdir / 'templates' / 'settings.html'
if p.exists():
    t = p.read_text(encoding='utf-8')
    t = t.replace('OneDrive/SharePoint, MediaFire, Dropbox, Pixeldrain e arquivos HTTP/HTTPS diretos', 'OneDrive/SharePoint, MediaFire, Dropbox, Pixeldrain, AkiraBox, BuzzHeavier e arquivos HTTP/HTTPS diretos')
    p.write_text(t, encoding='utf-8')

for q in (appdir/'drive_links.py', appdir/'app.py'):
    with tempfile.NamedTemporaryFile(suffix='.pyc') as f:
        py_compile.compile(str(q), doraise=True, cfile=f.name)
print('Git overlay OK: AkiraBox + BuzzHeavier + metadata')
