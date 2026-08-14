"""Unit tests for the parts of release_prep that read `cargo public-api`.

These need no repository: they feed the parser the exact shapes that fooled it
on real crates. The re-export case in particular passed both hand-checked
fixtures while quietly accusing five well-behaved types of lacking `Debug`.
"""

import importlib.machinery
import importlib.util
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


if __name__ == "__main__":
    unittest.main()
