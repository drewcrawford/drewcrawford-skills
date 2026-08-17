# Durable jobs

## Ownership and recovery

While a job runs, the VM owns authoritative state and log bytes under
`/var/lib/quiet-machine/jobs/JOB/`. The controller stores only reconnection
coordinates and cached results under `$XDG_STATE_HOME/quiet-machine/jobs/`, or
`~/.local/state/quiet-machine/jobs/`. Job IDs remain usable from another
working directory because each record contains its originating config path.

`run --detach --apply` returns only after the remote detached supervisor has
created durable state and inherited both the exclusive machine lock and a
completion lock. An SSH disconnect after that acknowledgement does not stop the
workload.

Each launch also starts a controller-side mirror in a separate process session.
It blocks on the same remote completion lock, then caches terminal state and the
complete log under the controller state directory and downloads artifacts. This
survives the originating CLI, SSH attachment, or Codex session ending and keeps
completed results available after the VM self-reaps. The mirror log and PID are
recorded in the local job index. A controller-host failure can still prevent the
final mirror; have the workload publish to external storage when that stronger
durability model is required.

## State and output

- `queued`: accepted; the supervisor has not started the task process.
- `running`: the task's transient systemd cgroup is live.
- `success`: exit zero.
- `failure`: task exited nonzero.
- `cancelled`: a cancellation request stopped the workload cgroup.
- `timeout`: the requested execution deadline expired.
- `infrastructure_lost`: the supervisor vanished or failed without a normal
  task result.

`logs JOB` reads saved bytes from offset zero. `logs JOB --follow` and
`attach JOB` continue until the supervisor releases its completion lock, then
drain the final bytes once more before returning. Reattaching starts a new read
from offset zero by default; pass `--since-byte OFFSET` with the last confirmed
byte count to resume without replaying earlier bytes. One attachment never
duplicates or drops bytes internally.

`wait JOB --format json` holds one SSH session blocked on the completion lock
and emits one `job_completed` object. This is the machine-readable completion
event for an execution layer that can yield on a child process. Webhook/product
callbacks are not configured by this version; the local mirror is the built-in
completion consumer.

## Cancellation and artifacts

Inspect `cancel JOB` before applying `cancel JOB --apply`. Cancellation marks
the durable request first, stops and drains only the recorded transient unit,
waits for terminal state, retains logs, attempts artifact recovery, and releases
the VM under its existing lease.

`artifacts JOB` returns a manifest while running or after completion.
`artifacts JOB --download` incrementally synchronizes the job's
`.quiet-machine-out/` into a job-specific local directory. Use `--output PATH`
to choose another destination. Files that the workload has not atomically
finished writing may naturally change during a running download; publish
checkpoints with write-then-rename when each checkpoint must be self-consistent.

The remote copy lasts until the VM is reaped. The session-independent local
mirror normally preserves terminal state, logs, and downloaded artifacts first.
If the controller host itself fails or cannot reconnect before lease expiry,
remote-only data disappears with the VM; this cleanup guarantee takes priority
over retaining an unacknowledged billable server.
