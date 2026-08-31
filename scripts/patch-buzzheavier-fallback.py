#!/usr/bin/env python3
from pathlib import Path
import re, sys, py_compile, tempfile

if len(sys.argv) < 2:
    raise SystemExit('uso: patch-buzzheavier-fallback.py SOURCE_ROOT')
root = Path(sys.argv[1])
p = root / 'app' / 'drive_links.py'
if not p.exists():
    raise SystemExit('BuzzHeavier overlay: app/drive_links.py ausente')

s = p.read_text(encoding='utf-8')
marker = 'RM_BUZZHEAVIER_MIRROR_FALLBACK_V1'
if marker not in s:
    pat = re.compile(r'(?s)\ndef _resolve_buzzheavier\(url\):.*?\n\ndef _resolve_akirabox\(url\):')
    m = pat.search(s)
    if not m:
        raise SystemExit('BuzzHeavier overlay: _resolve_buzzheavier/_resolve_akirabox não encontrados')

    replacement = r'''
# RM_BUZZHEAVIER_MIRROR_FALLBACK_V1
_BUZZHEAVIER_MIRRORS = ("buzzheavier.com", "bzzhr.co", "bzzhr.to")
_BUZZHEAVIER_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


def _buzzheavier_candidates(url):
    original = _validate_public_http_url(url)
    parts = urlsplit(original)
    host = (parts.hostname or "").lower()
    hosts = []
    if host in _BUZZHEAVIER_MIRRORS:
        hosts.append(host)
    hosts.extend(h for h in _BUZZHEAVIER_MIRRORS if h not in hosts)
    # The mirrors share the same public file id/path. Keep query parameters,
    # but always use HTTPS and discard fragments.
    return [urlunsplit(("https", h, parts.path or "/", parts.query, "")) for h in hosts]


def _resolve_buzzheavier(url):
    errors = []
    for candidate in _buzzheavier_candidates(url):
        try:
            response, page_url = _public_request(
                "GET", candidate,
                headers=dict(_BUZZHEAVIER_BROWSER_HEADERS),
                stream=True, timeout=(20, 60),
            )
            try:
                if response.status_code != 200:
                    errors.append(f"{urlsplit(candidate).hostname}: página HTTP {response.status_code}")
                    continue
                text = _read_html_preview(response)
                # Preserve same-origin cookies when the mirror supplies any.
                cookies = response.cookies.get_dict() if getattr(response, "cookies", None) is not None else {}
            finally:
                response.close()

            patterns = [
                r'hx-get=["\']([^"\']*/download[^"\']*)["\']',
                r'href=["\']([^"\']*/download[^"\']*)["\'][^>]*hx-',
                r'href=["\']([^"\']*/download[^"\']*)["\']',
            ]
            download_href = ""
            for pattern in patterns:
                match = re.search(pattern, text, re.I | re.S)
                if match:
                    download_href = html.unescape(match.group(1)).strip()
                    break
            if not download_href:
                errors.append(f"{urlsplit(candidate).hostname}: endpoint /download não encontrado")
                continue

            endpoint = _validate_public_http_url(urljoin(page_url, download_href))
            headers = dict(_BUZZHEAVIER_BROWSER_HEADERS)
            headers.update({
                "HX-Request": "true",
                "HX-Current-URL": page_url,
                "Referer": page_url,
                "Accept": "*/*",
            })
            if cookies:
                headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())

            response, final_url = _public_request(
                "GET", endpoint,
                headers=headers,
                stream=True, timeout=(20, 75),
            )
            try:
                hx_redirect = (response.headers.get("HX-Redirect") or response.headers.get("Hx-Redirect") or "").strip()
                location = (response.headers.get("Location") or response.headers.get("location") or "").strip()
                if hx_redirect:
                    return _validate_public_http_url(urljoin(page_url, hx_redirect))
                if location:
                    return _validate_public_http_url(urljoin(endpoint, location))
                if response.status_code not in {200, 206}:
                    errors.append(f"{urlsplit(candidate).hostname}: download HTTP {response.status_code}")
                    continue
                ctype = (response.headers.get("Content-Type") or "").lower()
                dispo = (response.headers.get("Content-Disposition") or "").lower()
                if "text/html" in ctype and "attachment" not in dispo:
                    errors.append(f"{urlsplit(candidate).hostname}: resposta HTML sem HX-Redirect")
                    continue
                return _validate_public_http_url(final_url)
            finally:
                response.close()
        except Exception as exc:
            errors.append(f"{urlsplit(candidate).hostname}: {exc}")

    detail = "; ".join(errors[-6:]) or "sem resposta dos mirrors"
    raise RuntimeError(f"BuzzHeavier bloqueou/recusou os mirrors disponíveis: {detail}")


def _resolve_akirabox(url):'''
    s = s[:m.start()] + '\n' + replacement + s[m.end():]
    p.write_text(s, encoding='utf-8')

with tempfile.NamedTemporaryFile(suffix='.pyc') as f:
    py_compile.compile(str(p), doraise=True, cfile=f.name)
print('BuzzHeavier overlay OK: browser headers + mirror fallback')
