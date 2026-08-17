#!/usr/bin/env python3
"""Plan and operate exclusive, self-reaping Hetzner task VMs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import sys
import time
import tomllib

EXIT_INFRA = 125
MANAGED = "quiet-machine-managed"
HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
REMOTE_AGENT = HERE / "remote_agent.py"
SERVICE = SKILL / "assets/quiet-machine-reaper.service"


class Failure(RuntimeError):
    pass


def duration(value: str) -> int:
    units = {"s": 1, "m": 60, "h": 3600}
    try:
        if not value or value[-1] not in units:
            raise ValueError
        number = float(value[:-1])
        if number <= 0:
            raise ValueError
        return int(number * units[value[-1]])
    except ValueError:
        raise argparse.ArgumentTypeError("duration must be positive, such as 30m, 2h, or 45s")


def retention(created: int, started: int, requested: int, quantum: int, guard: int) -> int:
    boundary = created + math.ceil((started + requested - created) / quantum) * quantum
    return max(started, boundary - guard)


def expand(value: str, base: Path) -> Path:
    path = Path(os.path.expanduser(value))
    return path if path.is_absolute() else (base / path).resolve()


def load_config(path: Path, profile: str | None):
    if not path.exists():
        raise Failure(f"configuration not found: {path}; copy assets/quiet-machine.example.toml")
    data = tomllib.loads(path.read_text())
    if profile is None:
        return data, None
    profiles = data.get("profiles", {})
    if profile not in profiles:
        raise Failure(f"profile {profile!r} not found in {path}")
    result = dict(profiles[profile])
    result["name"] = profile
    result["credential_file"] = data.get("credential_file", "~/.hetzner")
    return data, result


def token_path(profile: dict, base: Path) -> Path:
    return expand(profile.get("credential_file", "~/.hetzner"), base)


def read_token(profile: dict, base: Path, strict=True) -> str:
    path = token_path(profile, base)
    if not path.is_file():
        raise Failure(f"Hetzner token not found: {path}")
    mode = stat.S_IMODE(path.stat().st_mode)
    if strict and mode & 0o077:
        raise Failure(f"{path} mode is {mode:04o}; run doctor --fix-permissions --apply")
    value = path.read_text().strip()
    if not value:
        raise Failure(f"Hetzner token is empty: {path}")
    return value


def env_for(token: str):
    env = os.environ.copy()
    env["HCLOUD_TOKEN"] = token
    return env


def command(argv, *, env=None, input=None, capture=False, check=True):
    result = subprocess.run(argv, env=env, input=input, text=True, capture_output=capture)
    if check and result.returncode:
        detail = result.stderr.strip() if capture else ""
        raise Failure(f"command failed ({result.returncode}): {shlex.join(map(str, argv))}{': ' + detail if detail else ''}")
    return result


def hcloud(token: str, *args, capture=True):
    result = command(["hcloud", *map(str, args)], env=env_for(token), capture=capture)
    if capture and result.stdout.strip():
        return json.loads(result.stdout)
    return None


def profile_hash(profile: dict, base: Path, image_id: str) -> str:
    digest = hashlib.sha256()
    stable = {k: v for k, v in profile.items() if k not in {"credential_file", "ssh_private_key", "artifact_dir"}}
    digest.update(json.dumps(stable, sort_keys=True).encode())
    digest.update(str(image_id).encode())
    inputs = []
    if profile.get("setup_script"):
        inputs.append(profile["setup_script"])
    inputs.extend(profile.get("setup_files", []))
    for key in inputs:
        path = expand(key, base)
        if path.is_file():
            digest.update(path.read_bytes())
        elif path.is_dir():
            for child in sorted(p for p in path.rglob("*") if p.is_file()):
                digest.update(str(child.relative_to(path)).encode())
                digest.update(child.read_bytes())
        else:
            raise Failure(f"setup input not found: {path}")
    return digest.hexdigest()[:24]


def resolve_image(token: str, value: str):
    if value.startswith("selector:"):
        images = hcloud(token, "image", "list", "--type", "snapshot", "--selector", value[9:], "-o", "json")
        if not images:
            raise Failure(f"no snapshot matches {value}")
        item = sorted(images, key=lambda x: x["created"], reverse=True)[0]
    else:
        item = hcloud(token, "image", "describe", value, "-o", "json")
    return item


def servers(token: str):
    return hcloud(token, "server", "list", "--selector", f"{MANAGED}=true", "-o", "json") or []


def ssh_base(profile: dict, ip: str, base: Path):
    key = expand(profile["ssh_private_key"], base)
    known = Path.home() / ".cache/quiet-machine/known_hosts"
    known.parent.mkdir(parents=True, exist_ok=True)
    return ["ssh", "-i", str(key), "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
            "-o", "StrictHostKeyChecking=accept-new", "-o", f"UserKnownHostsFile={known}", f"root@{ip}"]


def server_ip(server):
    return server["public_net"]["ipv4"]["ip"]


def remote(profile, base, ip, args, *, input=None, check=True, tty=False):
    cmd = ssh_base(profile, ip, base)
    if tty:
        cmd.insert(1, "-t")
    cmd.append(shlex.join(map(str, args)))
    return command(cmd, input=input, check=check)


def install_remote(profile, base, ip, token):
    payload = REMOTE_AGENT.read_text()
    remote(profile, base, ip, ["install", "-m", "0700", "/dev/stdin", "/usr/local/sbin/quiet-machine-agent"], input=payload)
    remote(profile, base, ip, ["install", "-m", "0644", "/dev/stdin", "/etc/systemd/system/quiet-machine-reaper.service"], input=SERVICE.read_text())
    remote(profile, base, ip, ["systemctl", "daemon-reload"])
    remote(profile, base, ip, ["/usr/local/sbin/quiet-machine-agent", "arm"], input=token + "\n")


def wait_ssh(profile, base, ip, timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = remote(profile, base, ip, ["true"], check=False)
        if result.returncode == 0:
            return
        time.sleep(3)
    raise Failure(f"SSH did not become ready within {timeout}s")


def ensure_ssh_key(token, profile, base):
    public = expand(profile["ssh_public_key"], base)
    if not public.is_file():
        raise Failure(f"SSH public key not found: {public}")
    fingerprint = hashlib.sha256(public.read_bytes()).hexdigest()[:16]
    name = "quiet-machine-" + fingerprint
    keys = hcloud(token, "ssh-key", "list", "-o", "json") or []
    if not any(k["name"] == name for k in keys):
        hcloud(token, "ssh-key", "create", "--name", name, "--public-key-from-file", public,
               "--label", f"{MANAGED}=true", "-o", "json")
    return name


def create_server(token, profile, base, image, fingerprint, retain_until):
    ssh_key = ensure_ssh_key(token, profile, base)
    suffix = hashlib.sha256(os.urandom(16)).hexdigest()[:10]
    firewall_name = "quiet-machine-" + suffix
    fw = hcloud(token, "firewall", "create", "--name", firewall_name,
                "--label", f"{MANAGED}=true", "-o", "json")
    firewall = fw.get("firewall", fw)
    hcloud(token, "firewall", "add-rule", "--direction", "in", "--protocol", "tcp", "--port", "22",
           "--source-ips", profile["ssh_source_cidr"], firewall["id"])
    created = int(time.time())
    labels = {
        MANAGED: "true", "quiet-machine-profile": fingerprint,
        "quiet-machine-profile-name": profile["name"],
        "quiet-machine-state": "bootstrapping", "quiet-machine-created": str(created),
        "quiet-machine-retain-until": str(retain_until), "quiet-machine-hard-expiry": str(retain_until + 120),
    }
    args = ["server", "create", "--name", "quiet-machine-" + suffix, "--type", profile.get("server_type", "ccx13"),
            "--image", image["id"], "--location", profile["location"], "--ssh-key", ssh_key,
            "--firewall", firewall["id"], "--without-ipv6", "-o", "json"]
    for key, value in labels.items():
        args += ["--label", f"{key}={value}"]
    try:
        made = hcloud(token, *args)
        server = made.get("server", made)
        hcloud(token, "firewall", "add-label", "--overwrite", firewall["id"], f"quiet-machine-server={server['id']}")
        return server
    except Exception:
        hcloud(token, "firewall", "delete", firewall["id"], capture=False)
        raise


def candidate(token, profile, base, fingerprint):
    for server in servers(token):
        labels = server.get("labels", {})
        if labels.get("quiet-machine-profile") != fingerprint or labels.get("quiet-machine-state") != "ready":
            continue
        ip = server_ip(server)
        result = remote(profile, base, ip, ["/usr/local/sbin/quiet-machine-agent", "probe"], check=False)
        if result.returncode == 0:
            return server
    return None


def rsync(profile, base, source: Path, destination: str, excludes=(), pull=False):
    # rsync supplies the host; use the same SSH policy without its destination.
    key = expand(profile["ssh_private_key"], base)
    known = Path.home() / ".cache/quiet-machine/known_hosts"
    transport = f"ssh -i {shlex.quote(str(key))} -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile={shlex.quote(str(known))}"
    args = ["rsync", "-a", "--delete", "-e", transport]
    for item in excludes:
        args += ["--exclude", item]
    args += [str(source), destination] if not pull else [destination, str(source)]
    command(args)


def run_setup(token, profile, base, server, fingerprint, retain_until):
    script = profile.get("setup_script")
    if not script:
        hcloud(token, "server", "add-label", "--overwrite", server["id"],
               f"quiet-machine-profile={fingerprint}", "quiet-machine-state=ready")
        return
    ip = server_ip(server)
    remote(profile, base, ip, ["mkdir", "-p", "/var/lib/quiet-machine/setup"])
    rsync(profile, base, expand(script, base), f"root@{ip}:/var/lib/quiet-machine/setup/setup.sh")
    for item in profile.get("setup_files", []):
        path = expand(item, base)
        rsync(profile, base, path, f"root@{ip}:/var/lib/quiet-machine/setup/")
    timeout = duration(profile.get("setup_timeout", "30m"))
    result = remote(profile, base, ip, ["/usr/local/sbin/quiet-machine-agent", "setup", "--timeout", timeout,
                    "--retain-until", retain_until, "--profile", fingerprint, "--", "bash", "/var/lib/quiet-machine/setup/setup.sh"], check=False)
    if result.returncode:
        raise Failure(f"setup failed with exit {result.returncode}; server {server['id']} needs repair")


def plan_for(args, profile, base, token):
    image = resolve_image(token, profile["image"])
    fingerprint = profile_hash(profile, base, str(image["id"]))
    existing = candidate(token, profile, base, fingerprint)
    now = int(time.time())
    quantum = duration(profile.get("billing_quantum", "60m"))
    guard = duration(profile.get("billing_guard", "60s"))
    created = int(existing["labels"]["quiet-machine-created"]) if existing else now
    retain_until = retention(created, now, args.time, quantum, guard)
    if existing:
        retain_until = max(retain_until, int(existing["labels"].get("quiet-machine-retain-until", 0)))
    return image, fingerprint, existing, retain_until


def do_run(args, profile, base, token):
    image, fingerprint, server, retain_until = plan_for(args, profile, base, token)
    plan = {"action": "reuse" if server else "create", "profile": profile["name"], "image_id": image["id"],
            "server_id": server and server["id"], "requested_seconds": args.time, "retain_until": retain_until,
            "command": args.command}
    if not args.apply:
        print(json.dumps(plan, indent=2))
        return 0
    new = server is None
    if new:
        server = create_server(token, profile, base, image, fingerprint, retain_until)
        try:
            wait_ssh(profile, base, server_ip(server))
            install_remote(profile, base, server_ip(server), token)
        except Exception:
            try:
                hcloud(token, "server", "delete", server["id"], capture=False)
            finally:
                raise
        # A setup failure deliberately retains the armed machine for repair.
        run_setup(token, profile, base, server, fingerprint, retain_until)
    ip = server_ip(server)
    remote_dir = f"/var/lib/quiet-machine/runs/{int(time.time())}-{os.getpid()}"
    remote(profile, base, ip, ["mkdir", "-p", remote_dir])
    caches = profile.get("cache_paths", [])
    if caches:
        remote(profile, base, ip, ["mkdir", "-p", *caches])
        remote(profile, base, ip, ["chown", "-R", "quiet:quiet", *caches])
    rsync(profile, base, args.source.resolve().as_posix() + "/", f"root@{ip}:{remote_dir}/", profile.get("sync_excludes", [".git/", "target/"]))
    remote(profile, base, ip, ["mkdir", "-p", f"{remote_dir}/.quiet-machine-out"])
    remote(profile, base, ip, ["chown", "-R", "quiet:quiet", remote_dir])
    remote_cmd = ["env", f"QUIET_MACHINE_ARTIFACTS={remote_dir}/.quiet-machine-out",
                  "/usr/local/sbin/quiet-machine-agent", "run", "--timeout", args.time,
                  "--retain-until", retain_until, "--cwd", remote_dir, "--", *args.command]
    result = remote(profile, base, ip, remote_cmd, check=False)
    artifact = args.source / profile.get("artifact_dir", ".quiet-machine-out")
    try:
        artifact.mkdir(parents=True, exist_ok=True)
        rsync(profile, base, artifact, f"root@{ip}:{remote_dir}/.quiet-machine-out/", pull=True)
    except Exception as exc:
        print(f"artifact retrieval failed: {exc}", file=sys.stderr)
        result = subprocess.CompletedProcess([], EXIT_INFRA)
    report = {**plan, "server_id": server["id"], "exit_code": result.returncode, "new_server": new}
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    return result.returncode


def doctor(args, profile, base):
    path = token_path(profile, base)
    if args.fix_permissions:
        if not args.apply:
            print(json.dumps({"action": "chmod", "path": str(path), "mode": "0600"}, indent=2))
            return 0
        path.chmod(0o600)
    token = read_token(profile, base)
    missing = [name for name in ("hcloud", "ssh", "rsync") if shutil.which(name) is None]
    if missing:
        raise Failure("missing required commands: " + ", ".join(missing))
    image = resolve_image(token, profile["image"])
    st = hcloud(token, "server-type", "describe", profile.get("server_type", "ccx13"), "-o", "json")
    if st.get("cpu_type") != "dedicated":
        raise Failure(f"server type {st.get('name')} is not dedicated CPU")
    if st.get("architecture") != image.get("architecture"):
        raise Failure("server type and image architectures differ")
    profile_hash(profile, base, str(image["id"]))
    print(json.dumps({"ok": True, "profile": profile["name"], "image_id": image["id"], "server_type": st["name"]}))
    return 0


def do_list(args, token):
    items = servers(token)
    result = [{"id": s["id"], "name": s["name"], "status": s["status"], "ip": server_ip(s), "labels": s["labels"]} for s in items]
    print(json.dumps(result, indent=2) if args.format == "json" else "\n".join(f"{x['id']} {x['status']} {x['labels'].get('quiet-machine-state')} {x['ip']}" for x in result))
    return 0


def delete_server(token, sid, apply):
    item = hcloud(token, "server", "describe", sid, "-o", "json")
    if item.get("labels", {}).get(MANAGED) != "true":
        raise Failure(f"server {sid} is not managed by quiet-machine")
    print(json.dumps({"action": "delete", "server_id": item["id"], "apply": apply}))
    if apply:
        firewalls = hcloud(token, "firewall", "list", "--selector", f"quiet-machine-server={item['id']}", "-o", "json") or []
        for firewall in firewalls:
            if firewall.get("labels", {}).get(MANAGED) == "true":
                hcloud(token, "firewall", "delete", firewall["id"], capture=False)
        hcloud(token, "server", "delete", item["id"], capture=False)


def build_parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, default=Path(".quiet-machine.toml"))
    sub = p.add_subparsers(dest="action", required=True)
    d = sub.add_parser("doctor"); d.add_argument("--profile", required=True); d.add_argument("--fix-permissions", action="store_true"); d.add_argument("--apply", action="store_true")
    r = sub.add_parser("run"); r.add_argument("--profile", required=True); r.add_argument("--time", type=duration, required=True); r.add_argument("--source", type=Path, default=Path(".")); r.add_argument("--report", type=Path); r.add_argument("--apply", action="store_true"); r.add_argument("command", nargs=argparse.REMAINDER)
    l = sub.add_parser("list"); l.add_argument("--format", choices=("text", "json"), default="text")
    for name in ("destroy", "snapshot", "setup", "shell"):
        q = sub.add_parser(name); q.add_argument("--server", required=True); q.add_argument("--profile"); q.add_argument("--time", type=duration, default=duration("30m")); q.add_argument("--apply", action="store_true")
    x = sub.add_parser("reap"); x.add_argument("--apply", action="store_true")
    return p


def main(argv=None):
    try:
        args = build_parser().parse_args(argv)
        base = args.config.resolve().parent
        profile_name = getattr(args, "profile", None)
        data, profile = load_config(args.config, profile_name) if profile_name else load_config(args.config, None)
        if profile is None:
            # Non-profile commands still use the credential file.
            profile = {"credential_file": data.get("credential_file", "~/.hetzner")}
        if args.action == "doctor":
            return doctor(args, profile, base)
        token = read_token(profile, base)
        if profile_name is None and args.action in {"shell", "setup", "snapshot"}:
            selected = hcloud(token, "server", "describe", args.server, "-o", "json")
            selected_name = selected.get("labels", {}).get("quiet-machine-profile-name")
            if not selected_name:
                raise Failure("server has no profile-name label; pass --profile")
            _, profile = load_config(args.config, selected_name)
            profile_name = selected_name
        if args.action == "run":
            if args.command[:1] == ["--"]: args.command = args.command[1:]
            if not args.command: raise Failure("run requires a command after --")
            return do_run(args, profile, base, token)
        if args.action == "list": return do_list(args, token)
        if args.action == "destroy": delete_server(token, args.server, args.apply); return 0
        if args.action == "reap":
            now = int(time.time())
            for s in servers(token):
                labels = s["labels"]
                state = labels.get("quiet-machine-state")
                deadline = labels.get("quiet-machine-hard-expiry") if state in {"busy", "bootstrapping"} else labels.get("quiet-machine-retain-until")
                if int(deadline or "0") <= now:
                    delete_server(token, s["id"], args.apply)
            return 0
        if not args.apply:
            plan = {"action": args.action, "server_id": args.server, "apply": False}
            if args.action == "snapshot":
                plan.update({"power_off": True, "scrub_credentials": True,
                             "delete_source_after_attempt": True})
            print(json.dumps(plan, indent=2)); return 0
        server = hcloud(token, "server", "describe", args.server, "-o", "json")
        if server.get("labels", {}).get(MANAGED) != "true": raise Failure("refusing unmanaged server")
        ip = server_ip(server)
        if args.action == "shell":
            created = int(server["labels"]["quiet-machine-created"])
            retain_until = retention(created, int(time.time()), args.time,
                                      duration(profile.get("billing_quantum", "60m")),
                                      duration(profile.get("billing_guard", "60s")))
            return remote(profile, base, ip, ["/usr/local/sbin/quiet-machine-agent", "run",
                          "--timeout", args.time, "--retain-until", retain_until, "--cwd", "/home/quiet",
                          "--", "bash", "-l"], check=False, tty=True).returncode
        if args.action == "setup":
            image = {"id": server["image"]["id"]}; fp = profile_hash(profile, base, str(image["id"]))
            created = int(server["labels"]["quiet-machine-created"])
            retain_until = max(int(server["labels"].get("quiet-machine-retain-until", 0)),
                               retention(created, int(time.time()), args.time,
                                         duration(profile.get("billing_quantum", "60m")),
                                         duration(profile.get("billing_guard", "60s"))))
            run_setup(token, profile, base, server, fp, retain_until); return 0
        if args.action == "snapshot":
            probe = remote(profile, base, ip, ["/usr/local/sbin/quiet-machine-agent", "probe"], check=False)
            if probe.returncode:
                raise Failure("server is busy; snapshot requires the exclusive lock")
            remote(profile, base, ip, ["bash", "-lc",
                   "rm -rf /var/lib/quiet-machine/runs/* /var/lib/quiet-machine/setup /var/lib/quiet-machine/token; "
                   "cloud-init clean --logs --machine-id --seed --configs all; "
                   "rm -rf /run/cloud-init/* /var/lib/cloud/*; rm -f /etc/ssh/ssh_host_*; sync"])
            hcloud(token, "server", "shutdown", "--wait", "--wait-timeout", "2m", server["id"], capture=False)
            try:
                snap = hcloud(token, "server", "create-image", "--type", "snapshot", "--description",
                              f"quiet-machine captured from {server['id']}", "--label", "quiet-machine-captured=true",
                              "--label", f"quiet-machine-profile={server['labels'].get('quiet-machine-profile', '')}",
                              server["id"], "-o", "json")
            finally:
                # The scrubbed source no longer has a reaper token. Delete it even
                # after snapshot failure rather than leave a powered-off billable VM.
                hcloud(token, "server", "delete", server["id"], capture=False)
            image = snap.get("image", snap)
            print(json.dumps({"snapshot_id": image["id"], "profile_override": {"image": str(image["id"]) }}, indent=2))
            return 0
        return 0
    except Failure as exc:
        print(f"quiet-machine: {exc}", file=sys.stderr)
        return EXIT_INFRA


if __name__ == "__main__":
    raise SystemExit(main())
