#!/usr/bin/env python3
from pathlib import Path
import re, sys, py_compile, tempfile

if len(sys.argv) < 2:
    raise SystemExit('uso: patch-duplicate-history.py SOURCE_ROOT')
root = Path(sys.argv[1])
appdir = root / 'app'

def need(cond, msg):
    if not cond:
        raise SystemExit(msg)

# ---------------------------------------------------------------------------
# db.py: persistent per-link import history. This survives clearing job history.
# ---------------------------------------------------------------------------
p = appdir / 'db.py'
need(p.exists(), 'duplicate history overlay: app/db.py ausente')
s = p.read_text(encoding='utf-8')

if 'RM_DRIVE_LINK_HISTORY_V1' not in s:
    if not re.search(r'(?m)^import json$', s):
        s = s.replace('import os\n', 'import os\nimport json\n', 1)
    if not re.search(r'(?m)^import re$', s):
        s = s.replace('import os\n', 'import os\nimport re\n', 1)
    if 'from urllib.parse import ' not in s:
        marker = 'from datetime import datetime, timezone, timedelta\n'
        need(marker in s, 'duplicate history overlay: imports db.py inesperados')
        s = s.replace(marker, marker + 'from urllib.parse import parse_qsl, urlencode, unquote, urlsplit, urlunsplit\n', 1)

    marker = '\ndef create_drive_link_job('
    pos = s.find(marker)
    need(pos >= 0, 'duplicate history overlay: create_drive_link_job ausente')
    block = r'''

# RM_DRIVE_LINK_HISTORY_V1
_TRACKING_QUERY_KEYS = {"fbclid", "gclid", "dclid", "mc_cid", "mc_eid"}
_GOOGLE_LINK_ID_RES = (
    re.compile(r"/(?:file|document|spreadsheets|presentation|forms)/d/([A-Za-z0-9_-]{10,})", re.I),
    re.compile(r"/(?:drive/)?folders/([A-Za-z0-9_-]{10,})", re.I),
)


def _ensure_drive_link_history(db):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS drive_link_history (
            link_key TEXT PRIMARY KEY,
            url TEXT NOT NULL DEFAULT '',
            source_type TEXT NOT NULL DEFAULT '',
            label TEXT NOT NULL DEFAULT '',
            destination_slug TEXT NOT NULL DEFAULT '',
            destination_path TEXT NOT NULL DEFAULT '',
            job_id INTEGER NOT NULL DEFAULT 0,
            imported_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_drive_link_history_imported_at ON drive_link_history(imported_at)")


def _unwrap_href_li(raw):
    try:
        parts = urlsplit(str(raw or '').strip())
    except Exception:
        return str(raw or '').strip()
    if (parts.hostname or '').lower() != 'href.li':
        return str(raw or '').strip()
    target = parts.query or ''
    for _ in range(3):
        try:
            decoded = unquote(target)
        except Exception:
            break
        if decoded == target:
            break
        target = decoded
    return target if target.lower().startswith(('http://', 'https://')) else str(raw or '').strip()


def drive_link_history_key(item):
    item = item if isinstance(item, dict) else {"url": str(item or '')}
    source = str(item.get('source_type') or item.get('source') or '').strip().lower()
    raw = _unwrap_href_li(str(item.get('url') or '').strip())
    item_id = str(item.get('id') or item.get('item_id') or '').strip()
    try:
        parts = urlsplit(raw)
    except Exception:
        parts = None

    if source == 'google_drive' or (parts and (parts.hostname or '').lower() in {'drive.google.com', 'docs.google.com', 'drive.usercontent.google.com'}):
        gid = item_id
        if not gid and parts:
            for rx in _GOOGLE_LINK_ID_RES:
                m = rx.search(parts.path or '')
                if m:
                    gid = m.group(1)
                    break
            if not gid:
                gid = dict(parse_qsl(parts.query, keep_blank_values=True)).get('id', '')
        if re.fullmatch(r'[A-Za-z0-9_-]{10,}', gid or ''):
            return 'google_drive:' + gid

    if not parts or not parts.scheme or not parts.netloc:
        return (source or 'link') + ':' + raw.strip()

    scheme = parts.scheme.lower()
    host = (parts.hostname or '').lower().rstrip('.')
    port = parts.port
    netloc = host + (f':{port}' if port and not ((scheme == 'https' and port == 443) or (scheme == 'http' and port == 80)) else '')
    path = re.sub(r'/+', '/', parts.path or '/')
    if path != '/':
        path = path.rstrip('/')

    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        low = key.lower()
        if low.startswith('utm_') or low in _TRACKING_QUERY_KEYS:
            continue
        if host.endswith('dropbox.com') and low in {'dl', 'raw'}:
            continue
        query.append((key, value))
    query.sort(key=lambda x: (x[0].lower(), x[1]))
    canonical = urlunsplit((scheme, netloc, path, urlencode(query, doseq=True), ''))
    return (source or 'link') + ':' + canonical


def _history_insert(db, job_id, item, destination_slug='', destination_path='', imported_at=''):
    key = drive_link_history_key(item)
    if not key or key.endswith(':'):
        return
    db.execute(
        """
        INSERT INTO drive_link_history(link_key,url,source_type,label,destination_slug,destination_path,job_id,imported_at)
        VALUES(?,?,?,?,?,?,?,?)
        ON CONFLICT(link_key) DO UPDATE SET
            url=excluded.url,
            source_type=excluded.source_type,
            label=excluded.label,
            destination_slug=excluded.destination_slug,
            destination_path=excluded.destination_path,
            job_id=excluded.job_id,
            imported_at=excluded.imported_at
        """,
        (
            key,
            str((item or {}).get('url') or '')[:4000],
            str((item or {}).get('source_type') or (item or {}).get('source') or '')[:80],
            str((item or {}).get('name') or (item or {}).get('label') or '')[:500],
            str(destination_slug or '')[:120],
            str(destination_path or '')[:1200],
            int(job_id or 0),
            str(imported_at or utcnow()),
        ),
    )


def record_drive_link_history(job_id, item, destination_slug='', destination_path=''):
    with db_conn() as db:
        _ensure_drive_link_history(db)
        _history_insert(db, job_id, item, destination_slug, destination_path, utcnow())


def _backfill_drive_link_history(db):
    _ensure_drive_link_history(db)
    rows = db.execute(
        "SELECT id,destination_slug,resolved_destination_path,destination_path,items_json,completed_items,finished_at,updated_at "
        "FROM drive_link_jobs WHERE completed_items > 0 ORDER BY id ASC"
    ).fetchall()
    for row in rows:
        try:
            items = json.loads(row['items_json'] or '[]')
        except Exception:
            continue
        done = max(0, min(int(row['completed_items'] or 0), len(items)))
        when = row['finished_at'] or row['updated_at'] or utcnow()
        dest = row['resolved_destination_path'] or row['destination_path'] or ''
        for item in items[:done]:
            if isinstance(item, dict):
                _history_insert(db, row['id'], item, row['destination_slug'] or '', dest, when)


def check_drive_link_history(items):
    requested = [x if isinstance(x, dict) else {"url": str(x or '')} for x in (items or [])][:500]
    keys = [drive_link_history_key(x) for x in requested]
    with db_conn() as db:
        _backfill_drive_link_history(db)
        unique = [x for x in dict.fromkeys(keys) if x]
        found = {}
        if unique:
            placeholders = ','.join('?' for _ in unique)
            for row in db.execute(
                f"SELECT * FROM drive_link_history WHERE link_key IN ({placeholders})",
                unique,
            ):
                found[row['link_key']] = dict(row)
    matches = []
    for index, (item, key) in enumerate(zip(requested, keys)):
        row = found.get(key)
        matches.append({
            "index": index,
            "url": str(item.get('url') or ''),
            "duplicate": bool(row),
            "job_id": int((row or {}).get('job_id') or 0),
            "imported_at": str((row or {}).get('imported_at') or ''),
            "destination_slug": str((row or {}).get('destination_slug') or ''),
            "destination_path": str((row or {}).get('destination_path') or ''),
            "label": str((row or {}).get('label') or ''),
        })
    return matches
'''
    s = s[:pos] + block + s[pos:]
    p.write_text(s, encoding='utf-8')

p = appdir / 'drive_links.py'
need(p.exists(), 'duplicate history overlay: app/drive_links.py ausente')
s = p.read_text(encoding='utf-8')
if 'record_drive_link_history,' not in s:
    marker = '    get_drive_link_job,\n'
    need(marker in s, 'duplicate history overlay: import get_drive_link_job ausente')
    s = s.replace(marker, marker + '    record_drive_link_history,\n', 1)

if 'RM_RECORD_DRIVE_LINK_HISTORY_V1' not in s:
    marker = '                completed += 1\n'
    need(marker in s, 'duplicate history overlay: completed += 1 ausente')
    block = '''                # RM_RECORD_DRIVE_LINK_HISTORY_V1\n                try:\n                    record_drive_link_history(job_id, item, slug, destination_path)\n                except Exception:\n                    pass\n'''
    s = s.replace(marker, block + marker, 1)
    p.write_text(s, encoding='utf-8')

p = appdir / 'app.py'
need(p.exists(), 'duplicate history overlay: app/app.py ausente')
s = p.read_text(encoding='utf-8')
if '    check_drive_link_history,\n' not in s:
    marker = '    create_drive_link_job,\n'
    need(marker in s, 'duplicate history overlay: import create_drive_link_job ausente')
    s = s.replace(marker, marker + '    check_drive_link_history,\n', 1)

s = s.replace('"api": "drive-link-v12"', '"api": "drive-link-v13"')

if 'def extension_api_history_check(' not in s:
    marker = '\n@app.route("/api/v1/extension/analyze", methods=["POST", "OPTIONS"])\n'
    pos = s.find(marker)
    need(pos >= 0, 'duplicate history overlay: endpoint analyze ausente')
    block = '''\n@app.route("/api/v1/extension/history/check", methods=["POST", "OPTIONS"])\n@extension_api_required\ndef extension_api_history_check():\n    payload = request.get_json(silent=True) or {}\n    links = payload.get("links") or []\n    if not isinstance(links, list):\n        return jsonify({"ok": False, "error": "links deve ser uma lista"}), 400\n    matches = check_drive_link_history(links[:500])\n    return jsonify({\n        "ok": True,\n        "matches": matches,\n        "duplicates": sum(1 for x in matches if x.get("duplicate")),\n    })\n\n'''
    s = s[:pos] + block + s[pos:]
    p.write_text(s, encoding='utf-8')

for q in (appdir/'db.py', appdir/'drive_links.py', appdir/'app.py'):
    with tempfile.NamedTemporaryFile(suffix='.pyc') as f:
        py_compile.compile(str(q), doraise=True, cfile=f.name)
print('Duplicate history overlay OK: persistent link history + extension API v13')
