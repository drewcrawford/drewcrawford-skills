"""Unit tests for the parts of release_prep that read `cargo public-api`.

These need no repository: they feed the parser the exact shapes that fooled it
on real crates. The re-export case in particular passed both hand-checked
fixtures while quietly accusing five well-behaved types of lacking `Debug`.
"""

import importlib.machinery
import importlib.util
import types
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills/release-prep/scripts/release_prep"


def load():
    # The script has no .py suffix, so it needs an explicit source loader.
    loader = importlib.machinery.SourceFileLoader("release_prep", str(SCRIPT))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(module)
    return module


rp = load()


class AuditApiTests(unittest.TestCase):
    def test_a_reexported_type_keeps_the_traits_of_its_canonical_path(self):
        # `pub use crate::event::Event` puts the declaration in one module and
        # the impls in another; both are the same type.
        hard, soft = rp.audit_api(
            "c",
            [
                "pub struct c::dom::Event(_)",
                "pub struct c::websocket::Event(_)",
                "pub struct c::event::Event(_)",
                "impl core::fmt::Debug for c::event::Event",
            ],
        )
        self.assertEqual(hard, [])
        self.assertEqual(soft, [])

    def test_a_shortened_reexport_keeps_its_traits(self):
        hard, _ = rp.audit_api(
            "c",
            ["pub struct c::Mutex<T>", "impl<T: core::fmt::Debug> core::fmt::Debug for c::mutex::Mutex<T>"],
        )
        self.assertEqual(hard, [])

    def test_a_type_reachable_only_through_a_variant_is_reported(self):
        hard, _ = rp.audit_api(
            "c",
            [
                "#[non_exhaustive] pub enum c::AbiArg",
                "impl core::fmt::Debug for c::AbiArg",
                "pub c::AbiArg::Slice(c::SliceElem)",
            ],
        )
        self.assertTrue(any("SliceElem" in h and "never exported" in h for h in hard), hard)

    def test_a_variant_is_not_mistaken_for_an_unexported_type(self):
        hard, _ = rp.audit_api(
            "c",
            ["#[non_exhaustive] pub enum c::Kind", "impl core::fmt::Debug for c::Kind", "pub c::Kind::Slice(c::Kind)"],
        )
        self.assertEqual(hard, [])

    def test_a_missing_debug_is_reported(self):
        hard, _ = rp.audit_api("c", ["pub struct c::Thing"])
        self.assertEqual(hard, ["c::Thing: no Debug impl"])

    def test_a_trait_is_not_expected_to_implement_debug(self):
        hard, _ = rp.audit_api("c", ["pub trait c::AsJsValue"])
        self.assertEqual(hard, [])

    def test_an_error_type_must_implement_error(self):
        hard, _ = rp.audit_api("c", ["pub struct c::RecvError", "impl core::fmt::Debug for c::RecvError"])
        self.assertTrue(any("does not implement Error" in h for h in hard), hard)

    def test_open_questions_are_not_defects(self):
        hard, soft = rp.audit_api(
            "c",
            [
                "pub enum c::DeltaMode",
                "impl core::fmt::Debug for c::DeltaMode",
                "impl core::cmp::Eq for c::DeltaMode",
            ],
        )
        self.assertEqual(hard, [])
        self.assertEqual(len(soft), 2)  # exhaustive enum, and Eq without Hash


class ReadmeTransformTests(unittest.TestCase):
    def test_wrap_width_and_link_spelling_are_not_drift(self):
        lib = [
            "See [`export`] and the",
            "[guide](https://github.com/o/r/blob/main/docs/g.md).",
            "![logo](https://github.com/o/r/raw/main/art/l.png)",
            "[`export`]: https://example.invalid",
        ]
        readme = [
            "See `#[export]` and the [guide](./docs/g.md).",
            "![logo](art/l.png)",
        ]
        self.assertEqual(
            rp.canonical_blocks(rp.to_readme_form(lib, ("o", "r"))),
            rp.canonical_blocks(readme),
        )

    def test_bold_at_the_start_of_a_paragraph_is_not_a_bullet(self):
        self.assertEqual(rp.canonical_blocks(["**nightly** builds", "need flags"]), ["**nightly** builds need flags"])

    def test_a_wrapped_bullet_stays_one_block(self):
        self.assertEqual(rp.canonical_blocks(["* want tests to run", "in a browser;"]), ["* want tests to run in a browser;"])

    def test_real_drift_survives(self):
        self.assertNotEqual(rp.canonical_blocks(["See the guide"]), rp.canonical_blocks(["See the manual"]))


class MsrvTests(unittest.TestCase):
    """`cargo msrv` output, as it actually arrives when the script captures it.

    The default human format colours the version even with no terminal
    attached, so the reading came back wrapped in escape codes and the check
    skipped on a crate whose declaration was correct all along.
    """

    HUMAN = "   MSRV:                     \x1b[4m\x1b[1m\x1b[32m1.85.1\x1b[39m\x1b[0m\x1b[0m\n"

    def check(self, declared, msrv_stdout, msrv_stderr="", returncode=0, installed=True):
        def fake_run(cmd, cwd, timeout=None):
            if cmd[:3] == ["cargo", "msrv", "--version"]:
                return types.SimpleNamespace(returncode=0 if installed else 101, stdout="", stderr="")
            return types.SimpleNamespace(returncode=returncode, stdout=msrv_stdout, stderr=msrv_stderr)

        ctx = types.SimpleNamespace(
            root=Path("."),
            args=types.SimpleNamespace(slow=True),
            packages=[{"rust_version": declared, "edition": "2024"}],
        )
        real_run, rp.run = rp.run, fake_run
        try:
            return rp.check_msrv(ctx)
        finally:
            rp.run = real_run

    def test_the_minimal_format_is_what_gets_parsed(self):
        self.assertEqual(self.check("1.85.1", "1.85.1\n").status, rp.PASS)

    def test_a_coloured_human_reading_is_not_relied_on(self):
        # If the script ever asks for the human format again, this is the shape
        # it gets back — and no version comes out of it.
        self.assertIsNone(rp.re.search(r"^(\d+\.\d+(?:\.\d+)?)$", self.HUMAN.strip()))

    def test_a_patch_the_search_never_tried_is_not_a_mismatch(self):
        # cargo-msrv checks only the newest patch of each minor, so 1.85.1 is
        # the reading for anything that builds on 1.85.
        self.assertEqual(self.check("1.85", "1.85.1\n").status, rp.PASS)

    def test_a_wrong_minor_still_fails(self):
        self.assertEqual(self.check("1.84", "1.85.1\n").status, rp.FAIL)

    def test_an_uninstalled_cargo_msrv_says_so(self):
        finding = self.check("1.85.1", "", installed=False)
        self.assertEqual(finding.status, rp.SKIP)
        self.assertIn("not installed", finding.summary)

    def test_no_msrv_found_carries_the_command_to_run(self):
        finding = self.check("1.85.1", "", msrv_stderr="none\n", returncode=1)
        self.assertEqual(finding.status, rp.SKIP)
        self.assertIn("cargo msrv find --min 1.85", finding.prompt)


class CiTemplateTests(unittest.TestCase):
    """A project's copy of the CI template is allowed to grow.

    Byte equality made every project that installed a sibling tool ask
    forever, which is a verdict nobody can act on twice.
    """

    TEMPLATE = SCRIPT.parents[1] / "templates/ci.yml"

    def shape(self, text):
        return rp.workflow_shape(text)

    def test_the_marker_is_a_generation_not_any_comment(self):
        self.assertEqual(self.shape("# matrix v11\non: [push]\n").marker, "matrix v11")
        self.assertEqual(self.shape("# This file defines our CI\non: [push]\n").marker, "unversioned")
        self.assertEqual(self.shape("on: [push]\n").marker, "unversioned")

    def test_matrix_entries_are_the_projects_own(self):
        # The template says extra include: entries are to be preserved, so
        # nothing inside strategy: is compared.
        text = self.TEMPLATE.read_text().replace(
            '          - os: ubuntu-latest\n            target: "wasm32"\n',
            '          - os: macos-latest\n            target: "native"\n            channel: nightly\n',
        )
        self.assertEqual(self.shape(text).keys, self.shape(self.TEMPLATE.read_text()).keys)

    def test_a_run_body_is_not_mistaken_for_a_step(self):
        text = "# matrix v11\njobs:\n  ci:\n    steps:\n      - name: one\n        run: |\n          - not a step\n"
        self.assertEqual(self.shape(text).steps, ["one"])

    def test_a_project_step_is_reported_not_penalised(self):
        text = self.TEMPLATE.read_text().replace(
            "      - name: rustfmt",
            "      - name: Install wasm_lite runner\n        run: cargo build\n\n      - name: rustfmt",
        )
        shape = self.shape(text)
        template = self.shape(self.TEMPLATE.read_text())
        self.assertEqual([s for s in template.steps if s not in shape.steps], [])
        self.assertEqual([s for s in shape.steps if s not in template.steps], ["Install wasm_lite runner"])

    def test_a_raised_timeout_is_following_instructions(self):
        # The template tells the project needing it to raise this, so the key
        # is compared and the value is not.
        text = self.TEMPLATE.read_text().replace("timeout-minutes: 15", "timeout-minutes: 45")
        self.assertEqual(self.shape(text).keys, self.shape(self.TEMPLATE.read_text()).keys)

    def test_a_dropped_step_is_still_visible(self):
        text = self.TEMPLATE.read_text().replace("      - name: clippy\n        run: scripts/${{ matrix.target }}/clippy\n", "")
        self.assertNotIn("clippy", self.shape(text).steps)


class RustdocErrorTests(unittest.TestCase):
    OUTPUT = """\
error: unresolved link to `Gone::method`
 --> src/lib.rs:3:11
  |
3 | //! See [`Gone::method`] for details.
  |           ^^^^^^^^^^^^ no item named `Gone` in scope
  |
  = note: requested on the command line with `-D rustdoc::broken-intra-doc-links`

error: could not document `msrvtest`
"""

    def test_each_error_carries_its_location(self):
        self.assertEqual(
            rp.rustdoc_errors(self.OUTPUT),
            ["error: unresolved link to `Gone::method` --> src/lib.rs:3:11", "error: could not document `msrvtest`"],
        )

    def test_a_clean_build_yields_nothing(self):
        self.assertEqual(rp.rustdoc_errors("Documenting c v0.1.0\n    Finished\n"), [])


class VersionTests(unittest.TestCase):
    def test_patch_order_is_numeric(self):
        self.assertLess(rp.version_tuple("0.1.9"), rp.version_tuple("0.1.10"))

    def test_a_prerelease_sorts_below_its_release(self):
        self.assertLess(rp.version_tuple("1.0.0-rc.1"), rp.version_tuple("1.0.0"))

    def test_a_two_component_version_compares(self):
        self.assertEqual(rp.version_tuple("1.2"), rp.version_tuple("1.2.0"))

    def test_the_same_version_is_not_a_bump(self):
        self.assertFalse(rp.version_tuple("0.1.3") > rp.version_tuple("0.1.3"))


class ChangelogTests(unittest.TestCase):
    TEXT = """\
# Changelog

## [Unreleased]

## [0.1.3] - 2026-08-14

Three soundness fixes.

### Changed
- Swapped the WASM test toolchain
- Debug no longer asks for `R: Debug`

## [0.1.2] - 2026-07-01
- Something older
"""

    def test_entries_are_found_under_a_bracketed_heading(self):
        self.assertEqual(len(rp.changelog_entries(self.TEXT, "0.1.3")), 2)

    def test_a_subsection_does_not_end_the_version(self):
        # `### Changed` sits under `## [0.1.3]`, so its bullets belong to it.
        self.assertIn("- Swapped the WASM test toolchain", rp.changelog_entries(self.TEXT, "0.1.3"))

    def test_the_next_version_ends_the_section(self):
        self.assertNotIn("- Something older", rp.changelog_entries(self.TEXT, "0.1.3"))

    def test_a_version_with_no_heading_is_distinct_from_an_empty_one(self):
        self.assertIsNone(rp.changelog_entries(self.TEXT, "0.2.0"))
        self.assertEqual(rp.changelog_entries(self.TEXT, "Unreleased"), [])

    def test_a_bare_heading_is_matched(self):
        self.assertEqual(rp.changelog_entries("## 1.0.0\n- did a thing\n", "1.0.0"), ["- did a thing"])

    def test_a_longer_version_is_not_matched_by_a_prefix(self):
        self.assertIsNone(rp.changelog_entries("## [0.1.30]\n- x\n", "0.1.3"))


if __name__ == "__main__":
    unittest.main()
