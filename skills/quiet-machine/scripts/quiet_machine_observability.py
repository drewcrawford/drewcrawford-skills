#!/usr/bin/env python3
"""Guest fingerprinting, task telemetry, and CPU-affinity helpers.

The module deliberately has no dependency on the quiet-machine controller.  Its
parsers accept captured text so callers can persist the raw observations and
tests can describe virtual hardware without depending on the machine running
the test suite.  Collector functions accept an injectable command runner.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import platform
import re
import subprocess
from typing import Callable, Iterable, Mapping, Sequence


CommandRunner = Callable[[Sequence[str]], str]


def _integer(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.search(r"-?\d+", value.replace(",", ""))
    return int(match.group()) if match else None


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.search(r"-?(?:\d+(?:\.\d*)?|\.\d+)", value.replace(",", ""))
    return float(match.group()) if match else None


def _size_bytes(value: str | None) -> int | None:
    """Parse the human-readable sizes emitted by lscpu and /proc."""
    if value is None:
        return None
    match = re.search(r"([0-9.]+)\s*([kmgtpe]?i?b)?", value.strip(), re.I)
    if not match:
        return None
    number = float(match.group(1))
    unit = (match.group(2) or "b").lower()
    powers = {
        "b": 0, "kb": 1, "kib": 1, "mb": 2, "mib": 2,
        "gb": 3, "gib": 3, "tb": 4, "tib": 4, "pb": 5, "pib": 5,
        "eb": 6, "eib": 6,
    }
    return int(number * 1024 ** powers[unit])


def parse_lscpu(text: str) -> dict[str, str]:
    """Parse either ``lscpu`` text or ``lscpu --json`` output."""
    stripped = text.strip()
    if not stripped:
        return {}
    if stripped.startswith("{"):
        data = json.loads(stripped)
        entries = data.get("lscpu", [])
        return {
            str(item["field"]).rstrip(":").strip(): str(item.get("data", "")).strip()
            for item in entries if "field" in item
        }
    result: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def parse_cpuinfo(text: str) -> dict[str, str]:
    """Return stable identity fields from the first /proc/cpuinfo processor."""
    block = text.strip().split("\n\n", 1)[0]
    raw = parse_lscpu(block)
    return {
        "vendor": raw.get("vendor_id") or raw.get("CPU implementer") or "unknown",
        "model": raw.get("model name") or raw.get("Processor") or raw.get("Hardware") or "unknown",
    }


def parse_meminfo(text: str) -> int | None:
    """Return MemTotal in bytes."""
    for line in text.splitlines():
        if line.startswith("MemTotal:"):
            value = _integer(line)
            return value * 1024 if value is not None else None
    return None


def parse_cpufreq(text: str) -> dict[str, int | None]:
    """Summarize supplied sysfs frequency values, expressed in kHz.

    Input lines may be plain integers or ``name=value`` pairs.  Names containing
    ``min`` and ``max`` are treated as policy limits; other values are current
    observations.
    """
    groups: dict[str, list[int]] = {"min": [], "max": [], "current": []}
    for line in text.splitlines():
        key, _, raw = line.partition("=")
        if not _:
            raw, key = key, "current"
        value = _integer(raw)
        if value is None:
            continue
        kind = "min" if "min" in key.lower() else "max" if "max" in key.lower() else "current"
        groups[kind].append(value)
    return {
        "min_khz": min(groups["min"]) if groups["min"] else None,
        "max_khz": max(groups["max"]) if groups["max"] else None,
        "current_min_khz": min(groups["current"]) if groups["current"] else None,
        "current_max_khz": max(groups["current"]) if groups["current"] else None,
    }


def parse_cpu_topology(text: str) -> list[dict[str, int | None]]:
    """Parse ``lscpu -p=CPU,CORE,SOCKET,NODE`` CSV output."""
    rows: list[dict[str, int | None]] = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = [field.strip() for field in line.split(",")]
        if len(fields) != 4:
            continue
        values = [int(field) if field not in {"", "-"} else None for field in fields]
        rows.append(dict(zip(("cpu", "core", "socket", "node"), values)))
    return sorted(rows, key=lambda row: -1 if row["cpu"] is None else row["cpu"])


def smt_sibling_groups(topology: Iterable[Mapping[str, int | None]]) -> list[list[int]]:
    """Derive guest-visible logical-CPU sibling sets from core/socket IDs."""
    groups: dict[tuple[int, int], list[int]] = {}
    for row in topology:
        cpu, core, socket = row.get("cpu"), row.get("core"), row.get("socket")
        if cpu is None or core is None or socket is None:
            continue
        groups.setdefault((socket, core), []).append(cpu)
    return [sorted(group) for _, group in sorted(groups.items()) if len(group) > 1]


@dataclass(frozen=True)
class HardwareFingerprint:
    """Hardware and environment facts exposed to the guest OS."""

    server_type: str | None
    architecture: str | None
    cpu_vendor: str
    cpu_model: str
    logical_cpus: int | None
    sockets: int | None
    cores_per_socket: int | None
    threads_per_core: int | None
    smt_exposed: bool | None
    numa_nodes: int | None
    cpu_topology: list[dict[str, int | None]]
    smt_sibling_groups: list[list[int]]
    caches_bytes: dict[str, int]
    ram_bytes: int | None
    kernel: str
    hypervisor: str | None
    cpu_frequency_khz: dict[str, int | None]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def fingerprint_from_text(
    *, lscpu: str, cpuinfo: str, meminfo: str, kernel: str,
    virtualization: str = "", cpufreq: str = "", topology: str = "",
    server_type: str | None = None,
) -> HardwareFingerprint:
    """Build a fingerprint from Linux command/file output supplied by a caller."""
    cpu = parse_lscpu(lscpu)
    identity = parse_cpuinfo(cpuinfo)
    threads = _integer(cpu.get("Thread(s) per core"))
    caches: dict[str, int] = {}
    for label in ("L1d cache", "L1i cache", "L2 cache", "L3 cache"):
        size = _size_bytes(cpu.get(label))
        if size is not None:
            caches[label.split()[0].lower()] = size
    hypervisor = cpu.get("Hypervisor vendor") or virtualization.strip() or None
    if hypervisor == "none":
        hypervisor = None
    topology_rows = parse_cpu_topology(topology)
    frequency = parse_cpufreq(cpufreq)
    # Sysfs is preferable.  lscpu values are useful when a hypervisor does not
    # expose cpufreq, and are converted from MHz to the report's kHz unit.
    if frequency["min_khz"] is None and (mhz := _float(cpu.get("CPU min MHz"))) is not None:
        frequency["min_khz"] = int(mhz * 1000)
    if frequency["max_khz"] is None and (mhz := _float(cpu.get("CPU max MHz"))) is not None:
        frequency["max_khz"] = int(mhz * 1000)
    return HardwareFingerprint(
        server_type=server_type,
        architecture=cpu.get("Architecture"),
        cpu_vendor=cpu.get("Vendor ID") or identity["vendor"],
        cpu_model=cpu.get("Model name") or identity["model"],
        logical_cpus=_integer(cpu.get("CPU(s)")),
        sockets=_integer(cpu.get("Socket(s)")),
        cores_per_socket=_integer(cpu.get("Core(s) per socket")),
        threads_per_core=threads,
        smt_exposed=(threads > 1) if threads is not None else None,
        numa_nodes=_integer(cpu.get("NUMA node(s)")),
        cpu_topology=topology_rows,
        smt_sibling_groups=smt_sibling_groups(topology_rows),
        caches_bytes=caches,
        ram_bytes=parse_meminfo(meminfo),
        kernel=kernel.strip(),
        hypervisor=hypervisor,
        cpu_frequency_khz=frequency,
    )


def _default_runner(argv: Sequence[str]) -> str:
    result = subprocess.run(argv, text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def capture_hardware_fingerprint(
    server_type: str | None = None,
    *,
    runner: CommandRunner = _default_runner,
    root: Path = Path("/"),
) -> HardwareFingerprint:
    """Capture a fingerprint, tolerating unavailable optional guest facilities."""
    def read(relative: str) -> str:
        try:
            return (root / relative).read_text()
        except OSError:
            return ""

    freq_lines: list[str] = []
    cpu_root = root / "sys/devices/system/cpu"
    for path in sorted(cpu_root.glob("cpu[0-9]*/cpufreq/scaling_*_freq")):
        try:
            freq_lines.append(f"{path.name}={path.read_text().strip()}")
        except OSError:
            pass
    return fingerprint_from_text(
        lscpu=runner(["lscpu", "--json"]),
        cpuinfo=read("proc/cpuinfo"),
        meminfo=read("proc/meminfo"),
        kernel=runner(["uname", "-srvm"]) or platform.platform(),
        virtualization=runner(["systemd-detect-virt"]),
        cpufreq="\n".join(freq_lines),
        topology=runner(["lscpu", "-p=CPU,CORE,SOCKET,NODE"]),
        server_type=server_type,
    )


def parse_time_verbose(text: str) -> dict[str, float | int | None]:
    """Parse relevant GNU ``time --verbose`` observations."""
    fields = parse_lscpu(text)
    user = _float(fields.get("User time (seconds)")) or 0.0
    system = _float(fields.get("System time (seconds)")) or 0.0
    rss_kib = _integer(fields.get("Maximum resident set size (kbytes)"))
    return {
        "cpu_seconds": user + system,
        "peak_rss_bytes": rss_kib * 1024 if rss_kib is not None else None,
        "filesystem_inputs": _integer(fields.get("File system inputs")),
        "filesystem_outputs": _integer(fields.get("File system outputs")),
    }


def parse_proc_stat(text: str) -> dict[str, int]:
    """Parse the aggregate CPU counters from /proc/stat."""
    for line in text.splitlines():
        parts = line.split()
        if parts and parts[0] == "cpu":
            values = [int(value) for value in parts[1:]]
            values += [0] * (10 - len(values))
            return {
                "total": sum(values), "idle": values[3] + values[4],
                "steal": values[7],
            }
    return {"total": 0, "idle": 0, "steal": 0}


def parse_net_dev(text: str) -> dict[str, int]:
    """Aggregate network bytes, excluding the loopback interface."""
    received = transmitted = 0
    for line in text.splitlines():
        if ":" not in line:
            continue
        interface, raw = line.split(":", 1)
        values = raw.split()
        if interface.strip() == "lo" or len(values) < 9:
            continue
        received += int(values[0])
        transmitted += int(values[8])
    return {"read_bytes": received, "write_bytes": transmitted}


def parse_diskstats(text: str, devices: Iterable[str] | None = None) -> dict[str, int]:
    """Aggregate Linux diskstats sectors for explicitly selected devices.

    When no allow-list is supplied, obvious virtual/pseudo devices and
    partitions are omitted.  Supplying the benchmark data device is preferable
    because device-mapper stacks otherwise risk double counting.
    """
    selected = set(devices) if devices is not None else None
    read_sectors = write_sectors = 0
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 14:
            continue
        name = fields[2]
        if selected is not None:
            if name not in selected:
                continue
        elif (name.startswith(("loop", "ram", "fd", "sr", "dm-"))
              or re.search(r"(?:sd[a-z]|vd[a-z]|xvd[a-z])\d+$", name)
              or re.search(r"nvme\d+n\d+p\d+$", name)):
            continue
        read_sectors += int(fields[5])
        write_sectors += int(fields[9])
    # Linux diskstats sectors are defined as 512 bytes.
    return {"read_bytes": read_sectors * 512, "write_bytes": write_sectors * 512}


def _delta(after: Mapping[str, int], before: Mapping[str, int], key: str) -> int:
    return max(0, after.get(key, 0) - before.get(key, 0))


def summarize_telemetry(
    *, elapsed_seconds: float, time_verbose: str,
    proc_stat_before: str = "", proc_stat_after: str = "",
    diskstats_before: str = "", diskstats_after: str = "",
    net_dev_before: str = "", net_dev_after: str = "",
    active_thread_samples: Iterable[int] = (),
    active_core_samples: Iterable[int] = (),
    disk_devices: Iterable[str] | None = None,
    clock_ticks_per_second: int | None = None,
) -> dict[str, object]:
    """Combine task and host counter observations into a JSON-safe summary."""
    if elapsed_seconds <= 0:
        raise ValueError("elapsed_seconds must be positive")
    timed = parse_time_verbose(time_verbose)
    before_cpu, after_cpu = parse_proc_stat(proc_stat_before), parse_proc_stat(proc_stat_after)
    total_ticks = _delta(after_cpu, before_cpu, "total")
    idle_ticks = _delta(after_cpu, before_cpu, "idle")
    steal_ticks = _delta(after_cpu, before_cpu, "steal")
    ticks_per_second = (int(os.sysconf("SC_CLK_TCK")) if clock_ticks_per_second is None
                        else clock_ticks_per_second)
    if ticks_per_second <= 0:
        raise ValueError("clock_ticks_per_second must be positive")
    cpu_seconds = float(timed["cpu_seconds"] or 0.0)
    threads, cores = list(active_thread_samples), list(active_core_samples)
    before_disk = parse_diskstats(diskstats_before, disk_devices)
    after_disk = parse_diskstats(diskstats_after, disk_devices)
    before_net, after_net = parse_net_dev(net_dev_before), parse_net_dev(net_dev_after)
    return {
        "elapsed_seconds": elapsed_seconds,
        "cpu_seconds": cpu_seconds,
        # 100% means one logical CPU was fully occupied; parallel work may exceed 100%.
        "task_cpu_percent": cpu_seconds / elapsed_seconds * 100,
        "host_cpu_busy_percent": ((total_ticks - idle_ticks) / total_ticks * 100
                                  if total_ticks else None),
        "cpu_steal_percent": steal_ticks / total_ticks * 100 if total_ticks else None,
        "cpu_steal_seconds": steal_ticks / ticks_per_second,
        "peak_rss_bytes": timed["peak_rss_bytes"],
        "active_threads": {"max": max(threads) if threads else None,
                           "average": sum(threads) / len(threads) if threads else None},
        "active_cores": {"max": max(cores) if cores else None,
                         "average": sum(cores) / len(cores) if cores else None},
        "disk": {"read_bytes": _delta(after_disk, before_disk, "read_bytes"),
                 "write_bytes": _delta(after_disk, before_disk, "write_bytes")},
        "network": {"received_bytes": _delta(after_net, before_net, "read_bytes"),
                    "transmitted_bytes": _delta(after_net, before_net, "write_bytes")},
        "time_filesystem_operations": {
            "inputs": timed["filesystem_inputs"], "outputs": timed["filesystem_outputs"]},
    }


def sizing_advice(
    telemetry: Mapping[str, object], *, current_type: str, current_vcpus: int,
    current_ram_bytes: int,
    candidates: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    """Conservatively recommend, but never apply, one smaller server type.

    A candidate needs 40% memory headroom, 25% observed-core headroom, estimated
    CPU load below 60%, and low steal.  The nearest smaller fitting candidate is
    chosen to avoid recommending a large one-step reduction from a short sample.
    """
    peak = telemetry.get("peak_rss_bytes")
    cpu_percent = telemetry.get("task_cpu_percent")
    steal = telemetry.get("cpu_steal_percent")
    active = telemetry.get("active_cores")
    active_max = active.get("max") if isinstance(active, Mapping) else None
    result: dict[str, object] = {
        "current_type": current_type, "recommended_type": None,
        "automatic_change": False, "confidence": "insufficient-data", "reasons": [],
    }
    if not all(isinstance(value, (int, float)) for value in (peak, cpu_percent, steal, active_max)):
        result["reasons"] = ["peak memory, CPU, active-core, and steal observations are required"]
        return result
    if float(steal) > 2.0:
        result["confidence"] = "low"
        result["reasons"] = ["CPU steal exceeded 2%; rerun on a quieter host before sizing"]
        return result
    fitting = []
    for item in candidates:
        vcpus, ram = int(item["vcpus"]), int(item["ram_bytes"])
        if vcpus >= current_vcpus or ram > current_ram_bytes:
            continue
        if (float(peak) <= ram * 0.60
                and float(active_max) <= vcpus * 0.75
                and float(cpu_percent) / vcpus <= 60.0):
            fitting.append(item)
    if not fitting:
        result["confidence"] = "high"
        result["reasons"] = ["no smaller candidate preserves conservative CPU and memory headroom"]
        return result
    chosen = max(fitting, key=lambda item: (int(item["vcpus"]), int(item["ram_bytes"])))
    result.update(
        recommended_type=str(chosen["name"]), confidence="medium",
        reasons=["observed peak memory and CPU/core use fit with conservative headroom",
                 "benchmark again on the recommended type before adopting it"],
    )
    return result


def parse_cpu_list(value: str | Iterable[int]) -> tuple[int, ...]:
    """Parse Linux CPU-list notation and return unique sorted CPU IDs."""
    if not isinstance(value, str):
        cpus = [int(cpu) for cpu in value]
    else:
        cpus = []
        if not value.strip():
            return ()
        for part in value.split(","):
            part = part.strip()
            if not part:
                raise ValueError("empty CPU-list component")
            if "-" in part:
                first_text, last_text = part.split("-", 1)
                first, last = int(first_text), int(last_text)
                if first < 0 or last < first:
                    raise ValueError(f"invalid CPU range: {part}")
                cpus.extend(range(first, last + 1))
            else:
                cpus.append(int(part))
    if any(cpu < 0 for cpu in cpus):
        raise ValueError("CPU IDs must be non-negative")
    if len(cpus) != len(set(cpus)):
        raise ValueError("CPU list contains duplicates")
    return tuple(sorted(cpus))


def render_cpu_list(cpus: Iterable[int]) -> str:
    """Render CPU IDs using compact Linux CPU-list notation."""
    values = parse_cpu_list(cpus)
    if not values:
        return ""
    groups: list[str] = []
    start = previous = values[0]
    for value in values[1:]:
        if value == previous + 1:
            previous = value
            continue
        groups.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = value
    groups.append(str(start) if start == previous else f"{start}-{previous}")
    return ",".join(groups)


@dataclass(frozen=True)
class AffinityPlan:
    available_cpus: tuple[int, ...]
    benchmark_cpus: tuple[int, ...]
    helper_cpus: tuple[int, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "available_cpus": list(self.available_cpus),
            "benchmark_cpus": list(self.benchmark_cpus),
            "helper_cpus": list(self.helper_cpus),
            "benchmark_cpu_list": render_cpu_list(self.benchmark_cpus),
            "helper_cpu_list": render_cpu_list(self.helper_cpus),
            "disjoint": not bool(set(self.benchmark_cpus) & set(self.helper_cpus)),
        }

    def benchmark_prefix(self) -> list[str]:
        return ["taskset", "--cpu-list", render_cpu_list(self.benchmark_cpus)]

    def helper_prefix(self) -> list[str]:
        if not self.helper_cpus:
            raise ValueError("no CPUs were reserved for helper processes")
        return ["taskset", "--cpu-list", render_cpu_list(self.helper_cpus)]


def affinity_plan(
    *, available: str | Iterable[int], benchmark: str | Iterable[int],
    reserved_helpers: str | Iterable[int] = (),
) -> AffinityPlan:
    """Validate explicit, disjoint benchmark and helper CPU assignments."""
    available_cpus = parse_cpu_list(available)
    benchmark_cpus = parse_cpu_list(benchmark)
    helper_cpus = parse_cpu_list(reserved_helpers)
    if not available_cpus:
        raise ValueError("available CPU list must not be empty")
    if not benchmark_cpus:
        raise ValueError("benchmark CPU list must not be empty")
    unknown = (set(benchmark_cpus) | set(helper_cpus)) - set(available_cpus)
    if unknown:
        raise ValueError(f"CPU IDs are not available: {render_cpu_list(unknown)}")
    overlap = set(benchmark_cpus) & set(helper_cpus)
    if overlap:
        raise ValueError(f"benchmark and helper CPU lists overlap: {render_cpu_list(overlap)}")
    return AffinityPlan(available_cpus, benchmark_cpus, helper_cpus)


def record_effective_affinity(
    plan: AffinityPlan, *, benchmark: str | Iterable[int],
    helpers: str | Iterable[int] = (),
) -> dict[str, object]:
    """Record post-launch affinity and whether it matches the requested plan."""
    actual_benchmark = parse_cpu_list(benchmark)
    actual_helpers = parse_cpu_list(helpers)
    unknown = (set(actual_benchmark) | set(actual_helpers)) - set(plan.available_cpus)
    if unknown:
        raise ValueError(f"effective affinity includes unavailable CPUs: {render_cpu_list(unknown)}")
    return {
        "requested": plan.to_dict(),
        "effective_benchmark_cpus": list(actual_benchmark),
        "effective_helper_cpus": list(actual_helpers),
        "matches_request": (actual_benchmark == plan.benchmark_cpus
                            and actual_helpers == plan.helper_cpus),
    }


__all__ = [
    "AffinityPlan", "HardwareFingerprint", "affinity_plan",
    "capture_hardware_fingerprint", "fingerprint_from_text", "parse_cpu_list",
    "parse_cpufreq", "parse_cpuinfo", "parse_cpu_topology", "parse_diskstats", "parse_lscpu",
    "parse_meminfo", "parse_net_dev", "parse_proc_stat", "parse_time_verbose",
    "record_effective_affinity", "render_cpu_list", "sizing_advice",
    "smt_sibling_groups", "summarize_telemetry",
]
