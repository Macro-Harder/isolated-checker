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

import unittest

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


if __name__ == "__main__":
    unittest.main()
