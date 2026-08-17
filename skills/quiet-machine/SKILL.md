---
name: quiet-machine
description: Use this skill when a task needs an isolated, quiet Hetzner Cloud VM; when local code, dirty worktrees, or artifacts must be shipped to a dedicated machine; or when creating, repairing, reusing, snapshotting, and safely reaping short-lived test environments with custom Rust or other toolchains. Do not use it for untrusted workloads or permanent production infrastructure.
compatibility: Requires Linux, Python 3.11+, hcloud, ssh, rsync, systemd/cloud-init images, a sandbox Hetzner project token in ~/.hetzner, and network access.
---

# Quiet Machine

Run trusted work on exclusive Hetzner VMs. A VM may serve sequential tasks, but
the remote lock must never be shared by concurrent tasks.

Resolve all bundled paths relative to this skill directory. Use
`python3 scripts/quiet_machine.py` for lifecycle operations.

## Safety contract

- Use only the dedicated sandbox project represented by `~/.hetzner`.
- Run `doctor` first. Refuse state changes while the token is group/world
  readable; repair it only with the user's authorization.
- Plan state-changing commands first, then repeat them with `--apply`.
- Select and delete only resources carrying `quiet-machine-managed=true`.
- Never put the token in cloud-init, command arguments, logs, reports, source
  bundles, or snapshots. Arm the self-reaper over SSH before shipping code.
- Treat task code as trusted. Tasks receive passwordless sudo and can therefore
  read the sandbox token or disable cleanup.
- A powered-off Hetzner server remains billable. Delete expired servers.

## Project configuration

Create `.quiet-machine.toml` in the project. Start from
[`assets/quiet-machine.example.toml`](assets/quiet-machine.example.toml). Keep
all secrets out of this file.

Run:

```bash
python3 scripts/quiet_machine.py doctor --profile rust
python3 scripts/quiet_machine.py run --profile rust --time 30m -- cargo test
python3 scripts/quiet_machine.py run --profile rust --time 30m --apply -- cargo test
```

`run` prints a plan unless `--apply` is present. On apply it resolves the image,
claims an idle matching VM with a nonblocking remote lock or creates a new one,
runs setup when needed, syncs the source, executes the command, retrieves
`.quiet-machine-out/`, and releases the VM for reuse.

## Repair loop

Expect initial setup to be incomplete.

1. Inspect the failed setup and machine with `list`.
2. Acquire it exclusively with `shell --server ID --time 30m --apply`.
3. Repair and test with sudo.
4. Copy every successful repair into the project's setup script.
5. Run `setup --server ID --profile NAME`, inspect the plan, then add `--apply`.
6. Validate the changed setup on a fresh VM before calling it reproducible.

The setup bundle hash participates in pool matching. Never relabel a machine as
matching until the complete current setup succeeds.

Read [`references/image-authoring.md`](references/image-authoring.md) when
creating or updating a reusable Packer image. Read
[`references/lifecycle.md`](references/lifecycle.md) when diagnosing leases,
cleanup, snapshots, or credential handling.

## Other commands

```bash
python3 scripts/quiet_machine.py list --format json
python3 scripts/quiet_machine.py reap
python3 scripts/quiet_machine.py reap --apply
python3 scripts/quiet_machine.py destroy --server ID
python3 scripts/quiet_machine.py snapshot --server ID --profile rust
```

`reap`, `destroy`, `setup`, and `snapshot` are dry-run by default. Snapshotting
is a fast, non-reproducible shortcut; prefer rebuilding the image with Packer.
For safety, `snapshot --apply` scrubs and permanently deletes the source VM
after the snapshot attempt, including when snapshot creation fails. Inspect its
dry-run plan before applying it.

## Result handling

- Task stdout and stderr stream unchanged.
- Exit `124` means timeout, `125` means lifecycle/SSH/sync/setup failure, and
  `2` means invalid usage. Other `0`-`123` values are the task's status.
- Retrieve artifacts even after task failure when SSH remains available.
- Use `--report PATH` for a machine-readable lifecycle report.
