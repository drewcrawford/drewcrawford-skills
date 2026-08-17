#!/usr/bin/env python3
"""Remote lease holder and self-reaper. Installed root-only by quiet_machine.py."""

import argparse
import datetime
import fcntl
import json
import os
import pathlib
import pwd
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

for module_path in ("/usr/local/lib/quiet-machine", str(pathlib.Path(__file__).resolve().parent)):
    if module_path not in sys.path:
        sys.path.insert(0, module_path)
try:
    import quiet_machine_observability as observability
except ImportError:  # Preserve repair access on an older, partially upgraded VM.
    observability = None

ROOT = pathlib.Path("/var/lib/quiet-machine")
TOKEN = ROOT / "token"
LOCK = pathlib.Path("/run/quiet-machine/task.lock")
TASK_PID = pathlib.Path("/run/quiet-machine/task.pid")
ACTIVE_JOB = pathlib.Path("/run/quiet-machine/active-job")
JOBS = ROOT / "jobs"
API = "https://api.hetzner.cloud/v1"
META = "http://169.254.169.254/hetzner/v1/metadata/instance-id"
TERMINAL_STATES = {"success", "failure", "cancelled", "timeout", "infrastructure_lost"}
JOB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$")


def utc_timestamp(value=None):
    value = time.time() if value is None else value
    return datetime.datetime.fromtimestamp(value, datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def job_dir(job_id):
    if not JOB_ID.fullmatch(job_id):
        raise ValueError("job ID must contain only letters, digits, '.', '_' or '-' (max 63 characters)")
    return JOBS / job_id


def state_path(job_id):
    return job_dir(job_id) / "state.json"


def read_state(job_id):
    path = state_path(job_id)
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise ValueError(f"unknown job: {job_id}") from None


def write_state(job_id, state):
    """Atomically replace state while serializing writers for this job."""
    return mutate_state(job_id, lambda current: {**current, **state})


def mutate_state(job_id, transform):
    """Atomically read, transform, and replace a job record."""
    directory = job_dir(job_id)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = directory / "state.lock"
    with lock_path.open("a+") as state_lock:
        fcntl.flock(state_lock, fcntl.LOCK_EX)
        current = {}
        path = directory / "state.json"
        try:
            current = json.loads(path.read_text())
        except FileNotFoundError:
            pass
        current = transform(current)
        temporary = directory / f".state.{os.getpid()}.tmp"
        with temporary.open("w") as output:
            json.dump(current, output, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        return current


def _text(path, default=None):
    try:
        return pathlib.Path(path).read_text().strip()
    except (OSError, UnicodeError):
        return default


def _command_output(argv):
    try:
        return subprocess.run(argv, check=False, text=True, capture_output=True,
                              timeout=5).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def machine_fingerprint():
    """Describe the hardware the guest exposes, without guessing a host SKU."""
    if observability is not None:
        cloud = {}
        try:
            item = request("GET", "/servers/" + server_id())["server"]
            cloud = {
                "server_id": item.get("id"),
                "server_type": (item.get("server_type") or {}).get("name"),
                "location": (item.get("datacenter") or {}).get("location", {}).get("name"),
            }
        except Exception as exc:
            cloud = {"unavailable": str(exc)}
        result = observability.capture_hardware_fingerprint(
            server_type=cloud.get("server_type")).to_dict()
        policies = {
            "governors": sorted({value for path in pathlib.Path(
                "/sys/devices/system/cpu").glob("cpu[0-9]*/cpufreq/scaling_governor")
                if (value := _text(path))}),
            "drivers": sorted({value for path in pathlib.Path(
                "/sys/devices/system/cpu").glob("cpu[0-9]*/cpufreq/scaling_driver")
                if (value := _text(path))}),
            "boost": _text("/sys/devices/system/cpu/cpufreq/boost"),
        }
        result.update({"cloud": cloud, "cpu_frequency_policy": policies})
        return result
    cpuinfo = _text("/proc/cpuinfo", "")
    first = {}
    for line in cpuinfo.splitlines():
        if not line.strip():
            break
        if ":" in line:
            key, value = line.split(":", 1)
            first[key.strip()] = value.strip()
    topology = []
    for cpu in sorted(pathlib.Path("/sys/devices/system/cpu").glob("cpu[0-9]*"),
                      key=lambda p: int(p.name[3:])):
        topo = cpu / "topology"
        topology.append({
            "cpu": int(cpu.name[3:]),
            "package": _text(topo / "physical_package_id"),
            "core": _text(topo / "core_id"),
            "thread_siblings": _text(topo / "thread_siblings_list"),
        })
    caches = []
    seen = set()
    for cache in pathlib.Path("/sys/devices/system/cpu/cpu0/cache").glob("index*"):
        item = {
            "level": _text(cache / "level"), "type": _text(cache / "type"),
            "size": _text(cache / "size"),
            "shared_cpus": _text(cache / "shared_cpu_list"),
        }
        key = tuple(item.values())
        if key not in seen:
            caches.append(item)
            seen.add(key)
    memory_kib = None
    match = re.search(r"^MemTotal:\s+(\d+)\s+kB", _text("/proc/meminfo", ""), re.MULTILINE)
    if match:
        memory_kib = int(match.group(1))
    cloud = {}
    try:
        sid = server_id()
        cloud["server_id"] = int(sid) if sid.isdigit() else sid
        item = request("GET", "/servers/" + sid)["server"]
        cloud = {
            "server_id": item.get("id", cloud["server_id"]),
            "server_type": (item.get("server_type") or {}).get("name"),
            "location": (item.get("datacenter") or {}).get("location", {}).get("name"),
        }
    except Exception as exc:
        cloud["details_unavailable"] = str(exc)
    governors = sorted({value for path in pathlib.Path("/sys/devices/system/cpu").glob(
        "cpu[0-9]*/cpufreq/scaling_governor") if (value := _text(path))})
    frequencies = sorted({value for path in pathlib.Path("/sys/devices/system/cpu").glob(
        "cpu[0-9]*/cpufreq/scaling_cur_freq") if (value := _text(path))})
    uname = os.uname()
    return {
        "cloud": cloud,
        "cpu": {"vendor": first.get("vendor_id"), "model": first.get("model name"),
                "logical_cpus": os.cpu_count(), "topology": topology, "caches": caches,
                "governors": governors, "current_frequencies_khz": frequencies},
        "memory_kib": memory_kib,
        "kernel": {"system": uname.sysname, "release": uname.release,
                   "machine": uname.machine},
        "hypervisor": _command_output(["systemd-detect-virt"]),
    }


def _proc_stat():
    fields = (_text("/proc/stat", "cpu 0") or "cpu 0").splitlines()[0].split()[1:]
    values = [int(value) for value in fields]
    return {"total_ticks": sum(values), "steal_ticks": values[7] if len(values) > 7 else 0}


def _network_counters():
    received = transmitted = 0
    for line in (_text("/proc/net/dev", "") or "").splitlines()[2:]:
        if ":" not in line:
            continue
        _interface, values = line.split(":", 1)
        fields = values.split()
        if len(fields) >= 9:
            received += int(fields[0])
            transmitted += int(fields[8])
    return {"received_bytes": received, "transmitted_bytes": transmitted}


def artifact_manifest(state):
    root = state.get("artifact_location")
    result = {"job_id": state["job_id"], "state": state["state"],
              "artifact_location": root, "files": []}
    if not root:
        return result
    base = pathlib.Path(root)
    if not base.is_dir():
        return result
    for path in sorted(base.rglob("*")):
        if path.is_file():
            stat = path.stat()
            result["files"].append({"path": path.relative_to(base).as_posix(),
                                    "size": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    return result


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
    for key, value in values.items():
        if key == "quiet-machine-retain-until":
            try:
                value = max(int(current.get(key, "0")), int(value))
            except (TypeError, ValueError):
                pass
        current[key] = str(value)
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


def parse_cpu_list(value):
    if not value:
        return set()
    cpus = set()
    for component in value.split(","):
        component = component.strip()
        if not component:
            raise ValueError("CPU list contains an empty component")
        if "-" in component:
            first, last = (int(part) for part in component.split("-", 1))
            if first < 0 or last < first:
                raise ValueError(f"invalid CPU range: {component}")
            values = range(first, last + 1)
        else:
            values = [int(component)]
        for cpu in values:
            if cpu < 0 or cpu in cpus:
                raise ValueError(f"invalid or duplicate CPU ID: {cpu}")
            cpus.add(cpu)
    return cpus


def render_cpu_list(cpus):
    return ",".join(str(cpu) for cpu in sorted(cpus))


def normalize_affinity(args):
    available = set(os.sched_getaffinity(0))
    helper = parse_cpu_list(getattr(args, "helper_cpus", None))
    requested = parse_cpu_list(getattr(args, "cpus", None))
    benchmark = requested or (available - helper)
    unknown = (benchmark | helper) - available
    overlap = benchmark & helper
    if unknown:
        raise ValueError("CPU IDs are unavailable: " + render_cpu_list(unknown))
    if overlap:
        raise ValueError("benchmark and helper CPU lists overlap: "
                         + render_cpu_list(overlap))
    if not benchmark:
        raise ValueError("CPU reservation leaves no CPU for the benchmark")
    args.cpus = render_cpu_list(benchmark) if (requested or helper) else None
    args.helper_cpus = render_cpu_list(helper) if helper else None
    return {"available": render_cpu_list(available),
            "requested_task": args.cpus,
            "requested_helper": args.helper_cpus,
            "disjoint": True}


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
            environment = ["env", f"QUIET_MACHINE_HELPER_CPUS={getattr(args, 'helper_cpus', None) or ''}"]
            pinned = (["taskset", "--cpu-list", args.cpus]
                      if getattr(args, "cpus", None) else [])
            argv = [
                "timeout", "--signal=TERM", "--kill-after=30s", str(args.timeout),
                "sudo", "-u", "quiet", "--preserve-env=QUIET_MACHINE_ARTIFACTS", "--",
            ] + environment + pinned + command
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


def _pid_identity(pid):
    try:
        raw = pathlib.Path(f"/proc/{pid}/stat").read_text()
        # The parenthesized comm field may itself contain spaces.
        fields = raw[raw.rfind(")") + 2:].split()
        return {"pid": pid, "start_ticks": int(fields[19]),
                "boot_id": _text("/proc/sys/kernel/random/boot_id")}
    except (OSError, IndexError, ValueError):
        return None


def _identity_alive(identity):
    if not identity:
        return False
    return _pid_identity(identity.get("pid")) == identity


def _terminate_group(pid, grace=10, process=None):
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    if process is not None:
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            pass
    else:
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline:
            try:
                os.killpg(pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.1)
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _unit_main_pid(unit, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = _command_output(["systemctl", "show", "--property=MainPID",
                                 "--value", unit])
        try:
            pid = int(value or "0")
        except ValueError:
            pid = 0
        if pid > 0:
            return pid
        time.sleep(0.05)
    return None


def _unit_property(unit, name):
    return _command_output(["systemctl", "show", f"--property={name}",
                            "--value", unit])


def _unit_cgroup(unit):
    value = _unit_property(unit, "ControlGroup")
    if not value or not value.startswith("/"):
        return None
    path = pathlib.Path("/sys/fs/cgroup") / value.lstrip("/")
    return path if path.is_dir() else None


def _cgroup_pids(path):
    """Return every process in a transient unit, including nested cgroups."""
    result = set()
    if path is None:
        return result
    for procs in [path / "cgroup.procs", *path.glob("**/cgroup.procs")]:
        try:
            result.update(int(value) for value in procs.read_text().split())
        except (OSError, ValueError):
            continue
    return result


def _pid_metrics(pids):
    """Best-effort instantaneous details for an authoritative cgroup PID set."""
    threads = 0
    affinities = set()
    active_cpus = set()
    for pid in pids:
        try:
            status = _text(f"/proc/{pid}/status", "")
            match = re.search(r"^Cpus_allowed_list:\s+(.+)$", status, re.MULTILINE)
            if match:
                affinities.add(match.group(1).strip())
            tasks = list(pathlib.Path(f"/proc/{pid}/task").glob("[0-9]*"))
            threads += len(tasks)
            for task in tasks:
                raw_stat = _text(task / "stat", "")
                stat = raw_stat[raw_stat.rfind(")") + 2:].split()
                if len(stat) > 36:
                    active_cpus.add(int(stat[36]))
        except (OSError, ValueError):
            continue
    return {"active_threads": threads, "active_cpus": sorted(active_cpus),
            "affinity": sorted(affinities)}


def _cgroup_accounting(path):
    """Read cgroup-v2 lifetime counters that survive sampling gaps."""
    if path is None:
        return {"authoritative": False}
    cpu = _text(path / "cpu.stat", "")
    cpu_values = {}
    for line in cpu.splitlines():
        fields = line.split()
        if len(fields) == 2:
            try:
                cpu_values[fields[0]] = int(fields[1])
            except ValueError:
                pass
    memory_peak = _text(path / "memory.peak")
    memory_current = _text(path / "memory.current")
    io_read = io_write = 0
    io_available = False
    for line in (_text(path / "io.stat", "") or "").splitlines():
        for field in line.split()[1:]:
            key, separator, value = field.partition("=")
            if not separator:
                continue
            try:
                if key == "rbytes":
                    io_read += int(value)
                    io_available = True
                elif key == "wbytes":
                    io_write += int(value)
                    io_available = True
            except ValueError:
                pass
    try:
        peak = int(memory_peak)
        current = int(memory_current)
        usage_usec = int(cpu_values["usage_usec"])
        authoritative = True
    except (TypeError, ValueError, KeyError):
        peak = current = usage_usec = None
        authoritative = False
    return {
        "authoritative": authoritative,
        "cpu_usage_seconds": usage_usec / 1_000_000 if usage_usec is not None else None,
        "memory_peak_bytes": peak, "memory_current_bytes": current,
        "read_bytes": io_read if io_available else None,
        "write_bytes": io_write if io_available else None,
    }


def _unit_metrics(unit):
    path = _unit_cgroup(unit)
    accounting = _cgroup_accounting(path)
    return {**accounting, **_pid_metrics(_cgroup_pids(path))}


def _terminate_unit(unit, process=None, grace=10):
    subprocess.run(["systemctl", "kill", "--kill-whom=all", "--signal=TERM", unit],
                   check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if process is not None:
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            pass
    subprocess.run(["systemctl", "kill", "--kill-whom=all", "--signal=KILL", unit],
                   check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["systemctl", "stop", unit], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["systemctl", "reset-failed", unit], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _unit_active(unit):
    return bool(unit and subprocess.run(
        ["systemctl", "is-active", "--quiet", unit], check=False,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0)


def _final_state(job_id, state, exit_code, started, telemetry, error=None):
    finished = time.time()
    if isinstance(exit_code, int) and exit_code < 0:
        exit_code = 128 - exit_code

    def finish(current):
        final_state, final_code = state, exit_code
        if current.get("cancel_requested"):
            final_state, final_code = "cancelled", None
        elif final_state == "timeout":
            final_code = 124
        reasons = {"success": "exit_zero", "failure": "nonzero_exit",
                   "cancelled": "cancellation_requested", "timeout": "deadline_exceeded",
                   "infrastructure_lost": "supervisor_error"}
        requested = current.get("affinity", {})
        effective = telemetry.get("effective_affinity", [])
        canonical = lambda value: render_cpu_list(parse_cpu_list(value))
        helper = requested.get("requested_helper")
        requested_task = requested.get("requested_task")
        canonical_helper = canonical(helper) if helper else None
        canonical_task = canonical(requested_task) if requested_task else None
        canonical_effective = sorted({canonical(value) for value in effective})
        effective_helper = [value for value in canonical_effective
                            if canonical_helper and value == canonical_helper]
        effective_task = [value for value in canonical_effective
                          if value not in effective_helper]
        result = {
            "state": final_state, "finished_at": utc_timestamp(finished),
            "finished_at_unix": finished,
            "elapsed_seconds": max(0.0, finished - started),
            "exit_code": final_code, "terminal_reason": reasons[final_state],
            "telemetry": telemetry,
            "affinity": {
                **requested, "effective_task": effective_task,
                "effective_helper": effective_helper,
                "matches_request": (
                    (not canonical_task or effective_task == [canonical_task])
                    and (not canonical_helper
                         or effective_helper == [canonical_helper])),
            },
            "artifacts": artifact_manifest(current)["files"],
        }
        if error:
            result["error"] = error
        return {**current, **result}

    mutate_state(job_id, finish)


def job_worker(args):
    """Detached supervisor. The launcher passes both locks across exec."""
    global_handle = os.fdopen(args.lock_fd, "a+")
    complete_handle = os.fdopen(args.complete_fd, "a+")
    job_id = args.job_id
    started = time.time()
    task_started = None
    proc = None
    stat_before = network_before = None
    peak = {"active_threads": 0, "max_active_cores": 0,
            "observed_cpus": [], "affinity": [], "peak_rss_bytes": 0,
            "read_bytes": 0, "write_bytes": 0, "sample_count": 0}
    try:
        if getattr(args, "defer_start", False):
            deadline = time.monotonic() + getattr(args, "reservation_timeout", 600)
            while not (job_dir(job_id) / "start").exists():
                if read_state(job_id).get("cancel_requested"):
                    _final_state(job_id, "cancelled", None, started, {})
                    return 0
                if time.monotonic() >= deadline:
                    _final_state(job_id, "infrastructure_lost", None, started, {},
                                 "reserved job was not started before its deadline")
                    return 125
                time.sleep(0.1)
            args.retain_until = max(
                args.retain_until, int(read_state(job_id).get("retain_until", 0)))
        fingerprint = machine_fingerprint()
        write_state(job_id, {"supervisor": _pid_identity(os.getpid()),
                             "machine_fingerprint": fingerprint,
                             "server_id": fingerprint.get("cloud", {}).get("server_id")})
        if read_state(job_id).get("cancel_requested"):
            _final_state(job_id, "cancelled", None, started, {})
            return 0
        set_labels(**{
            "quiet-machine-state": "busy",
            "quiet-machine-job": job_id,
            "quiet-machine-hard-expiry": int(started) + args.timeout + 120,
            "quiet-machine-retain-until": args.retain_until,
        })
        ensure_user()
        # Guest-wide steal/network counters bracket the task. Workload CPU,
        # memory and I/O come from its transient cgroup, not the systemd-run
        # client process or sampling alone.
        stat_before = _proc_stat()
        network_before = _network_counters()
        helper_prefix = (f"taskset --cpu-list {args.helper_cpus}"
                         if args.helper_cpus else "")
        pinned = (["taskset", "--cpu-list", args.cpus] if args.cpus else [])
        unit = "quiet-machine-job-" + job_id
        argv = [
            "systemd-run", "--quiet", "--wait", "--pipe",
            f"--unit={unit}", "--property=KillMode=control-group",
            "--property=TimeoutStopSec=30s",
            f"--property=RuntimeMaxSec={args.timeout}s",
            "--property=CPUAccounting=yes", "--property=MemoryAccounting=yes",
            "--property=IOAccounting=yes", "--uid=quiet",
            f"--working-directory={args.cwd}", "--setenv=HOME=/home/quiet",
            "--setenv=PATH=/home/quiet/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            f"--setenv=QUIET_MACHINE_ARTIFACTS={os.environ.get('QUIET_MACHINE_ARTIFACTS', '')}",
            f"--setenv=QUIET_MACHINE_BENCHMARK_CPUS={args.cpus or ''}",
            f"--setenv=QUIET_MACHINE_HELPER_CPUS={args.helper_cpus or ''}",
            f"--setenv=QUIET_MACHINE_HELPER_PREFIX={helper_prefix}",
            *pinned, *args.command,
        ]
        log_path = job_dir(job_id) / "output.log"
        with log_path.open("ab", buffering=0) as output:
            task_started = time.time()
            set_labels(**{"quiet-machine-hard-expiry": int(task_started) + args.timeout + 120})
            proc = subprocess.Popen(argv, cwd=args.cwd, stdout=output,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            task_pid = _unit_main_pid(unit) or proc.pid
            TASK_PID.parent.mkdir(parents=True, exist_ok=True)
            TASK_PID.write_text(str(task_pid) + "\n")
            ACTIVE_JOB.write_text(job_id + "\n")
            write_state(job_id, {
                "state": "running", "started_at": utc_timestamp(task_started),
                "started_at_unix": task_started, "process": _pid_identity(task_pid),
                "unit": unit,
            })
            deadline = time.monotonic() + args.timeout
            timed_out = False
            while proc.poll() is None:
                current = _unit_metrics(unit)
                peak["sample_count"] += 1
                peak["active_threads"] = max(peak["active_threads"], current["active_threads"])
                peak["max_active_cores"] = max(peak["max_active_cores"],
                                                len(current["active_cpus"]))
                peak["observed_cpus"] = sorted(set(peak["observed_cpus"])
                                                | set(current["active_cpus"]))
                peak["peak_rss_bytes"] = max(peak["peak_rss_bytes"],
                                             current.get("memory_peak_bytes") or 0)
                peak["read_bytes"] = max(peak["read_bytes"],
                                         current.get("read_bytes") or 0)
                peak["write_bytes"] = max(peak["write_bytes"],
                                          current.get("write_bytes") or 0)
                peak["cpu_usage_seconds"] = max(
                    peak.get("cpu_usage_seconds", 0),
                    current.get("cpu_usage_seconds") or 0)
                peak["authoritative"] = bool(
                    peak.get("authoritative") or current.get("authoritative"))
                peak["affinity"] = sorted(set(peak["affinity"]) | set(current["affinity"]))
                if time.monotonic() >= deadline:
                    timed_out = True
                    _terminate_unit(unit, process=proc)
                    break
                time.sleep(0.25)
            code = proc.wait()
            # Capture lifetime cgroup counters before cleanup removes the unit.
            current = _unit_metrics(unit)
            peak["peak_rss_bytes"] = max(peak["peak_rss_bytes"],
                                         current.get("memory_peak_bytes") or 0)
            peak["read_bytes"] = max(peak["read_bytes"], current.get("read_bytes") or 0)
            peak["write_bytes"] = max(peak["write_bytes"], current.get("write_bytes") or 0)
            peak["cpu_usage_seconds"] = max(peak.get("cpu_usage_seconds", 0),
                                             current.get("cpu_usage_seconds") or 0)
            peak["authoritative"] = bool(
                peak.get("authoritative") or current.get("authoritative"))
            # A successful leader exit is not sufficient for reuse. Drain the
            # whole transient unit so background descendants cannot overlap the
            # next benchmark or append after completion.
            _terminate_unit(unit)
        stat_after = _proc_stat()
        network_after = _network_counters()
        elapsed = max(time.time() - task_started, 0.000001)
        cpu_seconds = peak.get("cpu_usage_seconds", 0)
        total_ticks = stat_after["total_ticks"] - stat_before["total_ticks"]
        steal_ticks = stat_after["steal_ticks"] - stat_before["steal_ticks"]
        tick_hz = os.sysconf("SC_CLK_TCK")
        telemetry = {
            "peak_rss_bytes": peak["peak_rss_bytes"],
            "authoritative_cgroup_counters": bool(peak.get("authoritative")),
            "sample_count": peak["sample_count"],
            "task_cpu_seconds": cpu_seconds,
            "task_cpu_percent": cpu_seconds / elapsed * 100,
            "active_threads": {"max": peak["active_threads"]},
            "active_cores": {"max": peak["max_active_cores"],
                             "observed_cpus": peak["observed_cpus"]},
            "effective_affinity": peak["affinity"],
            "cpu_steal_seconds": steal_ticks / tick_hz,
            "cpu_steal_percent": (steal_ticks / total_ticks * 100) if total_ticks > 0 else None,
            "disk": {"scope": "transient-unit-cgroup-v2", "sampling_interval_seconds": 0.25,
                     "read_bytes": peak["read_bytes"],
                     "write_bytes": peak["write_bytes"]},
            "network": {"scope": "guest",
                        "sampling_interval_seconds": 0.25,
                        "received_bytes": max(0, network_after["received_bytes"] - network_before["received_bytes"]),
                        "transmitted_bytes": max(0, network_after["transmitted_bytes"] - network_before["transmitted_bytes"])},
        }
        if timed_out:
            _final_state(job_id, "timeout", 124, task_started, telemetry)
        elif code == 0:
            _final_state(job_id, "success", 0, task_started, telemetry)
        else:
            _final_state(job_id, "failure", code, task_started, telemetry)
    except BaseException as exc:
        if proc is not None and proc.poll() is None:
            if "unit" in locals():
                _terminate_unit(unit, process=proc)
            else:
                _terminate_group(proc.pid, process=proc)
        try:
            _final_state(job_id, "infrastructure_lost", None, task_started or started, peak,
                         f"{type(exc).__name__}: {exc}")
        except Exception:
            pass
        return 125
    finally:
        for path in (TASK_PID, ACTIVE_JOB):
            try:
                if path == ACTIVE_JOB and _text(path) != job_id:
                    continue
                path.unlink(missing_ok=True)
            except OSError:
                pass
        try:
            set_labels(**{"quiet-machine-state": "ready", "quiet-machine-job": "",
                          "quiet-machine-retain-until": args.retain_until,
                          "quiet-machine-hard-expiry": args.retain_until + 120})
        except Exception as exc:
            try:
                write_state(job_id, {"release_error": f"{type(exc).__name__}: {exc}"})
            except Exception:
                pass
        # Explicit close documents the ordering: durable terminal state, then
        # completion notification, then pool availability.
        complete_handle.close()
        global_handle.close()
    return 0


def start_detached(args):
    if not args.job_id:
        raise ValueError("run --detach requires --job-id")
    affinity = normalize_affinity(args)
    directory = job_dir(args.job_id)
    JOBS.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        directory.mkdir(mode=0o700)
    except FileExistsError:
        raise ValueError(f"job already exists: {args.job_id}") from None
    global_handle = lock()
    if global_handle is None:
        directory.rmdir()
        return 75
    complete_handle = (directory / "complete.lock").open("a+")
    fcntl.flock(complete_handle, fcntl.LOCK_EX)
    now = time.time()
    state = {
        "version": 1, "job_id": args.job_id,
        "state": "reserved" if getattr(args, "defer_start", False) else "queued",
        "command": args.command, "cwd": args.cwd, "timeout_seconds": args.timeout,
        "retain_until": args.retain_until, "created_at": utc_timestamp(now),
        "created_at_unix": now,
        "artifact_location": os.environ.get("QUIET_MACHINE_ARTIFACTS"),
        "artifact_dir": os.environ.get("QUIET_MACHINE_ARTIFACTS"),
        "affinity": {**affinity, "effective_task": []},
        "exit_code": None, "cancel_requested": False,
    }
    write_state(args.job_id, state)
    set_labels(**{
        "quiet-machine-state": "busy", "quiet-machine-job": args.job_id,
        "quiet-machine-hard-expiry": int(now) + (
            getattr(args, "reservation_timeout", 600)
            if getattr(args, "defer_start", False) else args.timeout) + 120,
        "quiet-machine-retain-until": args.retain_until,
    })
    argv = [sys.executable, str(pathlib.Path(__file__).resolve()), "_job-worker",
            "--job-id", args.job_id, "--timeout", str(args.timeout),
            "--retain-until", str(args.retain_until), "--cwd", args.cwd,
            "--lock-fd", str(global_handle.fileno()),
            "--complete-fd", str(complete_handle.fileno()), "--", *args.command]
    if getattr(args, "defer_start", False):
        separator = argv.index("--")
        argv[separator:separator] = ["--defer-start", "--reservation-timeout",
                                    str(getattr(args, "reservation_timeout", 600))]
    if getattr(args, "helper_cpus", None):
        separator = argv.index("--")
        argv[separator:separator] = ["--helper-cpus", args.helper_cpus]
    if getattr(args, "cpus", None):
        separator = argv.index("--")
        argv[separator:separator] = ["--cpus", args.cpus]
    try:
        worker = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL, start_new_session=True,
                                  close_fds=True,
                                  pass_fds=(global_handle.fileno(), complete_handle.fileno()))
        write_state(args.job_id, {"supervisor": _pid_identity(worker.pid)})
    except BaseException as exc:
        write_state(args.job_id, {"state": "infrastructure_lost",
                                  "finished_at": utc_timestamp(), "exit_code": None,
                                  "terminal_reason": "launch_failed",
                                  "error": f"{type(exc).__name__}: {exc}"})
        complete_handle.close()
        global_handle.close()
        try:
            set_labels(**{"quiet-machine-state": "ready", "quiet-machine-job": "",
                          "quiet-machine-retain-until": args.retain_until,
                          "quiet-machine-hard-expiry": args.retain_until + 120})
        except Exception:
            pass
        return 125
    complete_handle.close()
    global_handle.close()
    print(json.dumps({"event": "job_reserved" if getattr(args, "defer_start", False) else "job_started",
                      "job_id": args.job_id,
                      "state": "reserved" if getattr(args, "defer_start", False) else "queued"},
                     sort_keys=True))
    return 0


def start_job(args):
    state = reconcile_state(args.job_id)
    if state.get("state") != "reserved":
        raise ValueError(f"job {args.job_id} is {state.get('state')}, not reserved")
    state = mutate_state(args.job_id, lambda current: {
        **current, "state": "queued", "start_requested_at": utc_timestamp(),
        "retain_until": max(int(current.get("retain_until", 0)),
                            args.retain_until),
    })
    (job_dir(args.job_id) / "start").touch(exist_ok=False)
    print(json.dumps({"event": "job_started", **state}, sort_keys=True))
    return 0


def reconcile_state(job_id):
    def reconcile(state):
        if state.get("state") in TERMINAL_STATES:
            return state
        if _identity_alive(state.get("supervisor")):
            return {**state, "elapsed_seconds": max(
                0.0, time.time() - state.get(
                    "started_at_unix", state["created_at_unix"]))}
        unit = state.get("unit")
        if _unit_active(unit):
            # The supervisor owns the pool lock, but systemd owns the workload.
            # If the former disappears, drain the latter before publishing a
            # terminal state so this VM can never be reused concurrently.
            _terminate_unit(unit)
        now = time.time()
        return {**state,
            "state": "infrastructure_lost", "exit_code": None,
            "finished_at": utc_timestamp(now), "finished_at_unix": now,
            "elapsed_seconds": max(0.0, now - state.get("started_at_unix", state["created_at_unix"])),
            "terminal_reason": "supervisor_disappeared",
            "error": "detached supervisor disappeared without recording completion",
        }
    return mutate_state(job_id, reconcile)


def status_job(args):
    print(json.dumps(reconcile_state(args.job_id), sort_keys=True))
    return 0


def list_jobs(_args):
    JOBS.mkdir(mode=0o700, parents=True, exist_ok=True)
    states = []
    for directory in JOBS.iterdir():
        if directory.is_dir() and (directory / "state.json").exists():
            try:
                states.append(reconcile_state(directory.name))
            except (OSError, ValueError, json.JSONDecodeError):
                continue
    states.sort(key=lambda item: item.get("created_at_unix", 0), reverse=True)
    print(json.dumps(states, sort_keys=True))
    return 0


def _wait_completion(job_id):
    # The detached supervisor inherits this locked file description from its
    # launcher. Acquiring a new lock therefore blocks without polling.
    with (job_dir(job_id) / "complete.lock").open("a+") as complete:
        fcntl.flock(complete, fcntl.LOCK_EX)


def wait_job(args):
    _wait_completion(args.job_id)
    state = reconcile_state(args.job_id)
    print(json.dumps({"event": "job_completed", **state}, sort_keys=True))
    return 0


def logs_job(args):
    # Binary pass-through avoids newline rewriting and keeps the byte offset
    # exact, so each byte is emitted once even while the log grows.
    read_state(args.job_id)
    path = job_dir(args.job_id) / "output.log"
    path.touch(exist_ok=True)
    with path.open("rb") as source:
        source.seek(getattr(args, "since_byte", 0))
        while True:
            chunk = source.read(64 * 1024)
            if chunk:
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
                continue
            if not args.follow:
                break
            with (job_dir(args.job_id) / "complete.lock").open("a+") as complete:
                try:
                    fcntl.flock(complete, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # Supervisor is done. One more read closes the race between
                    # the last log write and release of the completion lock.
                    chunk = source.read()
                    if chunk:
                        sys.stdout.buffer.write(chunk)
                        sys.stdout.buffer.flush()
                    break
                except BlockingIOError:
                    time.sleep(0.2)
    return 0


def artifacts_job(args):
    print(json.dumps(artifact_manifest(reconcile_state(args.job_id)), sort_keys=True))
    return 0


def cancel_job(args):
    state = reconcile_state(args.job_id)
    if state.get("state") in TERMINAL_STATES:
        if _unit_active(state.get("unit")):
            _terminate_unit(state["unit"])
        print(json.dumps(state, sort_keys=True))
        return 0
    unit = state.get("unit")
    active_unit = _unit_active(unit)
    identity = state.get("process")
    active_group = _identity_alive(identity)
    cancellable = state.get("state") in {"reserved", "queued"} or active_unit or active_group
    if cancellable:
        state = write_state(args.job_id, {"cancel_requested": True,
                                          "cancel_requested_at": utc_timestamp(),
                                          "cancel_signalled": active_unit})
        if active_unit:
            _terminate_unit(unit)
        elif active_group:
            _terminate_group(identity["pid"])
    _wait_completion(args.job_id)
    print(json.dumps(reconcile_state(args.job_id), sort_keys=True))
    return 0


def interactive_shell(args):
    """Run a real login shell in the SSH PTY while holding the pool lock."""
    handle = lock()
    if handle is None:
        return 75
    now = int(time.time())
    proc = None
    old_foreground = None
    saved_handlers = {}
    try:
        set_labels(**{"quiet-machine-state": "busy",
                      "quiet-machine-hard-expiry": now + args.timeout + 120,
                      "quiet-machine-retain-until": args.retain_until})
        ensure_user()
        argv = ["sudo", "-u", "quiet",
                "--preserve-env=TERM,COLORTERM,LANG,LC_ALL", "--", "bash", "-il"]
        proc = subprocess.Popen(argv, cwd=args.cwd, start_new_session=False,
                                preexec_fn=os.setpgrp)
        TASK_PID.write_text(str(proc.pid) + "\n")

        def forward(signum, _frame):
            if proc.poll() is None:
                try:
                    os.killpg(proc.pid, signum)
                except ProcessLookupError:
                    pass

        for signum in (signal.SIGHUP, signal.SIGTERM):
            saved_handlers[signum] = signal.signal(signum, forward)
        if os.isatty(0):
            saved_handlers[signal.SIGTTOU] = signal.signal(signal.SIGTTOU, signal.SIG_IGN)
            saved_handlers[signal.SIGTTIN] = signal.signal(signal.SIGTTIN, signal.SIG_IGN)
            old_foreground = os.tcgetpgrp(0)
            os.tcsetpgrp(0, proc.pid)
        try:
            code = proc.wait(timeout=args.timeout)
            return 128 - code if code < 0 else code
        except subprocess.TimeoutExpired:
            _terminate_group(proc.pid, process=proc)
            proc.wait()
            return 124
    finally:
        if proc is not None:
            _terminate_group(proc.pid, process=proc if proc.poll() is None else None)
        if old_foreground is not None:
            try:
                os.tcsetpgrp(0, old_foreground)
            except OSError:
                pass
        for signum, handler in saved_handlers.items():
            signal.signal(signum, handler)
        TASK_PID.unlink(missing_ok=True)
        try:
            set_labels(**{"quiet-machine-state": "ready",
                          "quiet-machine-retain-until": args.retain_until,
                          "quiet-machine-hard-expiry": args.retain_until + 120})
        finally:
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


def _main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("arm")
    sub.add_parser("probe")
    cancellation = sub.add_parser("cancel")
    cancellation.add_argument("job_id", nargs="?")
    sub.add_parser("reaper")
    sub.add_parser("jobs")
    for name in ("status", "wait", "artifacts"):
        p = sub.add_parser(name)
        p.add_argument("job_id")
    start = sub.add_parser("start")
    start.add_argument("job_id")
    start.add_argument("--retain-until", type=int, required=True)
    for name in ("logs", "attach"):
        p = sub.add_parser(name)
        p.add_argument("job_id")
        p.add_argument("--follow", action="store_true")
        p.add_argument("--since-byte", type=int, default=0)
    shell_parser = sub.add_parser("shell")
    shell_parser.add_argument("--timeout", type=int, required=True)
    shell_parser.add_argument("--retain-until", type=int, required=True)
    shell_parser.add_argument("--cwd", default="/home/quiet")
    for name in ("run", "setup"):
        p = sub.add_parser(name)
        p.add_argument("--timeout", type=int, required=True)
        p.add_argument("--retain-until", type=int, required=True)
        p.add_argument("--cwd", default="/")
        p.add_argument("--profile", default="")
        if name == "run":
            p.add_argument("--detach", action="store_true")
            p.add_argument("--job-id")
            p.add_argument("--cpus")
            p.add_argument("--helper-cpus")
            p.add_argument("--defer-start", action="store_true")
            p.add_argument("--reservation-timeout", type=int, default=600)
        p.add_argument("command", nargs=argparse.REMAINDER)
    worker = sub.add_parser("_job-worker", help=argparse.SUPPRESS)
    worker.add_argument("--job-id", required=True)
    worker.add_argument("--timeout", type=int, required=True)
    worker.add_argument("--retain-until", type=int, required=True)
    worker.add_argument("--cwd", required=True)
    worker.add_argument("--lock-fd", type=int, required=True)
    worker.add_argument("--complete-fd", type=int, required=True)
    worker.add_argument("--cpus")
    worker.add_argument("--helper-cpus")
    worker.add_argument("--defer-start", action="store_true")
    worker.add_argument("--reservation-timeout", type=int, default=600)
    worker.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.action in ("run", "setup", "_job-worker") and args.command[:1] == ["--"]:
        args.command = args.command[1:]
    if args.action in ("run", "setup", "_job-worker") and not args.command:
        parser.error(f"{args.action} requires a command after --")
    funcs = {
        "arm": arm, "probe": probe,
        "cancel": lambda a: cancel_job(a) if a.job_id else cancel(a),
        "run": lambda a: start_detached(a) if a.detach else run_locked(a),
        "setup": setup, "shell": interactive_shell, "reaper": reaper,
        "status": status_job, "jobs": list_jobs, "wait": wait_job,
        "start": start_job,
        "logs": logs_job, "attach": lambda a: logs_job(
            argparse.Namespace(job_id=a.job_id, follow=True,
                               since_byte=a.since_byte)),
        "artifacts": artifacts_job, "_job-worker": job_worker,
    }
    return funcs[args.action](args) or 0


def main():
    try:
        return _main()
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"quiet-machine-agent: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
