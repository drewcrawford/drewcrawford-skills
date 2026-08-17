#!/usr/bin/env python3
"""Remote lease holder and self-reaper. Installed root-only by quiet_machine.py."""

import argparse
import fcntl
import json
import os
import pathlib
import pwd
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path("/var/lib/quiet-machine")
TOKEN = ROOT / "token"
LOCK = pathlib.Path("/run/quiet-machine/task.lock")
TASK_PID = pathlib.Path("/run/quiet-machine/task.pid")
API = "https://api.hetzner.cloud/v1"
META = "http://169.254.169.254/hetzner/v1/metadata/instance-id"


def request(method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN.read_text().strip())
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        if method == "DELETE" and exc.code == 404:
            return {}
        raise


def server_id():
    with urllib.request.urlopen(META, timeout=5) as response:
        return response.read().decode().strip()


def labels():
    return request("GET", "/servers/" + server_id())["server"]["labels"]


def set_labels(**values):
    current = labels()
    current.update({k: str(v) for k, v in values.items()})
    request("PUT", "/servers/" + server_id(), {"labels": current})


def lock(nonblocking=True):
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    handle = LOCK.open("a+")
    flags = fcntl.LOCK_EX | (fcntl.LOCK_NB if nonblocking else 0)
    try:
        fcntl.flock(handle, flags)
        return handle
    except BlockingIOError:
        handle.close()
        return None


def arm(args):
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    token = sys.stdin.read().strip()
    if not token:
        raise SystemExit("empty token on stdin")
    TOKEN.write_text(token + "\n")
    TOKEN.chmod(0o600)
    ensure_user()
    subprocess.run(["systemctl", "enable", "--now", "quiet-machine-reaper.service"], check=True)
    # Setup has not succeeded yet. The local controller (or setup command)
    # performs the transition to ready.
    set_labels(**{"quiet-machine-state": "bootstrapping"})


def probe(_args):
    handle = lock()
    if handle is None:
        return 75
    handle.close()
    return 0


def ensure_user():
    try:
        pwd.getpwnam("quiet")
    except KeyError:
        subprocess.run(["useradd", "--create-home", "--shell", "/bin/bash", "quiet"], check=True)
    pathlib.Path("/etc/sudoers.d/quiet-machine").write_text("quiet ALL=(ALL) NOPASSWD: ALL\n")
    pathlib.Path("/etc/sudoers.d/quiet-machine").chmod(0o440)


def run_locked(args, setup=False):
    handle = lock()
    if handle is None:
        return 75
    now = int(time.time())
    set_labels(**{
        "quiet-machine-state": "busy",
        "quiet-machine-hard-expiry": now + args.timeout + 120,
        "quiet-machine-retain-until": args.retain_until,
    })
    try:
        command = args.command
        if setup:
            argv = ["timeout", "--signal=TERM", "--kill-after=30s",
                    str(args.timeout)] + command
        else:
            ensure_user()
            argv = [
                "timeout", "--signal=TERM", "--kill-after=30s", str(args.timeout),
                "sudo", "-u", "quiet", "--preserve-env=QUIET_MACHINE_ARTIFACTS", "--",
            ] + command
        # A distinct process group gives `cancel` one exact, bounded target.
        # The agent itself stays alive to restore the ready label in `finally`.
        proc = subprocess.Popen(argv, cwd=None if setup else args.cwd,
                                start_new_session=True)
        TASK_PID.write_text(str(proc.pid) + "\n")
        code = proc.wait()
        if code in (124, 137, 143):
            return 124
        return code if 0 <= code <= 123 else 125
    finally:
        TASK_PID.unlink(missing_ok=True)
        set_labels(**{
            "quiet-machine-state": "ready" if not setup else "ready",
            "quiet-machine-retain-until": args.retain_until,
            "quiet-machine-hard-expiry": args.retain_until + 120,
        })
        handle.close()


def cancel(_args):
    # If the lock is available there is no workload to cancel.  Removing a
    # stale pid file in that case avoids ever signalling a reused process ID.
    handle = lock()
    if handle is not None:
        handle.close()
        TASK_PID.unlink(missing_ok=True)
        return 0
    try:
        pid = int(TASK_PID.read_text().strip())
    except (FileNotFoundError, ValueError):
        return 75
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return 0
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return 0
        time.sleep(0.1)
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    return 0


def setup(args):
    try:
        code = run_locked(args, setup=True)
        if code:
            set_labels(**{"quiet-machine-state": "needs-repair"})
        else:
            set_labels(**{"quiet-machine-profile": args.profile})
        return code
    except Exception:
        set_labels(**{"quiet-machine-state": "needs-repair"})
        raise


def reap_once():
    data = labels()
    now = int(time.time())
    retain = int(data.get("quiet-machine-retain-until", "0"))
    hard = int(data.get("quiet-machine-hard-expiry", "0"))
    handle = lock()
    if now >= hard > 0 or (handle is not None and now >= retain > 0):
        sid = server_id()
        # An attached firewall cannot be deleted. Ask for self-deletion first,
        # then use the short interval before shutdown to remove the detached
        # managed object. The orphan-aware local reap collects it if the VM
        # disappears before this process reaches the second request.
        page = request("GET", "/firewalls?label_selector=quiet-machine-server%3D" + sid)
        request("DELETE", "/servers/" + sid)
        for firewall in page.get("firewalls", []):
            for _ in range(20):
                try:
                    request("DELETE", "/firewalls/" + str(firewall["id"]))
                    break
                except urllib.error.HTTPError as exc:
                    if exc.code != 409:
                        raise
                    time.sleep(0.25)
        return True
    if handle is not None:
        handle.close()
    return False


def reaper(_args):
    while True:
        try:
            if reap_once():
                return 0
        except Exception as exc:
            print("quiet-machine reaper:", exc, file=sys.stderr)
        time.sleep(20)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("arm")
    sub.add_parser("probe")
    sub.add_parser("cancel")
    sub.add_parser("reaper")
    for name in ("run", "setup"):
        p = sub.add_parser(name)
        p.add_argument("--timeout", type=int, required=True)
        p.add_argument("--retain-until", type=int, required=True)
        p.add_argument("--cwd", default="/")
        p.add_argument("--profile", default="")
        p.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.action in ("run", "setup") and args.command[:1] == ["--"]:
        args.command = args.command[1:]
    funcs = {"arm": arm, "probe": probe, "cancel": cancel,
             "run": lambda a: run_locked(a), "setup": setup,
             "reaper": reaper}
    return funcs[args.action](args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
