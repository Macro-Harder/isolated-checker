"""Seal phase and the three checks, slices S-02, S-03, S-04 and S-05.

Pins brief sections 5.4, 5.5 and 5.6: the pre run seal check as one
opening phase over every operation that reads a frozen set and issues
a report or a verdict, its custody gap outcome form at exit status 1
where the receipt comparison supports the determination and at exit
status 2 where it supports none, and the three checks in the order
authenticity, chain, completeness, with the invocation to record
comparisons made before any check verdict is formed.

Derivation and composition. The MaterialSealTests and
MaterialCheckTests classes present material, members, receipts, link
records, roster state and layout requirements, and pin derivation
over that material. The remaining classes present derived states and
per check outcomes through the seal, checks, comparisons, one_sided
and denominator keys; those cases are composition only, pinning how
presented outcomes compose into statuses and report forms, and are
not counted as derivation pins.

Scenario keys used here: seal, with values intact, altered_member,
removed_member, extra_member, anchor_missing, anchor_conflict,
anchor_other_intake, receipt_unrecomputable,
receipt_rewritten_off_anchor, receipt_build_mismatch,
first_receipt_claims_predecessor, chain_ends_early,
whole_intake_removed and
no_intake_order_record; determination_support, with values supported
or none, stating which side of the receipt comparison support line a
custody or invocation comparison case stands on; checks, a mapping
from check name to pass, fail, cannot_run_supported or
cannot_run_unsupported; comparisons, a mapping naming a mismatched
invocation comparison; one_sided, the classification presentation for
one sided chain material, with standing_unexplained_count stating the
count carried in from the previous report where a sequence is
presented; denominator, with value outside_bundle_unsupported or
outside_bundle_supported; collision_pair, a true value presenting two
members sharing a digest and a byte size; discovery, a mapping
presenting a slice S-02 discovery or uncovered member case in
presented state form, as a labelled form value and its named parts,
with no member bytes, packet structure or link record presented;
self_citing, a mapping presenting a self citing source offered as
corroboration; truncation, a mapping presenting truncated material
whose digests stay true against its claimed outline, with disposition
in content_trace or recorded_gap; unchecked_element, a mapping naming
an element, the check it bears on, and its support state;
presented_members, presented_receipt, presented_links,
presented_roster and presented_layout_requirements, the material keys
the harness material_scenario helper and the material check tests
state; declaration_recorded, a boolean standing for the defective
standing of the earlier version recorded by declaration in the gate
record, presented in the corrected run seal case.
"""

import pathlib
import tempfile
import unittest

import harness

BASE_MEMBERS = {
    "links.txt": "Link 1 names notes.txt for Seat Alpha.\n",
    "notes.txt": "The notes artefact body.\n",
    "step-record.txt": "Step record sections 1 to 3.\n",
}


class SealAndChecksTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def run_case(self, **overrides):
        invocation = harness.verdict_invocation(self.out, **overrides)
        return harness.run_invocation(invocation, self.out)

    def test_intact_seal_lets_the_run_reach_the_checks(self):
        status = self.run_case(scenario={"seal": "intact"})
        self.assertEqual(status, 0)
        self.assertTrue(harness.artefacts(self.out))

    def test_altered_member_takes_custody_gap_at_status_1(self):
        status = self.run_case(scenario={"seal": "altered_member"})
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("custody gap", text)
        self.assertIn("chain", text)

    def test_removed_member_takes_custody_gap_at_status_1(self):
        status = self.run_case(scenario={"seal": "removed_member"})
        self.assertEqual(status, 1)
        self.assertIn("custody gap", harness.combined_text(self.out))

    def test_extra_member_takes_custody_gap_at_status_1(self):
        status = self.run_case(scenario={"seal": "extra_member"})
        self.assertEqual(status, 1)
        self.assertIn("custody gap", harness.combined_text(self.out))

    def test_no_verdict_issues_over_a_broken_seal(self):
        status = self.run_case(scenario={"seal": "altered_member"})
        self.assertNotEqual(status, 0)
        self.assertNotIn("verdict: pass", harness.combined_text(self.out))

    def test_anchor_missing_supports_no_determination_and_takes_status_2(self):
        status = self.run_case(
            scenario={
                "seal": "anchor_missing",
                "determination_support": "none",
            }
        )
        self.assertEqual(status, 2)
        text = harness.combined_text(self.out)
        self.assertIn("custody gap", text)
        self.assertIn(harness._digest("receipt:base"), text)
        self.assertIn("anchor", text)

    def test_anchor_conflicting_with_receipt_digest_takes_status_1(self):
        status = self.run_case(
            scenario={
                "seal": "anchor_conflict",
                "determination_support": "supported",
            }
        )
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("custody gap", text)
        self.assertIn("anchor", text)

    def test_anchor_of_another_intake_takes_status_1(self):
        status = self.run_case(
            scenario={
                "seal": "anchor_other_intake",
                "determination_support": "supported",
            }
        )
        self.assertEqual(status, 1)
        self.assertIn("custody gap", harness.combined_text(self.out))

    def test_unrecomputable_receipt_takes_custody_gap_at_status_2(self):
        status = self.run_case(scenario={"seal": "receipt_unrecomputable"})
        self.assertEqual(status, 2)
        self.assertIn("custody gap", harness.combined_text(self.out))

    def test_receipt_rewritten_recomputing_but_off_anchor_takes_status_1(self):
        status = self.run_case(
            scenario={
                "seal": "receipt_rewritten_off_anchor",
                "determination_support": "supported",
            }
        )
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("custody gap", text)
        self.assertIn("anchor", text)
        self.assertIn(harness._digest("receipt:base"), text)

    def test_receipt_build_mismatch_with_invocation_takes_status_1(self):
        status = self.run_case(
            scenario={
                "seal": "receipt_build_mismatch",
                "determination_support": "supported",
            }
        )
        self.assertEqual(status, 1)
        self.assertIn("custody gap", harness.combined_text(self.out))

    def test_first_receipt_claiming_a_predecessor_takes_status_1(self):
        status = self.run_case(
            scenario={
                "seal": "first_receipt_claims_predecessor",
                "determination_support": "supported",
            }
        )
        self.assertEqual(status, 1)
        self.assertIn("custody gap", harness.combined_text(self.out))

    def test_chain_ending_early_against_the_intake_order_takes_custody_gap(self):
        status = self.run_case(scenario={"seal": "chain_ends_early"})
        self.assertEqual(status, 1)
        self.assertIn("custody gap", harness.combined_text(self.out))

    def test_no_intake_order_record_leaves_sequence_cases_unchecked_by_name(self):
        status = self.run_case(scenario={"seal": "no_intake_order_record"})
        self.assertEqual(status, 0)
        self.assertIn("unchecked", harness.combined_text(self.out))

    def test_broken_seal_in_a_rerun_takes_the_same_custody_form(self):
        status = self.run_case(
            mode="rerun",
            original_run_statement_digest=harness._digest("stmt:original"),
            scenario={"seal": "altered_member"},
        )
        self.assertEqual(status, 1)
        self.assertIn("custody gap", harness.combined_text(self.out))

    def test_broken_seal_in_an_appeal_run_takes_the_same_custody_form(self):
        status = self.run_case(
            mode="appeal",
            original_report_digest=harness._digest("report:original"),
            scenario={"seal": "removed_member"},
        )
        self.assertEqual(status, 1)
        self.assertIn("custody gap", harness.combined_text(self.out))

    def test_broken_seal_in_a_cure_run_takes_the_same_custody_form(self):
        status = self.run_case(
            mode="cure",
            original_report_digest=harness._digest("report:original"),
            discrepancy_numbers=[1],
            scenario={"seal": "extra_member"},
        )
        self.assertEqual(status, 1)
        self.assertIn("custody gap", harness.combined_text(self.out))

    def test_broken_seal_in_a_corrected_run_takes_the_same_custody_form(self):
        status = self.run_case(
            checker_version="checker-1.0.1",
            defective_run_statement_digest=harness._digest("stmt:defective"),
            scenario={
                "seal": "altered_member",
                "declaration_recorded": True,
            },
        )
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("custody gap", text)
        self.assertIn("chain", text)

    def test_broken_seal_under_dry_standing_takes_dry_status_4(self):
        status = self.run_case(
            mode="dry", scenario={"seal": "altered_member"}
        )
        self.assertEqual(status, 4)
        text = harness.combined_text(self.out)
        self.assertIn("DRY RUN", text)
        self.assertIn("custody gap", text)

    def test_seal_report_names_the_receipt_digest_and_the_failed_comparison(self):
        status = self.run_case(scenario={"seal": "altered_member"})
        self.assertEqual(status, 1)
        report = harness.signature_text(self.out, "custody gap")
        self.assertIn(harness._digest("receipt:base"), report)
        self.assertIn("member digest comparison", report)

    def test_report_carries_the_three_verdicts_in_r80_order(self):
        status = self.run_case()
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        positions = [
            text.index("authenticity"),
            text.index("chain"),
            text.index("completeness"),
        ]
        self.assertEqual(positions, sorted(positions))

    def test_authenticity_failure_takes_status_1(self):
        status = self.run_case(
            scenario={"checks": {"authenticity": "fail"}}
        )
        self.assertEqual(status, 1)
        self.assertIn("PARTIAL", harness.combined_text(self.out))

    def test_chain_failure_takes_status_1(self):
        status = self.run_case(scenario={"checks": {"chain": "fail"}})
        self.assertEqual(status, 1)

    def test_completeness_failure_takes_status_1(self):
        status = self.run_case(
            scenario={"checks": {"completeness": "fail"}}
        )
        self.assertEqual(status, 1)

    def test_two_failing_checks_are_both_carried_at_status_1(self):
        status = self.run_case(
            scenario={
                "checks": {"authenticity": "fail", "completeness": "fail"}
            }
        )
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("authenticity", text)
        self.assertIn("completeness", text)

    def test_check_cannot_run_with_support_takes_status_1(self):
        status = self.run_case(
            scenario={"checks": {"chain": "cannot_run_supported"}}
        )
        self.assertEqual(status, 1)
        self.assertIn("PARTIAL", harness.combined_text(self.out))

    def test_check_cannot_run_without_support_takes_status_2(self):
        status = self.run_case(
            scenario={"checks": {"chain": "cannot_run_unsupported"}}
        )
        self.assertEqual(status, 2)
        self.assertIn("UNVERIFIABLE", harness.combined_text(self.out))

    def test_authenticity_cannot_run_with_support_takes_status_1(self):
        status = self.run_case(
            scenario={"checks": {"authenticity": "cannot_run_supported"}}
        )
        self.assertEqual(status, 1)
        self.assertIn("PARTIAL", harness.combined_text(self.out))

    def test_authenticity_cannot_run_without_support_takes_status_2(self):
        status = self.run_case(
            scenario={"checks": {"authenticity": "cannot_run_unsupported"}}
        )
        self.assertEqual(status, 2)
        self.assertIn("UNVERIFIABLE", harness.combined_text(self.out))

    def test_completeness_cannot_run_with_support_takes_status_1(self):
        status = self.run_case(
            scenario={"checks": {"completeness": "cannot_run_supported"}}
        )
        self.assertEqual(status, 1)
        self.assertIn("PARTIAL", harness.combined_text(self.out))

    def test_completeness_cannot_run_without_support_takes_status_2(self):
        status = self.run_case(
            scenario={"checks": {"completeness": "cannot_run_unsupported"}}
        )
        self.assertEqual(status, 2)
        self.assertIn("UNVERIFIABLE", harness.combined_text(self.out))

    def test_load_bearing_unchecked_element_with_support_takes_status_1(self):
        status = self.run_case(
            scenario={
                "unchecked_element": {
                    "element": "roster state for the step time",
                    "bears_on": "authenticity",
                    "support": "supported",
                }
            }
        )
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("roster state for the step time", text)
        self.assertIn("authenticity", text)
        self.assertIn("unchecked", text)

    def test_load_bearing_unchecked_element_without_support_takes_status_2(self):
        status = self.run_case(
            scenario={
                "unchecked_element": {
                    "element": "roster state for the step time",
                    "bears_on": "authenticity",
                    "support": "none",
                }
            }
        )
        self.assertEqual(status, 2)
        text = harness.combined_text(self.out)
        self.assertIn("roster state for the step time", text)
        self.assertIn("authenticity", text)
        self.assertIn("UNVERIFIABLE", text)

    def test_load_bearing_unchecked_element_for_chain_without_support_takes_status_2(self):
        status = self.run_case(
            scenario={
                "unchecked_element": {
                    "element": "intake order record",
                    "bears_on": "chain",
                    "support": "none",
                }
            }
        )
        self.assertEqual(status, 2)
        text = harness.combined_text(self.out)
        self.assertIn("intake order record", text)
        self.assertIn("chain", text)

    def test_layout_digest_mismatch_with_support_takes_status_1(self):
        status = self.run_case(
            scenario={
                "comparisons": {"layout_digest": "mismatch"},
                "determination_support": "supported",
            }
        )
        self.assertEqual(status, 1)
        self.assertNotEqual(status, 0)
        self.assertIn("FAIL", harness.combined_text(self.out))

    def test_packet_form_version_mismatch_with_support_takes_status_1(self):
        status = self.run_case(
            scenario={
                "comparisons": {"packet_form_version": "mismatch"},
                "determination_support": "supported",
            }
        )
        self.assertEqual(status, 1)
        self.assertNotEqual(status, 0)

    def test_checker_version_mismatch_with_support_takes_status_1(self):
        status = self.run_case(
            scenario={
                "comparisons": {"checker_version": "mismatch"},
                "determination_support": "supported",
            }
        )
        self.assertEqual(status, 1)
        self.assertNotEqual(status, 0)

    def test_denominator_outside_bundle_with_support_takes_status_1(self):
        status = self.run_case(
            scenario={"denominator": "outside_bundle_supported"}
        )
        self.assertEqual(status, 1)

    def test_denominator_outside_bundle_without_support_takes_status_2(self):
        status = self.run_case(
            scenario={"denominator": "outside_bundle_unsupported"}
        )
        self.assertEqual(status, 2)
        self.assertIn("UNVERIFIABLE", harness.combined_text(self.out))

    def test_one_sided_both_showings_classify_structural_with_counts_carried(self):
        status = self.run_case(
            scenario={"one_sided": "structural_with_pending_record"}
        )
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("structural", text)
        self.assertIn("unchecked", text)
        self.assertIn("pending record", text)
        self.assertIn("overlap count: 1", text)

    def test_one_sided_structural_only_carries_a_zero_overlap_count(self):
        status = self.run_case(scenario={"one_sided": "structural_only"})
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("structural", text)
        self.assertIn("overlap count: 0", text)

    def test_one_sided_material_with_pending_record_only_is_timing(self):
        status = self.run_case(scenario={"one_sided": "timing"})
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("timing", text)
        self.assertIn("overlap count: 0", text)

    def test_one_sided_material_with_neither_showing_is_unexplained(self):
        status = self.run_case(scenario={"one_sided": "unexplained"})
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("unexplained", text)
        self.assertIn("unchecked", text)
        self.assertIn("unexplained count: 1", text)

    def test_unexplained_count_is_carried_from_report_to_report(self):
        first = self.run_case(scenario={"one_sided": "unexplained"})
        self.assertEqual(first, 0)
        out2 = pathlib.Path(self.tmp.name) / "out2"
        invocation = harness.verdict_invocation(
            out2,
            scenario={
                "one_sided": "unexplained",
                "standing_unexplained_count": 1,
            },
        )
        second = harness.run_invocation(invocation, out2)
        self.assertEqual(second, 0)
        self.assertIn("unexplained count: 2", harness.combined_text(out2))

    def test_collision_pair_is_named_a_collision_condition_discrepancy(self):
        status = self.run_case(scenario={"collision_pair": True})
        self.assertEqual(status, 1)
        self.assertIn(
            "collision", harness.combined_text(self.out)
        )


class MaterialSealTests(unittest.TestCase):
    """Seal derivation over presented members and receipt entries."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def run_material(self, members, receipt_members=None, **extra):
        scenario = harness.material_scenario(members, receipt_members, **extra)
        invocation = harness.verdict_invocation(self.out, scenario=scenario)
        return harness.run_invocation(invocation, self.out)

    def test_intact_material_set_reaches_the_checks_and_passes(self):
        status = self.run_material(dict(BASE_MEMBERS))
        self.assertEqual(status, 0)

    def test_altered_member_material_takes_custody_gap_at_status_1(self):
        altered = dict(BASE_MEMBERS)
        altered["notes.txt"] = "The notes artefact body, altered.\n"
        status = self.run_material(altered, dict(BASE_MEMBERS))
        self.assertEqual(status, 1)
        report = harness.signature_text(self.out, "custody gap")
        self.assertIn("notes.txt", report)
        self.assertIn("member digest comparison", report)
        self.assertIn(harness._digest("receipt:base"), report)

    def test_removed_member_material_takes_custody_gap_at_status_1(self):
        reduced = {
            name: text
            for name, text in BASE_MEMBERS.items()
            if name != "notes.txt"
        }
        status = self.run_material(reduced, dict(BASE_MEMBERS))
        self.assertEqual(status, 1)
        self.assertIn("notes.txt", harness.signature_text(self.out, "custody gap"))

    def test_extra_member_material_takes_custody_gap_at_status_1(self):
        grown = dict(BASE_MEMBERS)
        grown["extra.txt"] = "A member the receipt does not name.\n"
        status = self.run_material(grown, dict(BASE_MEMBERS))
        self.assertEqual(status, 1)
        self.assertIn("extra.txt", harness.signature_text(self.out, "custody gap"))


class MaterialCheckTests(unittest.TestCase):
    """Check derivation over presented link, roster and layout material."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def run_material(self, scenario):
        invocation = harness.verdict_invocation(self.out, scenario=scenario)
        return harness.run_invocation(invocation, self.out)

    def test_link_digest_mismatch_in_material_fails_authenticity(self):
        filed_notes = BASE_MEMBERS["notes.txt"]
        altered = dict(BASE_MEMBERS)
        altered["notes.txt"] = "The notes artefact body, altered.\n"
        scenario = harness.material_scenario(
            altered,
            presented_links=[
                {
                    "link": "Link 1",
                    "artefact": "notes.txt",
                    "recorded_digest": harness._blob_digest(
                        filed_notes.encode("utf-8")
                    ),
                }
            ],
        )
        status = self.run_material(scenario)
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("authenticity", text)
        self.assertIn("notes.txt", text)

    def test_spawn_bound_to_an_unauthorised_seat_in_material_fails_authenticity(self):
        scenario = harness.material_scenario(
            dict(BASE_MEMBERS),
            presented_links=[
                {
                    "link": "Link 1",
                    "artefact": "notes.txt",
                    "spawn": "spawn-alpha-001",
                    "seat": "Seat Gamma",
                }
            ],
            presented_roster={"Seat Alpha": ["spawn-alpha-001"]},
        )
        status = self.run_material(scenario)
        self.assertEqual(status, 1)
        self.assertIn("Seat Gamma", harness.combined_text(self.out))

    def test_missing_required_artefact_in_material_fails_completeness(self):
        reduced = {
            name: text
            for name, text in BASE_MEMBERS.items()
            if name != "step-record.txt"
        }
        scenario = harness.material_scenario(
            reduced,
            reduced,
            presented_layout_requirements=[
                "links.txt",
                "notes.txt",
                "step-record.txt",
            ],
        )
        status = self.run_material(scenario)
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("completeness", text)
        self.assertIn("step-record.txt", text)
        self.assertNotIn("custody gap", text)


class DiscoveryTests(unittest.TestCase):
    """Slice S-02 discovery and uncovered member cases, in presented state form."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def run_case(self, **overrides):
        invocation = harness.verdict_invocation(self.out, **overrides)
        return harness.run_invocation(invocation, self.out)

    def test_renamed_artefact_is_discovered_by_content_signature(self):
        status = self.run_case(
            scenario={
                "discovery": {
                    "form": "renamed_artefact",
                    "presented_name": "unexpected-name.txt",
                    "artefact_kind": "step record",
                    "content_signature": "step record signature",
                }
            }
        )
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("step record", text)
        self.assertIn("content signature", text)

    def test_artefact_discovery_cannot_locates_takes_the_missing_artefact_outcome(self):
        status = self.run_case(
            scenario={
                "discovery": {
                    "form": "unlocatable_artefact",
                    "artefact_kind": "step record",
                    "routes_tried": [
                        "content signature",
                        "ledger citation",
                        "step record citation",
                    ],
                }
            }
        )
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("missing artefact", text)
        self.assertIn("step record", text)
        self.assertIn("ledger citation", text)

    def test_unidentifiable_artefact_with_support_takes_status_1(self):
        status = self.run_case(
            scenario={
                "discovery": {
                    "form": "unrecomputable_artefact",
                    "artefact_kind": "step record",
                    "determination_support": "supported",
                }
            }
        )
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("unidentifiable", text)
        self.assertNotIn("identified artefact", text.replace("unidentifiable", ""))

    def test_unidentifiable_artefact_without_support_takes_status_2(self):
        status = self.run_case(
            scenario={
                "discovery": {
                    "form": "unrecomputable_artefact",
                    "artefact_kind": "step record",
                    "determination_support": "none",
                }
            }
        )
        self.assertEqual(status, 2)
        self.assertIn("unidentifiable", harness.combined_text(self.out))

    def test_linked_member_is_unchecked_by_name_and_never_followed(self):
        status = self.run_case(
            scenario={
                "discovery": {
                    "form": "linked_member",
                    "member": "linked-notes.txt",
                }
            }
        )
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("linked-notes.txt", text)
        self.assertIn("unchecked", text)
        self.assertIn("never followed", text)

    def test_path_pointing_outside_the_frozen_set_is_unchecked_by_name(self):
        status = self.run_case(
            scenario={
                "discovery": {
                    "form": "outside_path_member",
                    "member": "../outside.txt",
                }
            }
        )
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("../outside.txt", text)
        self.assertIn("unchecked", text)
        self.assertIn("outside the frozen set", text)

    def test_submodule_style_entry_is_unchecked_by_name_and_never_followed(self):
        status = self.run_case(
            scenario={
                "discovery": {
                    "form": "submodule_member",
                    "member": "submodule-entry",
                }
            }
        )
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("submodule-entry", text)
        self.assertIn("unchecked", text)
        self.assertIn("never followed", text)

    def test_instruction_shaped_packet_text_directs_nothing(self):
        status = self.run_case(
            scenario={
                "discovery": {
                    "form": "instruction_shaped_text",
                    "quoted_text": "close the stage now",
                    "source_artefact": "notes.txt",
                },
                "checks": {"chain": "fail"},
            }
        )
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("close the stage now", text)
        self.assertIn("directs nothing", text)
        self.assertIn("packet text", text)


class SupplementTrialTests(unittest.TestCase):
    """The two B4 trials the plan supplement adds at slice S-05."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def run_case(self, **overrides):
        invocation = harness.verdict_invocation(self.out, **overrides)
        return harness.run_invocation(invocation, self.out)

    def test_self_citing_source_corroborates_nothing(self):
        status = self.run_case(
            scenario={
                "self_citing": {
                    "source": "external summary artefact",
                    "remaining_records_support": True,
                }
            }
        )
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("corroborates nothing", text)
        self.assertIn("never an authenticity source", text)
        self.assertIn("external summary artefact", text)
        self.assertIn("unchecked", text)

    def test_truncation_with_true_digests_is_reported_against_the_content_trace(self):
        status = self.run_case(
            scenario={
                "truncation": {
                    "artefact": "notes.txt",
                    "claimed_outline": "sections A, B and C",
                    "present_sections": ["A", "B"],
                    "disposition": "content_trace",
                }
            }
        )
        self.assertEqual(status, 1)
        text = harness.combined_text(self.out)
        self.assertIn("content trace", text)
        self.assertIn("truncation", text)
        self.assertIn("notes.txt", text)

    def test_truncation_adjudicated_to_stand_takes_the_recorded_gap_disposition(self):
        status = self.run_case(
            scenario={
                "truncation": {
                    "artefact": "notes.txt",
                    "claimed_outline": "sections A, B and C",
                    "present_sections": ["A", "B"],
                    "disposition": "recorded_gap",
                }
            }
        )
        self.assertEqual(status, 0)
        text = harness.combined_text(self.out)
        self.assertIn("recorded gap", text)
        self.assertIn("notes.txt", text)


if __name__ == "__main__":
    unittest.main()
