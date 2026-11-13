"""Step 14 cure wave 1 pinning tests, added on the fix register's authority.

Each test class pins one triaged finding of design/steps/
step-14-fix-register.md, written test first: the test was run red
against the code as it stood before its finding's cure, and the
cure in the same commit turned it green. Classes land in register
order: T14-03, T14-04, T14-05, T14-08, T14-12.

Scenario keys used here, beside the harness's own: pinning_record,
a mapping in the SH-44 field names presenting the pinning record
the operator supplied for the freeze; context_claim, a mapping
with digest_algorithm and canonical_form presenting the context
record claim the freeze compares against the pin;
standing_rule_versions and outside_standard_versions, lists of
version pairs in the SH-05 item forms presenting the standing
rules and outside standards versions source; gate_record, a
mapping presenting the operator filed gate record state the
freeze reads, with anchor_home naming the anchor home.
"""

import pathlib
import tempfile
import unittest

import harness


class T1403GateRecordAuthorshipTests(unittest.TestCase):
    """T14-03: the checker writes no gate record, in no case."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def freeze(self, **overrides):
        invocation = harness.base_invocation(self.out, **overrides)
        return harness.run_intake_freeze(invocation, self.out)

    def test_committed_freeze_produces_no_gate_record_artefact(self):
        result = self.freeze()
        self.assertIsNotNone(result)
        names = [path.name for path in harness.artefacts(self.out)]
        self.assertNotIn("gate-record.txt", names)
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "gate record")
        )

    def test_operator_filed_gate_record_stands_unchanged_by_a_freeze(self):
        self.out.mkdir(parents=True, exist_ok=True)
        operator_text = (
            "gate record\n"
            "intake order: first; receipt digest operator-filed\n"
            "anchor home: operator-anchor-home\n"
        )
        gate_path = self.out / "gate-record.txt"
        gate_path.write_text(operator_text, encoding="utf-8")
        result = self.freeze()
        self.assertIsNotNone(result)
        self.assertEqual(
            gate_path.read_text(encoding="utf-8"), operator_text
        )


if __name__ == "__main__":
    unittest.main()
