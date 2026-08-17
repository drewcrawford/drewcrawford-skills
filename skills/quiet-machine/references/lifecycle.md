# Lifecycle and reliability

## Lease calculation

For creation time `C`, task start `S`, requested duration `D`, billing quantum
`Q`, and guard `G`, retain until:

```text
boundary = C + ceil((S + D - C) / Q) * Q
delete_at = boundary - G
```

Never reduce an existing deadline. If a task is still active at `delete_at`,
allow it to run until its requested deadline, then terminate it and delete the
server. The default quantum is 60 minutes and guard is 60 seconds.

## State machine

- `bootstrapping`: created with managed labels; no workload may run.
- `ready`: reaper is armed and setup fingerprint matches.
- `busy`: informational label; the remote `flock` is authoritative.
- `needs-repair`: setup failed; normal runs must not claim it.

The detached remote supervisor inherits `/run/quiet-machine/task.lock`, runs the
workload in a dedicated transient systemd cgroup, and holds the job's
`complete.lock` until terminal state and final log bytes are durable. `cancel
JOB` records intent before stopping the complete transient unit; the supervisor
remains alive long enough to write `cancelled`, restore the ready label, and
retain the lease deadline. The unit has its own runtime ceiling, so supervisor
loss cannot leave an unbounded workload behind. A second caller must acquire an
authoritative deferred-start reservation before source sync and create a new
server if the lock is held. The reaper deletes only while the lock is free,
except at the current job's hard deadline.

Durable execution states are `queued`, `running`, `success`, `failure`,
`cancelled`, `timeout`, and `infrastructure_lost`. The local index is not the
execution authority; it stores the config, VM, remote run directory, and cached
result needed to reconnect by job ID.

## Credentials

Read the raw token from `~/.hetzner`; require mode `0600`. Cloud-init and the
metadata service are not secret transports. Install public bootstrap code
first, then send the token through SSH stdin into a root-only file. The server
uses its documented metadata instance ID to delete itself through the API.

There is an unavoidable gap between server creation and reaper arming. Keep
local try/finally cleanup around that gap and reap expired bootstrap-labeled
resources at the beginning of every invocation.

## Snapshots

Require an idle lock. Scrub workspaces, artifacts, token, lifecycle state,
cloud-init identity, and SSH host keys. Power off before taking the snapshot.
The bundled command permanently deletes the scrubbed source server after the
snapshot attempt—even if snapshot creation fails—because it no longer has an
armed reaper. Label successful snapshots `quiet-machine-captured=true`; never
present them as reproducible.
