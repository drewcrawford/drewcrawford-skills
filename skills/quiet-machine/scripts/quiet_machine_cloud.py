#!/usr/bin/env python3
"""Pure cloud planning helpers for quiet-machine.

This module intentionally performs no network calls and no mutations.  The
main CLI can feed it Hetzner API objects, quota counters, and public-address
observations, then render or apply the returned plans explicitly.
"""

from __future__ import annotations

from datetime import datetime, timezone
import ipaddress
from typing import Iterable, Mapping, Sequence


MANAGED_LABEL = "quiet-machine-managed"


class CloudPlanningError(ValueError):
    """Input is incomplete or unsafe for a cloud operation."""


def _integer(value: object, name: str) -> int:
    if isinstance(value, bool):
        raise CloudPlanningError(f"{name} must be a non-negative integer")
    try:
        result = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise CloudPlanningError(f"{name} must be a non-negative integer") from exc
    if result < 0:
        raise CloudPlanningError(f"{name} must be a non-negative integer")
    return result


def _timestamp(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, datetime):
        moment = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return int(moment.timestamp())
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            try:
                moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc)
            return int(moment.timestamp())
    return None


def _iso8601(value: int | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")


def _server_type(
    server: Mapping[str, object],
    server_types: Mapping[object, Mapping[str, object]] | None,
) -> Mapping[str, object]:
    raw = server.get("server_type")
    if isinstance(raw, Mapping):
        return raw
    if server_types is not None:
        for key in (raw, str(raw) if raw is not None else None):
            if key in server_types:
                return server_types[key]
    return {"name": raw} if raw is not None else {}


def _location(server: Mapping[str, object]) -> str | None:
    datacenter = server.get("datacenter")
    if isinstance(datacenter, Mapping):
        location = datacenter.get("location")
        if isinstance(location, Mapping):
            return str(location.get("name")) if location.get("name") is not None else None
        if location is not None:
            return str(location)
        if datacenter.get("name") is not None:
            return str(datacenter["name"])
    location = server.get("location")
    if isinstance(location, Mapping):
        return str(location.get("name")) if location.get("name") is not None else None
    return str(location) if location is not None else None


def _image_revision(server: Mapping[str, object], labels: Mapping[str, object]) -> str | None:
    labelled = labels.get("quiet-machine-image-revision")
    if labelled not in (None, ""):
        return str(labelled)
    image = server.get("image")
    if isinstance(image, Mapping):
        value = image.get("id", image.get("name"))
        return str(value) if value is not None else None
    return str(image) if image is not None else None


def project_pool_row(
    server: Mapping[str, object],
    *,
    server_types: Mapping[object, Mapping[str, object]] | None = None,
    now: int | datetime | None = None,
) -> dict[str, object]:
    """Project a Hetzner server object into a stable, richer pool-list row."""

    labels_value = server.get("labels")
    labels: Mapping[str, object] = labels_value if isinstance(labels_value, Mapping) else {}
    kind = _server_type(server, server_types)
    created = _timestamp(labels.get("quiet-machine-created"))
    if created is None:
        created = _timestamp(server.get("created"))
    lease = _timestamp(labels.get("quiet-machine-retain-until"))
    current = _timestamp(now)
    if current is None:
        current = int(datetime.now(timezone.utc).timestamp())
    age = max(0, current - created) if created is not None else None
    current_job = labels.get(
        "quiet-machine-current-job",
        labels.get("quiet-machine-job-id", labels.get("quiet-machine-job")),
    )
    server_type_name = kind.get("name", server.get("server_type"))

    return {
        "id": server.get("id"),
        "name": server.get("name"),
        "status": server.get("status"),
        "server_type": str(server_type_name) if server_type_name is not None else None,
        "vcpu": kind.get("cores"),
        "ram_gb": kind.get("memory"),
        "cpu_type": kind.get("cpu_type"),
        "architecture": kind.get("architecture"),
        "location": _location(server),
        "lifecycle_state": labels.get("quiet-machine-state", "unknown"),
        "current_job": str(current_job) if current_job not in (None, "") else None,
        "lease_expires_epoch": lease,
        "lease_expires_at": _iso8601(lease),
        "setup_revision": labels.get("quiet-machine-profile"),
        "image_revision": _image_revision(server, labels),
        "created_epoch": created,
        "created_at": _iso8601(created),
        "billing_age_seconds": age,
    }


def project_pool_rows(
    servers: Iterable[Mapping[str, object]],
    *,
    server_types: Mapping[object, Mapping[str, object]] | None = None,
    now: int | datetime | None = None,
) -> list[dict[str, object]]:
    """Project and deterministically order a complete managed pool."""

    rows = [project_pool_row(server, server_types=server_types, now=now) for server in servers]
    return sorted(rows, key=lambda row: (str(row["name"] or ""), str(row["id"] or "")))


def _is_releasable_idle(server: Mapping[str, object]) -> bool:
    labels_value = server.get("labels")
    labels: Mapping[str, object] = labels_value if isinstance(labels_value, Mapping) else {}
    return (
        str(labels.get(MANAGED_LABEL, "")).lower() == "true"
        and labels.get("quiet-machine-state") in {"ready", "idle"}
        and not labels.get("quiet-machine-current-job")
        and not labels.get("quiet-machine-job-id")
        and not labels.get("quiet-machine-job")
    )


def assess_creation_quota(
    requested_server_type: Mapping[str, object],
    *,
    server_limit: int,
    server_count: int,
    dedicated_vcpu_limit: int | None,
    dedicated_vcpu_count: int,
    managed_servers: Iterable[Mapping[str, object]] = (),
    server_types: Mapping[object, Mapping[str, object]] | None = None,
    now: int | datetime | None = None,
) -> dict[str, object]:
    """Assess one server creation without mutating or deleting resources.

    ``server_count`` and ``dedicated_vcpu_count`` must describe the whole
    Hetzner project, not merely quiet-machine-labelled resources.
    """

    limit = _integer(server_limit, "server_limit")
    count = _integer(server_count, "server_count")
    dedicated_count = _integer(dedicated_vcpu_count, "dedicated_vcpu_count")
    requested_cores = _integer(requested_server_type.get("cores"), "requested server cores")
    cpu_type = str(requested_server_type.get("cpu_type", ""))
    requested_dedicated = requested_cores if cpu_type == "dedicated" else 0
    if requested_dedicated and dedicated_vcpu_limit is None:
        raise CloudPlanningError(
            "dedicated_vcpu_limit is required for a dedicated-CPU server request"
        )
    dedicated_limit = (
        _integer(dedicated_vcpu_limit, "dedicated_vcpu_limit")
        if dedicated_vcpu_limit is not None
        else None
    )

    server_available = max(0, limit - count)
    server_deficit = max(0, count + 1 - limit)
    dedicated_available = (
        max(0, dedicated_limit - dedicated_count) if dedicated_limit is not None else None
    )
    dedicated_deficit = (
        max(0, dedicated_count + requested_dedicated - dedicated_limit)
        if requested_dedicated and dedicated_available is not None
        else 0
    )
    reasons: list[str] = []
    if server_deficit:
        reasons.append(
            f"server quota short by {server_deficit}: {count} of {limit} in use, "
            "and creation needs 1"
        )
    if dedicated_deficit:
        reasons.append(
            f"dedicated-vCPU quota short by {dedicated_deficit}: "
            f"{dedicated_count} of {dedicated_limit} in use, and creation needs "
            f"{requested_dedicated}"
        )

    candidates: list[dict[str, object]] = []
    if reasons:
        for server in managed_servers:
            if not _is_releasable_idle(server):
                continue
            row = project_pool_row(server, server_types=server_types, now=now)
            released_dedicated = (
                _integer(row["vcpu"], "managed server vCPU count")
                if row["cpu_type"] == "dedicated" and row["vcpu"] is not None
                else 0
            )
            candidates.append(
                {
                    "server_id": row["id"],
                    "name": row["name"],
                    "server_type": row["server_type"],
                    "dedicated_vcpus_released": released_dedicated,
                    "lease_expires_at": row["lease_expires_at"],
                    "billing_age_seconds": row["billing_age_seconds"],
                }
            )
        candidates.sort(
            key=lambda item: (
                -int(item["dedicated_vcpus_released"]),
                str(item["lease_expires_at"] or ""),
                str(item["server_id"]),
            )
        )

    need_servers = server_deficit
    need_dedicated = dedicated_deficit
    suggested: list[object] = []
    for item in candidates:
        contributes = need_servers > 0 or (
            need_dedicated > 0 and int(item["dedicated_vcpus_released"]) > 0
        )
        if not contributes:
            continue
        suggested.append(item["server_id"])
        need_servers = max(0, need_servers - 1)
        need_dedicated = max(
            0, need_dedicated - int(item["dedicated_vcpus_released"])
        )
        if not need_servers and not need_dedicated:
            break

    allowed = not reasons
    return {
        "allowed": allowed,
        "request": {
            "server_type": requested_server_type.get("name"),
            "servers": 1,
            "dedicated_vcpus": requested_dedicated,
        },
        "quota": {
            "servers": {
                "limit": limit,
                "used": count,
                "available": server_available,
                "deficit": server_deficit,
            },
            "dedicated_vcpus": {
                "limit": dedicated_limit,
                "used": dedicated_count,
                "available": dedicated_available,
                "deficit": dedicated_deficit,
            },
        },
        "reasons": reasons,
        "releasable_managed_idle": candidates,
        "release_suggestion": {
            "server_ids": suggested,
            "would_satisfy_quota": not need_servers and not need_dedicated,
            "requires_explicit_authorization": True,
        },
        "mutation_performed": False,
    }


def _public_host_network(value: str, *, allow_bare_address: bool) -> ipaddress.IPv4Network | ipaddress.IPv6Network:
    candidate = value.strip()
    if not candidate:
        raise CloudPlanningError("SSH source CIDR is empty")
    if not allow_bare_address and "/" not in candidate:
        raise CloudPlanningError(
            f"SSH source CIDR must include /32 or /128: {candidate!r}"
        )
    if allow_bare_address and "/" not in candidate:
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError as exc:
            raise CloudPlanningError(f"invalid public IP address: {candidate!r}") from exc
        candidate = f"{address}/{address.max_prefixlen}"
    try:
        network = ipaddress.ip_network(candidate, strict=True)
    except ValueError as exc:
        raise CloudPlanningError(f"invalid SSH source CIDR: {candidate!r}") from exc
    if network.prefixlen != network.max_prefixlen:
        raise CloudPlanningError(
            f"SSH source CIDR must identify one host (/{network.max_prefixlen}), "
            f"not {network.with_prefixlen}"
        )
    address = network.network_address
    if (
        not address.is_global
        or address.is_multicast
        or address.is_unspecified
        or address.is_loopback
        or address.is_link_local
        or address.is_private
        or address.is_reserved
    ):
        raise CloudPlanningError(
            f"SSH source address must be a public unicast address: {address}"
        )
    return network


def validate_ssh_source_cidr(value: str) -> str:
    """Validate and normalize a public IPv4 /32 or IPv6 /128 source CIDR."""

    return _public_host_network(value, allow_bare_address=False).with_prefixlen


def discover_ssh_source_cidr(observations: Mapping[str, str] | Iterable[str]) -> str:
    """Resolve agreeing public-IP observations to one safe host CIDR.

    The caller owns provider/network I/O.  Passing multiple successful
    observations provides a disagreement check; this function never invents a
    fallback such as ``0.0.0.0/0``.
    """

    if isinstance(observations, Mapping):
        labelled: Sequence[tuple[str, str]] = list(observations.items())
    else:
        labelled = [(str(index), value) for index, value in enumerate(observations)]
    if not labelled:
        raise CloudPlanningError("no public-address observations were provided")
    resolved: dict[str, str] = {}
    for source, value in labelled:
        try:
            resolved[source] = _public_host_network(
                value, allow_bare_address=True
            ).with_prefixlen
        except (AttributeError, TypeError) as exc:
            raise CloudPlanningError(
                f"public-address observation {source!r} is not text"
            ) from exc
    distinct = sorted(set(resolved.values()))
    if len(distinct) != 1:
        detail = ", ".join(f"{source}={cidr}" for source, cidr in resolved.items())
        raise CloudPlanningError(f"public-address observations disagree: {detail}")
    return distinct[0]


def plan_ssh_source_cidr_update(
    current_cidrs: Iterable[str], proposed_cidr: str
) -> dict[str, object]:
    """Plan a managed SSH rule update; never returns a broad allow rule."""

    proposed = validate_ssh_source_cidr(proposed_cidr)
    current = list(current_cidrs)
    keep: list[str] = []
    unsafe: list[str] = []
    for value in current:
        try:
            normalized = validate_ssh_source_cidr(value)
        except CloudPlanningError:
            unsafe.append(value)
            continue
        if normalized == proposed and normalized not in keep:
            keep.append(normalized)
    remove = [value for value in current if value not in keep]
    add = [] if proposed in keep else [proposed]
    if not remove and not add:
        action = "none"
    elif remove:
        action = "replace"
    else:
        action = "add"
    return {
        "action": action,
        "proposed_cidr": proposed,
        "add": add,
        "remove": remove,
        "unsafe_existing": unsafe,
        "opens_public_ssh": False,
        "mutation_performed": False,
    }
