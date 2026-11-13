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


if __name__ == "__main__":
    unittest.main()
