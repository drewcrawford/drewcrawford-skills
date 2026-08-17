#!/usr/bin/env python3
"""Plan and operate exclusive, self-reaping Hetzner task VMs."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
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
import urllib.error
import urllib.request

EXIT_INFRA = 125
MANAGED = "quiet-machine-managed"
HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
REMOTE_AGENT = HERE / "remote_agent.py"
OBSERVABILITY = HERE / "quiet_machine_observability.py"
SERVICE = SKILL / "assets/quiet-machine-reaper.service"

# Executing this file adds HERE to sys.path. Tests and embedders commonly load
# it through importlib, so make the bundled helper modules discoverable there as
# well.
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import quiet_machine_cloud as cloud
import quiet_machine_jobs as jobs_index
import quiet_machine_observability as observability


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
    operational = {
        "credential_file", "ssh_private_key", "ssh_public_key",
        "ssh_source_cidr", "artifact_dir", "billing_quantum", "billing_guard",
        "sync_excludes", "cache_paths", "quota", "setup_timeout",
    }
    stable = {k: v for k, v in profile.items() if k not in operational}
    digest.update(json.dumps(stable, sort_keys=True).encode())
    digest.update(str(image_id).encode())
    # These files are installed on every managed host.  A controller update
    # must not silently reuse a ready VM running an older lifecycle agent.
    digest.update(REMOTE_AGENT.read_bytes())
    digest.update(OBSERVABILITY.read_bytes())
    digest.update(SERVICE.read_bytes())
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


def managed_firewalls(token: str):
    return hcloud(token, "firewall", "list", "--selector", f"{MANAGED}=true", "-o", "json") or []


def known_hosts_path() -> Path:
    return Path.home() / ".cache/quiet-machine/known_hosts"


def forget_managed_host(ip: str):
    """Forget an address before first contact with a newly created VM.

    Cloud addresses are routinely reused.  The previous key remains valuable
    while reusing an existing managed server, but it cannot authenticate a new
    server which Hetzner happened to assign the same address.
    """
    known = known_hosts_path()
    if not known.exists():
        return
    command(["ssh-keygen", "-f", str(known), "-R", ip], capture=True,
            check=False)


def ssh_base(profile: dict, ip: str, base: Path):
    key = expand(profile["ssh_private_key"], base)
    known = known_hosts_path()
    known.parent.mkdir(parents=True, exist_ok=True)
    return ["ssh", "-i", str(key), "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
            "-o", "StrictHostKeyChecking=accept-new", "-o", f"UserKnownHostsFile={known}", f"root@{ip}"]


def server_ip(server):
    return server["public_net"]["ipv4"]["ip"]


def emit_progress(args, stage: str, message: str, **fields):
    mode = getattr(args, "events", "text")
    if mode == "none":
        return
    event = {"event": "progress", "stage": stage, "message": message,
             "timestamp": int(time.time()), **fields}
    if mode == "json":
        print(json.dumps(event, sort_keys=True), file=sys.stderr, flush=True)
    else:
        print(f"quiet-machine [{stage}] {message}", file=sys.stderr, flush=True)


def discover_source_cidr() -> str:
    observations = {}
    failures = []
    for name, url in (
        ("ipify", "https://api4.ipify.org"),
        ("amazon", "https://checkip.amazonaws.com"),
    ):
        try:
            with urllib.request.urlopen(url, timeout=8) as response:
                observations[name] = response.read(256).decode().strip()
        except (OSError, UnicodeError, urllib.error.URLError) as exc:
            failures.append(f"{name}: {exc}")
    if len(observations) < 2:
        raise Failure("automatic SSH source discovery requires two agreeing providers; "
                      + "; ".join(failures))
    try:
        result = cloud.discover_ssh_source_cidr(observations)
        if ipaddress.ip_network(result).version != 4:
            raise Failure("automatic SSH source discovery returned IPv6, but managed "
                          "servers currently use IPv4-only SSH")
        return result
    except cloud.CloudPlanningError as exc:
        raise Failure(str(exc)) from exc


def resolved_profile(profile: dict) -> dict:
    result = dict(profile)
    configured = str(result.get("ssh_source_cidr", "auto"))
    try:
        result["ssh_source_cidr"] = (discover_source_cidr() if configured == "auto"
                                     else cloud.validate_ssh_source_cidr(configured))
        if ipaddress.ip_network(result["ssh_source_cidr"]).version != 4:
            raise Failure("IPv6 SSH source CIDRs are unsupported while managed servers "
                          "are provisioned with --without-ipv6")
    except cloud.CloudPlanningError as exc:
        raise Failure(str(exc)) from exc
    return result


def server_firewall_plan(token: str, server: dict, cidr: str):
    matches = hcloud(token, "firewall", "list", "--selector",
                     f"quiet-machine-server={server['id']}", "-o", "json") or []
    managed = [item for item in matches
               if item.get("labels", {}).get(MANAGED) == "true"]
    if len(managed) != 1:
        raise Failure(f"server {server['id']} must have exactly one managed firewall")
    firewall = managed[0]
    current = []
    for rule in firewall.get("rules", []):
        if (rule.get("direction") == "in" and rule.get("protocol") == "tcp"
                and str(rule.get("port")) == "22"):
            current.extend(rule.get("source_ips", []))
    try:
        return firewall, cloud.plan_ssh_source_cidr_update(current, cidr)
    except cloud.CloudPlanningError as exc:
        raise Failure(str(exc)) from exc


def refresh_server_firewall(token: str, server: dict, cidr: str, apply: bool):
    firewall, plan = server_firewall_plan(token, server, cidr)
    if plan["action"] != "none" and apply:
        rules = [{"direction": "in", "protocol": "tcp", "port": "22",
                  "source_ips": [plan["proposed_cidr"]], "destination_ips": [],
                  "description": "quiet-machine SSH"}]
        command(["hcloud", "firewall", "replace-rules", "--rules-file", "-",
                 str(firewall["id"])], env=env_for(token),
                input=json.dumps(rules))
        plan = {**plan, "mutation_performed": True}
    return {"firewall_id": firewall["id"], **plan}


def remote(profile, base, ip, args, *, input=None, check=True, tty=False,
           capture=False):
    cmd = ssh_base(profile, ip, base)
    if tty:
        # Force allocation even when the controller itself is not attached to
        # a terminal. The remote shell command still validates that stdin is a
        # PTY before offering job-control guarantees.
        cmd.insert(1, "-tt")
    cmd.append(shlex.join(map(str, args)))
    return command(cmd, input=input, check=check, capture=capture)


def install_remote(profile, base, ip, token):
    payload = REMOTE_AGENT.read_text()
    remote(profile, base, ip, ["install", "-d", "-m", "0755", "/usr/local/lib/quiet-machine"])
    remote(profile, base, ip, ["install", "-m", "0644", "/dev/stdin",
                               "/usr/local/lib/quiet-machine/quiet_machine_observability.py"],
           input=OBSERVABILITY.read_text())
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
    created = int(time.time())
    labels = {
        MANAGED: "true", "quiet-machine-profile": fingerprint,
        "quiet-machine-profile-name": profile["name"],
        "quiet-machine-state": "bootstrapping", "quiet-machine-created": str(created),
        "quiet-machine-retain-until": str(retain_until), "quiet-machine-hard-expiry": str(retain_until + 120),
    }
    firewall = None
    server = None
    try:
        fw = hcloud(token, "firewall", "create", "--name", firewall_name,
                    "--label", f"{MANAGED}=true", "-o", "json")
        firewall = fw.get("firewall", fw)
        # These mutation-only hcloud commands print human success text rather
        # than JSON.  Do not send that text through the JSON-return helper.
        hcloud(token, "firewall", "add-rule", "--direction", "in", "--protocol", "tcp", "--port", "22",
               "--source-ips", profile["ssh_source_cidr"], firewall["id"], capture=False)
        args = ["server", "create", "--name", "quiet-machine-" + suffix, "--type", profile.get("server_type", "ccx13"),
                "--image", image["id"], "--location", profile["location"], "--ssh-key", ssh_key,
                "--firewall", firewall["id"], "--without-ipv6", "-o", "json"]
        for key, value in labels.items():
            args += ["--label", f"{key}={value}"]
        made = hcloud(token, *args)
        server = made.get("server", made)
        hcloud(token, "firewall", "add-label", "--overwrite", firewall["id"],
               f"quiet-machine-server={server['id']}", capture=False)
        return server
    except BaseException:
        if server is not None:
            hcloud(token, "server", "delete", server["id"], capture=False)
        if firewall is not None:
            hcloud(token, "firewall", "delete", firewall["id"], capture=False)
        raise


def candidate(token, profile, base, fingerprint, *, refresh_firewall=False,
              probe=True):
    for server in servers(token):
        labels = server.get("labels", {})
        if labels.get("quiet-machine-profile") != fingerprint or labels.get("quiet-machine-state") != "ready":
            continue
        if profile.get("ssh_source_cidr"):
            refresh_server_firewall(token, server, profile["ssh_source_cidr"],
                                    refresh_firewall)
        if not probe:
            return server
        ip = server_ip(server)
        result = remote(profile, base, ip, ["/usr/local/sbin/quiet-machine-agent", "probe"], check=False)
        if result.returncode == 0:
            return server
    return None


def quota_preflight(token: str, profile: dict):
    """Return current project usage and configured-limit assessment.

    Hetzner's public Cloud API exposes current resources and creation failures,
    but not a project's customized limit values. Profiles may therefore record
    the Console values for an exact non-mutating preflight.
    """
    all_servers = hcloud(token, "server", "list", "-o", "json") or []
    types = hcloud(token, "server-type", "list", "-o", "json") or []
    by_name = {item.get("name"): item for item in types}
    by_id = {item.get("id"): item for item in types}
    requested = by_name.get(profile.get("server_type", "ccx13"))
    if requested is None:
        requested = hcloud(token, "server-type", "describe",
                           profile.get("server_type", "ccx13"), "-o", "json")
    dedicated_used = 0
    for server in all_servers:
        raw = server.get("server_type")
        kind = raw if isinstance(raw, dict) else by_id.get(raw) or by_name.get(raw) or {}
        if kind.get("cpu_type") == "dedicated":
            dedicated_used += int(kind.get("cores", 0))
    quota = profile.get("quota", {})
    server_limit = quota.get("servers")
    vcpu_limit = quota.get("dedicated_vcpus")
    if server_limit is None or (requested.get("cpu_type") == "dedicated"
                                and vcpu_limit is None):
        return {
            "allowed": None,
            "reason": "project limit values are not exposed by the Hetzner Cloud API; "
                      "set profile.quota.servers and profile.quota.dedicated_vcpus "
                      "from the Console Limits page for exact preflight",
            "usage": {"servers": len(all_servers),
                      "dedicated_vcpus": dedicated_used},
            "mutation_performed": False,
        }
    try:
        return cloud.assess_creation_quota(
            requested, server_limit=server_limit, server_count=len(all_servers),
            dedicated_vcpu_limit=vcpu_limit,
            dedicated_vcpu_count=dedicated_used,
            managed_servers=[item for item in all_servers
                             if item.get("labels", {}).get(MANAGED) == "true"],
            server_types={**by_name, **by_id}, now=int(time.time()))
    except cloud.CloudPlanningError as exc:
        raise Failure(f"invalid quota configuration: {exc}") from exc


def rsync(profile, base, source: Path, destination: str, excludes=(), pull=False):
    # rsync supplies the host; use the same SSH policy without its destination.
    key = expand(profile["ssh_private_key"], base)
    known = known_hosts_path()
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
    existing = candidate(token, profile, base, fingerprint,
                         refresh_firewall=args.apply, probe=args.apply)
    now = int(time.time())
    quantum = duration(profile.get("billing_quantum", "60m"))
    guard = duration(profile.get("billing_guard", "60s"))
    created = int(existing["labels"]["quiet-machine-created"]) if existing else now
    retain_until = retention(created, now, args.time, quantum, guard)
    if existing:
        retain_until = max(retain_until, int(existing["labels"].get("quiet-machine-retain-until", 0)))
    return image, fingerprint, existing, retain_until


def do_run(args, profile, base, token):
    raw_cpus = getattr(args, "cpus", "")
    raw_helpers = getattr(args, "helper_cpus", "")
    raw_cpus = raw_cpus if isinstance(raw_cpus, str) else ""
    raw_helpers = raw_helpers if isinstance(raw_helpers, str) else ""
    try:
        requested_cpus = observability.parse_cpu_list(raw_cpus)
        helper_cpus = observability.parse_cpu_list(raw_helpers)
    except (TypeError, ValueError) as exc:
        raise Failure(f"invalid CPU affinity: {exc}") from exc
    overlap = set(requested_cpus) & set(helper_cpus)
    if overlap:
        raise Failure("benchmark and helper CPU lists overlap: "
                      + observability.render_cpu_list(overlap))
    emit_progress(args, "quota", "checking pool capacity")
    image, fingerprint, server, retain_until = plan_for(args, profile, base, token)
    planned_action = ("reuse" if server else "create") if args.apply else (
        "claim-attempt" if server else "create")
    plan = {"action": planned_action, "profile": profile["name"], "image_id": image["id"],
            "server_id": server and server["id"], "requested_seconds": args.time, "retain_until": retain_until,
            "command": args.command, "detach": bool(getattr(args, "detach", False)),
            "ssh_source_cidr": profile.get("ssh_source_cidr"),
            "cpu_affinity": getattr(args, "cpus", None),
            "helper_cpu_affinity": getattr(args, "helper_cpus", None)}
    if server is None and "location" in profile:
        plan["quota"] = quota_preflight(token, profile)
        if plan["quota"].get("allowed") is False:
            raise Failure("creation does not fit configured quota: "
                          + "; ".join(plan["quota"]["reasons"])
                          + "; managed idle release candidates: "
                          + json.dumps(plan["quota"]["releasable_managed_idle"]))
        if (args.apply and plan["quota"].get("allowed") is None
                and not args.allow_unknown_quota):
            raise Failure(plan["quota"]["reason"]
                          + "; pass --allow-unknown-quota to let the Hetzner API "
                            "enforce the limit during creation")
    if not args.apply:
        print(json.dumps(plan, indent=2))
        return 0
    new = server is None
    if new:
        emit_progress(args, "create", "creating dedicated VM")
        server = create_server(token, profile, base, image, fingerprint, retain_until)
        try:
            emit_progress(args, "bootstrap", "waiting for SSH and arming self-reaper",
                          server_id=server["id"])
            forget_managed_host(server_ip(server))
            wait_ssh(profile, base, server_ip(server))
            install_remote(profile, base, server_ip(server), token)
        except BaseException:
            try:
                delete_server(token, server["id"], True)
            finally:
                raise
        # A setup failure deliberately retains the armed machine for repair.
        emit_progress(args, "setup", "running project setup bundle",
                      server_id=server["id"])
        run_setup(token, profile, base, server, fingerprint, retain_until)
    else:
        emit_progress(args, "claim", f"claimed idle VM {server['id']}")
    ip = server_ip(server)
    # The workload runs as `quiet`.  `/var/lib/quiet-machine` is deliberately
    # 0700 root because it contains the sandbox API token; placing work below
    # it lets a relative shell entrypoint start from an already-open cwd but
    # breaks tools (Node module resolution among them) which canonicalize that
    # cwd and traverse the absolute parent path.  Keep code under the task
    # user's home and credentials under the root-only state directory.
    job_id = jobs_index.new_job_id()
    remote_dir = f"/home/quiet/.quiet-machine/runs/{job_id}"
    artifact = args.source.resolve() / profile.get("artifact_dir", ".quiet-machine-out") / job_id
    record = {
        **plan, "job_id": job_id, "server_id": server["id"], "server_ip": ip,
        "new_server": new, "config": str(args.config.resolve()),
        "source": str(args.source.resolve()), "remote_dir": remote_dir,
        "artifact_location": str(artifact), "created_at": int(time.time()),
        "state": "launching", "report": str(args.report.resolve()) if args.report else None,
    }
    # Persist reconnection coordinates before the remote side can start. A
    # controller crash after this point leaves a discoverable record.
    jobs_index.save(record)
    reservation_timeout = duration(profile.get("reservation_timeout", "30m"))

    def reserve(target_server):
        target_ip = server_ip(target_server)
        command_line = [
            "env", f"QUIET_MACHINE_ARTIFACTS={remote_dir}/.quiet-machine-out",
            "/usr/local/sbin/quiet-machine-agent", "run", "--detach",
            "--defer-start", "--reservation-timeout", reservation_timeout,
            "--job-id", job_id, "--timeout", args.time,
            "--retain-until", retain_until, "--cwd", remote_dir,
        ]
        if getattr(args, "cpus", None):
            command_line += ["--cpus", args.cpus]
        if getattr(args, "helper_cpus", None):
            command_line += ["--helper-cpus", args.helper_cpus]
        command_line += ["--", *args.command]
        return remote(profile, base, target_ip, command_line,
                      check=False, capture=True)

    emit_progress(args, "claim", "reserving VM through the authoritative lock",
                  job_id=job_id, server_id=server["id"])
    launch = reserve(server)
    if launch.returncode == 75:
        try:
            emit_progress(args, "create", "candidate lost a concurrent claim; creating another VM")
            quota = quota_preflight(token, profile)
            if quota.get("allowed") is False:
                raise Failure("concurrent claim requires another VM but quota is exhausted: "
                              + "; ".join(quota["reasons"]))
            if quota.get("allowed") is None and not args.allow_unknown_quota:
                raise Failure(quota["reason"] + "; pass --allow-unknown-quota")
            server = create_server(token, profile, base, image, fingerprint, retain_until)
            new = True
            try:
                forget_managed_host(server_ip(server))
                wait_ssh(profile, base, server_ip(server))
                install_remote(profile, base, server_ip(server), token)
            except BaseException:
                try:
                    delete_server(token, server["id"], True)
                finally:
                    raise
            run_setup(token, profile, base, server, fingerprint, retain_until)
            ip = server_ip(server)
            record.update(server_id=server["id"], server_ip=ip,
                          new_server=True, action="create-after-concurrent-claim")
            jobs_index.save(record)
            launch = reserve(server)
        except BaseException as exc:
            jobs_index.update(job_id, state="infrastructure_lost",
                              launch_error=f"{type(exc).__name__}: {exc}")
            raise
    if launch.returncode:
        # A transport failure can happen after the VM has durably accepted the
        # reservation. Reconcile by job ID before deciding it failed; never
        # overwrite an authoritative remote reservation with infrastructure
        # loss merely because its acknowledgement was dropped.
        try:
            accepted = remote_json(
                profile, base, ip,
                ["/usr/local/sbin/quiet-machine-agent", "status", job_id])
        except Failure:
            accepted = None
        if not accepted or accepted.get("state") not in {
                "reserved", "queued", "running", *jobs_index.TERMINAL_STATES}:
            jobs_index.update(job_id, state="reservation_unconfirmed",
                              launch_error=launch.stderr.strip())
            raise Failure(
                f"remote reservation acknowledgement was lost ({launch.returncode}); "
                f"job {job_id} remains indexed and may still be recoverable with status")
    jobs_index.update(job_id, state="reserved")
    try:
        remote(profile, base, ip, ["mkdir", "-p", remote_dir])
        caches = profile.get("cache_paths", [])
        if caches:
            remote(profile, base, ip, ["mkdir", "-p", *caches])
            remote(profile, base, ip, ["chown", "-R", "quiet:quiet", *caches])
        emit_progress(args, "sync", "uploading source worktree", job_id=job_id)
        rsync(profile, base, args.source.resolve().as_posix() + "/",
              f"root@{ip}:{remote_dir}/",
              profile.get("sync_excludes", [".git/", "target/"]))
        remote(profile, base, ip, ["mkdir", "-p", f"{remote_dir}/.quiet-machine-out"])
        remote(profile, base, ip, ["chown", "-R", "quiet:quiet", remote_dir])
        # Provisioning, setup, reservation, and sync do not consume the
        # requested execution window. Extend at the actual start point.
        created = int(server.get("labels", {}).get("quiet-machine-created", int(time.time())))
        retain_until = max(
            retain_until,
            retention(created, int(time.time()), args.time,
                      duration(profile.get("billing_quantum", "60m")),
                      duration(profile.get("billing_guard", "60s"))),
        )
        plan["retain_until"] = retain_until
    except BaseException:
        # The start marker has not been sent yet, so cancelling this reservation
        # cannot kill a workload that survived a controller disconnect.
        remote(profile, base, ip,
               ["/usr/local/sbin/quiet-machine-agent", "cancel", job_id],
               check=False, capture=True)
        raise
    emit_progress(args, "run", "starting reserved durable workload",
                  job_id=job_id, server_id=server["id"])
    try:
        remote_json(profile, base, ip,
                    ["/usr/local/sbin/quiet-machine-agent", "start", job_id,
                     "--retain-until", retain_until])
    except Failure as start_error:
        # `start` is idempotently discoverable. If SSH drops after the marker is
        # written, the workload must continue; do not send cancellation on an
        # ambiguous transport result.
        try:
            started_state = remote_json(
                profile, base, ip,
                ["/usr/local/sbin/quiet-machine-agent", "status", job_id])
        except Failure:
            started_state = None
        if started_state and started_state.get("state") in {
                "queued", "running", *jobs_index.TERMINAL_STATES}:
            jobs_index.update(job_id, state=started_state["state"],
                              last_status=started_state,
                              start_acknowledgement_lost=True)
        else:
            jobs_index.update(job_id, state="start_unconfirmed",
                              start_error=str(start_error))
            if getattr(args, "detach", False):
                print(json.dumps({"job_id": job_id, "state": "start_unconfirmed",
                                  "server_id": server["id"],
                                  "artifact_location": str(artifact)}, sort_keys=True))
                return 0
            raise Failure(f"start acknowledgement was lost; job {job_id} may continue "
                          "remotely and can be recovered with status") from start_error
    record.update(retain_until=retain_until)
    current_record = jobs_index.load(job_id)
    next_state = current_record.get("state")
    if next_state in {"reserved", "launching", "reservation_unconfirmed"}:
        next_state = "queued"
    jobs_index.update(job_id, retain_until=retain_until, state=next_state)
    record = jobs_index.load(job_id)
    # Keep a controller-side mirror alive independently of this CLI/SSH
    # session. It waits on the remote completion lock, then copies terminal
    # state, the complete log and artifacts before the VM's self-reaper runs.
    try:
        start_local_mirror(job_id)
    except (OSError, jobs_index.JobIndexError) as exc:
        jobs_index.update(job_id, mirror_error=f"{type(exc).__name__}: {exc}")
        print(f"quiet-machine: warning: local result mirror did not start for {job_id}: {exc}",
              file=sys.stderr)
    if getattr(args, "detach", False):
        print(json.dumps({"job_id": job_id, "state": record.get("state", "queued"),
                          "server_id": server["id"],
                          "artifact_location": str(artifact)}, sort_keys=True))
        return 0
    try:
        follow = remote(profile, base, ip,
                        ["/usr/local/sbin/quiet-machine-agent", "logs", job_id,
                         "--follow"], check=False)
        if follow.returncode:
            raise Failure(f"log attachment ended with SSH exit {follow.returncode}; "
                          f"job {job_id} continues remotely")
    except KeyboardInterrupt:
        print(f"quiet-machine: job {job_id} continues remotely; use cancel {job_id} --apply to stop it",
              file=sys.stderr)
        return 130
    state = fetch_job_state(record, profile, base)
    emit_progress(args, "artifacts", "retrieving final artifacts", job_id=job_id)
    retrieve_job_artifacts(record, profile, base, state)
    write_job_report(record, state)
    emit_progress(args, "release", f"job finished as {state['state']}", job_id=job_id)
    return jobs_index.exit_code(state)


def job_context(record: dict):
    config = Path(record["config"])
    _, profile = load_config(config, record["profile"])
    base = config.resolve().parent
    profile = resolved_profile(profile)
    token = read_token(profile, base)
    server = hcloud(token, "server", "describe", record["server_id"], "-o", "json")
    if server.get("labels", {}).get(MANAGED) != "true":
        raise Failure(f"job {record['job_id']} points to an unmanaged server")
    refresh_server_firewall(token, server, profile["ssh_source_cidr"], True)
    current_ip = server_ip(server)
    if current_ip != record.get("server_ip"):
        jobs_index.update(record["job_id"], server_ip=current_ip)
        record["server_ip"] = current_ip
    return profile, base, token


def remote_json(profile, base, ip, argv):
    result = remote(profile, base, ip, argv, check=False, capture=True)
    if result.returncode:
        raise Failure(f"remote command failed ({result.returncode}): "
                      f"{result.stderr.strip() or shlex.join(map(str, argv))}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise Failure(f"remote command returned invalid JSON: {exc}") from exc


def sizing_for_state(token: str, server: dict, state: dict):
    telemetry = state.get("telemetry")
    kind = server.get("server_type") or {}
    if not isinstance(telemetry, dict) or not isinstance(kind, dict):
        return None
    if state.get("state") != "success":
        return {"current_type": kind.get("name"), "recommended_type": None,
                "automatic_change": False, "confidence": "insufficient-data",
                "reasons": ["sizing advice requires a successful representative run"]}
    if telemetry.get("authoritative_cgroup_counters") is not True:
        return {"current_type": kind.get("name"), "recommended_type": None,
                "automatic_change": False, "confidence": "insufficient-data",
                "reasons": ["authoritative cgroup CPU and memory counters are required for sizing advice"]}
    if int(telemetry.get("sample_count", 0)) < 3:
        return {"current_type": kind.get("name"), "recommended_type": None,
                "automatic_change": False, "confidence": "insufficient-data",
                "reasons": ["at least three runtime samples are required for sizing advice"]}
    location = ((server.get("datacenter") or {}).get("location") or {}).get("name")
    candidates = []
    for item in hcloud(token, "server-type", "list", "-o", "json") or []:
        prices = item.get("prices") or []
        available_here = (not prices or not location
                          or any(price.get("location") == location for price in prices))
        if (available_here and item.get("cpu_type") == kind.get("cpu_type")
                and item.get("architecture") == kind.get("architecture")):
            candidates.append({"name": item.get("name"), "vcpus": item.get("cores"),
                               "ram_bytes": int(float(item.get("memory", 0)) * 1024 ** 3)})
    normalized = dict(telemetry)
    if "peak_rss_bytes" not in normalized and "peak_rss_kib" in normalized:
        normalized["peak_rss_bytes"] = normalized["peak_rss_kib"] * 1024
    if "task_cpu_percent" not in normalized:
        normalized["task_cpu_percent"] = normalized.get("cpu_utilization_percent")
    if isinstance(normalized.get("active_cores"), int):
        normalized["active_cores"] = {"max": normalized["active_cores"]}
    elif "active_cores" not in normalized and isinstance(normalized.get("active_threads"), int):
        normalized["active_cores"] = {"max": normalized["active_threads"]}
    try:
        return observability.sizing_advice(
            normalized, current_type=str(kind.get("name")),
            current_vcpus=int(kind.get("cores", 0)),
            current_ram_bytes=int(float(kind.get("memory", 0)) * 1024 ** 3),
            candidates=candidates)
    except (TypeError, ValueError):
        return None


def fetch_job_state(record: dict, profile: dict, base: Path):
    token = read_token(profile, base)
    server = hcloud(token, "server", "describe", record["server_id"], "-o", "json")
    if server.get("labels", {}).get(MANAGED) != "true":
        raise Failure(f"job {record['job_id']} points to an unmanaged server")
    state = remote_json(profile, base, server_ip(server),
                        ["/usr/local/sbin/quiet-machine-agent", "status",
                         record["job_id"]])
    advice = sizing_for_state(token, server, state)
    if advice is not None:
        state["sizing_advice"] = advice
    jobs_index.update(record["job_id"], state=state.get("state"),
                      last_status=state, last_checked_at=int(time.time()))
    return state


def retrieve_job_artifacts(record: dict, profile: dict, base: Path, state=None):
    artifact = Path(record["artifact_location"])
    artifact.mkdir(parents=True, exist_ok=True)
    rsync(profile, base, artifact,
          f"root@{record['server_ip']}:{record['remote_dir']}/.quiet-machine-out/",
          pull=True)
    jobs_index.update(record["job_id"], artifact_location=str(artifact),
                      artifacts_retrieved_at=int(time.time()))
    return artifact


def retrieve_job_log(record: dict, profile: dict, base: Path):
    """Mirror the authoritative remote log before the leased VM is reaped."""
    path = jobs_index.state_root() / "logs" / f"{record['job_id']}.log"
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    rsync(profile, base, path,
          f"root@{record['server_ip']}:/var/lib/quiet-machine/jobs/"
          f"{record['job_id']}/output.log", pull=True)
    jobs_index.update(record["job_id"], local_log=str(path),
                      log_retrieved_at=int(time.time()))
    return path


def start_local_mirror(job_id: str):
    """Start a session-independent controller that caches terminal results."""
    jobs_index.load(job_id)
    directory = jobs_index.state_root() / "mirror"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    log_path = directory / f"{job_id}.log"
    output = log_path.open("ab", buffering=0)
    try:
        worker = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "_mirror", job_id],
            stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
            start_new_session=True, close_fds=True, env=os.environ.copy())
    finally:
        output.close()
    jobs_index.update(job_id, mirror_pid=worker.pid, mirror_log=str(log_path),
                      mirror_started_at=int(time.time()))
    return worker.pid


def do_mirror(args):
    """Wait durably and cache state, logs and artifacts on the controller."""
    record = jobs_index.load(args.job_id)
    deadline = int(record.get("retain_until", time.time() + 3600)) + 120
    last_error = None
    while time.time() < deadline:
        try:
            record = jobs_index.load(args.job_id)
            profile, base, token = job_context(record)
            state = remote_json(
                profile, base, record["server_ip"],
                ["/usr/local/sbin/quiet-machine-agent", "wait", args.job_id])
            server = hcloud(token, "server", "describe", record["server_id"],
                            "-o", "json")
            advice = sizing_for_state(token, server, state)
            if advice is not None:
                state["sizing_advice"] = advice
            jobs_index.update(args.job_id, state=state.get("state"),
                              last_status=state,
                              last_checked_at=int(time.time()))
            errors = {}
            try:
                retrieve_job_log(record, profile, base)
            except Exception as exc:
                errors["log_mirror_error"] = str(exc)
            try:
                retrieve_job_artifacts(record, profile, base, state)
            except Exception as exc:
                errors["artifact_retrieval_error"] = str(exc)
            if errors:
                state.update(errors)
                jobs_index.update(args.job_id, last_status=state)
            write_job_report(record, state)
            return 0
        except (Failure, jobs_index.JobIndexError) as exc:
            last_error = str(exc)
            time.sleep(2)
    jobs_index.update(args.job_id, mirror_error=last_error or "lease expired",
                      mirror_finished_at=int(time.time()))
    return EXIT_INFRA


def write_job_report(record: dict, state: dict):
    if record.get("report"):
        path = Path(record["report"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({**record, "result": state}, indent=2) + "\n")


def unavailable_job_state(record: dict, exc: Failure):
    cached = record.get("last_status")
    if isinstance(cached, dict) and cached.get("state") in jobs_index.TERMINAL_STATES:
        return {**cached, "remote_available": False}
    if "not found" in str(exc).lower():
        state = {
            "job_id": record["job_id"], "state": "infrastructure_lost",
            "exit_code": None, "terminal_reason": "server_disappeared",
            "error": str(exc), "finished_at_unix": time.time(),
        }
        jobs_index.update(record["job_id"], state=state["state"],
                          last_status=state, last_checked_at=int(time.time()))
        return state
    raise exc


def do_status(args):
    try:
        record = jobs_index.load(args.job_id)
    except jobs_index.JobIndexError as exc:
        raise Failure(str(exc)) from exc
    try:
        profile, base, _ = job_context(record)
        state = fetch_job_state(record, profile, base)
    except Failure as exc:
        state = unavailable_job_state(record, exc)
    result = {**state, "vm": record["server_id"],
              "artifact_location": record["artifact_location"]}
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        elapsed = result.get("elapsed_seconds")
        elapsed_text = f"{elapsed:.1f}s" if isinstance(elapsed, (int, float)) else "unknown"
        print(f"{record['job_id']} {result['state']} vm={record['server_id']} "
              f"elapsed={elapsed_text} "
              f"exit={result.get('exit_code')} artifacts={record['artifact_location']}")
    return 0


def do_jobs(args):
    result = []
    for record in jobs_index.all_jobs():
        state = record.get("last_status") or {"state": record.get("state", "unknown")}
        if state.get("state") not in jobs_index.TERMINAL_STATES:
            try:
                profile, base, _ = job_context(record)
                state = fetch_job_state(record, profile, base)
            except Failure as exc:
                try:
                    state = unavailable_job_state(record, exc)
                except Failure:
                    state = {**state, "connection_error": str(exc)}
        result.append({
            "job_id": record["job_id"], "state": state.get("state"),
            "command": state.get("command", record.get("command")),
            "vm": record.get("server_id"),
            "created_at": state.get("created_at", record.get("created_at")),
            "started_at": state.get("started_at"),
            "finished_at": state.get("finished_at"),
            "elapsed_seconds": state.get("elapsed_seconds"),
            "exit_code": state.get("exit_code"),
            "timeout_seconds": state.get("timeout_seconds", record.get("requested_seconds")),
            "artifact_location": record.get("artifact_location"),
        })
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("\n".join(
            f"{item['job_id']} {item['state']} vm={item['vm']} "
            f"elapsed={item['elapsed_seconds']} exit={item['exit_code']} "
            f"artifacts={item['artifact_location']}"
            for item in result))
    return 0


def do_logs(args):
    try:
        record = jobs_index.load(args.job_id)
    except jobs_index.JobIndexError as exc:
        raise Failure(str(exc)) from exc
    cached = record.get("last_status") or {}
    local = record.get("local_log")
    if cached.get("state") in jobs_index.TERMINAL_STATES and local and Path(local).is_file():
        with Path(local).open("rb") as source:
            source.seek(args.since_byte)
            shutil.copyfileobj(source, sys.stdout.buffer)
        return 0
    try:
        profile, base, _ = job_context(record)
    except Failure:
        local = record.get("local_log")
        if not local or not Path(local).is_file():
            raise
        with Path(local).open("rb") as source:
            source.seek(args.since_byte)
            shutil.copyfileobj(source, sys.stdout.buffer)
        return 0
    command_line = ["/usr/local/sbin/quiet-machine-agent", "logs", args.job_id]
    if args.since_byte:
        command_line += ["--since-byte", args.since_byte]
    if args.follow or args.action == "attach":
        command_line.append("--follow")
    result = remote(profile, base, record["server_ip"], command_line, check=False)
    if result.returncode:
        raise Failure(f"log connection failed with SSH exit {result.returncode}; "
                      "the remote job may still be running")
    return 0


def do_wait(args):
    try:
        record = jobs_index.load(args.job_id)
    except jobs_index.JobIndexError as exc:
        raise Failure(str(exc)) from exc
    try:
        profile, base, token = job_context(record)
    except Failure as exc:
        state = unavailable_job_state(record, exc)
        if state.get("state") not in jobs_index.TERMINAL_STATES:
            raise
        event = {"event": "job_completed", **state}
        print(json.dumps(event, sort_keys=True) if args.format == "json"
              else f"{args.job_id} {state.get('state')} exit={state.get('exit_code')}")
        return jobs_index.exit_code(state)
    # This is one blocking SSH command. The remote agent waits on a completion
    # flock inherited by the detached supervisor, so the local side never polls.
    state = remote_json(profile, base, record["server_ip"],
                        ["/usr/local/sbin/quiet-machine-agent", "wait", args.job_id])
    server = hcloud(token, "server", "describe", record["server_id"], "-o", "json")
    advice = sizing_for_state(token, server, state)
    if advice is not None:
        state["sizing_advice"] = advice
    jobs_index.update(args.job_id, state=state.get("state"), last_status=state,
                      last_checked_at=int(time.time()))
    try:
        retrieve_job_artifacts(record, profile, base, state)
    except Exception as exc:
        state["artifact_retrieval_error"] = str(exc)
    write_job_report(record, state)
    if args.format == "json":
        print(json.dumps(state, sort_keys=True))
    else:
        print(f"{args.job_id} {state.get('state')} exit={state.get('exit_code')} "
              f"elapsed={state.get('elapsed_seconds')}s")
    return jobs_index.exit_code(state)


def do_cancel_job(args):
    try:
        record = jobs_index.load(args.job_id)
    except jobs_index.JobIndexError as exc:
        raise Failure(str(exc)) from exc
    plan = {"action": "cancel", "job_id": args.job_id,
            "server_id": record["server_id"], "apply": args.apply}
    if not args.apply:
        print(json.dumps(plan, indent=2))
        return 0
    profile, base, token = job_context(record)
    state = remote_json(profile, base, record["server_ip"],
                        ["/usr/local/sbin/quiet-machine-agent", "cancel", args.job_id])
    server = hcloud(token, "server", "describe", record["server_id"], "-o", "json")
    advice = sizing_for_state(token, server, state)
    if advice is not None:
        state["sizing_advice"] = advice
    jobs_index.update(args.job_id, state=state.get("state"), last_status=state,
                      last_checked_at=int(time.time()))
    try:
        retrieve_job_artifacts(record, profile, base, state)
    except Exception as exc:
        state["artifact_retrieval_error"] = str(exc)
    write_job_report(record, state)
    print(json.dumps(state, sort_keys=True))
    return 0


def do_artifacts(args):
    try:
        record = jobs_index.load(args.job_id)
    except jobs_index.JobIndexError as exc:
        raise Failure(str(exc)) from exc
    try:
        profile, base, _ = job_context(record)
    except Failure:
        root = Path(record["artifact_location"])
        if not root.is_dir():
            raise
        files = []
        for path in sorted(root.rglob("*")):
            if path.is_file():
                info = path.stat()
                files.append({"path": path.relative_to(root).as_posix(),
                              "size": info.st_size, "mtime_ns": info.st_mtime_ns})
        print(json.dumps({"job_id": args.job_id,
                          "state": (record.get("last_status") or {}).get(
                              "state", record.get("state")),
                          "artifact_location": str(root), "files": files,
                          "source": "controller-mirror"}, indent=2, sort_keys=True))
        return 0
    manifest = remote_json(profile, base, record["server_ip"],
                           ["/usr/local/sbin/quiet-machine-agent", "artifacts",
                            args.job_id])
    if args.download:
        if args.output:
            record = {**record, "artifact_location": str(args.output.resolve())}
        manifest["downloaded_to"] = str(retrieve_job_artifacts(record, profile, base))
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


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
    result = cloud.project_pool_rows(items, now=int(time.time()))
    ips = {item["id"]: server_ip(item) for item in items}
    for row in result:
        row["ip"] = ips.get(row["id"])
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print("\n".join(
            f"{row['id']} {row['status']} {row['lifecycle_state']} "
            f"{row['server_type']} {row['vcpu']}vCPU/{row['ram_gb']}GB "
            f"{row['location']} job={row['current_job'] or '-'} "
            f"lease={row['lease_expires_at'] or '-'} age={row['billing_age_seconds']}s "
            f"setup={row['setup_revision'] or '-'} image={row['image_revision'] or '-'}"
            for row in result))
    return 0


def delete_server(token, sid, apply):
    item = hcloud(token, "server", "describe", sid, "-o", "json")
    if item.get("labels", {}).get(MANAGED) != "true":
        raise Failure(f"server {sid} is not managed by quiet-machine")
    print(json.dumps({"action": "delete", "server_id": item["id"], "apply": apply}))
    if apply:
        firewalls = hcloud(token, "firewall", "list", "--selector", f"quiet-machine-server={item['id']}", "-o", "json") or []
        # Hetzner refuses deletion of an attached firewall. Delete the server
        # first so it never spends a failure window publicly reachable without
        # its ingress policy, then retry the now-orphaned managed firewall while
        # the asynchronous detach settles.
        hcloud(token, "server", "delete", item["id"], capture=False)
        for firewall in firewalls:
            if firewall.get("labels", {}).get(MANAGED) == "true":
                failure = None
                for _ in range(20):
                    try:
                        hcloud(token, "firewall", "delete", firewall["id"], capture=False)
                        failure = None
                        break
                    except Failure as exc:
                        failure = exc
                        time.sleep(0.5)
                if failure is not None:
                    raise failure


def build_parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, default=Path(".quiet-machine.toml"))
    sub = p.add_subparsers(dest="action", required=True)
    d = sub.add_parser("doctor"); d.add_argument("--profile", required=True); d.add_argument("--fix-permissions", action="store_true"); d.add_argument("--apply", action="store_true")
    r = sub.add_parser("run"); r.add_argument("--profile", required=True); r.add_argument("--time", type=duration, required=True); r.add_argument("--source", type=Path, default=Path(".")); r.add_argument("--report", type=Path); r.add_argument("--detach", action="store_true"); r.add_argument("--events", choices=("text", "json", "none"), default="text"); r.add_argument("--cpus"); r.add_argument("--helper-cpus"); r.add_argument("--allow-unknown-quota", action="store_true"); r.add_argument("--apply", action="store_true"); r.add_argument("command", nargs=argparse.REMAINDER)
    l = sub.add_parser("list"); l.add_argument("--format", choices=("text", "json"), default="text")
    s = sub.add_parser("status"); s.add_argument("job_id"); s.add_argument("--format", choices=("text", "json"), default="text")
    j = sub.add_parser("jobs"); j.add_argument("--format", choices=("text", "json"), default="text")
    for name in ("logs", "attach"):
        q = sub.add_parser(name); q.add_argument("job_id"); q.add_argument("--follow", action="store_true"); q.add_argument("--since-byte", type=int, default=0)
    w = sub.add_parser("wait"); w.add_argument("job_id"); w.add_argument("--format", choices=("text", "json"), default="json")
    c = sub.add_parser("cancel"); c.add_argument("job_id"); c.add_argument("--apply", action="store_true")
    a = sub.add_parser("artifacts"); a.add_argument("job_id"); a.add_argument("--download", action="store_true"); a.add_argument("--output", type=Path)
    for name in ("destroy", "snapshot", "setup", "shell"):
        q = sub.add_parser(name); q.add_argument("--server", required=True); q.add_argument("--profile"); q.add_argument("--time", type=duration, default=duration("30m")); q.add_argument("--apply", action="store_true")
    x = sub.add_parser("reap"); x.add_argument("--apply", action="store_true")
    return p


def main(argv=None):
    try:
        raw_args = sys.argv[1:] if argv is None else list(argv)
        # Private controller worker entrypoint. Keep it out of the user-facing
        # command list while retaining normal error handling and one executable.
        if raw_args[:1] == ["_mirror"] and len(raw_args) == 2:
            return do_mirror(argparse.Namespace(job_id=raw_args[1]))
        args = build_parser().parse_args(raw_args)
        if args.action == "status": return do_status(args)
        if args.action == "jobs": return do_jobs(args)
        if args.action in {"logs", "attach"}: return do_logs(args)
        if args.action == "wait": return do_wait(args)
        if args.action == "cancel": return do_cancel_job(args)
        if args.action == "artifacts": return do_artifacts(args)
        base = args.config.resolve().parent
        profile_name = getattr(args, "profile", None)
        data, profile = load_config(args.config, profile_name) if profile_name else load_config(args.config, None)
        if profile is None:
            # Non-profile commands still use the credential file.
            profile = {"credential_file": data.get("credential_file", "~/.hetzner")}
        if args.action == "doctor":
            profile = resolved_profile(profile)
            return doctor(args, profile, base)
        token = read_token(profile, base)
        if profile_name is None and args.action in {"shell", "setup", "snapshot"}:
            selected = hcloud(token, "server", "describe", args.server, "-o", "json")
            selected_name = selected.get("labels", {}).get("quiet-machine-profile-name")
            if not selected_name:
                raise Failure("server has no profile-name label; pass --profile")
            _, profile = load_config(args.config, selected_name)
            profile_name = selected_name
        if profile_name is not None and args.action in {"run", "shell", "setup", "snapshot"}:
            profile = resolved_profile(profile)
        if args.action == "run":
            if args.command[:1] == ["--"]: args.command = args.command[1:]
            if not args.command: raise Failure("run requires a command after --")
            return do_run(args, profile, base, token)
        if args.action == "list": return do_list(args, token)
        if args.action == "destroy": delete_server(token, args.server, args.apply); return 0
        if args.action == "reap":
            now = int(time.time())
            live_servers = servers(token)
            for s in live_servers:
                labels = s["labels"]
                state = labels.get("quiet-machine-state")
                deadline = labels.get("quiet-machine-hard-expiry") if state in {"busy", "bootstrapping"} else labels.get("quiet-machine-retain-until")
                if int(deadline or "0") <= now:
                    delete_server(token, s["id"], args.apply)
            # A VM can disappear after asking the API to delete itself but
            # before its process removes the now-detached firewall. Reap only
            # managed, unattached firewalls whose labelled server is absent.
            live_ids = {str(s["id"]) for s in live_servers}
            for firewall in managed_firewalls(token):
                owner = firewall.get("labels", {}).get("quiet-machine-server")
                if owner in live_ids or firewall.get("applied_to"):
                    continue
                print(json.dumps({"action": "delete-orphan-firewall",
                                  "firewall_id": firewall["id"],
                                  "apply": args.apply}))
                if args.apply:
                    hcloud(token, "firewall", "delete", firewall["id"], capture=False)
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
        if profile.get("ssh_source_cidr"):
            refresh_server_firewall(token, server, profile["ssh_source_cidr"], True)
        if args.action == "shell":
            created = int(server["labels"]["quiet-machine-created"])
            retain_until = retention(created, int(time.time()), args.time,
                                      duration(profile.get("billing_quantum", "60m")),
                                      duration(profile.get("billing_guard", "60s")))
            return remote(profile, base, ip, ["/usr/local/sbin/quiet-machine-agent", "shell",
                          "--timeout", args.time, "--retain-until", retain_until, "--cwd", "/home/quiet",
                          ], check=False, tty=True).returncode
        if args.action == "setup":
            image = {"id": server["image"]["id"]}; fp = profile_hash(profile, base, str(image["id"]))
            created = int(server["labels"]["quiet-machine-created"])
            retain_until = max(int(server["labels"].get("quiet-machine-retain-until", 0)),
                               retention(created, int(time.time()), args.time,
                                         duration(profile.get("billing_quantum", "60m")),
                                         duration(profile.get("billing_guard", "60s"))))
            # `setup` is also the in-place control-plane upgrade path.  The
            # agent and reaper participate in the profile fingerprint, so the
            # relabel below is valid only after their current bytes are armed.
            install_remote(profile, base, ip, token)
            run_setup(token, profile, base, server, fp, retain_until); return 0
        if args.action == "snapshot":
            probe = remote(profile, base, ip, ["/usr/local/sbin/quiet-machine-agent", "probe"], check=False)
            if probe.returncode:
                raise Failure("server is busy; snapshot requires the exclusive lock")
            remote(profile, base, ip, ["bash", "-lc",
                   "rm -rf /home/quiet/.quiet-machine/runs /var/lib/quiet-machine/jobs "
                   "/var/lib/quiet-machine/setup /var/lib/quiet-machine/token; "
                   "rm -f /run/quiet-machine/task.pid /run/quiet-machine/active-job; "
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
