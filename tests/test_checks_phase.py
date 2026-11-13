"""Slice S-05 checks, direct core tests.

These tests exercise the three checks at plan module MD-05 in
process, over in memory inputs in the forms the cured surfaces
issue: members as the reading layer reads them (digests recomputed
from bytes, no presented digest trusted), a custody receipt built
through the MD-02 seam, a layout in the SH-03 form, link records in
the owned field form the reading layer extracts, and a roster in
its state at the step time. They pin the shared machinery of the
three checks first (the discrepancy entry form at SH-14, the one
sided classification at SH-16, the invocation to record
comparisons, and the collision twin naming), then each check in
R-80 order. The suite level check pins in test_seal_and_checks.py
run through the operation surface of later slices and are
accounted in the slice receipt in that form.
"""

import unittest

import isolated_checker as ic
from isolated_checker import canonical, checks, receipts
from isolated_checker.reading import ReadingCounter
from isolated_checker.shapes import ShapeError

MEMBERS = {
    "links.txt": "Link 1 names notes.txt for Seat Alpha.\n",
    "notes.txt": "The notes artefact body.\n",
    "step-record.txt": "Step record sections 1 to 3.\n",
}


def member_list(members=MEMBERS):
    return [
        {"name": name, "content": members[name]} for name in sorted(members)
    ]


def build_receipt(members=MEMBERS):
    entries = []
    for name in sorted(members):
        data = members[name].encode("utf-8")
        entries.append(
            {
                "member_digest": canonical.git_blob_digest(data),
                "member_byte_size": len(data),
                "source_kind": "handed in material",
            }
        )
    receipt = receipts.custody_receipt(
        "isolated-checker-test-build",
        "step-gate-1",
        entries,
        "gate verifier",
        "producer seat",
        "2026-11-13T00:00:00Z",
        1,
        None,
        canonical.record_digest(
            "SH-05",
            receipts.context_record(
                "isolated-checker-test-build",
                "step-gate-1",
                "packet-form-1",
                "SHA-256",
                "CFE-1",
                [],
                [],
            ),
        ),
    )
    return canonical.with_receipt_self_digest(receipt)


def build_layout():
    return checks.layout_record(
        layout_digest=canonical.git_blob_digest(b"layout-bytes"),
        layout_version="layout-1",
        artefact_entries=[
            {"artefact_kind": "link record", "content_properties": []},
            {"artefact_kind": "step record", "content_properties": []},
        ],
        seat_set=["Seat Alpha"],
        record_kind_sources=[
            {"record_kind": "link record", "source_kind": "packet supplied record"},
            {"record_kind": "roster", "source_kind": "platform sourced record"},
        ],
        publication_time="2026-11-13T00:00:00Z",
        republication_entries=[],
    )


class SharedMachineryTests(unittest.TestCase):
    def test_checks_stand_in_r80_order(self):
        self.assertEqual(checks.CHECKS, ("authenticity", "chain", "completeness"))

    def test_layout_record_stands_in_sh03_form(self):
        layout = build_layout()
        self.assertEqual(layout["layout_version"], "layout-1")
        self.assertEqual(
            checks.layout_source_for(layout, "roster"), "platform sourced record"
        )
        self.assertIsNone(checks.layout_source_for(layout, "unknown kind"))

    def test_spawn_reference_stands_in_sh42_form(self):
        ref = checks.spawn_reference("spawn-alpha-001", "Seat Alpha", "roster-entry-1")
        self.assertEqual(ref["spawn_identity"], "spawn-alpha-001")
        self.assertEqual(ref["performer_seat"], "Seat Alpha")

    def test_discrepancy_entry_requires_the_q2_fields(self):
        with self.assertRaises(ShapeError):
            checks.discrepancy_entry(
                1,
                "authenticity",
                "other named form",
                governing_element_reference=None,
                subject_digest="a" * 40,
            )

    def test_kind_entry_carries_its_defect_kind_code(self):
        entry = checks.discrepancy_entry(
            1,
            "chain",
            "kind",
            defect_kind_code="CH1",
            governing_element_reference="ledger transition 1",
            subject_digest="b" * 40,
            receipt_position=2,
        )
        self.assertEqual(entry["defect_kind_code"], "CH1")
        self.assertEqual(
            entry["root_cause_key"], "chain:ledger transition 1:CH1"
        )

    def test_not_located_and_unidentifiable_are_distinct_forms(self):
        missing = checks.discrepancy_entry(
            1,
            "completeness",
            "other named form",
            discrepancy_form_name="missing artefact",
            governing_element_reference="layout artefact step record",
            subject_name="step record",
            routes_tried=["filename", "content signature"],
        )
        unident = checks.discrepancy_entry(
            2,
            "authenticity",
            "other named form",
            discrepancy_form_name="unidentifiable",
            governing_element_reference="link 1 citation",
            subject_name="step record",
            identification_form="unidentifiable",
        )
        self.assertEqual(
            missing["subject_identification"]["identification_form"], "not located"
        )
        self.assertEqual(
            unident["subject_identification"]["identification_form"],
            "unidentifiable",
        )
        self.assertEqual(missing["routes_tried"], ["filename", "content signature"])

    def test_collision_twins_carry_distinct_subject_identifications(self):
        shared = canonical.git_blob_digest(b"same bytes")
        entries = checks.collision_twin_entries(
            [
                {"member_digest": shared, "member_byte_size": 10},
                {"member_digest": shared, "member_byte_size": 10},
                {"member_digest": "c" * 40, "member_byte_size": 3},
            ]
        )
        self.assertEqual(len(entries), 2)
        positions = {
            e["subject_identification"]["receipt_position"] for e in entries
        }
        self.assertEqual(positions, {1, 2})
        for entry in entries:
            self.assertIn("collision", entry["discrepancy_form_name"])

    def test_no_collision_where_digests_differ(self):
        self.assertEqual(
            checks.collision_twin_entries(
                [
                    {"member_digest": "a" * 40, "member_byte_size": 1},
                    {"member_digest": "b" * 40, "member_byte_size": 1},
                ]
            ),
            [],
        )

    def test_member_readings_recompute_and_leave_uncovered_unchecked(self):
        counter = ReadingCounter()
        readings, unchecked = checks.read_frozen_members(
            member_list()
            + [{"name": "linked.txt", "content": "x", "form": "linked member"}],
            counter,
        )
        by_name = {r["name"]: r for r in readings}
        self.assertEqual(
            by_name["notes.txt"]["digest_git_blob_sha1"],
            canonical.git_blob_digest(MEMBERS["notes.txt"].encode("utf-8")),
        )
        self.assertEqual(unchecked, ["linked.txt"])
        self.assertEqual(counter.members_read, 3)


class OneSidedClassificationTests(unittest.TestCase):
    def classify(self, items, carried=0):
        return checks.classify_one_sided(items, carried)

    def test_both_showings_classify_structural_with_overlap_counted(self):
        result = self.classify(
            [
                {
                    "identification": "item-1",
                    "layout_requires_counterpart": False,
                    "layout_provision": "layout section 2",
                    "pending_record_reference": "gate record append 7",
                }
            ]
        )
        self.assertEqual(
            result["classifications"][0]["classification_heading"], "structural"
        )
        self.assertEqual(result["overlap_count"], 1)
        self.assertEqual(
            result["classifications"][0]["pending_counterpart_record_reference"],
            "gate record append 7",
        )

    def test_structural_only_carries_zero_overlap(self):
        result = self.classify(
            [
                {
                    "identification": "item-1",
                    "layout_requires_counterpart": False,
                    "layout_provision": "layout section 2",
                    "pending_record_reference": None,
                }
            ]
        )
        self.assertEqual(result["overlap_count"], 0)
        self.assertEqual(result["unexplained_count"], 0)

    def test_pending_only_is_timing(self):
        result = self.classify(
            [
                {
                    "identification": "item-1",
                    "layout_requires_counterpart": True,
                    "layout_provision": "layout section 2",
                    "pending_record_reference": "gate record append 7",
                }
            ]
        )
        self.assertEqual(
            result["classifications"][0]["classification_heading"], "timing"
        )

    def test_neither_showing_is_unexplained_and_count_carries(self):
        result = self.classify(
            [
                {
                    "identification": "item-1",
                    "layout_requires_counterpart": True,
                    "layout_provision": "layout section 2",
                    "pending_record_reference": None,
                }
            ],
            carried=1,
        )
        self.assertEqual(
            result["classifications"][0]["classification_heading"], "unexplained"
        )
        self.assertEqual(result["unexplained_count"], 2)
        self.assertEqual(result["unchecked_elements"], ["item-1"])


class InvocationComparisonTests(unittest.TestCase):
    def compare(self, **overrides):
        values = {
            "invocation_layout_digest": "L1",
            "invocation_layout_version": "layout-1",
            "layout_read_digest": "L1",
            "layout_read_version": "layout-1",
            "invocation_build": "isolated-checker-test-build",
            "invocation_stage": "step-gate-1",
            "receipt_build": "isolated-checker-test-build",
            "receipt_stage": "step-gate-1",
            "context_packet_form_version": "packet-form-1",
            "invocation_packet_form_version": "packet-form-1",
            "layout_as_used_digest": "L1",
            "layout_as_used_version": "layout-1",
            "run_checker_version": "checker-1.0.0",
            "invocation_checker_version": "checker-1.0.0",
            "determination_supported": True,
            "remaining_support": False,
        }
        values.update(overrides)
        return checks.invocation_comparisons(**values)

    def test_matching_invocation_compares_clean(self):
        self.assertEqual(self.compare(), [])

    def test_layout_mismatch_supported_takes_custody_gap(self):
        failures = self.compare(layout_read_digest="L2")
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["comparison"], "layout digest comparison")
        self.assertEqual(failures[0]["outcome_word"], "custody gap")

    def test_build_mismatch_supported_takes_custody_gap(self):
        failures = self.compare(receipt_build="other-build")
        self.assertEqual(failures[0]["outcome_word"], "custody gap")

    def test_packet_form_mismatch_unsupported_takes_unverifiable(self):
        failures = self.compare(
            context_packet_form_version="packet-form-2",
            determination_supported=False,
            remaining_support=False,
        )
        self.assertEqual(failures[0]["outcome_word"], "UNVERIFIABLE")

    def test_checker_version_mismatch_unsupported_with_support_takes_partial(self):
        failures = self.compare(
            run_checker_version="checker-9.9.9",
            determination_supported=False,
            remaining_support=True,
        )
        self.assertEqual(failures[0]["outcome_word"], "FAIL with stage PARTIAL")


class AuthenticityTests(unittest.TestCase):
    def run_auth(self, members=MEMBERS, **kwargs):
        kwargs.setdefault(
            "links",
            [
                {
                    "link": "Link 1",
                    "artefact": "notes.txt",
                    "recorded_digest": canonical.git_blob_digest(
                        MEMBERS["notes.txt"].encode("utf-8")
                    ),
                    "spawn": "spawn-alpha-001",
                    "seat": "Seat Alpha",
                    "source_kind": "platform sourced record",
                }
            ],
        )
        kwargs.setdefault("roster", {"Seat Alpha": ["spawn-alpha-001"]})
        kwargs.setdefault("layout", build_layout())
        from isolated_checker import authenticity

        return authenticity.check_authenticity(member_list(members), **kwargs)

    def test_clean_authenticity_passes_at_full_binding(self):
        result = self.run_auth()
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["discrepancy_entries"], [])
        self.assertEqual(result["strengths"]["Link 1"], "full spawn binding")

    def test_link_digest_mismatch_fails_authenticity(self):
        altered = dict(MEMBERS)
        altered["notes.txt"] = "The notes artefact body, altered.\n"
        result = self.run_auth(members=altered)
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(result["outcome_word"], "FAIL with stage PARTIAL")
        entry = result["discrepancy_entries"][0]
        self.assertEqual(entry["check"], "authenticity")
        self.assertEqual(entry["discrepancy_form_name"], "digest mismatch")
        self.assertEqual(
            entry["subject_identification"]["digest"],
            canonical.git_blob_digest(altered["notes.txt"].encode("utf-8")),
        )

    def test_presented_digest_is_never_trusted(self):
        members = member_list()
        for member in members:
            if member["name"] == "notes.txt":
                member["digest_git_blob_sha1"] = canonical.git_blob_digest(
                    b"forged bytes"
                )
                member["content"] = "The notes artefact body, altered.\n"
        from isolated_checker import authenticity

        result = authenticity.check_authenticity(
            members,
            links=[
                {
                    "link": "Link 1",
                    "artefact": "notes.txt",
                    "recorded_digest": canonical.git_blob_digest(
                        MEMBERS["notes.txt"].encode("utf-8")
                    ),
                }
            ],
            roster={"Seat Alpha": ["spawn-alpha-001"]},
            layout=build_layout(),
        )
        self.assertEqual(result["verdict"], "fail")

    def test_spawn_bound_to_an_unauthorised_seat_fails(self):
        result = self.run_auth(
            links=[
                {
                    "link": "Link 1",
                    "artefact": "notes.txt",
                    "recorded_digest": canonical.git_blob_digest(
                        MEMBERS["notes.txt"].encode("utf-8")
                    ),
                    "spawn": "spawn-alpha-001",
                    "seat": "Seat Gamma",
                }
            ]
        )
        self.assertEqual(result["verdict"], "fail")
        entry = result["discrepancy_entries"][0]
        self.assertEqual(
            entry["discrepancy_form_name"],
            "spawn identity does not resolve to an authorised seat",
        )
        self.assertEqual(entry["governing_element_reference"], "Link 1 spawn binding")

    def test_no_roster_state_means_the_spawn_limb_cannot_run_supported(self):
        result = self.run_auth(roster=None)
        self.assertEqual(result["verdict"], "cannot run")
        self.assertEqual(result["outcome_word"], "FAIL with stage PARTIAL")
        self.assertIn(
            "roster state for the step time", result["unchecked_elements"]
        )

    def test_no_roster_state_without_support_is_unverifiable(self):
        result = self.run_auth(roster=None, determination_supported=False)
        self.assertEqual(result["verdict"], "cannot run")
        self.assertEqual(result["outcome_word"], "UNVERIFIABLE")

    def test_unrecomputable_citation_is_unidentifiable_and_cannot_run(self):
        result = self.run_auth(
            links=[
                {
                    "link": "Link 1",
                    "artefact": "notes.txt",
                    "recorded_digest": None,
                }
            ]
        )
        self.assertEqual(result["verdict"], "cannot run")
        entry = result["discrepancy_entries"][0]
        self.assertEqual(
            entry["subject_identification"]["identification_form"], "unidentifiable"
        )

    def test_missing_artefact_is_not_located_and_fails(self):
        result = self.run_auth(
            links=[
                {
                    "link": "Link 9",
                    "artefact": "ghost.txt",
                    "recorded_digest": "d" * 40,
                }
            ]
        )
        self.assertEqual(result["verdict"], "fail")
        entry = result["discrepancy_entries"][0]
        self.assertEqual(
            entry["subject_identification"]["identification_form"], "not located"
        )
        self.assertTrue(entry["routes_tried"])

    def test_required_record_from_the_wrong_source_fails(self):
        result = self.run_auth(
            required_records=[
                {
                    "record_kind": "roster",
                    "name": "notes.txt",
                    "source_kind": "packet supplied record",
                }
            ]
        )
        self.assertEqual(result["verdict"], "fail")
        entry = result["discrepancy_entries"][-1]
        self.assertEqual(
            entry["discrepancy_form_name"],
            "record did not come from the source the layout names",
        )

    def test_required_record_from_the_layout_source_passes(self):
        result = self.run_auth(
            required_records=[
                {
                    "record_kind": "roster",
                    "name": "notes.txt",
                    "source_kind": "platform sourced record",
                }
            ]
        )
        self.assertEqual(result["verdict"], "pass")

    def test_self_citing_source_corroborates_nothing(self):
        result = self.run_auth(
            sources=[
                {
                    "name": "external summary artefact",
                    "self_citing": True,
                    "remaining_support": True,
                }
            ]
        )
        self.assertEqual(result["verdict"], "fail")
        self.assertIn("external summary artefact", result["unchecked_elements"])
        self.assertIn("corroborates nothing", " ".join(result["notes"]))
        self.assertIn("never an authenticity source", " ".join(result["notes"]))

    def test_transcription_strength_is_carried_for_packet_supplied_records(self):
        result = self.run_auth(
            links=[
                {
                    "link": "Link 1",
                    "artefact": "notes.txt",
                    "recorded_digest": canonical.git_blob_digest(
                        MEMBERS["notes.txt"].encode("utf-8")
                    ),
                    "spawn": "spawn-alpha-001",
                    "seat": "Seat Alpha",
                    "source_kind": "packet supplied record",
                }
            ]
        )
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(
            result["strengths"]["Link 1"], "transcription consistency"
        )


CHAIN_MEMBERS = {
    "step-a-output.txt": "Shared material body.\n",
    "step-b-input.txt": "Shared material body.\n",
    "extra.txt": "An additional input, not shared material.\n",
}


class ChainTests(unittest.TestCase):
    def run_chain(self, members=CHAIN_MEMBERS, **kwargs):
        from isolated_checker import chain

        return chain.check_chain(
            [{"name": n, "content": c} for n, c in sorted(members.items())],
            **kwargs,
        )

    def test_matching_shared_material_passes(self):
        result = self.run_chain(
            pairs=[
                {
                    "governing_element_reference": "step a to step b join",
                    "left": "step-a-output.txt",
                    "right": "step-b-input.txt",
                }
            ]
        )
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["discrepancy_entries"], [])

    def test_digest_mismatch_on_shared_material_fails_chain(self):
        members = dict(CHAIN_MEMBERS)
        members["step-b-input.txt"] = "Shared material body, altered.\n"
        result = self.run_chain(
            members=members,
            pairs=[
                {
                    "governing_element_reference": "step a to step b join",
                    "left": "step-a-output.txt",
                    "right": "step-b-input.txt",
                }
            ],
        )
        self.assertEqual(result["verdict"], "fail")
        entry = result["discrepancy_entries"][0]
        self.assertEqual(entry["check"], "chain")
        self.assertEqual(entry["discrepancy_form_name"], "shared material digest mismatch")

    def test_additional_input_is_not_by_itself_a_chain_failure(self):
        result = self.run_chain(
            pairs=[
                {
                    "governing_element_reference": "step a to step b join",
                    "left": "step-a-output.txt",
                    "right": "step-b-input.txt",
                }
            ]
        )
        self.assertEqual(result["verdict"], "pass")
        self.assertIn("extra.txt", result["additional_inputs"])

    def test_presented_digests_on_members_are_never_trusted(self):
        members = [
            {
                "name": "step-a-output.txt",
                "content": "Shared material body.\n",
                "digest_git_blob_sha1": "f" * 40,
            },
            {
                "name": "step-b-input.txt",
                "content": "Shared material body.\n",
                "digest_git_blob_sha1": "e" * 40,
            },
        ]
        from isolated_checker import chain

        result = chain.check_chain(
            members,
            pairs=[
                {
                    "governing_element_reference": "join",
                    "left": "step-a-output.txt",
                    "right": "step-b-input.txt",
                }
            ],
        )
        self.assertEqual(result["verdict"], "pass")

    def test_ledger_transition_matching_including_time_passes(self):
        result = self.run_chain(
            ledger_transitions=[
                {
                    "governing_element_reference": "ledger transition 1",
                    "left": "step-a-output.txt",
                    "right": "step-b-input.txt",
                    "left_time": "2026-11-13T01:00:00Z",
                    "right_time": "2026-11-13T01:00:00Z",
                }
            ]
        )
        self.assertEqual(result["verdict"], "pass")

    def test_ledger_transition_time_mismatch_fails_chain(self):
        result = self.run_chain(
            ledger_transitions=[
                {
                    "governing_element_reference": "ledger transition 1",
                    "left": "step-a-output.txt",
                    "right": "step-b-input.txt",
                    "left_time": "2026-11-13T01:00:00Z",
                    "right_time": "2026-11-13T02:00:00Z",
                }
            ]
        )
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(
            result["discrepancy_entries"][0]["discrepancy_form_name"],
            "ledger transition time mismatch",
        )

    def test_missing_side_of_a_join_is_not_located_and_fails(self):
        result = self.run_chain(
            pairs=[
                {
                    "governing_element_reference": "join",
                    "left": "step-a-output.txt",
                    "right": "ghost.txt",
                }
            ]
        )
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(
            result["discrepancy_entries"][0]["subject_identification"][
                "identification_form"
            ],
            "not located",
        )

    def test_one_sided_material_is_classified_and_changes_no_outcome(self):
        result = self.run_chain(
            pairs=[
                {
                    "governing_element_reference": "join",
                    "left": "step-a-output.txt",
                    "right": "step-b-input.txt",
                }
            ],
            one_sided_items=[
                {
                    "identification": "pending-append",
                    "layout_requires_counterpart": True,
                    "layout_provision": "layout section 2",
                    "pending_record_reference": "gate record append 7",
                },
                {
                    "identification": "orphan-item",
                    "layout_requires_counterpart": True,
                    "layout_provision": "layout section 2",
                    "pending_record_reference": None,
                },
            ],
            carried_unexplained_count=1,
        )
        self.assertEqual(result["verdict"], "pass")
        headings = [
            c["classification_heading"] for c in result["classifications"]
        ]
        self.assertEqual(headings, ["timing", "unexplained"])
        self.assertEqual(result["unexplained_count"], 2)
        self.assertIn("orphan-item", result["unchecked_elements"])


class CompletenessTests(unittest.TestCase):
    def run_comp(self, members=MEMBERS, **kwargs):
        from isolated_checker import completeness

        kwargs.setdefault("layout", build_layout())
        kwargs.setdefault(
            "required_elements",
            [
                {"name": "links.txt", "governing_element_reference": "layout links"},
                {"name": "notes.txt", "governing_element_reference": "layout notes"},
                {
                    "name": "step-record.txt",
                    "governing_element_reference": "layout step record",
                },
            ],
        )
        return completeness.check_completeness(member_list(members), **kwargs)

    def test_complete_set_passes(self):
        result = self.run_comp()
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["discrepancy_entries"], [])

    def test_stated_none_counts_as_present(self):
        reduced = {n: c for n, c in MEMBERS.items() if n != "step-record.txt"}
        result = self.run_comp(
            members=reduced,
            required_elements=[
                {"name": "links.txt", "governing_element_reference": "layout links"},
                {
                    "name": "step-record.txt",
                    "governing_element_reference": "layout step record",
                    "stated_none": True,
                },
            ],
        )
        self.assertEqual(result["verdict"], "pass")
        self.assertIn("step-record.txt", result["counted_present"])

    def test_missing_required_artefact_fails_completeness(self):
        reduced = {n: c for n, c in MEMBERS.items() if n != "step-record.txt"}
        result = self.run_comp(members=reduced)
        self.assertEqual(result["verdict"], "fail")
        entry = result["discrepancy_entries"][0]
        self.assertEqual(entry["check"], "completeness")
        self.assertEqual(entry["discrepancy_form_name"], "missing artefact")
        self.assertNotEqual(entry["discrepancy_category"], "custody gap")

    def test_no_denominator_outside_the_bundle_supported(self):
        result = self.run_comp(
            denominator_outside_bundle=False, determination_supported=True
        )
        self.assertEqual(result["verdict"], "cannot run")
        self.assertEqual(result["outcome_word"], "FAIL with stage PARTIAL")

    def test_no_denominator_outside_the_bundle_unsupported(self):
        result = self.run_comp(
            denominator_outside_bundle=False, determination_supported=False
        )
        self.assertEqual(result["verdict"], "cannot run")
        self.assertEqual(result["outcome_word"], "UNVERIFIABLE")

    def test_no_layout_means_no_denominator(self):
        result = self.run_comp(layout=None)
        self.assertEqual(result["verdict"], "cannot run")

    def test_empty_denominator_for_a_stage_with_steps_cannot_run(self):
        result = self.run_comp(required_elements=[], has_steps=True)
        self.assertEqual(result["verdict"], "cannot run")
        self.assertIn("empty", result["cannot_run_reason"])

    def test_missing_content_property_fails(self):
        result = self.run_comp(
            required_elements=[
                {
                    "name": "notes.txt",
                    "governing_element_reference": "layout notes",
                    "content_properties": ["artefact body", "signature block"],
                }
            ]
        )
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(
            result["discrepancy_entries"][0]["discrepancy_form_name"],
            "artefact content property missing",
        )

    def test_truncation_against_the_content_trace_fails(self):
        result = self.run_comp(
            required_elements=[
                {
                    "name": "notes.txt",
                    "governing_element_reference": "layout notes",
                    "missing_sections": ["C"],
                    "disposition": "content_trace",
                }
            ]
        )
        self.assertEqual(result["verdict"], "fail")
        entry = result["discrepancy_entries"][0]
        self.assertEqual(entry["discrepancy_form_name"], "truncation")
        self.assertIn("content trace", " ".join(result["notes"]))

    def test_truncation_adjudicated_to_stand_is_a_recorded_gap(self):
        result = self.run_comp(
            required_elements=[
                {
                    "name": "notes.txt",
                    "governing_element_reference": "layout notes",
                    "missing_sections": ["C"],
                    "disposition": "recorded_gap",
                }
            ]
        )
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["recorded_gap_elements"], ["notes.txt"])


# The runner's home is re-pinned under Step 14 finding T14-16 as a
# cure consequence: run_all_checks stands in checks_runner.py,
# which depends on the shared machinery and on the three checks,
# and checks.py imports none of its consumers. These tests call
# the runner through the package surface, which re-exports it
# from that home; their setups and expectations stand unchanged.


class RunAllChecksTests(unittest.TestCase):
    def test_all_three_checks_run_in_r80_order_and_pass_clean(self):
        result = ic.run_all_checks(
            member_list(),
            links=[
                {
                    "link": "Link 1",
                    "artefact": "notes.txt",
                    "recorded_digest": canonical.git_blob_digest(
                        MEMBERS["notes.txt"].encode("utf-8")
                    ),
                    "spawn": "spawn-alpha-001",
                    "seat": "Seat Alpha",
                    "source_kind": "platform sourced record",
                }
            ],
            roster={"Seat Alpha": ["spawn-alpha-001"]},
            layout=build_layout(),
            required_elements=[
                {"name": "links.txt", "governing_element_reference": "layout links"},
                {"name": "notes.txt", "governing_element_reference": "layout notes"},
                {
                    "name": "step-record.txt",
                    "governing_element_reference": "layout step record",
                },
            ],
        )
        self.assertEqual(
            [r["check"] for r in result["checks"]],
            ["authenticity", "chain", "completeness"],
        )
        self.assertEqual(
            [r["verdict"] for r in result["checks"]], ["pass", "pass", "pass"]
        )

    def test_collision_twins_fail_the_combined_run(self):
        receipt = build_receipt()
        result = ic.run_all_checks(
            member_list(),
            receipt_members=receipt["members"],
            layout=build_layout(),
            required_elements=[
                {"name": "links.txt", "governing_element_reference": "layout links"}
            ],
        )
        # The receipt above is built over distinct members, so no
        # twin stands in it; a receipt over twin members follows.
        self.assertEqual(result["collision_entries"], [])
        twin_receipt_members = [
            {"member_digest": "a" * 40, "member_byte_size": 5},
            {"member_digest": "a" * 40, "member_byte_size": 5},
        ]
        result = ic.run_all_checks(
            member_list(),
            receipt_members=twin_receipt_members,
            layout=build_layout(),
            required_elements=[
                {"name": "links.txt", "governing_element_reference": "layout links"}
            ],
        )
        self.assertEqual(len(result["collision_entries"]), 2)
        self.assertEqual(result["checks"][0]["verdict"], "fail")


if __name__ == "__main__":
    unittest.main()
