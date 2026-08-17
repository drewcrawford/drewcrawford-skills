# Benchmark evidence and isolation

## Fingerprint and telemetry

Every durable result records what the guest actually exposes: Hetzner server
type and location, CPU model/vendor, logical topology and SMT siblings, cache
sizes, RAM, kernel, virtualization, and available frequency/governor data. Do
not translate those facts into a promise about the exact physical host SKU.

Runtime telemetry includes peak RSS, task CPU time/utilization, maximum active
threads and observed CPUs, CPU steal time, transient-unit cgroup disk I/O,
guest network traffic, and effective affinity. CPU time, memory peak, and disk
I/O are read from the workload's cgroup-v2 lifetime counters, so short spikes
do not depend on the 250 ms process sampler. Treat guest-wide network and steal
counters as context rather than task-exclusive accounting.

Sizing advice is conservative and advisory. It requires authoritative cgroup
memory and CPU counters plus
active-core, and steal evidence; refuses to recommend downsizing when evidence
is missing or steal is high; preserves headroom; and never changes the profile.
Benchmark the proposed smaller type before adopting it because the machine type
is part of the benchmark contract.

## CPU affinity

Pass Linux CPU-list syntax explicitly:

```bash
python3 scripts/quiet_machine.py run --profile rust --time 30m \
  --cpus 0-2 --helper-cpus 3 --detach --apply -- ./benchmark
```

The controller validates syntax. The VM validates IDs against its effective
cpuset and rejects overlap. The measured process tree is launched through
`taskset`; the job record includes requested and observed affinity. A helper
reservation does not discover or move arbitrary browser processes. Launch each
helper through `$QUIET_MACHINE_HELPER_PREFIX`, for example:

```bash
$QUIET_MACHINE_HELPER_PREFIX chromium --headless &
exec ./measured-workload
```

The first version does not change CPU governors or other host tuning. If a
trusted setup script changes tuning, make it record the change and restore it;
otherwise the VM is not reusable for comparable benchmarks.

## Quota and source CIDR

The CLI queries current servers, server types, and dedicated-vCPU usage before
creation. Hetzner's public API does not expose customized project limit values,
so copy the server and dedicated-vCPU limits from the Console into the profile's
`quota` table for exact refusal and release suggestions. Suggestions list only
managed idle VMs and never delete them automatically. Creation refuses when
those limits are unknown unless the caller explicitly passes
`--allow-unknown-quota`, in which case the Hetzner create API remains the final
limit check.

With `ssh_source_cidr = "auto"`, two independent public-address observations
must agree on a public unicast address. The managed firewall permits only that
single IPv4 `/32`, matching the managed VM's IPv4-only SSH path. Discovery
failure or disagreement stops the operation;
there is no `0.0.0.0/0` or `::/0` fallback.
