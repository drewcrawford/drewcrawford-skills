import importlib.util
from pathlib import Path
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills/quiet-machine/scripts/quiet_machine_cloud.py"
)
SPEC = importlib.util.spec_from_file_location("quiet_machine_cloud", SCRIPT)
cloud = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cloud)


def server(
    sid,
    *,
    state="ready",
    current_job=None,
    server_type=None,
    created="1000",
    lease="4600",
):
    labels = {
        cloud.MANAGED_LABEL: "true",
        "quiet-machine-state": state,
        "quiet-machine-created": created,
        "quiet-machine-retain-until": lease,
        "quiet-machine-profile": "setup-fingerprint",
    }
    if current_job:
        labels["quiet-machine-current-job"] = current_job
    return {
        "id": sid,
        "name": f"quiet-{sid}",
        "status": "running",
        "labels": labels,
        "server_type": server_type
        or {
            "name": "ccx13",
            "cores": 2,
            "memory": 8.0,
            "cpu_type": "dedicated",
            "architecture": "x86",
        },
        "datacenter": {"location": {"name": "ash"}},
        "image": {"id": 99},
    }


class PoolProjectionTests(unittest.TestCase):
    def test_projects_benchmark_capacity_and_lifecycle(self):
        row = cloud.project_pool_row(server(42, current_job="job-abc"), now=1600)
        self.assertEqual(
            row,
            {
                "id": 42,
                "name": "quiet-42",
                "status": "running",
                "server_type": "ccx13",
                "vcpu": 2,
                "ram_gb": 8.0,
                "cpu_type": "dedicated",
                "architecture": "x86",
                "location": "ash",
                "lifecycle_state": "ready",
                "current_job": "job-abc",
                "lease_expires_epoch": 4600,
                "lease_expires_at": "1970-01-01T01:16:40Z",
                "setup_revision": "setup-fingerprint",
                "image_revision": "99",
                "created_epoch": 1000,
                "created_at": "1970-01-01T00:16:40Z",
                "billing_age_seconds": 600,
            },
        )

    def test_supports_separate_server_type_catalog_and_iso_creation(self):
        item = server(7, server_type="ccx23", created="2026-08-17T12:00:00Z")
        row = cloud.project_pool_row(
            item,
            server_types={
                "ccx23": {
                    "name": "ccx23",
                    "cores": 4,
                    "memory": 16,
                    "cpu_type": "dedicated",
                    "architecture": "x86",
                }
            },
            now=1786969800,
        )
        self.assertEqual(row["vcpu"], 4)
        self.assertEqual(row["ram_gb"], 16)
        self.assertEqual(row["billing_age_seconds"], 1800)


class QuotaTests(unittest.TestCase):
    def test_deficit_includes_usage_already_over_limit(self):
        result = cloud.assess_creation_quota(
            {"name": "ccx13", "cores": 2, "cpu_type": "dedicated"},
            server_limit=10,
            server_count=12,
            dedicated_vcpu_limit=8,
            dedicated_vcpu_count=9,
        )
        self.assertEqual(result["quota"]["servers"]["deficit"], 3)
        self.assertEqual(result["quota"]["dedicated_vcpus"]["deficit"], 3)

    def test_reports_exact_server_and_dedicated_vcpu_deficits(self):
        busy = server(1, state="busy", current_job="running")
        idle = server(2)
        result = cloud.assess_creation_quota(
            {"name": "ccx23", "cores": 4, "cpu_type": "dedicated"},
            server_limit=4,
            server_count=4,
            dedicated_vcpu_limit=8,
            dedicated_vcpu_count=7,
            managed_servers=[busy, idle],
            now=2000,
        )
        self.assertFalse(result["allowed"])
        self.assertEqual(result["quota"]["servers"]["deficit"], 1)
        self.assertEqual(result["quota"]["dedicated_vcpus"]["deficit"], 3)
        self.assertIn("server quota short by 1", result["reasons"][0])
        self.assertIn("dedicated-vCPU quota short by 3", result["reasons"][1])
        self.assertEqual(
            [item["server_id"] for item in result["releasable_managed_idle"]],
            [2],
        )
        self.assertNotIn(1, result["release_suggestion"]["server_ids"])
        self.assertTrue(result["release_suggestion"]["requires_explicit_authorization"])
        self.assertFalse(result["mutation_performed"])

    def test_capacity_allows_creation_without_release_advice(self):
        result = cloud.assess_creation_quota(
            {"name": "ccx13", "cores": 2, "cpu_type": "dedicated"},
            server_limit=10,
            server_count=2,
            dedicated_vcpu_limit=16,
            dedicated_vcpu_count=4,
            managed_servers=[server(2)],
        )
        self.assertTrue(result["allowed"])
        self.assertEqual(result["reasons"], [])
        self.assertEqual(result["releasable_managed_idle"], [])

    def test_dedicated_request_requires_dedicated_quota(self):
        with self.assertRaisesRegex(cloud.CloudPlanningError, "dedicated_vcpu_limit"):
            cloud.assess_creation_quota(
                {"name": "ccx13", "cores": 2, "cpu_type": "dedicated"},
                server_limit=10,
                server_count=2,
                dedicated_vcpu_limit=None,
                dedicated_vcpu_count=0,
            )

    def test_unmanaged_and_nonidle_servers_are_never_release_candidates(self):
        unmanaged = server(1)
        unmanaged["labels"][cloud.MANAGED_LABEL] = "false"
        repair = server(2, state="needs-repair")
        result = cloud.assess_creation_quota(
            {"name": "ccx13", "cores": 2, "cpu_type": "dedicated"},
            server_limit=1,
            server_count=1,
            dedicated_vcpu_limit=2,
            dedicated_vcpu_count=2,
            managed_servers=[unmanaged, repair],
        )
        self.assertEqual(result["releasable_managed_idle"], [])
        self.assertFalse(result["release_suggestion"]["would_satisfy_quota"])


class SourceCidrTests(unittest.TestCase):
    def test_accepts_only_public_single_host_cidrs(self):
        self.assertEqual(cloud.validate_ssh_source_cidr("8.8.8.8/32"), "8.8.8.8/32")
        self.assertEqual(
            cloud.validate_ssh_source_cidr("2606:4700:4700::1111/128"),
            "2606:4700:4700::1111/128",
        )

    def test_rejects_broad_private_loopback_link_local_and_bare_values(self):
        rejected = [
            "0.0.0.0/0",
            "::/0",
            "8.8.8.0/24",
            "10.0.0.1/32",
            "127.0.0.1/32",
            "169.254.1.2/32",
            "224.0.0.1/32",
            "::1/128",
            "fe80::1/128",
            "ff02::1/128",
            "8.8.8.8",
        ]
        for value in rejected:
            with self.subTest(value=value), self.assertRaises(cloud.CloudPlanningError):
                cloud.validate_ssh_source_cidr(value)

    def test_discovery_normalizes_agreeing_ipv4_observations(self):
        self.assertEqual(
            cloud.discover_ssh_source_cidr(
                {"provider-a": "8.8.8.8\n", "provider-b": "8.8.8.8/32"}
            ),
            "8.8.8.8/32",
        )

    def test_discovery_rejects_disagreement_and_no_observations(self):
        with self.assertRaisesRegex(cloud.CloudPlanningError, "disagree"):
            cloud.discover_ssh_source_cidr(["8.8.8.8", "1.1.1.1"])
        with self.assertRaisesRegex(cloud.CloudPlanningError, "no public-address"):
            cloud.discover_ssh_source_cidr([])

    def test_update_plan_removes_broad_rule_without_adding_a_fallback(self):
        plan = cloud.plan_ssh_source_cidr_update(
            ["0.0.0.0/0", "1.1.1.1/32"], "8.8.8.8/32"
        )
        self.assertEqual(plan["action"], "replace")
        self.assertEqual(plan["add"], ["8.8.8.8/32"])
        self.assertEqual(plan["remove"], ["0.0.0.0/0", "1.1.1.1/32"])
        self.assertEqual(plan["unsafe_existing"], ["0.0.0.0/0"])
        self.assertFalse(plan["opens_public_ssh"])
        self.assertFalse(plan["mutation_performed"])

    def test_update_plan_is_noop_for_matching_narrow_rule(self):
        plan = cloud.plan_ssh_source_cidr_update(["8.8.8.8/32"], "8.8.8.8/32")
        self.assertEqual(plan["action"], "none")
        self.assertEqual(plan["add"], [])
        self.assertEqual(plan["remove"], [])


if __name__ == "__main__":
    unittest.main()
