#!/usr/bin/env python3
from pathlib import Path
import re, sys, py_compile, tempfile

if len(sys.argv) != 2:
    raise SystemExit('uso: patch-archive-auth-compat.py SOURCE_ROOT')
root = Path(sys.argv[1])
appdir = root / 'app'
app_py = appdir / 'app.py'
api_template = appdir / 'templates' / 'api_manager.html'
settings_template = appdir / 'templates' / 'settings.html'
if not app_py.exists():
    raise SystemExit('Archive auth compat: app/app.py ausente')

s = app_py.read_text(encoding='utf-8')
if 'RM_ARCHIVE_IMPORT_ROUTES_V1' not in s:
    raise SystemExit('Archive auth compat: rotas seguras da extensão não foram aplicadas')


def _auth_score(line):
    low = line.lower()
    if 'extension_api_required' in low or low.startswith('@app.'):
        return -100
    score = 0
    for word, points in (
        ('login', 8), ('auth', 7), ('admin', 6), ('require', 5),
        ('protect', 4), ('session', 3), ('user', 2),
    ):
        if word in low:
            score += points
    for word in ('csrf', 'limiter', 'cache', 'rate', 'cors'):
        if word in low:
            score -= 5
    return score


def _detect_route_guard(text):
    # Current HA builds changed the decorator name over time. Reuse an existing
    # guard from a protected HTML page instead of assuming login_required.
    rx = re.compile(
        r'(?m)^@app\.route\((?P<route>[^\n]+)\)\n'
        r'(?P<decorators>(?:@[A-Za-z_][^\n]*\n)*)'
        r'def\s+[A-Za-z_]\w*\s*\('
    )
    preferred = ('settings', 'api', 'account', 'drive', 'dashboard', 'admin', 'upload')
    best = ('', -999)
    for m in rx.finditer(text):
        route = (m.group('route') or '').lower()
        decs = [x.strip() for x in (m.group('decorators') or '').splitlines() if x.strip()]
        for dec in decs:
            score = _auth_score(dec)
            if any(k in route for k in preferred):
                score += 5
            if score > best[1]:
                best = (dec, score)
    return best[0] if best[1] >= 4 else ''


def _has_global_auth(text):
    # Accept a before_request guard only when its body visibly combines an
    # authentication/session check with redirect/abort/login behavior.
    rx = re.compile(
        r'(?ms)^@app\.before_request\s*\n(?:@[A-Za-z_][^\n]*\n)*'
        r'def\s+[A-Za-z_]\w*\s*\([^)]*\):\n(?P<body>(?:^[ \t]+.*\n?){1,80})'
    )
    for m in rx.finditer(text):
        low = (m.group('body') or '').lower()
        identity = any(k in low for k in ('session', 'current_user', 'authenticated', 'logged_in', 'login'))
        enforcement = any(k in low for k in ('redirect', 'abort(', 'unauthorized', 'login'))
        if identity and enforcement:
            return True
    return False


def _strip_ui(path, marker):
    if not path.exists():
        return
    text = path.read_text(encoding='utf-8')
    new = re.sub(r'\n?<!-- ' + re.escape(marker) + r' -->.*?</script>\n?', '\n', text, flags=re.S)
    if new != text:
        path.write_text(new, encoding='utf-8')


guard = _detect_route_guard(s)
global_auth = _has_global_auth(s)
web_safe = bool(guard or global_auth)

if web_safe and 'RM_ARCHIVE_WEB_ROUTES_V1' not in s:
    marker = '# RM_ARCHIVE_IMPORT_ROUTES_V1'
    pos = s.find(marker)
    if pos < 0:
        raise SystemExit('Archive auth compat: marcador das rotas archive não encontrado')
    deco = guard + '\n' if guard else ''
    web = r'''
# RM_ARCHIVE_WEB_ROUTES_V1
@app.route("/api/v1/archive/settings", methods=["GET", "POST"])
__AUTH__def web_archive_settings():
    if request.method == "GET":
        return jsonify({"ok": True, "settings": archive_public_settings()})
    payload = request.get_json(silent=True) or {}
    values = payload.get("settings") if isinstance(payload.get("settings"), dict) else payload
    archive_save_settings(values)
    return jsonify({"ok": True, "settings": archive_public_settings()})

@app.route("/api/v1/archive/jobs/<job_id>/password", methods=["POST"])
__AUTH__def web_archive_job_password(job_id):
    payload = request.get_json(silent=True) or {}
    try:
        job = archive_resume_with_password(job_id, payload.get("password") or "")
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "job": job})

@app.route("/api/v1/archive/jobs", methods=["GET"])
__AUTH__def web_archive_jobs():
    try:
        limit = max(1, min(200, int(request.args.get("limit", "50"))))
    except Exception:
        limit = 50
    return jsonify({"ok": True, "jobs": archive_list_jobs(limit)})

'''.replace('__AUTH__', deco)
    s = s[:pos] + web + s[pos:]
    app_py.write_text(s, encoding='utf-8')
    print('Archive auth compat: rotas web protegidas usando ' + (guard or 'before_request global'))
elif not web_safe:
    # Never leave UI that calls unprotected/nonexistent web endpoints. Archive
    # import itself remains fully available through @extension_api_required.
    _strip_ui(api_template, 'RM_ARCHIVE_MANAGER_V1')
    _strip_ui(settings_template, 'RM_ARCHIVE_SETTINGS_UI_V1')
    print('Archive auth compat: sem guard web identificável; extensão continua ativa, UI web de compactados foi omitida por segurança')
else:
    print('Archive auth compat: rotas web já presentes')

with tempfile.NamedTemporaryFile(suffix='.pyc') as f:
    py_compile.compile(str(app_py), doraise=True, cfile=f.name)
print('Archive auth compat OK')
