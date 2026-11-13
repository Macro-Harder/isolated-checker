"""Slice S-04 seal phase, direct core tests.

These tests exercise the seal phase at plan module MD-04 in
process, over in memory inputs in the cured forms the freeze
surface issues: a custody receipt built through the MD-02 seam
and completed with its self digest, member byte strings as the
reading layer reads them, an anchor entry in the SH-07 form, and
an intake order in the SH-08 form. They pin the seal comparison
set of contract XR-01: receipt recomputation against members,
anchor comparison, and sequence comparison against the intake
order field, with the custody gap emission form at exit status 1
where the receipt comparison supports the determination and at
exit status 2 where it supports none. The suite level seal pins
in test_seal_and_checks.py run through the operation surface of
later slices and are accounted in the slice receipt in that form.
"""

import unittest

import isolated_checker as ic
from isolated_checker import canonical, receipts, seal
from isolated_checker.reading import ReadingCounter
from isolated_checker.shapes import ShapeError

MEMBERS = {
    "links.txt": "Link 1 names notes.txt for Seat Alpha.\n",
    "notes.txt": "The notes artefact body.\n",
    "step-record.txt": "Step record sections 1 to 3.\n",
}


def build_receipt(members=MEMBERS, position=1, predecessor=None):
    ordered = sorted(members)
    entries = []
    for name in ordered:
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
        position,
        predecessor,
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


def member_list(members=MEMBERS):
    return [
        {"name": name, "content": members[name]} for name in sorted(members)
    ]


def receipt_names(members=MEMBERS):
    return sorted(members)


def run_seal(receipt, members=MEMBERS, **kwargs):
    kwargs.setdefault("anchor_entry", receipts.anchor_entry(receipt["self_digest"]))
    kwargs.setdefault(
        "intake_order",
        [seal.intake_order_item(1, receipt["self_digest"])],
    )
    return seal.check_seal(
        receipt=receipt,
        members=member_list(members),
        receipt_member_names=receipt_names(),
        **kwargs,
    )


class SealComparisonTests(unittest.TestCase):
    def test_intact_set_proceeds_with_no_custody_gap(self):
        receipt = build_receipt()
        result = run_seal(receipt)
        self.assertEqual(result["status"], "intact")
        self.assertIsNone(result["exit_status"])
        self.assertEqual(result["failed_comparisons"], [])
        self.assertEqual(result["discrepancy_entries"], [])
        self.assertTrue(result["receipt_recomputes"])

    def test_altered_member_takes_custody_gap_at_status_1(self):
        receipt = build_receipt()
        altered = dict(MEMBERS)
        altered["notes.txt"] = "The notes artefact body, altered.\n"
        result = run_seal(receipt, altered)
        self.assertEqual(result["status"], "broken seal")
        self.assertEqual(result["outcome_word"], "custody gap")
        self.assertEqual(result["exit_status"], 1)
        self.assertIn("member digest comparison", result["failed_comparisons"])
        entry = result["discrepancy_entries"][0]
        self.assertEqual(entry["check"], "chain")
        self.assertEqual(entry["discrepancy_category"], "custody gap")
        self.assertIsNone(entry["defect_kind_code"])
        self.assertEqual(
            entry["governing_element_reference"], "member digest comparison"
        )
        self.assertEqual(result["failures"][0]["subject_name"], "notes.txt")

    def test_removed_member_takes_custody_gap_at_status_1(self):
        receipt = build_receipt()
        reduced = {
            name: text for name, text in MEMBERS.items() if name != "notes.txt"
        }
        result = run_seal(receipt, reduced)
        self.assertEqual(result["exit_status"], 1)
        self.assertEqual(result["failures"][0]["subject_name"], "notes.txt")

    def test_extra_member_takes_custody_gap_at_status_1(self):
        receipt = build_receipt()
        grown = dict(MEMBERS)
        grown["extra.txt"] = "A member the receipt does not name.\n"
        result = run_seal(receipt, grown)
        self.assertEqual(result["exit_status"], 1)
        self.assertIn("extra.txt", [f["subject_name"] for f in result["failures"]])

    def test_digest_only_member_is_never_trusted(self):
        receipt = build_receipt()
        presented = member_list()
        for entry in presented:
            if entry["name"] == "notes.txt":
                entry["content"] = None
        result = seal.check_seal(
            receipt=receipt,
            members=presented,
            receipt_member_names=receipt_names(),
            anchor_entry=receipts.anchor_entry(receipt["self_digest"]),
            intake_order=[seal.intake_order_item(1, receipt["self_digest"])],
        )
        self.assertEqual(result["status"], "broken seal")
        self.assertIn("member digest comparison", result["failed_comparisons"])

    def test_anchor_missing_supports_no_determination_and_takes_status_2(self):
        receipt = build_receipt()
        result = run_seal(receipt, anchor_entry=None)
        self.assertEqual(result["exit_status"], 2)
        self.assertIn("anchor comparison", result["failed_comparisons"])
        self.assertFalse(result["determination_supported"])

    def test_anchor_conflict_takes_status_1(self):
        receipt = build_receipt()
        other = receipts.anchor_entry(canonical.raw_digest(b"other receipt"))
        result = run_seal(receipt, anchor_entry=other)
        self.assertEqual(result["exit_status"], 1)
        self.assertIn("anchor comparison", result["failed_comparisons"])

    def test_anchor_of_another_intake_takes_status_1(self):
        receipt = build_receipt()
        other_receipt = build_receipt(position=1)
        other_receipt = dict(other_receipt, freeze_time="2026-11-13T01:00:00Z")
        other_receipt = canonical.with_receipt_self_digest(other_receipt)
        order = [
            seal.intake_order_item(1, other_receipt["self_digest"]),
        ]
        result = seal.check_seal(
            receipt=other_receipt,
            members=member_list(),
            receipt_member_names=receipt_names(),
            anchor_entry=receipts.anchor_entry(receipt["self_digest"]),
            intake_order=[
                seal.intake_order_item(1, receipt["self_digest"]),
                seal.intake_order_item(2, other_receipt["self_digest"]),
            ],
        )
        # The set's own receipt stands second in the order while the
        # anchor names the first intake: the anchor belongs to
        # another intake for this set's position.
        self.assertEqual(result["status"], "broken seal")
        self.assertEqual(result["exit_status"], 1)
        self.assertTrue(order)

    def test_unrecomputable_receipt_takes_status_2(self):
        receipt = build_receipt()
        receipt = dict(receipt, self_digest=canonical.raw_digest(b"forged"))
        result = run_seal(
            receipt, anchor_entry=receipts.anchor_entry(receipt["self_digest"])
        )
        self.assertEqual(result["exit_status"], 2)
        self.assertIn("receipt recomputation", result["failed_comparisons"])
        self.assertFalse(result["receipt_recomputes"])

    def test_rewritten_receipt_recomputing_but_off_anchor_takes_status_1(self):
        receipt = build_receipt()
        standing_anchor = receipts.anchor_entry(receipt["self_digest"])
        rewritten = dict(build_receipt(), freeze_time="2026-11-13T02:00:00Z")
        rewritten = canonical.with_receipt_self_digest(rewritten)
        self.assertNotEqual(rewritten["self_digest"], receipt["self_digest"])
        result = seal.check_seal(
            receipt=rewritten,
            members=member_list(),
            receipt_member_names=receipt_names(),
            anchor_entry=standing_anchor,
            intake_order=[seal.intake_order_item(1, rewritten["self_digest"])],
        )
        self.assertTrue(result["receipt_recomputes"])
        self.assertEqual(result["exit_status"], 1)
        self.assertIn("anchor comparison", result["failed_comparisons"])

    def test_receipt_build_mismatch_with_invocation_takes_status_1(self):
        receipt = build_receipt()
        result = run_seal(receipt, invocation_build="another-build")
        self.assertEqual(result["exit_status"], 1)
        self.assertIn(
            "receipt build and stage comparison", result["failed_comparisons"]
        )

    def test_first_receipt_claiming_a_predecessor_takes_status_1(self):
        receipt = canonical.with_receipt_self_digest(
            dict(
                build_receipt(),
                predecessor_receipt_digest=canonical.raw_digest(b"prior"),
            )
        )
        result = run_seal(
            receipt, anchor_entry=receipts.anchor_entry(receipt["self_digest"])
        )
        self.assertEqual(result["exit_status"], 1)
        self.assertIn("sequence comparison", result["failed_comparisons"])

    def test_chain_ending_early_against_the_intake_order_takes_custody_gap(self):
        first = build_receipt()
        second = build_receipt(position=2, predecessor=first["self_digest"])
        order = [seal.intake_order_item(2, second["self_digest"])]
        result = seal.check_seal(
            receipt=second,
            members=member_list(),
            receipt_member_names=receipt_names(),
            anchor_entry=receipts.anchor_entry(second["self_digest"]),
            intake_order=order,
        )
        self.assertEqual(result["exit_status"], 1)
        self.assertIn("sequence comparison", result["failed_comparisons"])

    def test_whole_intake_removal_against_the_intake_order_takes_custody_gap(self):
        receipt = build_receipt()
        other = canonical.raw_digest(b"another intake receipt")
        result = run_seal(
            receipt, intake_order=[seal.intake_order_item(1, other)]
        )
        self.assertEqual(result["exit_status"], 1)
        self.assertIn("sequence comparison", result["failed_comparisons"])

    def test_no_intake_order_record_leaves_sequence_cases_unchecked_by_name(self):
        receipt = build_receipt()
        result = run_seal(receipt, intake_order=None)
        self.assertEqual(result["status"], "intact")
        self.assertIn("receipt chain ends early", result["unchecked_elements"])
        self.assertIn("whole intake removal", result["unchecked_elements"])


class SealEmissionFormTests(unittest.TestCase):
    def test_seven_operations_named_once(self):
        self.assertEqual(
            seal.SEAL_OPERATIONS,
            (
                "verdict run",
                "rerun",
                "appeal run",
                "cure run",
                "corrected run",
                "dry run",
                "CH7 recheck",
            ),
        )

    def test_seal_break_report_and_entry_stand_in_registered_forms(self):
        receipt = build_receipt()
        altered = dict(MEMBERS)
        altered["notes.txt"] = "The notes artefact body, altered.\n"
        result = run_seal(receipt, altered)
        report = result["report"]
        self.assertEqual(report["custody_receipt_digest"], receipt["self_digest"])
        self.assertEqual(report["discrepancy_list"], result["discrepancy_entries"])
        text = seal.seal_break_filed_text(result)
        self.assertIn("custody gap", text)
        self.assertIn("chain", text)
        self.assertIn(receipt["self_digest"], text)
        self.assertIn("member digest comparison", text)
        self.assertIn("notes.txt", text)
        self.assertNotIn("verdict: pass", text)

    def test_custody_gap_entry_requires_the_q2_fields(self):
        entry = seal.custody_gap_entry(
            1, "member digest comparison", "notes.txt", "a" * 40, 2
        )
        self.assertEqual(entry["entry_number"], 1)
        with self.assertRaises(ShapeError):
            seal.custody_gap_entry(1, "member digest comparison", None, None, None)

    def test_fixity_mismatch_form_stands_in_the_sh37_row(self):
        record = seal.fixity_mismatch_record(
            "receipt-digest", "notes.txt", "a" * 40, "b" * 40, "cursor-1"
        )
        self.assertEqual(record["result_word"], "custody gap")
        self.assertEqual(
            record["store_discrepancy"]["digest_expected"], "a" * 40
        )
        with self.assertRaises(ShapeError):
            seal.fixity_mismatch_record("receipt-digest", "notes.txt", None, "b" * 40)

    def test_reading_counter_hook_counts_every_byte_the_seal_reads(self):
        receipt = build_receipt()
        counter = ReadingCounter()
        result = run_seal(receipt, counter=counter)
        self.assertGreater(counter.bytes_read, 0)
        self.assertEqual(counter.members_read, len(MEMBERS))
        # Strengthened under Step 14 finding T14-20: the digest
        # computation count is pinned on this seal run, the three
        # member recomputations and the receipt recomputation note
        # the seal phase makes before resting any comparison on
        # the receipt, four in all, so this test fails with that
        # note removed.
        self.assertEqual(counter.digest_computations, 4)
        self.assertIs(result["counter"], counter)

    def test_package_reexports_the_seal_phase(self):
        self.assertIs(ic.check_seal, seal.check_seal)

    def test_seal_consumes_a_cured_freeze_result_as_issued(self):
        from isolated_checker import freeze as freeze_core
        from isolated_checker import pinning

        handed = [
            {
                "name": name,
                "content": MEMBERS[name],
                "source_kind": "handed in material",
            }
            for name in sorted(MEMBERS)
        ]
        frozen = freeze_core.freeze_intake(
            handed,
            [dict(member) for member in handed],
            build="isolated-checker-test-build",
            stage="step-gate-1",
            packet_form_version="packet-form-1",
            checker_version="checker-1.0.0",
            freeze_time="2026-11-13T00:00:00Z",
            pinning_record=pinning.pinning_record(
                "SHA-256", "CFE-1", "checker-1.0.0"
            ),
            standing_rule_versions=[],
            outside_standard_versions=[],
            anchor_home="anchor-home",
        )
        self.assertEqual(frozen["status"], "frozen")
        result = seal.check_seal(
            receipt=frozen["receipt"],
            members=[
                {"name": reading["name"], "content": reading["content"]}
                for reading in frozen["members"]
            ],
            receipt_member_names=[
                reading["name"] for reading in frozen["members"]
            ],
            anchor_entry=frozen["anchor_entry"],
            intake_order=[
                seal.intake_order_item(1, frozen["receipt_digest"])
            ],
        )
        self.assertEqual(result["status"], "intact")
        self.assertEqual(result["receipt_digest"], frozen["receipt_digest"])


if __name__ == "__main__":
    unittest.main()
