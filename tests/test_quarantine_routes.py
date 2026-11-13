"""Quarantine, cure, appeal and the CH7 recheck, slice S-16.

Pins brief sections 5.23 to 5.27: quarantine as a segregation rule
with its record form and its recorded gap exception, cure and appeal
as different routes in different record forms with their misform
treatments and their gate sequence window, and the CH7 recheck as an
operation called outside the mode field, with its case by case
outcomes. A recheck whose transition is present carries no whole
packet outcome and no whole packet exit status, stated by the harness
as a return value of None.

Scenario keys used here: route, a mapping with form in cure, appeal,
cure_disputing_a_fact, appeal_quietly_correcting or appeal_by_argument;
window, with values after_ruling_before_close, before_ruling or
after_gate_close; quarantine, a mapping presenting failed material,
its report digest and the discrepancies it must answer, or an
ingestion, destination, readership or marking presentation of
criterion F5; original_report_artefact, the path of the original
report file the run actually holds, for the neither route edits pin;
recheck, a mapping with transition in absent or present, and seal, as
in the seal module, for the recheck seal phase; checks, as in the
seal module, in the quarantine presentation cases; recorded_gap, a
boolean, in the recorded gap material case; bound_hit, as in the
outcomes module, in the recheck bound standing case; gating, as in
the gating module, in the recheck dry standing case.
"""

import hashlib
import pathlib
import tempfile
import unittest

import harness

QUARANTINE_FIELDS = [
    "report digest",
    "discrepancies",
    "failure wording",
]


class QuarantineRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def run_route(self, mode, out=None, **overrides):
        target = out or self.out
        overrides.setdefault("mode", mode)
        overrides.setdefault(
            "original_report_digest", harness._digest("report:original")
        )
        invocation = harness.verdict_invocation(target, **overrides)
        return harness.run_invocation(invocation, target)

    def test_failed_material_sits_in_quarantine_under_a_quarantine_record(self):
        status = self.run_route(
            "verdict",
            scenario={
                "checks": {"chain": "fail"},
                "quarantine": {
                    "report_digest": harness._digest("report:original"),
                    "discrepancies": [2, 5],
                },
            },
        )
        self.assertEqual(status, 1)
        record = harness.signature_text(self.out, "quarantine record")
        self.assertIn(harness._digest("report:original"), record)
        self.assertIn("2", record)
        self.assertIn("5", record)
        self.assertIn("FAIL", record)
        self.assertEqual(harness.record_fields(record), QUARANTINE_FIELDS)

    def test_recorded_gap_material_is_not_quarantined(self):
        status = self.run_route(
            "verdict", scenario={"recorded_gap": True}
        )
        self.assertEqual(status, 0)
        self.assertNotIn(
            "quarantine record", harness.combined_text(self.out)
        )

    def test_failed_material_is_never_filed_as_closure_evidence(self):
        self.run_route(
            "verdict",
            scenario={
                "checks": {"chain": "fail"},
                "quarantine": {"ingestion": "filed_as_closure_evidence"},
            },
        )
        text = harness.combined_text(self.out)
        self.assertIn("never filed as closure evidence", text)
        self.assertIn("not ingested as settled", text)

    def test_failed_material_is_not_ingested_into_shared_memory_as_settled(self):
        self.run_route(
            "verdict",
            scenario={
                "checks": {"chain": "fail"},
                "quarantine": {"destination": "shared_memory_as_settled"},
            },
        )
        self.assertIn(
            "not ingested as settled", harness.combined_text(self.out)
        )

    def test_record_of_a_failure_in_shared_memory_carries_the_failure_wording(self):
        self.run_route(
            "verdict",
            scenario={
                "checks": {"chain": "fail"},
                "quarantine": {
                    "marking": "shared_memory",
                    "report_digest": harness._digest("report:original"),
                    "discrepancies": [2],
                },
            },
        )
        record = harness.signature_text(self.out, "record of the failure")
        self.assertIn(harness._digest("report:original"), record)
        self.assertIn("FAIL", record)
        self.assertNotIn("settled", record)

    def test_readership_is_limited_to_the_stated_list(self):
        status = self.run_route(
            "verdict",
            scenario={
                "checks": {"chain": "fail"},
                "quarantine": {"reader": "an outside seat"},
            },
        )
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("readership", text)
        self.assertIn("gate board", text)
        self.assertIn("operator", text)
        self.assertIn("producers", text)
        self.assertIn("not open", text)

    def test_derived_material_is_marked_in_the_home_it_now_sits_in(self):
        self.run_route(
            "verdict",
            scenario={
                "checks": {"chain": "fail"},
                "quarantine": {
                    "derived_from_failed": "citation and digest references",
                    "report_digest": harness._digest("report:original"),
                    "discrepancies": [2],
                },
            },
        )
        text = harness.combined_text(self.out)
        self.assertIn("derived", text)
        self.assertIn("marked", text)
        self.assertIn(harness._digest("report:original"), text)

    def test_derived_material_with_no_stated_record_link_is_not_covered_by_the_marking(self):
        status = self.run_route(
            "verdict",
            scenario={
                "quarantine": {
                    "derived_from_failed": "no stated record link",
                    "report_digest": harness._digest("report:original"),
                    "discrepancies": [2],
                },
            },
        )
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("derived", text)
        self.assertIn("not covered by the marking", text)
        self.assertNotIn("quarantine record", text)

    def test_route_presented_before_the_ruling_is_not_run(self):
        status = self.run_route(
            "cure",
            discrepancy_numbers=[1],
            scenario={
                "route": {"form": "cure"},
                "window": "before_ruling",
            },
        )
        self.assertIsNone(status)
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "discrepancy report")
        )

    def test_cure_runs_in_full_on_a_new_intake_and_issues_a_new_report(self):
        status = self.run_route(
            "cure",
            discrepancy_numbers=[2, 5],
            scenario={"route": {"form": "cure"}},
        )
        self.assertEqual(status, 0)
        self.assertIsNotNone(
            harness.artefact_with_signature(self.out, "discrepancy report")
        )
        self.assertIsNotNone(
            harness.artefact_with_signature(self.out, "run statement")
        )

    def test_cure_record_names_the_discrepancies_and_the_original_report(self):
        self.run_route(
            "cure",
            discrepancy_numbers=[2, 5],
            scenario={"route": {"form": "cure"}},
        )
        text = harness.combined_text(self.out)
        self.assertIn(harness._digest("report:original"), text)
        self.assertIn("2", text)
        self.assertIn("5", text)

    def test_appeal_by_counter_evidence_produces_a_new_verdict(self):
        status = self.run_route(
            "appeal", scenario={"route": {"form": "appeal"}}
        )
        self.assertEqual(status, 0)
        self.assertIn(
            harness._digest("report:original"),
            harness.combined_text(self.out),
        )

    def test_appeal_by_argument_alone_has_no_route(self):
        status = self.run_route(
            "appeal", scenario={"route": {"form": "appeal_by_argument"}}
        )
        self.assertIsNone(status)
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "discrepancy report")
        )

    def test_cure_record_disputing_a_fact_is_treated_as_no_route(self):
        status = self.run_route(
            "cure",
            discrepancy_numbers=[1],
            scenario={"route": {"form": "cure_disputing_a_fact"}},
        )
        self.assertIsNone(status)

    def test_appeal_packet_quietly_correcting_is_recorded_as_a_cure(self):
        self.run_route(
            "appeal",
            scenario={"route": {"form": "appeal_quietly_correcting"}},
        )
        self.assertIn("cure", harness.combined_text(self.out))

    def test_route_presented_inside_the_window_is_run(self):
        status = self.run_route(
            "cure",
            discrepancy_numbers=[1],
            scenario={
                "route": {"form": "cure"},
                "window": "after_ruling_before_close",
            },
        )
        self.assertEqual(status, 0)

    def test_route_presented_after_the_gate_closes_is_not_run_for_that_gate(self):
        status = self.run_route(
            "cure",
            discrepancy_numbers=[1],
            scenario={
                "route": {"form": "cure"},
                "window": "after_gate_close",
            },
        )
        self.assertIsNone(status)
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "discrepancy report")
        )

    def test_neither_route_edits_the_original_report(self):
        original = pathlib.Path(self.tmp.name) / "original-report.txt"
        original.write_text("original report bytes", encoding="utf-8")
        before = hashlib.sha256(original.read_bytes()).hexdigest()
        for mode, extra in (
            ("cure", {"discrepancy_numbers": [1]}),
            ("appeal", {}),
        ):
            out = pathlib.Path(self.tmp.name) / ("out-" + mode)
            self.run_route(
                mode,
                out=out,
                scenario={
                    "route": {"form": mode},
                    "original_report_artefact": str(original),
                },
                **extra,
            )
            after = hashlib.sha256(original.read_bytes()).hexdigest()
            self.assertEqual(before, after)
            self.assertEqual(
                original.read_text(encoding="utf-8"),
                "original report bytes",
            )


class Ch7RecheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def recheck(self, **overrides):
        invocation = harness.base_invocation(self.out, **overrides)
        return harness.run_recheck(
            invocation,
            self.out,
            original_run_statement_digest=harness._digest("stmt:original"),
            gate_record={
                "digest": harness._digest("gate:record"),
                "names_pending_append": True,
            },
        )

    def test_transition_still_absent_takes_status_1(self):
        status = self.recheck(scenario={"recheck": {"transition": "absent"}})
        self.assertEqual(status, 1)
        self.assertIn("PARTIAL", harness.combined_text(self.out))

    def test_transition_present_carries_no_whole_packet_status(self):
        status = self.recheck(
            scenario={"recheck": {"transition": "present"}}
        )
        self.assertIsNone(status)
        self.assertIn(
            "transition present", harness.combined_text(self.out)
        )

    def test_recheck_issues_its_own_report_and_leaves_the_original_unedited(self):
        self.recheck(scenario={"recheck": {"transition": "absent"}})
        self.assertIsNotNone(
            harness.artefact_with_signature(self.out, "recheck report")
        )
        text = harness.combined_text(self.out)
        self.assertIn(
            harness._digest("report:original"),
            text,
        )
        self.assertIn("verdict run form", text)
        self.assertIn("cited", text)
        self.assertIn("never amended", text)

    def test_broken_seal_in_the_recheck_seal_phase_takes_custody_gap(self):
        status = self.recheck(
            scenario={
                "recheck": {"transition": "absent"},
                "seal": "altered_member",
            }
        )
        self.assertEqual(status, 1)
        self.assertIn("custody gap", harness.combined_text(self.out))

    def test_bound_standing_does_not_apply_to_a_recheck(self):
        status = self.recheck(
            scenario={
                "recheck": {"transition": "absent"},
                "bound_hit": {"bound": "read_volume_bytes"},
            }
        )
        self.assertEqual(status, 1)
        self.assertNotEqual(status, 3)

    def test_dry_standing_does_not_apply_to_a_recheck(self):
        status = self.recheck(
            scenario={
                "recheck": {"transition": "present"},
                "gating": {"calibration_state": "not_calibrated"},
            }
        )
        self.assertIsNone(status)
        self.assertNotEqual(status, 4)


if __name__ == "__main__":
    unittest.main()
