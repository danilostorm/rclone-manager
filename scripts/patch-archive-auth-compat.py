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
    # CSRF/rate-limit/CORS decorators are NOT authentication/authorization.
    # Never promote names such as require_csrf merely because they contain
    # "require".
    if (
        'extension_api_required' in low
        or low.startswith('@app.')
        or any(word in low for word in ('csrf', 'limiter', 'rate_limit', 'ratelimit', 'cache', 'cors'))
    ):
        return -100
    score = 0
    for word, points in (
        ('login', 10), ('authenticated', 10), ('authentication', 10),
        ('auth_required', 10), ('admin', 8), ('permission', 7),
        ('authorize', 7), ('protect', 5), ('session_required', 8),
    ):
        if word in low:
            score += points
    return score


def _detect_route_guard(text):
    # Reuse only a decorator that clearly signals authentication/authorization.
    rx = re.compile(
        r'(?m)^@app\.route\((?P<route>[^\n]+)\)\n'
        r'(?P<decorators>(?:@[A-Za-z_][^\n]*\n)*)'
        r'def\s+[A-Za-z_]\w*\s*\('
    )
    preferred = ('settings', 'account', 'drive', 'dashboard', 'admin', 'upload')
    best = ('', -999)
    for m in rx.finditer(text):
        route = (m.group('route') or '').lower()
        decs = [x.strip() for x in (m.group('decorators') or '').splitlines() if x.strip()]
        for dec in decs:
            score = _auth_score(dec)
            if score > 0 and any(k in route for k in preferred):
                score += 3
            if score > best[1]:
                best = (dec, score)
    return best[0] if best[1] >= 7 else ''


def _has_global_auth(text):
    # Accept a before_request guard only when its body visibly combines an
    # identity/auth check with redirect/abort/login enforcement.
    rx = re.compile(
        r'(?ms)^@app\.before_request\s*\n(?:@[A-Za-z_][^\n]*\n)*'
        r'def\s+[A-Za-z_]\w*\s*\([^)]*\):\n(?P<body>(?:^[ \t]+.*\n?){1,120})'
    )
    for m in rx.finditer(text):
        low = (m.group('body') or '').lower()
        identity = any(k in low for k in (
            'current_user', 'authenticated', 'logged_in', 'is_admin',
            'session.get("user', "session.get('user",
            'session.get("admin', "session.get('admin",
            'session.get("logged', "session.get('logged",
        ))
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


def _remove_archive_web_routes(text):
    # Always remove our previous optional web block first. This is important
    # because HA4.7.4.1 could mistakenly generate it with @require_csrf.
    start = text.find('# RM_ARCHIVE_WEB_ROUTES_V1')
    if start < 0:
        return text, False
    end = text.find('# RM_ARCHIVE_IMPORT_ROUTES_V1', start)
    if end < 0:
        raise SystemExit('Archive auth compat: bloco web antigo sem marcador final')
    prefix = text[:start]
    suffix = text[end:]
    return prefix.rstrip() + '\n\n' + suffix.lstrip(), True


def _build_web_routes(deco):
    return r'''# RM_ARCHIVE_WEB_ROUTES_V1
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


# Remove any HA4.7.4.1 optional web block before auth discovery so it cannot
# influence the detector itself.
s, removed_old_web = _remove_archive_web_routes(s)

guard = _detect_route_guard(s)
global_auth = _has_global_auth(s)
web_safe = bool(guard or global_auth)

if web_safe:
    marker = '# RM_ARCHIVE_IMPORT_ROUTES_V1'
    pos = s.find(marker)
    if pos < 0:
        raise SystemExit('Archive auth compat: marcador das rotas archive não encontrado')
    deco = guard + '\n' if guard else ''
    web = _build_web_routes(deco)
    s = s[:pos] + web + s[pos:]
    app_py.write_text(s, encoding='utf-8')
    print('Archive auth compat: rotas web protegidas usando ' + (guard or 'before_request global'))
else:
    # Never expose panel endpoints behind CSRF only. The browser extension
    # remains fully functional through @extension_api_required.
    app_py.write_text(s, encoding='utf-8')
    _strip_ui(api_template, 'RM_ARCHIVE_MANAGER_V1')
    _strip_ui(settings_template, 'RM_ARCHIVE_SETTINGS_UI_V1')
    if removed_old_web:
        print('Archive auth compat: removidas rotas HA4.7.4.1 protegidas apenas por CSRF')
    print('Archive auth compat: sem autenticação web comprovada; extensão continua ativa e UI web opcional foi omitida')

with tempfile.NamedTemporaryFile(suffix='.pyc') as f:
    py_compile.compile(str(app_py), doraise=True, cfile=f.name)
print('Archive auth compat OK')
