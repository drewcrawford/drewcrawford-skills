"""Durable local index for quiet-machine jobs.

The remote VM owns authoritative execution state.  This index only records how
to find that state again after the originating process or client disappears.
"""

from __future__ import annotations

import json
import fcntl
import os
from pathlib import Path
import re
import tempfile
import time
import uuid
from contextlib import contextmanager


JOB_ID = re.compile(r"^qm-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}$")
TERMINAL_STATES = {
    "success", "failure", "cancelled", "timeout", "infrastructure_lost",
}


class JobIndexError(RuntimeError):
    pass


def new_job_id(now: float | None = None) -> str:
    stamp = time.gmtime(time.time() if now is None else now)
    return time.strftime("qm-%Y%m%dT%H%M%SZ-", stamp) + uuid.uuid4().hex[:12]


def validate_job_id(job_id: str) -> str:
    if not JOB_ID.fullmatch(job_id):
        raise JobIndexError(f"invalid quiet-machine job ID: {job_id!r}")
    return job_id


def state_root() -> Path:
    override = os.environ.get("QUIET_MACHINE_STATE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    xdg = os.environ.get("XDG_STATE_HOME")
    parent = Path(xdg).expanduser() if xdg else Path.home() / ".local/state"
    return parent / "quiet-machine"


def job_path(job_id: str) -> Path:
    return state_root() / "jobs" / (validate_job_id(job_id) + ".json")


def _save_unlocked(record: dict) -> Path:
    job_id = validate_job_id(str(record.get("job_id", "")))
    path = job_path(job_id)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    payload = json.dumps(record, indent=2, sort_keys=True) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=".job-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return path


@contextmanager
def _job_lock(job_id: str):
    path = job_path(job_id)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    with lock_path.open("a+") as handle:
        os.chmod(lock_path, 0o600)
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def save(record: dict) -> Path:
    job_id = validate_job_id(str(record.get("job_id", "")))
    with _job_lock(job_id):
        return _save_unlocked(record)


def load(job_id: str) -> dict:
    path = job_path(job_id)
    try:
        record = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise JobIndexError(f"unknown quiet-machine job: {job_id}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise JobIndexError(f"cannot read quiet-machine job index {path}: {exc}") from exc
    if record.get("job_id") != job_id:
        raise JobIndexError(f"job index identity mismatch in {path}")
    return record


def update(job_id: str, **values) -> dict:
    with _job_lock(job_id):
        record = load(job_id)
        record.update(values)
        _save_unlocked(record)
        return record


def all_jobs() -> list[dict]:
    directory = state_root() / "jobs"
    if not directory.exists():
        return []
    records = []
    for path in directory.glob("qm-*.json"):
        try:
            record = json.loads(path.read_text())
            validate_job_id(str(record.get("job_id", "")))
            records.append(record)
        except (OSError, json.JSONDecodeError, JobIndexError):
            continue
    return sorted(records, key=lambda item: item.get("created_at", 0), reverse=True)


def exit_code(state: dict) -> int:
    name = state.get("state")
    if name == "success":
        return 0
    if name == "timeout":
        return 124
    if name == "infrastructure_lost":
        return 125
    if name == "cancelled":
        return 130
    code = state.get("exit_code")
    return code if isinstance(code, int) and 1 <= code <= 123 else 125
