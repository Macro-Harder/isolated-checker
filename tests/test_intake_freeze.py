"""Intake, freeze and the run record pair form, slices S-01 and S-03.

Pins brief sections 5.2 to 5.4 and 5.17, and criterion F1 in its
intake limbs and criterion A3 in its pair form: one custody receipt
per intake issued at freeze, freeze as a two pass atomic capture in
which any difference between the two full set passes is an intake
failure and no receipt issues, material that cannot be frozen taking
an intake failure record outside the frozen set with no report and no
exit status, and one run statement per verdict standing run as the
run half of the same artefact pair. Freeze intake is called outside
the mode field, as brief section 5.8 states, through the harness
run_intake_freeze helper. An intake failure takes no exit status,
stated by the harness as a return value of None.

Scenario keys used here: freeze, a mapping with second_pass_differs, a
boolean presenting source material that changes between the two
passes, cannot_be_frozen, a boolean presenting material that cannot
be frozen at all, anchor_entry, a boolean
presenting the anchor entry written at freeze time, and late_member,
a boolean presenting a member arriving after the freeze, in the late
member case; seal, as in the
seal module, with whole_intake_removed presented under that key, not
as a field of the freeze mapping; store_production,
a mapping presenting a held set called for by its custody receipt
digest, with withdrawn stating a set called for after withdrawal;
pairing, a mapping presenting a run statement and a report paired
across runs or with a set digest absent or exchanged;
gate_citation_omits_statement, a boolean presenting a gate citation
of a verdict that omits its run statement; quote, a mapping
presenting a discrepancy that needs packet text quoted;
disagreement_protocol, a mapping presenting one case of the Decision
4 disagreement protocol beside a report; presented_receipt, the
receipt entries presented for a freeze, each naming a member with
its digest and byte size, in the receipt member case; checks, as in
the seal module, in the pair form and disagreement cases;
interrupted, a boolean presenting a run interrupted before its
completion act; torn_run, a mapping with form in
report_without_completion_act or report_without_run_statement,
presenting a torn run output in the interrupted cases.
"""

import pathlib
import re
import tempfile
import unittest

import harness

RECEIPT_FIELDS = [
    "build",
    "stage",
    "members",
    "member sources",
    "frozen by seat",
    "handed over by seat",
    "freeze time",
    "sequence element",
    "context record digest",
    "receipt self digest",
]

RUN_STATEMENT_FIELDS = [
    "checker version",
    "receipt digest",
    "computed set digest",
    "layout digest",
    "outside sources",
    "calibration state",
    "bound values and ruling",
    "digest algorithm and canonical form",
    "algorithm trust state",
    "operator seat",
    "layout identity and version",
    "fixture suite version",
    "roster state source",
    "intake order field",
    "snapshot digests",
    "version standing",
    "defective run statement citation",
    "report digest",
]

LIMIT_NAMES = [
    "quality or substance",
    "epistemic independence",
    "personal identity",
    "content of a brief",
    "checker isolation or integrity",
    "truth of a stated reason",
    "completeness beyond the layout and fields actually read",
    "authenticity beyond the anchor actually consulted",
    "timing property no record taken at the time supports",
    "semantic fidelity",
    "agreement as truth",
    "platform fact where the platform record is the only witness",
    "recorded gap as repaired, dry run as verdict, later verdict as earlier",
    "unidentifiable citation as an identified artefact",
    "check that did not run as a pass",
    "digest match as proof the bytes are the bytes originally filed",
]

MEMBER_TEXTS = {
    "notes.txt": "The notes artefact body.\n",
    "step-record.txt": "Step record sections 1 to 3.\n",
}


def member_entries():
    entries = []
    for name in sorted(MEMBER_TEXTS):
        data = MEMBER_TEXTS[name].encode("utf-8")
        entries.append(
            {
                "name": name,
                "digest_git_blob_sha1": harness._blob_digest(data),
                "byte_size": len(data),
            }
        )
    return entries


class IntakeFreezeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def freeze(self, **overrides):
        invocation = harness.base_invocation(self.out, **overrides)
        return harness.run_intake_freeze(invocation, self.out)

    def test_clean_freeze_issues_exactly_one_receipt(self):
        result = self.freeze()
        self.assertIsNotNone(result)
        receipts = [
            path
            for path in harness.artefacts(self.out)
            if "custody receipt" in path.read_text(
                encoding="utf-8", errors="replace"
            )
        ]
        self.assertEqual(len(receipts), 1)

    def test_receipt_names_every_member_by_digest_and_byte_size(self):
        # Re-expected under Step 14 finding T14-05: a member
        # presented by digest and byte size only, with no bytes,
        # is never frozen on the presented digest, so this pin
        # now presents the same members by their bytes, in the
        # real content form, and the receipt names them by the
        # digests recomputed from those bytes, which are the
        # member_entries digests below.
        self.freeze(
            scenario={
                "presented_members": [
                    {"name": name, "content": MEMBER_TEXTS[name]}
                    for name in sorted(MEMBER_TEXTS)
                ]
            }
        )
        receipt = harness.signature_text(self.out, "custody receipt")
        for entry in member_entries():
            self.assertIn(entry["name"], receipt)
            self.assertIn(entry["digest_git_blob_sha1"], receipt)
            self.assertIn(str(entry["byte_size"]), receipt)
        self.assertIn("first", receipt)

    def test_receipt_field_list_matches_the_brief_list_in_order(self):
        self.freeze()
        receipt = harness.signature_text(self.out, "custody receipt")
        self.assertEqual(harness.record_fields(receipt), RECEIPT_FIELDS)

    def test_second_pass_difference_is_an_intake_failure_with_no_receipt(self):
        result = self.freeze(scenario={"freeze": {"second_pass_differs": True}})
        self.assertIsNone(result)
        names = [path.name for path in harness.artefacts(self.out)]
        self.assertFalse(any("receipt" in name for name in names))
        self.assertIn("intake failure", harness.combined_text(self.out))

    def test_material_that_cannot_be_frozen_takes_an_intake_failure_record(self):
        result = self.freeze(scenario={"freeze": {"cannot_be_frozen": True}})
        self.assertIsNone(result)
        text = harness.combined_text(self.out)
        self.assertIn("intake failure", text)
        names = [path.name for path in harness.artefacts(self.out)]
        self.assertFalse(any("report" in name for name in names))

    def test_anchor_entry_written_at_freeze_carries_its_qualified_form(self):
        self.freeze(scenario={"freeze": {"anchor_entry": True}})
        text = harness.combined_text(self.out)
        self.assertIn("anchor", text)
        self.assertIn("detects accident and casual rewriting", text)
        self.assertIn("not a determined editor", text)

    def test_freeze_writes_no_gate_record_and_authors_no_intake_order_field(self):
        # Re-expected under Step 14 finding T14-03: SH-40 and Q8
        # state the checker writes into the gate record in no case
        # and beside it in no case, and SH-08 states the intake
        # order field is the operator's field. The earlier
        # expectation, that the freeze writes that field naming
        # the invocation receipt digest, is the contrary
        # expectation that finding names.
        result = self.freeze(scenario={"freeze": {"anchor_entry": True}})
        self.assertIsNotNone(result)
        names = [path.name for path in harness.artefacts(self.out)]
        self.assertNotIn("gate-record.txt", names)
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "gate record")
        )

    def test_late_member_is_a_new_intake_and_never_an_edit(self):
        first = self.freeze()
        self.assertIsNotNone(first)
        out2 = pathlib.Path(self.tmp.name) / "out2"
        invocation = harness.base_invocation(
            out2,
            receipt_digest=harness._digest("receipt:second"),
            scenario={"freeze": {"late_member": True}},
        )
        second = harness.run_intake_freeze(invocation, out2)
        self.assertIsNotNone(second)
        # Re-expected under Step 14 finding T14-10, citation digest
        # limb: the digest filed for the new intake is the issued
        # receipt's own self digest, the value this freeze returns.
        # The earlier expectation, that the invocation supplied
        # receipt digest stands in the filed text, is the contrary
        # expectation that finding names, a presented digest filed
        # as a record identity.
        self.assertIn(second, harness.combined_text(out2))
        self.assertNotIn(
            harness._digest("receipt:second"),
            harness.combined_text(out2),
        )


class ProductionAndPairingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def run_case(self, **overrides):
        invocation = harness.verdict_invocation(self.out, **overrides)
        return harness.run_invocation(invocation, self.out)

    def test_production_of_a_held_set_matches_its_receipt_member_by_member(self):
        status = self.run_case(
            mode="rerun",
            original_run_statement_digest=harness._digest("stmt:original"),
            scenario={
                "store_production": {
                    "receipt_digest": harness._digest("receipt:base"),
                    "members": member_entries(),
                }
            },
        )
        self.assertEqual(status, 0)
        produced = harness.signature_text(self.out, "produced set")
        for entry in member_entries():
            self.assertIn(entry["name"], produced)
            self.assertIn(entry["digest_git_blob_sha1"], produced)
            self.assertIn(str(entry["byte_size"]), produced)
        member_digests = re.findall(r"\b[0-9a-f]{40}\b", produced)
        self.assertEqual(len(member_digests), len(member_entries()))

    def test_set_called_for_after_withdrawal_takes_the_production_failure(self):
        status = self.run_case(
            mode="rerun",
            original_run_statement_digest=harness._digest("stmt:original"),
            scenario={
                "store_production": {
                    "receipt_digest": harness._digest("receipt:base"),
                    "members": member_entries(),
                    "withdrawn": True,
                }
            },
        )
        self.assertEqual(status, 2)
        self.assertNotEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("cannot be produced in its receipt form", text)
        self.assertNotIn("rebuilt set", text)
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "comparison record")
        )

    def test_whole_intake_removed_is_compared_against_the_intake_order_field(self):
        status = self.run_case(
            scenario={"seal": "whole_intake_removed"}
        )
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("custody gap", text)
        self.assertIn("intake order", text)

    def test_run_statement_of_one_run_beside_the_report_of_another_is_rejected(self):
        status = self.run_case(
            scenario={
                "pairing": {
                    "form": "statement_of_one_run_report_of_another",
                    "statement_run": "run-a",
                    "report_run": "run-b",
                }
            }
        )
        self.assertEqual(status, 1)
        self.assertNotEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("rejected as a citation", text)
        self.assertIn("run-a", text)
        self.assertIn("run-b", text)

    def test_statement_with_one_set_digest_absent_counts_as_disagreement(self):
        status = self.run_case(
            scenario={"pairing": {"form": "one_set_digest_absent"}}
        )
        self.assertEqual(status, 1)
        self.assertNotEqual(status, 0)
        self.assertIn(
            "rejected as a citation", harness.combined_text(self.out)
        )

    def test_statement_with_the_two_set_digests_exchanged_counts_as_disagreement(self):
        status = self.run_case(
            scenario={"pairing": {"form": "set_digests_exchanged"}}
        )
        self.assertEqual(status, 1)
        self.assertNotEqual(status, 0)
        self.assertIn(
            "rejected as a citation", harness.combined_text(self.out)
        )

    def test_gate_citation_omitting_the_statement_is_incomplete_and_barred(self):
        status = self.run_case(
            scenario={"gate_citation_omits_statement": True}
        )
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("incomplete", text)
        self.assertIn("may not rely", text)

    def test_quote_is_compared_against_its_source_and_carries_its_qualification(self):
        quote_text = "the step finished before the gate opened"
        source = MEMBER_TEXTS["notes.txt"] + quote_text + "\n"
        status = self.run_case(
            scenario={
                "checks": {"chain": "fail"},
                "quote": {
                    "text": quote_text,
                    "source_artefact": "notes.txt",
                    "source_digest": harness._blob_digest(
                        source.encode("utf-8")
                    ),
                    "qualification": "transcription strength only",
                },
            }
        )
        self.assertEqual(status, 1)
        report = harness.signature_text(self.out, "discrepancy report")
        self.assertIn(quote_text, report)
        self.assertIn("notes.txt", report)
        self.assertIn("filer claim", report)
        self.assertIn("transcription strength only", report)
        self.assertIn("packet text", report)

    def test_each_limit_is_compared_limit_by_limit_against_the_fixed_table(self):
        status = self.run_case()
        self.assertEqual(status, 0)
        report = harness.signature_text(self.out, "discrepancy report")
        self.assertEqual(report.count("always bounding"), 16)
        for index, name in enumerate(LIMIT_NAMES, start=1):
            self.assertIn("limit " + str(index), report)
            self.assertIn(name, report)

    def test_disagreement_protocol_failure_reproduced_is_recorded_beside_the_failure(self):
        status = self.run_case(
            scenario={
                "checks": {"chain": "fail"},
                "disagreement_protocol": {"case": "failure_reproduced"},
            }
        )
        self.assertEqual(status, 1)
        gate = harness.signature_text(self.out, "gate record")
        self.assertIn("board judgement", gate)
        self.assertIn("failure stands", gate)
        self.assertNotIn("relabeled", gate)

    def test_disagreement_protocol_board_failure_beside_a_pass_is_recorded(self):
        status = self.run_case(
            scenario={
                "disagreement_protocol": {"case": "board_finds_failure"}
            }
        )
        self.assertEqual(status, 0)
        gate = harness.signature_text(self.out, "gate record")
        self.assertIn("board finding", gate)
        self.assertIn("does not compel", gate)

    def test_disagreement_protocol_unrecorded_disagreement_is_never_resolved(self):
        status = self.run_case(
            scenario={
                "disagreement_protocol": {"case": "unrecorded"}
            }
        )
        self.assertEqual(status, 0)
        gate = harness.signature_text(self.out, "gate record")
        self.assertIn("never having been resolved", gate)


class RunStatementPairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def run_case(self, **overrides):
        invocation = harness.verdict_invocation(self.out, **overrides)
        return harness.run_invocation(invocation, self.out)

    def statement_text(self):
        return harness.signature_text(self.out, "run statement")

    def test_one_run_statement_stands_per_verdict_run(self):
        self.run_case()
        statements = [
            path
            for path in harness.artefacts(self.out)
            if "run statement" in path.read_text(
                encoding="utf-8", errors="replace"
            )
        ]
        self.assertEqual(len(statements), 1)

    def test_run_statement_field_list_matches_the_brief_list_in_order(self):
        self.run_case()
        self.assertEqual(
            harness.record_fields(self.statement_text()),
            RUN_STATEMENT_FIELDS,
        )

    def test_run_statement_carries_receipt_and_computed_set_digests_as_two_fields(self):
        self.run_case()
        statement = self.statement_text()
        self.assertIn(harness._digest("receipt:base"), statement)
        self.assertIn("computed set digest", statement)

    def test_run_statement_names_each_outside_source_consulted_by_kind(self):
        self.run_case()
        self.assertIn("source", self.statement_text())

    def test_run_statement_carries_the_calibration_state_and_its_record_digest(self):
        self.run_case()
        statement = self.statement_text()
        self.assertIn("calibrated", statement)

    def test_run_statement_carries_bound_values_and_the_ruling_reference(self):
        self.run_case()
        statement = self.statement_text()
        self.assertIn(harness.TEST_BOUND_RULING_REF, statement)
        self.assertIn("no bound reached", statement)

    def test_run_statement_carries_the_snapshot_digests(self):
        self.run_case()
        self.assertIn("snapshot", self.statement_text())

    def test_interrupted_run_takes_no_status_and_its_output_is_discarded(self):
        status = self.run_case(scenario={"interrupted": True})
        self.assertIsNone(status)
        self.assertIn("interrupted", harness.combined_text(self.out))
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "discrepancy report")
        )

    def test_torn_run_report_form_output_without_a_completion_act_is_interrupted(self):
        status = self.run_case(
            scenario={"torn_run": {"form": "report_without_completion_act"}}
        )
        self.assertIsNone(status)
        record = harness.artefact_with_signature(self.out, "interrupted")
        self.assertIsNotNone(record)
        self.assertIn("interrupted run record", record[1])
        self.assertNotIn("verdict:", record[1])
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "discrepancy report")
        )

    def test_torn_run_output_with_its_run_statement_missing_is_interrupted(self):
        status = self.run_case(
            scenario={"torn_run": {"form": "report_without_run_statement"}}
        )
        self.assertIsNone(status)
        record = harness.artefact_with_signature(self.out, "interrupted")
        self.assertIsNotNone(record)
        self.assertIn("interrupted run record", record[1])
        self.assertNotIn("verdict:", record[1])
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "discrepancy report")
        )


if __name__ == "__main__":
    unittest.main()
