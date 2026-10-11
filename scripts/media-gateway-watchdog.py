#!/usr/bin/env python3
"""Rclone Manager: host-side Gateway watchdog (Unraid, Oracle/VPS, Zorin).

Does not restart Docker, alter media files, or remove Media Pools. Reads the
MultiServer Agent's existing library/backend selections. When a local Media
Pool has usable entries but its stable path is missing/stale, first asks the
Agent to switch the selected backend, then (on local backends only) applies
a host bind mount as a limited fallback. Remote backends are recovered via
the Agent API only.

Use --once for diagnostics; --loop --repair for unattended recovery.
"""
# RM_MEDIA_GATEWAY_WATCHDOG_V1
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.request import Request, urlopen

PARENT = Path("/media-union")
ALLOWED_SOURCE = Path("/mnt/rclone-manager-remotes")
AGENT_DEFAULT = Path("/boot/config/plugins/rclone-manager-multiserver-agent")
INTERVAL = 90
FAILURE_THRESHOLD = 2
COOLDOWN = 600

SAMPLE_CODE = """
import json, os, sys
p = sys.argv[1]
out = []
with os.scandir(p) as items:
    for item in items:
        if item.name not in ('.', '..'):
            out.append(item.name)
        if len(out) >= 12:
            break
print(json.dumps(out, ensure_ascii=False))
"""


def emit(level, message):
    when = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"{when} [{level}] {message}", flush=True)


def cmd(argv, timeout=12):
    try:
        return subprocess.run(argv, text=True, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None


def is_mount(path, fstype=None):
    proc = cmd(["findmnt", "-rn", "-M", str(path), "-o", "FSTYPE"], 6)
    if not proc or proc.returncode != 0:
        return False
    values = [x.strip() for x in proc.stdout.splitlines()]
    return bool(values) if fstype is None else fstype in values


def names(path):
    proc = cmd([sys.executable, "-c", SAMPLE_CODE, str(path)], 12)
    if not proc or proc.returncode:
        return None
    try:
        result = json.loads(proc.stdout)
        return result if isinstance(result, list) else None
    except (ValueError, TypeError):
        return None


def under(path, parent):
    try:
        return Path(path).is_absolute() and Path(path) != parent and Path(path).is_relative_to(parent)
    except (ValueError, TypeError):
        return False


def library_entries(agent_state):
    backends = agent_state.get("backends") or {}
    libraries = agent_state.get("libraries") or {}
    if not isinstance(backends, dict) or not isinstance(libraries, dict):
        return
    for slug, lib in libraries.items():
        if not isinstance(lib, dict):
            continue
        dest = str(lib.get("stable_path") or "")
        bid = str(lib.get("backend_id") or "")
        backend = backends.get(bid)
        if not isinstance(backend, dict):
            continue
        transport = str(backend.get("transport") or "").lower()
        source = str(backend.get("source_path") or "")
        # Only first-level gateway paths. Never act on /media-union itself,
        # unrelated directories or paths supplied outside the managed root.
        if not under(dest, PARENT) or Path(dest).parent != PARENT:
            continue
        if transport not in {"local", "sftp", "ssh"}:
            continue
        yield dict(slug=str(slug), dest=Path(dest), source=Path(source) if source else None,
                   backend_id=bid, transport=transport)


def read_agent_settings(platform):
    if platform == "unraid":
        base = AGENT_DEFAULT
        candidates = [base / "agent.env"]
        state = base / "state" / "state.json"
    else:
        candidates = [
            Path("/opt/rclone-manager-multiserver-agent/agent.env"),
            Path("/etc/default/rclone-manager-multiserver-agent"),
            Path("/etc/rclone-manager-multiserver-agent.env"),
        ]
        state = Path("/var/lib/rclone-manager-multiserver/state.json")

    values = {}
    for env_file in candidates:
        if not env_file.is_file():
            continue
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k in {"MS_AGENT_TOKEN", "MS_PORT", "MS_BIND", "MS_STATE_DIR"}:
                    values[k] = v.strip().strip("'\"")
            break
        except OSError:
            continue
    if values.get("MS_STATE_DIR"):
        state = Path(values["MS_STATE_DIR"]) / "state.json"
    return state, values


def agent_switch(entry, settings):
    token = settings.get("MS_AGENT_TOKEN", "")
    if not token:
        return False, "token do Agent indisponível"
    bind = settings.get("MS_BIND", "127.0.0.1")
    if bind in {"0.0.0.0", "::", "[::]", ""}:
        bind = "127.0.0.1"
    port = settings.get("MS_PORT", "8765")
    if not port.isdigit():
        return False, "porta do Agent inválida"
    payload = json.dumps({
        "library_slug": entry["slug"],
        "backend_id": entry["backend_id"],
        "stable_path": str(entry["dest"]),
    }).encode("utf-8")
    req = Request(
        f"http://{bind}:{port}/v1/gateway/switch",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=14) as response:
            data = json.loads(response.read(16384))
        return bool(data.get("ok")), ("ok" if data.get("ok") else str(data.get("error") or "falha no Agent")[:200])
    except (URLError, OSError, ValueError) as exc:
        return False, type(exc).__name__


def safe_state(state_dir):
    try:
        p = state_dir / "state.json"
        loaded = json.loads(p.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(state_dir, state):
    try:
        state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        tmp = state_dir / "state.json.tmp"
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(state_dir / "state.json")
    except OSError as exc:
        emit("ERROR", f"não foi possível persistir estado ({type(exc).__name__})")


def prepare_shared_parent():
    # Docker propagation depends on the parent being a shared mount. Never
    # change / itself; bind the dedicated /media-union directory to itself.
    if not PARENT.is_dir():
        return False
    if not is_mount(PARENT):
        p = cmd(["mount", "--bind", str(PARENT), str(PARENT)], timeout=8)
        if not p or p.returncode:
            return False
    p = cmd(["mount", "--make-rshared", str(PARENT)], timeout=8)
    return bool(p and p.returncode == 0)


def healthy(entry):
    dest = entry["dest"]
    if not is_mount(dest):
        return False, "gateway desmontado"

    dest_names = names(dest)
    if dest_names is None:
        return False, "gateway inacessível"

    if entry["transport"] != "local":
        # Remote libraries may legitimately be empty; readable mount counts
        # as healthy until a backend-specific check can be performed.
        return True, "gateway remoto legível"

    src = entry["source"]
    if not src or not under(src, ALLOWED_SOURCE):
        return None, "origem local fora do diretório gerenciado"
    if not is_mount(src, "fuse.rclone"):
        return None, "origem FUSE não montada"
    src_names = names(src)
    if src_names is None:
        return None, "origem FUSE inacessível"
    if not src_names:
        return None, "origem vazia; não assumir que o Gateway deve ter arquivos"
    if any(n in dest_names for n in src_names):
        return True, "origem e gateway correspondem"
    return False, "gateway sem as pastas presentes na origem"


def direct_bind(entry):
    src, dest = entry["source"], entry["dest"]
    if not src or not under(src, ALLOWED_SOURCE) or not under(dest, PARENT):
        return False, "caminho não permitido"
    if not is_mount(src, "fuse.rclone") or not names(src):
        return False, "origem não validada"
    if not prepare_shared_parent():
        return False, "não foi possível preparar propagação de /media-union"
    try:
        dest.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False, "destino não pode ser criado"

    # Bind over a stale gateway, as verified in the AEROCOOL recovery. No
    # umount -l, kill, rm or Docker restart: the watchdog cannot disrupt a
    # healthy source. Cooldown+health checks prevent mounting repeatedly.
    result = cmd(["mount", "--bind", str(src), str(dest)], 15)
    if not result or result.returncode:
        return False, "mount --bind falhou"
    check, note = healthy(entry)
    return check is True, note


def probe_once(platform, repair=False, state_dir=None, threshold=FAILURE_THRESHOLD):
    if state_dir is None:
        base = "/mnt/user/appdata/rclone-manager" if platform == "unraid" else "/opt/rclone-manager"
        state_dir = Path(base) / "data" / "media-gateway-watchdog"

    agent_file, settings = read_agent_settings(platform)
    if not agent_file.is_file():
        emit("INFO", f"Agent ainda não configurado ({agent_file}); aguardando")
        return 0
    try:
        agent_data = json.loads(agent_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        emit("WARNING", "não foi possível ler estado do Agent; sem alterações")
        return 1

    saved = safe_state(state_dir) if repair else {}
    now = time.time()
    count = 0

    for entry in library_entries(agent_data):
        count += 1
        slug = entry["slug"]
        selected = saved.get(slug, {}) if isinstance(saved.get(slug), dict) else {}
        ok, why = healthy(entry)

        if ok is True:
            if selected.get("failures"):
                emit("INFO", f"{slug}: gateway voltou ao normal")
            selected["failures"] = 0
            selected["last_status"] = "healthy"
            saved[slug] = selected
            if not repair:
                emit("OK", f"{slug}: {why}")
            continue

        if ok is None:
            emit("INFO", f"{slug}: aguardando sem intervir ({why})")
            selected["failures"] = 0
            selected["last_status"] = "source_not_ready"
            saved[slug] = selected
            continue

        emit("WARNING", f"{slug}: {why} ({entry['transport']} / {entry['backend_id']})")
        selected["last_status"] = "degraded"
        selected["failures"] = int(selected.get("failures") or 0) + 1
        saved[slug] = selected
        if not repair or selected["failures"] < threshold:
            continue

        last = float(selected.get("last_attempt") or 0)
        if now - last < COOLDOWN:
            continue

        # Do not race with a Docker recreate / deployment in progress.
        container = "rclone-manager" if platform == "unraid" else (
            "rclone-manager-zorin" if platform == "zorin" else "rclone-manager-vps"
        )
        status = cmd(["docker", "inspect", "-f", "{{.State.Running}}", container], timeout=8)
        if not status or status.returncode or status.stdout.strip() != "true":
            emit("INFO", f"{slug}: Manager indisponível; recuperação adiada")
            continue

        selected["last_attempt"] = now
        emit("WARNING", f"{slug}: solicitando recuperação ao MultiServer Agent")
        switched, reason = agent_switch(entry, settings)
        if switched:
            time.sleep(2)
            ok2, why2 = healthy(entry)
            if ok2 is True:
                emit("OK", f"{slug}: Gateway recuperado pelo Agent")
                selected["failures"] = 0
                selected["last_status"] = "healthy"
                continue
        else:
            emit("WARNING", f"{slug}: Agent não recuperou o Gateway ({reason})")

        if entry["transport"] == "local":
            success, message = direct_bind(entry)
            if success:
                emit("OK", f"{slug}: Gateway local recuperado por bind seguro")
                selected["failures"] = 0
                selected["last_status"] = "healthy"
            else:
                emit("ERROR", f"{slug}: recuperação não concluída ({message})")
        else:
            emit("WARNING", f"{slug}: backend remoto depende do Agent; nenhuma montagem local forçada")

    if not count:
        emit("INFO", "nenhuma biblioteca gerenciada encontrada neste servidor")

    if repair:
        write_state(state_dir, saved)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", choices=["unraid", "vps", "zorin"], required=True)
    ap.add_argument("--once", action="store_true", help="diagnóstico não destrutivo")
    ap.add_argument("--loop", action="store_true", help="execução contínua")
    ap.add_argument("--repair", action="store_true", help="habilitar recuperação automática")
    ap.add_argument("--interval", type=int, default=INTERVAL)
    ap.add_argument("--state-dir", type=Path)
    ap.add_argument("--threshold", type=int, default=FAILURE_THRESHOLD)
    args = ap.parse_args()
    if os.geteuid() != 0:
        ap.error("o watchdog deve executar como root")
    if not args.loop and not args.once:
        ap.error("use --once ou --loop")
    if args.loop and not args.repair:
        ap.error("--loop exige --repair")

    root = args.state_dir or Path(
        "/mnt/user/appdata/rclone-manager/data/media-gateway-watchdog"
        if args.platform == "unraid"
        else "/opt/rclone-manager/data/media-gateway-watchdog"
    )
    root.mkdir(parents=True, exist_ok=True, mode=0o700)

    if args.loop:
        lockfile = root / "watchdog.lock"
        lock = lockfile.open("a+")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            emit("INFO", "já existe um watchdog rodando; saindo")
            return 0

        emit("INFO", f"watchdog iniciado ({args.platform}), intervalo {max(30,args.interval)}s")
        while True:
            try:
                probe_once(args.platform, repair=True, state_dir=root, threshold=max(2,args.threshold))
            except Exception as exc:
                emit("ERROR", f"ciclo não concluído: {type(exc).__name__}: {str(exc)[:150]}")
            time.sleep(max(30, args.interval))

    return probe_once(args.platform, repair=args.repair, state_dir=root,
                      threshold=max(1,args.threshold))


if __name__ == "__main__":
    sys.exit(main())
