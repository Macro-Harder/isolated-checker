"""Self describing frozen set, addendum form and fixity checks.

Pins brief sections 5.28 to 5.33, covering slices S-01, S-06 and
S-15: the context record carrying set intrinsic fields only, the
addendum form and its successor and consequence rule, and the
scheduled fixity checks with the match word, the quarter selection in
receipt digest order with its rotation cursor and due limb, and the
mismatch form as a custody gap against the store taking no exit
status and issuing no discrepancy report. A fixity outcome takes no
exit status, stated by the harness as a return value of None. Fixity
invocations name the kept sets by receipt digest in the receipt
field, as brief section 5.8 states, through the harness field
kept_set_receipt_digests.

Scenario keys used here: context, a mapping presenting a context
record claim that departs from the pinned pair or from the intrinsic
field list; algorithm_trust, a mapping presenting an algorithm trust
declaration state for a run; addendum, a mapping with form in valid,
missing, fork, cycle, unauthorised_filer_roster,
unauthorised_filer_identity, superseded_link, two_successors or
later_intake, and labelled_late, a boolean; check_point, a mapping
with cursor, the receipt digest cursor from the previous point or
None, due sets presented through check_point_history, a mapping from
a kept set digest to the number of check points it has already had,
so the set whose fourth check point falls at this point is derived
from that material, and mismatch, the digest of a set whose bytes no
longer recompute, or lost_receipt, the digest of a set whose receipt
is lost, or restore, added_ahead_of_cursor, removed_checked_sets or
resolution, the further fixity presentations, and kept_run_records,
a list of kept run records presented by their statement digests with
their record contents and anchor digests, for the kept run record
form of brief section 5.33.
"""

import hashlib
import json
import pathlib
import re
import tempfile
import unittest

import harness

D1 = harness._digest("kept:set:1")
D2 = harness._digest("kept:set:2")
D3 = harness._digest("kept:set:3")
D4 = harness._digest("kept:set:4")
D5 = harness._digest("kept:set:5")
D6 = harness._digest("kept:set:6")
D7 = harness._digest("kept:set:7")
D8 = harness._digest("kept:set:8")
KEPT = sorted([D1, D2, D3, D4, D5, D6, D7, D8])

CONTEXT_FIELDS = [
    "build",
    "stage",
    "packet form version",
    "digest algorithm and canonical form",
    "standing rules versions",
    "outside standards versions",
]

ADDENDUM_FIELDS = [
    "original digest",
    "corrected digest",
    "correction time",
    "reason",
    "filed by seat",
]

FIXITY_RECORD_FIELDS = [
    "kept sets",
    "selected sets",
    "cursor",
    "result per set",
    "mismatch standing",
]

VERSION_ENTRY_FIELDS = [
    "version",
    "became current time",
    "packet form versions",
    "calibration suite version and result",
    "declaration state",
    "calibration events",
    "declaration events",
]


class ContextRecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def run_case(self, **overrides):
        invocation = harness.verdict_invocation(self.out, **overrides)
        return harness.run_invocation(invocation, self.out)

    def test_context_record_carries_the_intrinsic_fields(self):
        status = self.run_case()
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("packet-form-1", text)
        self.assertIn("isolated-checker-test-build", text)

    def test_context_record_field_list_matches_the_brief_list_in_order(self):
        self.run_case()
        record = harness.signature_text(self.out, "context record")
        self.assertEqual(harness.record_fields(record), CONTEXT_FIELDS)

    def test_context_record_names_no_receipt_digest(self):
        self.run_case(scenario={"context": {"names_receipt_digest": True}})
        text = harness.combined_text(self.out)
        self.assertNotIn("context record names receipt", text)

    def test_algorithm_claim_departing_from_the_pinned_pair_cannot_run_clean(self):
        status = self.run_case(
            scenario={
                "context": {"algorithm_claim": "unpinned"},
                "determination_support": "supported",
            }
        )
        self.assertEqual(status, 1)
        self.assertNotEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("pinned pair", text)
        statement = harness.signature_text(self.out, "run statement")
        self.assertIn("algorithm trust state", statement)
        state_lines = [
            line
            for line in statement.splitlines()
            if line.strip().lower().startswith("algorithm trust state")
        ]
        self.assertTrue(state_lines)
        self.assertIn(
            state_lines[0].split(":", 1)[1].strip(),
            ("trusted", "declared untrusted"),
        )
        self.assertIn("restated", text)
        self.assertIn("citation strength", text)
        self.assertIn("digest match under", text)
        self.assertIn("no longer trusted", text)

    def test_declared_untrusted_algorithm_with_no_successor_takes_status_2(self):
        status = self.run_case(
            scenario={
                "algorithm_trust": {
                    "state": "declared_untrusted",
                    "declaration_digest": harness._digest("declaration:alg"),
                    "successor_in_force": False,
                }
            }
        )
        self.assertEqual(status, 2)
        text = harness.combined_text(self.out)
        self.assertIn("UNVERIFIABLE", text)
        self.assertIn("declared untrusted", text)
        self.assertIn(harness._digest("declaration:alg"), text)
        self.assertIn("digest match under", text)
        self.assertIn("no longer trusted", text)

    def test_kept_set_redigested_under_a_successor_runs_on_the_second_digests(self):
        status = self.run_case(
            scenario={
                "algorithm_trust": {
                    "state": "declared_untrusted",
                    "second_digesting": {
                        "done": True,
                        "successor": "successor-algorithm",
                        "old_digest": harness._digest("digest:old"),
                        "new_digest": harness._digest("digest:new"),
                    },
                }
            }
        )
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn(harness._digest("digest:old"), text)
        self.assertIn(harness._digest("digest:new"), text)
        self.assertIn("addendum", text)
        self.assertIn("original receipt never rewritten", text)

    def test_run_specific_fields_stand_in_the_run_statement(self):
        self.run_case()
        statement = harness.signature_text(self.out, "run statement")
        self.assertIn("checker-1.0.0", statement)
        self.assertIn("layout-form-1", statement)


class AddendumTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def run_case(self, **overrides):
        invocation = harness.verdict_invocation(self.out, **overrides)
        return harness.run_invocation(invocation, self.out)

    def test_valid_addendum_reports_both_digests_and_which_was_checked(self):
        status = self.run_case(scenario={"addendum": {"form": "valid"}})
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn(harness._digest("artefact:original"), text)
        self.assertIn(harness._digest("artefact:corrected"), text)

    def test_addendum_field_list_matches_the_brief_list_in_order(self):
        self.run_case(scenario={"addendum": {"form": "valid"}})
        record = harness.signature_text(self.out, "addendum")
        self.assertEqual(harness.record_fields(record), ADDENDUM_FIELDS)
        self.assertIn("filer claim", record)

    def test_superseded_link_is_a_discrepancy_naming_both_digests(self):
        status = self.run_case(
            scenario={"addendum": {"form": "superseded_link"}}
        )
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn(harness._digest("artefact:original"), text)
        self.assertIn(harness._digest("artefact:corrected"), text)

    def test_correction_with_no_addendum_is_not_a_clean_pass(self):
        status = self.run_case(scenario={"addendum": {"form": "missing"}})
        self.assertEqual(status, 1)
        self.assertNotEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("no addendum", text)
        self.assertIn("correction", text)

    def test_labelled_late_completion_is_still_reported_late(self):
        status = self.run_case(
            scenario={
                "addendum": {
                    "form": "valid",
                    "labelled_late": True,
                    "missed_property": "filed before the gate opened",
                }
            }
        )
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("late", text)
        self.assertIn("filed before the gate opened", text)
        self.assertIn("not a pass", text)

    def test_corrected_bytes_are_checked_only_as_a_new_intake(self):
        status = self.run_case(
            scenario={"addendum": {"form": "corrected_bytes_original_link"}}
        )
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("new intake", text)
        self.assertIn("never under the original link authority", text)

    def test_no_report_states_a_correction_time_as_a_checked_fact(self):
        self.run_case(scenario={"addendum": {"form": "valid"}})
        text = harness.combined_text(self.out)
        self.assertIn("filer claim", text)
        self.assertNotIn("correction time: checked fact", text)

    def test_two_addenda_claiming_the_same_predecessor_take_no_terminal_digest(self):
        status = self.run_case(
            scenario={"addendum": {"form": "two_successors"}}
        )
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("two addenda", text)
        self.assertIn(harness._digest("artefact:original"), text)
        self.assertIn("no terminal digest", text)

    def test_addendum_arriving_in_a_later_intake_is_a_new_intake_matter(self):
        status = self.run_case(
            scenario={"addendum": {"form": "later_intake"}}
        )
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("later intake", text)
        self.assertIn("new intake", text)
        self.assertIn(harness._digest("artefact:original"), text)
        self.assertIn(harness._digest("artefact:corrected"), text)

    def test_forked_addendum_chain_takes_no_terminal_digest(self):
        status = self.run_case(scenario={"addendum": {"form": "fork"}})
        self.assertEqual(status, 1)
        self.assertIn("fork", harness.combined_text(self.out))

    def test_cyclic_addendum_chain_takes_no_terminal_digest(self):
        status = self.run_case(scenario={"addendum": {"form": "cycle"}})
        self.assertEqual(status, 1)
        self.assertIn("cycle", harness.combined_text(self.out))

    def test_unauthorised_filer_failing_the_roster_test_is_not_followed(self):
        status = self.run_case(
            scenario={"addendum": {"form": "unauthorised_filer_roster"}}
        )
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("unauthorised filing", text)
        self.assertIn("roster", text)

    def test_unauthorised_filer_failing_the_identity_test_is_not_followed(self):
        status = self.run_case(
            scenario={"addendum": {"form": "unauthorised_filer_identity"}}
        )
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("unauthorised filing", text)
        self.assertIn("identity match", text)


class VersionEntryFormTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def test_version_history_entry_field_list_matches_the_brief_list_in_order(self):
        invocation = harness.verdict_invocation(
            self.out,
            scenario={"version_history": {"entry_presented": True}},
        )
        harness.run_invocation(invocation, self.out)
        record = harness.signature_text(self.out, "version entry")
        self.assertEqual(harness.record_fields(record), VERSION_ENTRY_FIELDS)


class FixityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def fixity(self, kept, out=None, **overrides):
        target = out or self.out
        overrides.setdefault("mode", "fixity")
        overrides.setdefault("kept_set_receipt_digests", kept)
        invocation = harness.base_invocation(target, **overrides)
        return harness.run_invocation(invocation, target)

    def test_matching_sets_take_the_word_match_and_no_status(self):
        status = self.fixity(KEPT[:3])
        self.assertIsNone(status)
        self.assertIn("match", harness.combined_text(self.out))

    def test_fixity_writes_exactly_one_record_to_the_store_record(self):
        self.fixity(KEPT[:3])
        records = [
            path
            for path in harness.artefacts(self.out)
            if "fixity record" in path.read_text(
                encoding="utf-8", errors="replace"
            )
        ]
        self.assertEqual(len(records), 1)
        record = harness.signature_text(self.out, "fixity record")
        self.assertEqual(harness.record_fields(record), FIXITY_RECORD_FIELDS)

    def test_store_record_carries_predictability_and_the_restore_bound_as_limits(self):
        self.fixity(KEPT[:3], scenario={"store_record_limits": True})
        record = harness.signature_text(self.out, "store record")
        self.assertIn("predictability", record)
        self.assertIn("restore bound", record)
        self.assertIn("limit", record)

    def test_three_kept_sets_select_exactly_one_set(self):
        self.fixity(KEPT[:3])
        text = harness.combined_text(self.out)
        selected = [digest for digest in KEPT[:3] if digest in text]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0], KEPT[0])

    def test_quarter_of_eight_kept_sets_selects_two_sets(self):
        self.fixity(KEPT)
        text = harness.combined_text(self.out)
        selected = [digest for digest in KEPT if digest in text]
        self.assertEqual(selected, KEPT[:2])

    def test_first_point_begins_at_the_smallest_digest(self):
        self.fixity(KEPT, scenario={"check_point": {"cursor": None}})
        text = harness.combined_text(self.out)
        self.assertIn(KEPT[0], text)
        self.assertNotIn(KEPT[-1], text)

    def test_selection_resumes_after_the_cursor_and_wraps(self):
        self.fixity(
            KEPT,
            scenario={"check_point": {"cursor": KEPT[-2]}},
        )
        text = harness.combined_text(self.out)
        self.assertIn(KEPT[-1], text)
        self.assertIn(KEPT[0], text)

    def test_due_set_is_derived_from_its_check_point_history(self):
        self.fixity(
            KEPT,
            scenario={
                "check_point": {
                    "cursor": KEPT[0],
                    "check_point_history": {KEPT[5]: 3, KEPT[1]: 1},
                }
            },
        )
        self.assertIn(KEPT[5], harness.combined_text(self.out))

    def test_removed_cursor_set_begins_at_the_next_greater_digest(self):
        kept = [digest for digest in KEPT if digest != KEPT[2]]
        self.fixity(
            kept,
            scenario={"check_point": {"cursor": KEPT[2]}},
        )
        self.assertIn(KEPT[3], harness.combined_text(self.out))

    def test_sets_added_ahead_of_the_cursor_join_the_selection_in_order(self):
        added = harness._digest("kept:set:added")
        kept = sorted(KEPT[:4] + [added])
        self.fixity(
            kept,
            scenario={
                "check_point": {
                    "cursor": KEPT[0],
                    "added_ahead_of_cursor": [added],
                }
            },
        )
        text = harness.combined_text(self.out)
        self.assertIn(added, text)
        self.assertIn("added", text)

    def test_removal_of_checked_sets_advances_the_selection_past_them(self):
        self.fixity(
            KEPT,
            scenario={
                "check_point": {
                    "cursor": KEPT[0],
                    "removed_checked_sets": [KEPT[1]],
                }
            },
        )
        text = harness.combined_text(self.out)
        self.assertIn(KEPT[1], text)
        self.assertIn("removed", text)
        self.assertIn(KEPT[2], text)

    def test_mismatch_is_a_store_custody_gap_with_no_status_and_no_report(self):
        status = self.fixity(
            KEPT[:3],
            scenario={"check_point": {"mismatch": KEPT[0]}},
        )
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("custody gap", text)
        self.assertIn("store", text)
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "discrepancy report")
        )

    def test_mismatch_suspends_the_rerun_and_appeal_routes(self):
        self.fixity(
            KEPT[:3],
            scenario={"check_point": {"mismatch": KEPT[0]}},
        )
        self.assertIn("suspended", harness.combined_text(self.out))

    def test_resolution_act_is_a_new_intake_of_the_material_as_it_now_stands(self):
        self.fixity(
            KEPT[:3],
            scenario={
                "check_point": {
                    "mismatch": KEPT[0],
                    "resolution": "new_intake",
                }
            },
        )
        text = harness.combined_text(self.out)
        self.assertIn("new intake of the material as it now stands", text)

    def test_restored_set_takes_the_word_match_again_after_its_new_intake(self):
        status = self.fixity(
            KEPT[:3],
            scenario={"check_point": {"restore": KEPT[0]}},
        )
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("restored", text)
        self.assertIn("match", text)

    def test_unresolvable_set_keeps_its_routes_closed(self):
        self.fixity(
            KEPT[:3],
            scenario={
                "check_point": {
                    "mismatch": KEPT[0],
                    "material_available": False,
                }
            },
        )
        self.assertIn("unresolvable", harness.combined_text(self.out))

    def kept_run_record(self, label):
        record = {
            "statement digest": harness._digest("stmt:" + label),
            "checker version": "checker-1.0.0",
            "report digest": harness._digest("report:" + label),
        }
        canonical = json.dumps(record, sort_keys=True) + "\n"
        anchor = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return {"record": record, "anchor_digest": anchor}

    def test_kept_run_records_are_ordered_and_counted_by_statement_digest(self):
        presented = [
            self.kept_run_record("record-c"),
            self.kept_run_record("record-a"),
            self.kept_run_record("record-b"),
        ]
        status = self.fixity(
            KEPT[:3],
            scenario={"check_point": {"kept_run_records": presented}},
        )
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("kept run records: 3", text)
        digests = sorted(
            item["record"]["statement digest"] for item in presented
        )
        positions = [text.index(digest) for digest in digests]
        self.assertEqual(positions, sorted(positions))

    def test_kept_run_record_self_digest_recomputed_against_its_anchor_takes_match(self):
        presented = [self.kept_run_record("record-a")]
        status = self.fixity(
            KEPT[:3],
            scenario={"check_point": {"kept_run_records": presented}},
        )
        self.assertIsNone(status)
        record = harness.signature_text(self.out, "fixity record")
        statement_digest = presented[0]["record"]["statement digest"]
        self.assertTrue(
            any(
                statement_digest in line and re.search(r"\bmatch\b", line)
                for line in record.splitlines()
            )
        )
        self.assertFalse(
            any(
                statement_digest in line and "store discrepancy" in line
                for line in record.splitlines()
            )
        )
        self.assertIn(presented[0]["anchor_digest"], record)
        self.assertIn(statement_digest, record)

    def test_kept_run_record_mismatch_is_a_store_discrepancy_with_routes_suspended(self):
        presented = [self.kept_run_record("record-a")]
        presented[0]["anchor_digest"] = harness._digest("anchor:other")
        status = self.fixity(
            KEPT[:3],
            scenario={"check_point": {"kept_run_records": presented}},
        )
        self.assertIsNone(status)
        record = harness.signature_text(self.out, "fixity record")
        self.assertIn("store discrepancy", record)
        self.assertIn("suspended", record)
        lines = record.splitlines()
        statement_digest = presented[0]["record"]["statement digest"]
        self.assertFalse(
            any(
                statement_digest in line and re.search(r"\bmatch\b", line)
                for line in lines
            )
        )
        self.assertTrue(
            any(
                "rerun" in line and "suspended" in line
                for line in lines
            )
        )
        self.assertTrue(
            any(
                "appeal" in line and "suspended" in line
                for line in lines
            )
        )
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "discrepancy report")
        )

    def test_lost_receipt_suspends_the_routes_while_no_target_stands(self):
        status = self.fixity(
            KEPT[:3],
            scenario={"check_point": {"lost_receipt": KEPT[1]}},
        )
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("lost", text)
        self.assertIn("suspended", text)


if __name__ == "__main__":
    unittest.main()
