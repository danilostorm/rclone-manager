#!/usr/bin/env python3
from pathlib import Path
import re, sys, py_compile, tempfile

if len(sys.argv) < 2:
    raise SystemExit('uso: patch-pixeldrain-list.py SOURCE_ROOT')

root = Path(sys.argv[1])
p = root / 'app' / 'drive_links.py'
if not p.exists():
    raise SystemExit('Pixeldrain overlay: app/drive_links.py ausente')

s = p.read_text(encoding='utf-8')
marker = 'RM_PIXELDRAIN_LIST_EXPAND_V1'
if marker not in s:
    # Ensure URL helpers are available even on older live-source installations.
    if not re.search(r'(?m)^from urllib\.parse import .*\burlsplit\b', s):
        imports = re.findall(r'(?m)^from urllib\.parse import ([^\n]+)$', s)
        if imports:
            old = imports[0]
            names = [x.strip() for x in old.split(',') if x.strip()]
            for name in ('urlsplit',):
                if name not in names:
                    names.append(name)
            s = s.replace('from urllib.parse import ' + old, 'from urllib.parse import ' + ', '.join(names), 1)
        else:
            insert_at = 0
            m = re.search(r'(?m)^(?:from __future__ import .*\n)?', s)
            if m:
                insert_at = m.end()
            s = s[:insert_at] + 'from urllib.parse import urlsplit\n' + s[insert_at:]

    # Locate the normalization function by the existing result-limit marker.
    result_limit = s.find('    if len(result) > 2000:\n')
    if result_limit < 0:
        raise SystemExit('Pixeldrain overlay: fim de normalize_items não encontrado')
    def_start = s.rfind('\ndef ', 0, result_limit)
    if def_start < 0:
        raise SystemExit('Pixeldrain overlay: função normalize_items não encontrada')
    sig_end = s.find('\n', def_start + 1)
    if sig_end < 0:
        raise SystemExit('Pixeldrain overlay: assinatura normalize_items inválida')
    signature = s[def_start + 1:sig_end]
    if 'links' not in signature:
        raise SystemExit('Pixeldrain overlay: normalize_items não recebe links')

    helper = r'''

# RM_PIXELDRAIN_LIST_EXPAND_V1
_PIXELDRAIN_LIST_HOSTS = (
    "pixeldrain.com",
    "pixeldrain.net",
    "pixeldra.in",
    "pixeldrain.nl",
    "pixeldrain.biz",
    "pixeldrain.tech",
    "pixeldrain.dev",
)


def _pixeldrain_list_id(raw_url):
    try:
        parsed = urlsplit(str(raw_url or "").strip())
    except Exception:
        return ""
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in _PIXELDRAIN_LIST_HOSTS:
        return ""
    match = re.fullmatch(r"/l/([A-Za-z0-9_-]{4,})/?", parsed.path or "")
    return match.group(1) if match else ""


def _pixeldrain_fetch_list(list_id, preferred_host="pixeldrain.com"):
    hosts = []
    if preferred_host in _PIXELDRAIN_LIST_HOSTS:
        hosts.append(preferred_host)
    hosts.extend(h for h in _PIXELDRAIN_LIST_HOSTS if h not in hosts)
    errors = []
    for host in hosts:
        api_url = f"https://{host}/api/list/{list_id}"
        try:
            response, final_url = _public_request("GET", api_url, stream=True, timeout=(20, 75))
            try:
                if response.status_code != 200:
                    errors.append(f"{host}: HTTP {response.status_code}")
                    continue
                try:
                    data = response.json()
                except Exception:
                    text = _read_html_preview(response, max_bytes=4 * 1024 * 1024)
                    import json as _json
                    data = _json.loads(text)
            finally:
                response.close()
            if not isinstance(data, dict) or not isinstance(data.get("files"), list):
                errors.append(f"{host}: resposta sem files")
                continue
            return data, (urlsplit(final_url).hostname or host)
        except Exception as exc:
            errors.append(f"{host}: {exc}")
    detail = "; ".join(errors[-7:]) or "sem resposta"
    raise RuntimeError(f"Pixeldrain não conseguiu abrir a lista {list_id}: {detail}")


def _expand_pixeldrain_lists(links):
    expanded = []
    for row in (links or []):
        original = dict(row) if isinstance(row, dict) else {"url": str(row or "")}
        raw_url = str(original.get("url") or "").strip()
        list_id = _pixeldrain_list_id(raw_url)
        if not list_id:
            expanded.append(row)
            continue

        preferred = (urlsplit(raw_url).hostname or "pixeldrain.com").lower().rstrip(".")
        data, api_host = _pixeldrain_fetch_list(list_id, preferred)
        files = data.get("files") or []
        if not files:
            raise RuntimeError(f"Pixeldrain: a lista {list_id} está vazia")

        for entry in files:
            if not isinstance(entry, dict):
                continue
            file_id = str(entry.get("id") or "").strip()
            if not re.fullmatch(r"[A-Za-z0-9_-]{4,}", file_id):
                continue
            # Respect Pixeldrain's own availability flag when it is explicit.
            if entry.get("can_download") is False:
                continue
            name = str(entry.get("name") or file_id).strip()
            try:
                size = max(0, int(entry.get("size") or 0))
            except (TypeError, ValueError):
                size = 0
            ext = ""
            if "." in name:
                ext = re.sub(r"[^A-Za-z0-9]", "", name.rsplit(".", 1)[-1])[:12].upper()

            child = dict(original)
            child.update({
                "url": f"https://{api_host}/api/file/{file_id}?download",
                "source_type": "pixeldrain",
                "name": name,
                "label": name,
                "size_bytes": size,
                "file_extension": ext,
                "pixeldrain_list_id": list_id,
                "pixeldrain_file_id": file_id,
            })
            expanded.append(child)

    return expanded
'''

    # Helper goes immediately before normalize_items so it is available at runtime.
    s = s[:def_start] + helper + s[def_start:]

    # Re-locate function after inserting helper, then preprocess input links once.
    result_limit = s.find('    if len(result) > 2000:\n')
    def_start = s.rfind('\ndef ', 0, result_limit)
    sig_end = s.find('\n', def_start + 1)
    insertion = '    links = _expand_pixeldrain_lists(links)\n'
    if insertion not in s[def_start:result_limit]:
        s = s[:sig_end + 1] + insertion + s[sig_end + 1:]

    p.write_text(s, encoding='utf-8')

with tempfile.NamedTemporaryFile(suffix='.pyc') as f:
    py_compile.compile(str(p), doraise=True, cfile=f.name)

print('Pixeldrain overlay OK: /l/<id> -> API list -> arquivos diretos')
