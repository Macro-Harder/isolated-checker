"""Step 14 cure wave 2a pinning tests, added on the fix register's authority.

Each test class pins one triaged finding of design/steps/
step-14-fix-register.md, written test first: the test was run red
against the code as it stood before its finding's cure, and the
cure in the same commit turned it green. Classes land in register
order: T14-07, then T14-10.

The T14-07 tests call the discovery classification directly, in
the presented case form slice S-02 delivers. The T14-10 tests run
freeze intake through the harness, as the suite's filed
convention presents it, with the invocation receipt_digest field
set to a value differing from the issued self digest.
"""

import pathlib
import tempfile
import unittest

import harness
from isolated_checker import discovery


class T1407DiscoveryComposesNoDeterminationTests(unittest.TestCase):
    """T14-07: discovery composes no run determination, no exit status."""

    def unrecomputable(self, support):
        return discovery.classify_discovery(
            {
                "form": "unrecomputable_artefact",
                "artefact_kind": "step record",
                "determination_support": support,
            }
        )

    def test_unrecomputable_with_support_carries_no_determination_or_status(self):
        result = self.unrecomputable("supported")
        self.assertNotIn("determination", result)
        self.assertNotIn("exit_status", result)

    def test_unrecomputable_without_support_carries_no_determination_or_status(self):
        result = self.unrecomputable("none")
        self.assertNotIn("determination", result)
        self.assertNotIn("exit_status", result)

    def test_unidentifiable_form_itself_stands_as_s02_delivers_it(self):
        for support in ("supported", "none"):
            result = self.unrecomputable(support)
            self.assertEqual(result["outcome"], "unidentifiable")
            self.assertEqual(result["artefact_kind"], "step record")
            self.assertIs(result["identified"], False)

    def test_unrecomputable_case_returns_the_discovery_facts(self):
        # The facts discovery supplies, in MD-16 terms: the
        # artefact was located, and the recompute test failed on
        # it. A run determination is composed from facts of this
        # kind by MD-06, and an exit status is gated by MD-15,
        # when the operation surface lands at S-07.
        result = self.unrecomputable("supported")
        self.assertIs(result["located"], True)
        self.assertIs(result["recomputable"], False)

    def test_no_discovery_form_carries_a_determination_or_an_exit_status(self):
        cases = [
            {
                "form": "renamed_artefact",
                "artefact_kind": "step record",
                "content_signature": "sig",
                "presented_name": "renamed.txt",
            },
            {
                "form": "unlocatable_artefact",
                "artefact_kind": "step record",
                "routes_tried": ["filename"],
            },
            {
                "form": "unrecomputable_artefact",
                "artefact_kind": "step record",
                "determination_support": "supported",
            },
            {
                "form": "unrecomputable_artefact",
                "artefact_kind": "step record",
                "determination_support": "none",
            },
            {"form": "linked_member", "member": "linked.txt"},
            {"form": "submodule_member", "member": "sub.txt"},
            {"form": "outside_path_member", "member": "outside.txt"},
            {
                "form": "instruction_shaped_text",
                "quoted_text": "do the thing",
                "source_artefact": "packet.txt",
            },
        ]
        for case in cases:
            result = discovery.classify_discovery(case)
            self.assertNotIn("determination", result, case["form"])
            self.assertNotIn("exit_status", result, case["form"])

    def test_classification_text_invites_no_status_composition_from_it(self):
        # The docstring invitation to compose statuses from the
        # classification is part of the carriage the finding
        # names, and it comes off with the fields.
        doc = discovery.classify_discovery.__doc__ or ""
        self.assertNotIn("composes statuses from it", doc)
        module_doc = discovery.__doc__ or ""
        self.assertNotIn("composes statuses from it", module_doc)


SUPPLIED_DIGEST = "f" * 64


class T1410NoPresentedDigestFiledAsIdentityTests(unittest.TestCase):
    """T14-10, citation digest limb: no presented digest filed as identity."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def freeze_with_supplied_digest(self):
        invocation = harness.base_invocation(
            self.out, receipt_digest=SUPPLIED_DIGEST
        )
        return harness.run_intake_freeze(invocation, self.out)

    def test_supplied_digest_differing_from_self_digest_is_filed_nowhere(self):
        result = self.freeze_with_supplied_digest()
        self.assertIsNotNone(result)
        self.assertNotEqual(result, SUPPLIED_DIGEST)
        # No filed artefact of the freeze names the supplied
        # value at all: no text names a presented form for a
        # freeze receipt digest, so it stands not at all, in the
        # anchor text and in every other filed text alike.
        self.assertNotIn(SUPPLIED_DIGEST, harness.combined_text(self.out))

    def test_anchor_text_names_the_issued_self_digest_as_receipt_digest(self):
        result = self.freeze_with_supplied_digest()
        self.assertIsNotNone(result)
        anchor = harness.signature_text(self.out, "anchor record")
        named = {}
        for line in anchor.splitlines():
            name, _, value = line.partition(":")
            named[name.strip()] = value.strip()
        self.assertEqual(named["anchor entry"], result)
        self.assertEqual(named["receipt digest"], result)

    def test_anchor_receipt_digest_is_the_custody_receipt_self_digest(self):
        result = self.freeze_with_supplied_digest()
        self.assertIsNotNone(result)
        receipt_text = harness.signature_text(self.out, "custody receipt")
        self_digest = None
        for line in receipt_text.splitlines():
            if line.startswith("receipt self digest:"):
                self_digest = line.partition(":")[2].strip()
        self.assertEqual(self_digest, result)
        anchor = harness.signature_text(self.out, "anchor record")
        self.assertIn("receipt digest: " + self_digest, anchor)


if __name__ == "__main__":
    unittest.main()
