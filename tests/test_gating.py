"""Gating inputs, gating precedence and output area validation, slice S-07.

Pins brief sections 5.9 and 5.10: the gating inputs enforced before
any check runs, the four limb precedence order in its fixed form, and
the output area validation refusals. A refusal and the no bound values
state each take no exit status, which the harness states as a return
value of None, and each produces exactly the one artefact its limb
states and no other limb artefact.

Derivation and composition. The ReadInterfaceTests class presents
records and entries, not derived results, through IF-CAL, IF-VER and
IF-LAY and pins derivation over that material. The gating cases in
GatingTests present gating record states through the gating key;
those cases are composition only, pinning how presented states
compose under the precedence order, and are not derivation pins.

Scenario keys used here: gating, a mapping with calibration_state in
calibrated, not_calibrated, no_record or latest_failed;
declaration_state in none, quarantined or defective; version_current,
a boolean; suite_digest_matches, a boolean. Output area cases are
presented by the output_relation scenario key, with values valid,
inside_frozen_set, inside_packet_sources, inside_anchor_record,
names_existing_report and gate_evidence_home, the last standing for a
dry run whose output area is the gate evidence home. Read interface
cases are presented by the read_interface key, a mapping with kind in
IF-CAL, IF-VER or IF-LAY and the presented record or entry; IF-CAL
cases present a set of calibration records, in covering, non
covering, latest failing and suite digest mismatching forms, with no
record carrying a derived result field, and IF-VER cases present an
entry with its correction where the corrected standing is derived.
Filing
cases are presented by the filing key. Version history cases, slice
S-14, are presented by the version_history and gate_citation keys.
"""

import hashlib
import json
import pathlib
import tempfile
import unittest

import harness


def record_digest(record):
    """Digest a presented record in the harness canonical record form."""
    canonical = json.dumps(record, sort_keys=True) + "\n"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class GatingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def run_case(self, **overrides):
        invocation = harness.verdict_invocation(self.out, **overrides)
        return harness.run_invocation(invocation, self.out)

    def test_calibrated_current_undeclared_run_proceeds_to_a_verdict(self):
        status = self.run_case()
        self.assertEqual(status, 0)

    def test_quarantined_version_is_refused_with_no_status(self):
        status = self.run_case(
            scenario={"gating": {"declaration_state": "quarantined"}}
        )
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("refusal", text)
        self.assertIn("quarantine", text)

    def test_defective_version_is_refused_with_no_status(self):
        status = self.run_case(
            scenario={"gating": {"declaration_state": "defective"}}
        )
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("refusal", text)
        self.assertIn("defective", text)
        self.assertIn("declaration", text)
        self.assertEqual(len(harness.artefacts(self.out)), 1)
        refusal = harness.artefact_with_signature(self.out, "refusal record")
        self.assertIsNotNone(refusal)
        self.assertIn("declaration", refusal[1])
        self.assertIn("defective", refusal[1])
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "discrepancy report")
        )

    def test_refusal_on_a_declared_version_produces_no_report(self):
        self.run_case(
            scenario={"gating": {"declaration_state": "quarantined"}}
        )
        self.assertEqual(len(harness.artefacts(self.out)), 1)
        refusal = harness.artefact_with_signature(self.out, "refusal record")
        self.assertIsNotNone(refusal)
        self.assertIn("declaration", refusal[1])
        self.assertIn("quarantined", refusal[1])
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "discrepancy report")
        )

    def test_refusal_on_a_declared_version_takes_no_dry_standing(self):
        status = self.run_case(
            scenario={
                "gating": {
                    "declaration_state": "defective",
                    "calibration_state": "not_calibrated",
                }
            }
        )
        self.assertIsNone(status)
        self.assertNotIn("DRY RUN", harness.combined_text(self.out))

    def test_no_bound_values_is_not_a_verdict_run_and_takes_no_status(self):
        status = self.run_case(bound_values=None, bound_ruling_ref=None)
        self.assertIsNone(status)
        self.assertIn(
            "no bound values in force", harness.combined_text(self.out)
        )

    def test_no_bound_values_produces_one_run_record_and_no_verdict_report(self):
        self.run_case(bound_values=None, bound_ruling_ref=None)
        self.assertEqual(len(harness.artefacts(self.out)), 1)
        record = harness.artefact_with_signature(
            self.out, "no bound values in force"
        )
        self.assertIsNotNone(record)
        self.assertIn("run record", record[1])
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "discrepancy report")
        )

    def test_uncalibrated_version_takes_forced_dry_standing_at_status_4(self):
        status = self.run_case(
            scenario={"gating": {"calibration_state": "not_calibrated"}}
        )
        self.assertEqual(status, 4)
        text = harness.combined_text(self.out)
        self.assertIn("DRY RUN", text)
        self.assertIn("not calibrated", text)

    def test_dry_standing_limb_produces_its_output_with_its_run_statement(self):
        status = self.run_case(
            scenario={"gating": {"calibration_state": "not_calibrated"}}
        )
        self.assertEqual(status, 4)
        self.assertEqual(len(harness.artefacts(self.out)), 1)
        self.assertIsNotNone(
            harness.artefact_with_signature(self.out, "DRY RUN")
        )
        self.assertIsNotNone(
            harness.artefact_with_signature(self.out, "run statement")
        )
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "discrepancy report")
        )

    def test_no_covering_calibration_record_derives_not_calibrated(self):
        status = self.run_case(
            scenario={"gating": {"calibration_state": "no_record"}}
        )
        self.assertEqual(status, 4)
        self.assertIn("not calibrated", harness.combined_text(self.out))

    def test_latest_covering_record_a_failure_derives_not_calibrated(self):
        status = self.run_case(
            scenario={"gating": {"calibration_state": "latest_failed"}}
        )
        self.assertEqual(status, 4)

    def test_suite_digest_mismatch_derives_not_calibrated(self):
        status = self.run_case(
            scenario={"gating": {"suite_digest_matches": False}}
        )
        self.assertEqual(status, 4)
        self.assertIn("not calibrated", harness.combined_text(self.out))

    def test_not_current_version_is_refused_with_no_status(self):
        status = self.run_case(
            scenario={"gating": {"version_current": False}}
        )
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("refusal", text)
        self.assertIn("version standing", text)
        self.assertIn("checker-1.0.0", text)
        self.assertEqual(len(harness.artefacts(self.out)), 1)
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "discrepancy report")
        )

    def test_declaration_refusal_beats_the_no_bound_values_state(self):
        status = self.run_case(
            bound_values=None,
            bound_ruling_ref=None,
            scenario={"gating": {"declaration_state": "quarantined"}},
        )
        self.assertIsNone(status)
        self.assertEqual(len(harness.artefacts(self.out)), 1)
        self.assertIsNotNone(
            harness.artefact_with_signature(self.out, "refusal record")
        )

    def test_no_bound_values_beats_dry_standing(self):
        status = self.run_case(
            bound_values=None,
            bound_ruling_ref=None,
            scenario={"gating": {"calibration_state": "not_calibrated"}},
        )
        self.assertIsNone(status)
        self.assertIn(
            "no bound values in force", harness.combined_text(self.out)
        )
        self.assertNotIn("DRY RUN", harness.combined_text(self.out))

    def test_no_bound_values_beats_the_not_current_case(self):
        status = self.run_case(
            bound_values=None,
            bound_ruling_ref=None,
            scenario={"gating": {"version_current": False}},
        )
        self.assertIsNone(status)
        self.assertEqual(len(harness.artefacts(self.out)), 1)
        record = harness.artefact_with_signature(
            self.out, "no bound values in force"
        )
        self.assertIsNotNone(record)
        self.assertIn("run record", record[1])
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "refusal record")
        )

    def test_dry_standing_beats_the_not_current_case(self):
        status = self.run_case(
            scenario={
                "gating": {
                    "calibration_state": "not_calibrated",
                    "version_current": False,
                }
            }
        )
        self.assertEqual(status, 4)
        self.assertIn("DRY RUN", harness.combined_text(self.out))

    def test_declaration_refusal_beats_the_not_current_case(self):
        status = self.run_case(
            scenario={
                "gating": {
                    "declaration_state": "defective",
                    "version_current": False,
                }
            }
        )
        self.assertIsNone(status)
        self.assertIn("refusal", harness.combined_text(self.out))

    def test_output_area_inside_the_frozen_set_is_refused(self):
        status = self.run_case(
            scenario={"output_relation": "inside_frozen_set"}
        )
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("refusal", text)
        self.assertIn("frozen set", text)
        self.assertIn("run record", text)
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "discrepancy report")
        )

    def test_output_area_inside_the_packet_sources_is_refused(self):
        status = self.run_case(
            scenario={"output_relation": "inside_packet_sources"}
        )
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("refusal", text)
        self.assertIn("packet sources", text)
        self.assertIn("run record", text)
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "discrepancy report")
        )

    def test_output_area_inside_the_anchor_record_is_refused(self):
        status = self.run_case(
            scenario={"output_relation": "inside_anchor_record"}
        )
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("refusal", text)
        self.assertIn("anchor record", text)
        self.assertIn("run record", text)
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "discrepancy report")
        )

    def test_output_area_naming_an_existing_report_is_refused(self):
        status = self.run_case(
            scenario={"output_relation": "names_existing_report"}
        )
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("refusal", text)
        self.assertIn("existing report", text)
        self.assertIn("run record", text)
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "discrepancy report")
        )

    def test_dry_run_into_the_gate_evidence_home_is_refused(self):
        status = self.run_case(
            mode="dry",
            scenario={"output_relation": "gate_evidence_home"},
        )
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("refusal", text)
        self.assertIn("gate evidence home", text)
        self.assertIn("run record", text)
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "discrepancy report")
        )

    def test_output_area_refusal_runs_no_check(self):
        self.run_case(scenario={"output_relation": "inside_frozen_set"})
        text = harness.combined_text(self.out)
        self.assertNotIn("authenticity", text)

    def test_operator_set_dry_run_on_a_calibrated_version_carries_calibrated(self):
        status = self.run_case(mode="dry")
        self.assertEqual(status, 4)
        text = harness.combined_text(self.out)
        self.assertIn("DRY RUN", text)
        self.assertIn("calibrated", text.replace("not calibrated", ""))

    def test_dry_run_output_carries_no_grade_and_no_verdict(self):
        status = self.run_case(mode="dry")
        self.assertEqual(status, 4)
        text = harness.combined_text(self.out)
        self.assertIn("DRY RUN", text)
        self.assertIn("gate evidence", text)
        self.assertIn("NOT A VERDICT", text)
        self.assertNotIn("grade:", text.lower())
        self.assertNotIn("verdict: pass", text.lower())
        self.assertNotIn("verdict: fail", text.lower())


class ReadInterfaceTests(unittest.TestCase):
    """The three read interface forms, presented records not derived results."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def run_interface(self, kind, presented):
        invocation = harness.verdict_invocation(
            self.out,
            scenario={"read_interface": {"kind": kind, "presented": presented}},
        )
        return harness.run_invocation(invocation, self.out)

    def cal_record(self, matched=58, mismatched=0, **field_overrides):
        record = {
            "checker version": "checker-1.0.0",
            "fixture suite version": "fixture-suite-1",
            "suite digest": harness._digest("suite:base"),
            "packet form version": "packet-form-1",
            "layout form version": "layout-form-1",
            "per fixture results": {
                "matched": matched,
                "mismatched": mismatched,
            },
            "limit form tests": "pass",
        }
        record.update(field_overrides)
        return record

    def test_if_cal_derives_the_state_and_the_record_digest(self):
        older = self.cal_record(matched=57, mismatched=1)
        latest = self.cal_record()
        status = self.run_interface(
            "IF-CAL", {"records": [older, latest]}
        )
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("calibrated", text)
        self.assertNotIn("not calibrated", text)
        self.assertIn(record_digest(latest), text)

    def test_if_cal_derives_not_calibrated_from_a_failed_record(self):
        older = self.cal_record()
        latest = self.cal_record(matched=57, mismatched=1)
        status = self.run_interface(
            "IF-CAL", {"records": [older, latest]}
        )
        self.assertEqual(status, 4)
        text = harness.combined_text(self.out)
        self.assertIn("not calibrated", text)
        self.assertIn(record_digest(latest), text)

    def test_if_cal_derives_not_calibrated_from_a_non_covering_record(self):
        record = self.cal_record(
            **{"layout form version": "layout-form-99"}
        )
        status = self.run_interface("IF-CAL", {"records": [record]})
        self.assertEqual(status, 4)
        text = harness.combined_text(self.out)
        self.assertIn("not calibrated", text)
        self.assertIn("layout-form-99", text)
        self.assertIn(record_digest(record), text)

    def test_if_cal_derives_not_calibrated_from_a_mismatching_suite_digest(self):
        record = self.cal_record(
            **{"suite digest": harness._digest("suite:other")}
        )
        presented = {
            "records": [record],
            "suite_digest": harness._digest("suite:base"),
        }
        status = self.run_interface("IF-CAL", presented)
        self.assertEqual(status, 4)
        text = harness.combined_text(self.out)
        self.assertIn("not calibrated", text)
        self.assertIn(harness._digest("suite:other"), text)
        self.assertIn(record_digest(record), text)

    def test_if_ver_returns_current_determination_declaration_state_and_entry(self):
        entry = {
            "version": "checker-1.0.0",
            "became current": "2026-11-01",
            "declaration state": "none",
            "packet form versions": ["packet-form-1"],
        }
        status = self.run_interface("IF-VER", entry)
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("current", text)
        self.assertIn("none", text)
        self.assertIn("checker-1.0.0", text)

    def test_if_ver_returns_not_current_for_a_superseded_entry(self):
        entry = {
            "version": "checker-0.9.0",
            "became current": "2026-10-01",
            "superseded by": "checker-1.0.0",
            "declaration state": "quarantined",
        }
        self.run_interface("IF-VER", entry)
        text = harness.combined_text(self.out)
        self.assertIn("not current", text)
        self.assertIn("quarantined", text)
        self.assertIn("checker-0.9.0", text)

    def test_if_ver_reads_the_entry_in_its_corrected_standing(self):
        entry = {
            "version": "checker-1.0.0",
            "became current": "2026-11-01",
            "declaration state": "none",
            "packet form versions": ["packet-form-1"],
        }
        presented = {
            "entry": entry,
            "correction": {
                "field": "declaration state",
                "value": "quarantined",
            },
        }
        status = self.run_interface("IF-VER", presented)
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("quarantined", text)
        self.assertIn("checker-1.0.0", text)
        self.assertIn("correction", text)

    def test_if_lay_reads_the_layout_named_by_digest_and_version(self):
        presented = {
            "layout_digest": harness._digest("layout:base"),
            "layout_version": "layout-form-1",
        }
        status = self.run_interface("IF-LAY", presented)
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn(harness._digest("layout:base"), text)
        self.assertIn("layout-form-1", text)
        self.assertIn("layout", text)


class FilingTests(unittest.TestCase):
    """The filing step of brief section 5.10, slice S-08 in its filing limb."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def run_case(self, **overrides):
        invocation = harness.verdict_invocation(self.out, **overrides)
        return harness.run_invocation(invocation, self.out)

    def test_filing_checks_each_digest_and_the_gate_record_cites_by_digest(self):
        status = self.run_case(scenario={"filing": {"digest_matches": True}})
        self.assertEqual(status, 0)
        gate = harness.signature_text(self.out, "gate record")
        statement = harness.signature_text(self.out, "run statement")
        self.assertIn("filed", gate)
        report_digest = None
        for line in statement.splitlines():
            if line.strip().lower().startswith("report digest"):
                report_digest = line.split(":", 1)[1].strip()
        self.assertIsNotNone(report_digest)
        self.assertEqual(len(report_digest), 64)
        self.assertIn(report_digest, gate)

    def test_filing_digest_mismatch_stops_the_filing_and_records_a_custody_gap(self):
        status = self.run_case(scenario={"filing": {"digest_matches": False}})
        self.assertEqual(status, 0)
        gate = harness.signature_text(self.out, "gate record")
        self.assertIn("custody gap", gate)
        self.assertIn("filing", gate)
        self.assertIn("not filed", gate)


class VersionHistoryTests(unittest.TestCase):
    """Slice S-14: version history record duties and gate reliance duties."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def run_case(self, **overrides):
        invocation = harness.verdict_invocation(self.out, **overrides)
        return harness.run_invocation(invocation, self.out)

    def test_version_entries_and_amendment_entries_are_kept_distinct(self):
        status = self.run_case(
            scenario={
                "version_history": {
                    "version_entries": ["checker-1.0.0", "checker-1.0.1"],
                    "amendment_entries": ["amendment-1"],
                }
            }
        )
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("version entries: 2", text)
        self.assertIn("amendment entries: 1", text)

    def test_correction_stands_as_a_new_entry_citing_the_entry_corrected(self):
        status = self.run_case(
            scenario={
                "version_history": {
                    "correction": {
                        "corrects": harness._digest("entry:original"),
                        "field": "declaration state",
                        "value": "quarantined",
                    }
                }
            }
        )
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn(harness._digest("entry:original"), text)
        self.assertIn("new entry", text)
        self.assertIn("quarantined", text)

    def test_gate_reads_the_original_entry_as_corrected_by_its_latest_correction(self):
        status = self.run_case(
            scenario={
                "gate_citation": {
                    "version": "checker-1.0.0",
                    "entry_state": "none",
                    "latest_correction_state": "quarantined",
                }
            }
        )
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("refusal", text)
        self.assertIn("quarantined", text)

    def test_a_version_with_no_entry_is_relied_on_by_no_gate(self):
        status = self.run_case(
            scenario={
                "gate_citation": {
                    "version": "checker-9.9.9",
                    "entry_state": "no entry",
                }
            }
        )
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("refusal", text)
        self.assertIn("no entry", text)

    def test_twice_calibrated_version_gate_citation_uses_the_latest_event(self):
        status = self.run_case(
            scenario={
                "gate_citation": {
                    "version": "checker-1.0.0",
                    "calibration_events": ["not calibrated", "calibrated"],
                }
            }
        )
        self.assertEqual(status, 0)
        self.assertIn("calibrated", harness.combined_text(self.out))

    def test_gate_reliance_refused_on_a_calibration_field_mismatch(self):
        status = self.run_case(
            scenario={
                "gate_citation": {
                    "version": "checker-1.0.0",
                    "calibration_field_mismatch": "suite digest",
                }
            }
        )
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("reliance refused", text)
        self.assertIn("suite digest", text)

    def test_gate_reliance_refused_where_a_cited_calibration_record_cannot_be_produced(self):
        status = self.run_case(
            scenario={
                "gate_citation": {
                    "version": "checker-1.0.0",
                    "calibration_record_producible": False,
                }
            }
        )
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("reliance refused", text)
        self.assertIn("cannot be produced", text)

    def test_gate_reliance_refused_where_the_statement_digest_misses_its_anchor(self):
        status = self.run_case(
            scenario={
                "gate_citation": {
                    "version": "checker-1.0.0",
                    "statement_digest_matches_anchor": False,
                }
            }
        )
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("reliance refused", text)
        self.assertIn("anchor", text)

    def test_declaration_record_carries_the_four_part_defect_scope_statement(self):
        parts = [
            "the authenticity check",
            "packets at step gates 1 to 3",
            "versions checker-1.0.0 only",
            "verdicts issued before the declaration",
        ]
        status = self.run_case(
            scenario={
                "version_history": {
                    "declaration": {
                        "state": "defective",
                        "defect_scope_parts": parts,
                    }
                }
            }
        )
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("defect scope", text)
        for part in parts:
            self.assertIn(part, text)

    def test_identification_enumerates_affected_verdicts_and_names_an_incomplete_residue(self):
        status = self.run_case(
            scenario={
                "version_history": {
                    "identification": {
                        "affected": ["verdict-1", "verdict-2"],
                        "unidentifiable": ["verdict-3"],
                    }
                }
            }
        )
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("verdict-1", text)
        self.assertIn("verdict-2", text)
        self.assertIn("partial", text)
        self.assertIn("verdict-3", text)
        self.assertTrue(
            any(
                "verdict-3" in line and "residue" in line
                for line in text.splitlines()
            )
        )

    def test_sorting_sorts_each_verdict_and_decides_nothing_about_closure(self):
        status = self.run_case(
            scenario={
                "version_history": {
                    "sorting": {
                        "in_scope": ["verdict-1"],
                        "shown_out_of_scope": ["verdict-2"],
                        "indeterminate": ["verdict-3"],
                    }
                }
            }
        )
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("in scope", text)
        self.assertIn("out of scope", text)
        self.assertIn("indeterminate", text)
        self.assertIn("decides nothing about any closure", text)
        lines = text.splitlines()
        self.assertTrue(
            any(
                "verdict-1" in line
                and "in scope" in line
                and "out of scope" not in line
                for line in lines
            )
        )
        self.assertTrue(
            any(
                "verdict-2" in line and "out of scope" in line
                for line in lines
            )
        )
        self.assertTrue(
            any(
                "verdict-3" in line and "indeterminate" in line
                for line in lines
            )
        )


if __name__ == "__main__":
    unittest.main()
