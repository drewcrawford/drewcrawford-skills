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

The remote controller holds `/run/quiet-machine/task.lock` and records the
active task process group in `/run/quiet-machine/task.pid`. `cancel` signals
only that group; the controller remains alive long enough to restore the ready
label and lease deadline. A second caller
must try the lock nonblockingly and create a new server on failure. The reaper
deletes only while the lock is free, except at the hard deadline.

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
