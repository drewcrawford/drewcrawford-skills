import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPT = (Path(__file__).resolve().parents[1]
          / "skills/quiet-machine/scripts/quiet_machine_observability.py")
SPEC = importlib.util.spec_from_file_location("quiet_machine_observability", SCRIPT)
obs = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = obs
SPEC.loader.exec_module(obs)


LSCPU = """Architecture:                         x86_64
CPU(s):                               4
Vendor ID:                            AuthenticAMD
Model name:                           AMD EPYC Processor
Thread(s) per core:                   2
Core(s) per socket:                   2
Socket(s):                            1
NUMA node(s):                         1
Hypervisor vendor:                    KVM
L1d cache:                            64 KiB
L1i cache:                            64 KiB
L2 cache:                             2 MiB
L3 cache:                             32 MiB
"""


class FingerprintTests(unittest.TestCase):
    def test_guest_visible_hardware_is_structured(self):
        result = obs.fingerprint_from_text(
            lscpu=LSCPU,
            cpuinfo="vendor_id: AuthenticAMD\nmodel name: fallback\n",
            meminfo="MemTotal:       16384000 kB\n",
            kernel="Linux 6.12.0 x86_64",
            virtualization="kvm",
            cpufreq="scaling_min_freq=1200000\nscaling_max_freq=3500000\n"
                    "scaling_cur_freq=2799000\nscaling_cur_freq=3100000\n",
            topology="0,0,0,0\n1,0,0,0\n2,1,0,0\n3,1,0,0\n",
            server_type="ccx13",
        ).to_dict()
        self.assertEqual(result["server_type"], "ccx13")
        self.assertEqual(result["cpu_vendor"], "AuthenticAMD")
        self.assertEqual(result["cpu_model"], "AMD EPYC Processor")
        self.assertEqual(result["logical_cpus"], 4)
        self.assertEqual(result["threads_per_core"], 2)
        self.assertTrue(result["smt_exposed"])
        self.assertEqual(result["smt_sibling_groups"], [[0, 1], [2, 3]])
        self.assertEqual(result["cpu_topology"][2], {"cpu": 2, "core": 1,
                                                     "socket": 0, "node": 0})
        self.assertEqual(result["caches_bytes"]["l3"], 32 * 1024 * 1024)
        self.assertEqual(result["ram_bytes"], 16384000 * 1024)
        self.assertEqual(result["hypervisor"], "KVM")
        self.assertEqual(result["cpu_frequency_khz"]["current_max_khz"], 3100000)

    def test_lscpu_json_and_non_x86_cpuinfo_are_supported(self):
        text = '{"lscpu":[{"field":"Architecture:","data":"aarch64"},' \
               '{"field":"CPU(s):","data":"8"}]}'
        self.assertEqual(obs.parse_lscpu(text), {"Architecture": "aarch64", "CPU(s)": "8"})
        identity = obs.parse_cpuinfo("CPU implementer : 0x41\nHardware : Neoverse\n")
        self.assertEqual(identity, {"vendor": "0x41", "model": "Neoverse"})

    def test_collector_uses_injected_runner_and_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "proc").mkdir()
            (root / "proc/cpuinfo").write_text("vendor_id: GenuineIntel\nmodel name: virtual\n")
            (root / "proc/meminfo").write_text("MemTotal: 1024 kB\n")
            outputs = {
                ("lscpu", "--json"): '{"lscpu":[{"field":"CPU(s):","data":"1"}]}',
                ("lscpu", "-p=CPU,CORE,SOCKET,NODE"): "0,0,0,0",
                ("uname", "-srvm"): "Linux test",
                ("systemd-detect-virt",): "kvm",
            }
            value = obs.capture_hardware_fingerprint(
                "cx-test", runner=lambda argv: outputs[tuple(argv)], root=root)
        self.assertEqual(value.logical_cpus, 1)
        self.assertEqual(value.ram_bytes, 1024 * 1024)
        self.assertEqual(value.hypervisor, "kvm")


TIME_VERBOSE = """User time (seconds): 5.00
System time (seconds): 1.00
Maximum resident set size (kbytes): 262144
File system inputs: 8
File system outputs: 16
"""


class TelemetryTests(unittest.TestCase):
    def test_summarizes_resource_use_and_counter_deltas(self):
        before_disk = "8 0 sda 1 0 100 0 1 0 200 0 0 0 0 0 0 0\n"
        after_disk = "8 0 sda 2 0 110 0 2 0 230 0 0 0 0 0 0 0\n"
        before_net = "eth0: 100 0 0 0 0 0 0 0 200 0 0 0 0 0 0 0\n"
        after_net = "eth0: 400 0 0 0 0 0 0 0 700 0 0 0 0 0 0 0\n"
        result = obs.summarize_telemetry(
            elapsed_seconds=4, time_verbose=TIME_VERBOSE,
            proc_stat_before="cpu 100 0 20 800 0 0 0 10\n",
            proc_stat_after="cpu 130 0 30 840 0 0 0 12\n",
            diskstats_before=before_disk, diskstats_after=after_disk,
            net_dev_before=before_net, net_dev_after=after_net,
            active_thread_samples=[1, 3, 2], active_core_samples=[1, 2, 2],
            clock_ticks_per_second=100,
        )
        self.assertEqual(result["peak_rss_bytes"], 256 * 1024 * 1024)
        self.assertEqual(result["task_cpu_percent"], 150)
        self.assertAlmostEqual(result["cpu_steal_percent"], 2 / 82 * 100)
        self.assertEqual(result["cpu_steal_seconds"], 0.02)
        self.assertEqual(result["active_threads"], {"max": 3, "average": 2})
        self.assertEqual(result["active_cores"]["max"], 2)
        self.assertEqual(result["disk"], {"read_bytes": 10 * 512, "write_bytes": 30 * 512})
        self.assertEqual(result["network"], {"received_bytes": 300, "transmitted_bytes": 500})

    def test_elapsed_time_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            obs.summarize_telemetry(elapsed_seconds=0, time_verbose="")


class SizingTests(unittest.TestCase):
    def telemetry(self, **changes):
        value = {"peak_rss_bytes": 2 * 1024**3, "task_cpu_percent": 80.0,
                 "cpu_steal_percent": 0.2, "active_cores": {"max": 1}}
        value.update(changes)
        return value

    def test_recommends_nearest_smaller_type_without_applying_it(self):
        advice = obs.sizing_advice(
            self.telemetry(), current_type="ccx43", current_vcpus=16,
            current_ram_bytes=64 * 1024**3,
            candidates=[
                {"name": "ccx13", "vcpus": 4, "ram_bytes": 16 * 1024**3},
                {"name": "ccx23", "vcpus": 8, "ram_bytes": 32 * 1024**3},
            ],
        )
        self.assertEqual(advice["recommended_type"], "ccx23")
        self.assertFalse(advice["automatic_change"])

    def test_high_steal_refuses_to_size(self):
        advice = obs.sizing_advice(
            self.telemetry(cpu_steal_percent=4), current_type="ccx23", current_vcpus=8,
            current_ram_bytes=32 * 1024**3,
            candidates=[{"name": "ccx13", "vcpus": 4, "ram_bytes": 16 * 1024**3}],
        )
        self.assertIsNone(advice["recommended_type"])
        self.assertIn("steal", advice["reasons"][0])

    def test_missing_evidence_does_not_guess(self):
        advice = obs.sizing_advice(
            {}, current_type="ccx13", current_vcpus=4, current_ram_bytes=16 * 1024**3,
            candidates=[],
        )
        self.assertEqual(advice["confidence"], "insufficient-data")


class AffinityTests(unittest.TestCase):
    def test_expands_validates_and_renders_disjoint_assignments(self):
        plan = obs.affinity_plan(available="0-3", benchmark="2-3", reserved_helpers="0-1")
        self.assertEqual(plan.benchmark_prefix(), ["taskset", "--cpu-list", "2-3"])
        self.assertEqual(plan.helper_prefix(), ["taskset", "--cpu-list", "0-1"])
        self.assertTrue(plan.to_dict()["disjoint"])
        effective = obs.record_effective_affinity(
            plan, benchmark="2-3", helpers="0-1")
        self.assertTrue(effective["matches_request"])

    def test_effective_affinity_mismatch_is_recorded(self):
        plan = obs.affinity_plan(available="0-3", benchmark="2-3", reserved_helpers="0-1")
        effective = obs.record_effective_affinity(plan, benchmark="2", helpers="0-1")
        self.assertFalse(effective["matches_request"])

    def test_overlap_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "overlap"):
            obs.affinity_plan(available="0-3", benchmark="1-2", reserved_helpers="2-3")

    def test_unavailable_cpu_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not available"):
            obs.affinity_plan(available="0-3", benchmark="4")

    def test_duplicate_and_backward_ranges_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicates"):
            obs.parse_cpu_list("0,0")
        with self.assertRaisesRegex(ValueError, "invalid CPU range"):
            obs.parse_cpu_list("3-1")


if __name__ == "__main__":
    unittest.main()
