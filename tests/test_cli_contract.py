import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


COMMANDS = [
    [PYTHON, str(ROOT / "skills/changelog/scripts/changelog_generator.py")],
    [str(ROOT / "skills/changelog/scripts/compare_api.sh")],
    [str(ROOT / "skills/dev-browser/server.sh")],
    [PYTHON, str(ROOT / "skills/ecosystem-deps/ecosystem_deps.py")],
    [PYTHON, str(ROOT / "skills/gitea/scripts/gitea_builds.py")],
    [str(ROOT / "skills/github/scripts/github_builds")],
    [str(ROOT / "skills/release-prep/scripts/11_ensure_agents_symlink")],
    [str(ROOT / "skills/release-prep/scripts/check_docs")],
    [str(ROOT / "skills/release-prep/scripts/compare_api.sh")],
    [str(ROOT / "skills/release-prep/scripts/compare_docs.sh")],
    [str(ROOT / "skills/release-prep/scripts/line_count")],
    [str(ROOT / "skills/release-prep/scripts/release_prep")],
    [str(ROOT / "skills/release-prep/scripts/spdx")],
    [PYTHON, str(ROOT / "skills/write-skills/scripts/validate_skill.py")],
]


def run(command, cwd, env=None):
    clean_env = os.environ.copy()
    clean_env.pop("GITHUB_TOKEN", None)
    clean_env.pop("GITEA_TOKEN", None)
    clean_env.pop("GITEA_URL", None)
    clean_env.pop("GITEA_CONFIG", None)
    if env:
        clean_env.update(env)
    return subprocess.run(
        command,
        cwd=cwd,
        env=clean_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
        check=False,
    )


class InterfaceContractTests(unittest.TestCase):
    def test_help_is_successful_credential_free_and_side_effect_free(self):
        for command in COMMANDS:
            with self.subTest(command=command), tempfile.TemporaryDirectory() as directory:
                cwd = Path(directory)
                before = list(cwd.iterdir())
                result = run(command + ["--help"], cwd)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage", result.stdout.lower())
                self.assertEqual(list(cwd.iterdir()), before)

    def test_unknown_arguments_exit_two(self):
        for command in COMMANDS:
            with self.subTest(command=command), tempfile.TemporaryDirectory() as directory:
                result = run(command + ["--definitely-invalid"], directory)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertTrue(result.stderr)

    def test_api_tools_parse_before_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            github = run(
                [str(ROOT / "skills/github/scripts/github_builds"), "owner", "repo"],
                directory,
            )
            self.assertEqual(github.returncode, 1)
            self.assertEqual(github.stdout, "")
            self.assertIn("GITHUB_TOKEN", github.stderr)

            config = Path(directory) / "empty-gitea-config"
            config.write_text("", encoding="utf-8")
            gitea = run(
                [
                    PYTHON,
                    str(ROOT / "skills/gitea/scripts/gitea_builds.py"),
                    "owner",
                    "repo",
                    "--config",
                    str(config),
                ],
                directory,
            )
            self.assertEqual(gitea.returncode, 1)
            self.assertEqual(gitea.stdout, "")
            self.assertIn("GITEA_URL", gitea.stderr)

    def test_structured_outputs_are_valid_json(self):
        validate = run(
            [
                PYTHON,
                str(ROOT / "skills/write-skills/scripts/validate_skill.py"),
                "--format",
                "json",
                str(ROOT / "skills/write-skills"),
            ],
            ROOT,
        )
        self.assertEqual(validate.returncode, 0, validate.stderr)
        self.assertTrue(json.loads(validate.stdout)[0]["valid"])

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "Cargo.lock").write_text(
                'version = 3\n\n[[package]]\nname = "root"\nversion = "0.1.0"\n'
                'dependencies = ["foo"]\n\n[[package]]\nname = "foo"\nversion = "1.2.3"\n',
                encoding="utf-8",
            )
            ecosystem = run(
                [
                    PYTHON,
                    str(ROOT / "skills/ecosystem-deps/ecosystem_deps.py"),
                    "--crates",
                    "foo",
                    "--format",
                    "json",
                    str(workspace),
                ],
                workspace,
            )
            self.assertEqual(ecosystem.returncode, 0, ecosystem.stderr)
            self.assertEqual(json.loads(ecosystem.stdout)["dependencies"][0]["name"], "foo")

            (workspace / "src").mkdir()
            (workspace / "src/lib.rs").write_text("fn small() {}\n", encoding="utf-8")
            counts = run(
                [str(ROOT / "skills/release-prep/scripts/line_count"), "--format", "json", str(workspace)],
                workspace,
            )
            self.assertEqual(counts.returncode, 0, counts.stderr)
            self.assertEqual(json.loads(counts.stdout)["files"], 1)

    def test_mutating_helpers_are_check_only_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("instructions\n", encoding="utf-8")
            check = run([str(ROOT / "skills/release-prep/scripts/11_ensure_agents_symlink")], root)
            self.assertEqual(check.returncode, 1)
            self.assertFalse((root / "CLAUDE.md").exists())
            apply = run(
                [str(ROOT / "skills/release-prep/scripts/11_ensure_agents_symlink"), "--apply"],
                root,
            )
            self.assertEqual(apply.returncode, 0, apply.stderr)
            self.assertEqual(os.readlink(root / "CLAUDE.md"), "AGENTS.md")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("instructions\n", encoding="utf-8")
            claude = root / "CLAUDE.md"
            claude.write_text("keep me\n", encoding="utf-8")
            refused = run(
                [str(ROOT / "skills/release-prep/scripts/11_ensure_agents_symlink"), "--apply"],
                root,
            )
            self.assertEqual(refused.returncode, 2)
            self.assertEqual(claude.read_text(encoding="utf-8"), "keep me\n")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src/lib.rs").write_text(
                "// SPDX-License-Identifier: MIT\npub fn root() {}\n", encoding="utf-8"
            )
            target = root / "src/other.rs"
            original = "pub fn other() {}\n"
            target.write_text(original, encoding="utf-8")
            check = run([str(ROOT / "skills/release-prep/scripts/spdx")], root)
            self.assertEqual(check.returncode, 1)
            self.assertEqual(target.read_text(encoding="utf-8"), original)
            apply = run([str(ROOT / "skills/release-prep/scripts/spdx"), "--apply"], root)
            self.assertEqual(apply.returncode, 0, apply.stderr)
            self.assertTrue(target.read_text(encoding="utf-8").startswith("// SPDX-License-Identifier: MIT"))

    def test_spdx_runs_from_a_virtual_workspace_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Cargo.toml").write_text(
                '[workspace]\nmembers = ["crates/*"]\n\n'
                '[workspace.package]\nlicense = "MIT OR Apache-2.0"\n',
                encoding="utf-8",
            )
            for name, manifest in (
                ("inherits", '[package]\nname = "inherits"\nlicense.workspace = true\n'),
                ("owns", '[package]\nname = "owns"\nlicense = "MIT"\n'),
            ):
                crate = root / "crates" / name
                (crate / "src").mkdir(parents=True)
                (crate / "Cargo.toml").write_text(manifest, encoding="utf-8")
                (crate / "src/lib.rs").write_text(f"pub fn {name}() {{}}\n", encoding="utf-8")

            spdx = str(ROOT / "skills/release-prep/scripts/spdx")
            check = run([spdx], root)
            self.assertEqual(check.returncode, 1, check.stderr)
            self.assertIn("crates/inherits/src/lib.rs", check.stdout)
            apply = run([spdx, "--apply"], root)
            self.assertEqual(apply.returncode, 0, apply.stderr)
            self.assertTrue(
                (root / "crates/inherits/src/lib.rs")
                .read_text(encoding="utf-8")
                .startswith("// SPDX-License-Identifier: MIT OR Apache-2.0")
            )
            self.assertTrue(
                (root / "crates/owns/src/lib.rs")
                .read_text(encoding="utf-8")
                .startswith("// SPDX-License-Identifier: MIT\n")
            )
            self.assertEqual(run([spdx], root).returncode, 0)

    def test_spdx_reports_crates_with_no_discoverable_license(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Cargo.toml").write_text('[package]\nname = "bare"\n', encoding="utf-8")
            (root / "src").mkdir()
            source = root / "src/lib.rs"
            source.write_text("pub fn bare() {}\n", encoding="utf-8")

            spdx = str(ROOT / "skills/release-prep/scripts/spdx")
            unresolved = run([spdx, "--apply"], root)
            self.assertEqual(unresolved.returncode, 2)
            self.assertIn("no license", unresolved.stderr)
            self.assertEqual(source.read_text(encoding="utf-8"), "pub fn bare() {}\n")

            override = run([spdx, "--apply", "--spdx", "MIT"], root)
            self.assertEqual(override.returncode, 0, override.stderr)
            self.assertTrue(
                source.read_text(encoding="utf-8").startswith("// SPDX-License-Identifier: MIT\n")
            )

    def test_comparison_tools_preserve_dirty_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            repo = temp / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
            (repo / "Cargo.toml").write_text(
                '[package]\nname = "demo"\nversion = "0.1.0"\n', encoding="utf-8"
            )
            marker = repo / "marker"
            marker.write_text("old\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-qm", "old"], check=True)
            subprocess.run(["git", "-C", str(repo), "tag", "v1"], check=True)
            marker.write_text("new\n", encoding="utf-8")

            bin_dir = temp / "bin"
            bin_dir.mkdir()
            cargo = bin_dir / "cargo"
            cargo.write_text(
                "#!/bin/sh\n"
                "set -eu\n"
                "if [ \"$1\" = public-api ]; then cat marker; exit 0; fi\n"
                "if [ \"$1\" = metadata ]; then\n"
                "  printf '{\"packages\":[{\"manifest_path\":\"%s/Cargo.toml\",\"name\":\"demo\"}],\"target_directory\":\"%s/target\"}\\n' \"$PWD\" \"$PWD\"\n"
                "  exit 0\n"
                "fi\n"
                "if [ \"$1\" = +nightly ] && [ \"$2\" = rustdoc ]; then\n"
                "  mkdir -p target/doc\n"
                "  value=$(cat marker)\n"
                "  printf '{\"index\":{\"1\":{\"name\":\"Thing\",\"docs\":\"%s docs\",\"inner\":{\"struct\":{}}}}}\\n' \"$value\" > target/doc/demo.json\n"
                "  exit 0\n"
                "fi\n"
                "echo unsupported cargo invocation >&2\nexit 2\n",
                encoding="utf-8",
            )
            cargo.chmod(0o755)
            env = {"PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", "")}

            for script in (
                ROOT / "skills/changelog/scripts/compare_api.sh",
                ROOT / "skills/release-prep/scripts/compare_api.sh",
                ROOT / "skills/release-prep/scripts/compare_docs.sh",
            ):
                with self.subTest(script=script):
                    result = run([str(script), "--root", str(repo), "v1", "--quiet"] if script.name == "compare_docs.sh" else [str(script), "--root", str(repo), "v1"], temp, env=env)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(marker.read_text(encoding="utf-8"), "new\n")
                    self.assertFalse((repo / "old.txt").exists())
                    self.assertFalse((repo / "new.txt").exists())
                    worktrees = subprocess.run(
                        ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
                        text=True,
                        stdout=subprocess.PIPE,
                        check=True,
                    ).stdout
                    self.assertEqual(worktrees.count("worktree "), 1)

    def test_comparison_tools_fall_back_to_an_empty_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            repo = temp / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
            (repo / "Cargo.toml").write_text(
                '[package]\nname = "demo"\nversion = "0.1.0"\n', encoding="utf-8"
            )
            (repo / "marker").write_text("only\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-qm", "first"], check=True)

            bin_dir = temp / "bin"
            bin_dir.mkdir()
            cargo = bin_dir / "cargo"
            cargo.write_text(
                "#!/bin/sh\n"
                "set -eu\n"
                "if [ \"$1\" = public-api ]; then cat marker; exit 0; fi\n"
                "if [ \"$1\" = metadata ]; then\n"
                "  printf '{\"packages\":[{\"manifest_path\":\"%s/Cargo.toml\",\"name\":\"demo\"}],\"target_directory\":\"%s/target\"}\\n' \"$PWD\" \"$PWD\"\n"
                "  exit 0\n"
                "fi\n"
                "if [ \"$1\" = +nightly ] && [ \"$2\" = rustdoc ]; then\n"
                "  mkdir -p target/doc\n"
                "  value=$(cat marker)\n"
                "  printf '{\"index\":{\"1\":{\"name\":\"Thing\",\"docs\":\"%s docs\",\"inner\":{\"struct\":{}}}}}\\n' \"$value\" > target/doc/demo.json\n"
                "  exit 0\n"
                "fi\n"
                "echo unsupported cargo invocation >&2\nexit 2\n",
                encoding="utf-8",
            )
            cargo.chmod(0o755)
            env = {"PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", "")}

            for script, added in (
                (ROOT / "skills/changelog/scripts/compare_api.sh", "+only"),
                (ROOT / "skills/release-prep/scripts/compare_api.sh", "+only"),
                (ROOT / "skills/release-prep/scripts/compare_docs.sh", '+    "name": "struct::Thing"'),
            ):
                with self.subTest(script=script):
                    command = [str(script), "--root", str(repo)]
                    if script.name == "compare_docs.sh":
                        command.append("--quiet")
                    result = run(command, temp, env=env)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("empty baseline", result.stderr)
                    self.assertIn("--- empty baseline", result.stdout)
                    self.assertIn(added, result.stdout)
                    removals = [
                        line
                        for line in result.stdout.splitlines()
                        if line.startswith("-") and not line.startswith("---")
                    ]
                    self.assertEqual(removals, [])


if __name__ == "__main__":
    unittest.main()
