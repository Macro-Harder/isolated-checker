"""Slice S-06 addendum handling, direct core tests.

These tests exercise addendum handling at plan module MD-05 in
process, over in memory inputs in the forms the earlier slices
issue: addendum records in the SH-35 form slice S-01 delivers,
discrepancy entries in the SH-14 form the checks build through,
and member material recomputed through the reading layer, no
presented digest trusted. They pin the presented case kinds of
plan statement P1-S06-3, criterion A8: a superseded link; bytes
changed with no addendum; an openly labelled late completion; a
forking chain; a cycling chain; two successors for one digest;
an addendum in a later intake; and addenda failing each of the
two filer tests, roster authorisation and identity match. The
suite level A8 pins in test_self_describing.py run through the
operation surface of slices S-07 onward and are accounted in the
slice receipt in that form.
"""

import unittest

import isolated_checker as ic
from isolated_checker import addendum_handling as ah
from isolated_checker import canonical
from isolated_checker.reading import ReadingCounter
from isolated_checker.shapes import ShapeError

A = "1" * 40
B = "2" * 40
C = "3" * 40
D = "4" * 40
E = "5" * 40

SEAT = "Seat Alpha"
PRODUCER = "Seat Alpha"


def addendum(original, corrected, seat=SEAT, **context):
    presentation = {
        "original_digest": original,
        "corrected_digest": corrected,
        "correction_time": "2026-11-13T01:00:00Z",
        "correction_reason_filer_claim": "late entry completed",
        "correcting_seat": seat,
    }
    presentation.update(context)
    return presentation


def handle(addenda, **kwargs):
    kwargs.setdefault("authorised_seats", [SEAT, "Seat Beta"])
    return ah.handle_addenda(addenda, **kwargs)


class RecordFormTests(unittest.TestCase):
    def test_addendum_record_stands_in_sh35_form_through_the_seam(self):
        record = ah.validate_addendum(addendum(A, B))
        self.assertEqual(record["original_digest"], A)
        self.assertEqual(record["corrected_digest"], B)
        self.assertNotIn("packet", record)

    def test_addendum_record_missing_a_brief_field_raises_through_the_seam(self):
        presentation = addendum(A, B)
        del presentation["correcting_seat"]
        with self.assertRaises(ShapeError):
            ah.validate_addendum(presentation)

    def test_second_digesting_fields_are_all_or_none(self):
        presentation = addendum(A, B, old_digest=A, new_digest=E)
        with self.assertRaises(ShapeError):
            ah.validate_addendum(presentation)

    def test_second_digesting_binds_old_and_new_side_by_side(self):
        result = handle(
            [
                addendum(
                    A,
                    B,
                    old_digest=A,
                    new_digest=E,
                    successor_algorithm="successor-algorithm",
                    original_filing_seat=SEAT,
                )
            ]
        )
        disposition = result["addenda"][0]
        self.assertTrue(disposition["followed"])
        self.assertEqual(
            disposition["second_digesting"],
            {
                "old_digest": A,
                "new_digest": E,
                "successor_algorithm": "successor-algorithm",
            },
        )
        self.assertFalse(disposition["original_receipt_rewritten"])


class ChainFollowingTests(unittest.TestCase):
    def test_valid_addendum_is_followed_to_one_terminal_digest(self):
        result = handle([addendum(A, B, original_filing_seat=SEAT)])
        self.assertEqual(result["discrepancy_entries"], [])
        self.assertEqual(len(result["chains"]), 1)
        chain = result["chains"][0]
        self.assertEqual(chain["terminal_digest"], B)
        self.assertEqual(chain["path"], [A, B])
        self.assertEqual(chain["depth"], 1)

    def test_chain_of_three_is_followed_to_one_terminal_digest(self):
        result = handle(
            [
                addendum(A, B, original_filing_seat=SEAT),
                addendum(B, C, original_filing_seat=SEAT),
                addendum(C, D, original_filing_seat=SEAT),
            ]
        )
        self.assertEqual(result["discrepancy_entries"], [])
        chain = result["chains"][0]
        self.assertEqual(chain["terminal_digest"], D)
        self.assertEqual(chain["path"], [A, B, C, D])

    def test_traversal_depth_is_counted_through_the_chain(self):
        counter = ReadingCounter()
        result = handle(
            [
                addendum(A, B, original_filing_seat=SEAT),
                addendum(B, C, original_filing_seat=SEAT),
                addendum(C, D, original_filing_seat=SEAT),
            ],
            counter=counter,
        )
        self.assertEqual(result["max_traversal_depth"], 3)
        self.assertEqual(counter.max_depth, 3)

    def test_successor_limit_is_per_packet(self):
        result = handle(
            [
                addendum(A, B, original_filing_seat=SEAT, packet="packet-1"),
                addendum(A, C, original_filing_seat=SEAT, packet="packet-2"),
            ]
        )
        self.assertEqual(result["discrepancy_entries"], [])
        self.assertEqual(result["forks"], [])
        terminals = sorted(
            chain["terminal_digest"] for chain in result["chains"]
        )
        self.assertEqual(terminals, [B, C])

    def test_forked_chain_is_a_discrepancy_naming_the_digests(self):
        result = handle(
            [
                addendum(A, B, original_filing_seat=SEAT),
                addendum(B, C, original_filing_seat=SEAT),
                addendum(B, D, original_filing_seat=SEAT),
            ]
        )
        self.assertEqual(len(result["forks"]), 1)
        fork = result["forks"][0]
        self.assertEqual(fork["digest"], B)
        self.assertEqual(sorted(fork["claimed_successors"]), [C, D])
        self.assertIsNone(result["chains"][0]["terminal_digest"])
        entry = result["discrepancy_entries"][0]
        self.assertEqual(entry["check"], "chain")
        self.assertEqual(entry["discrepancy_form_name"], "fork")
        self.assertEqual(entry["subject_identification"]["digest"], B)
        self.assertIsNone(entry["defect_kind_code"])
        text = ah.addendum_handling_filed_text(result)
        self.assertIn("fork", text)
        self.assertIn("no terminal digest", text)
        self.assertIn(B, text)
        self.assertIn(C, text)
        self.assertIn(D, text)

    def test_two_successors_for_one_digest_take_no_terminal_digest(self):
        result = handle(
            [
                addendum(A, B, original_filing_seat=SEAT),
                addendum(A, C, original_filing_seat=SEAT),
            ]
        )
        self.assertEqual(len(result["forks"]), 1)
        self.assertIsNone(result["chains"][0]["terminal_digest"])
        text = ah.addendum_handling_filed_text(result)
        self.assertIn("two addenda", text)
        self.assertIn("no terminal digest", text)
        self.assertIn(A, text)

    def test_cycling_chain_is_a_discrepancy_naming_the_cycle_digests(self):
        result = handle(
            [
                addendum(A, B, original_filing_seat=SEAT),
                addendum(B, C, original_filing_seat=SEAT),
                addendum(C, A, original_filing_seat=SEAT),
            ]
        )
        self.assertEqual(len(result["cycles"]), 1)
        self.assertEqual(sorted(result["cycles"][0]["digests"]), [A, B, C])
        self.assertIsNone(result["chains"][0]["terminal_digest"])
        entry = result["discrepancy_entries"][0]
        self.assertEqual(entry["discrepancy_form_name"], "cycle")
        text = ah.addendum_handling_filed_text(result)
        self.assertIn("cycle", text)
        self.assertIn("no terminal digest", text)

    def test_self_cycling_addendum_takes_no_terminal_digest(self):
        result = handle([addendum(A, A, original_filing_seat=SEAT)])
        self.assertEqual(len(result["cycles"]), 1)
        self.assertIsNone(result["chains"][0]["terminal_digest"])


class SupersededLinkTests(unittest.TestCase):
    def test_superseded_link_names_both_digests_and_which_was_checked(self):
        result = handle(
            [addendum(A, B, original_filing_seat=SEAT)],
            links=[{"link": "Link 1", "artefact": "notes.txt", "cited_digest": A}],
        )
        self.assertEqual(len(result["superseded_links"]), 1)
        link = result["superseded_links"][0]
        self.assertEqual(link["cited_digest"], A)
        self.assertEqual(link["successor_digest"], B)
        self.assertEqual(link["terminal_digest"], B)
        self.assertEqual(link["checked_digest"], A)
        entry = result["discrepancy_entries"][0]
        self.assertEqual(entry["discrepancy_form_name"], "superseded link")
        self.assertEqual(entry["subject_identification"]["digest"], A)
        text = ah.addendum_handling_filed_text(result)
        self.assertIn(A, text)
        self.assertIn(B, text)
        self.assertIn("checked digest: " + A, text)

    def test_superseded_link_mid_chain_checks_the_cited_digest(self):
        result = handle(
            [
                addendum(A, B, original_filing_seat=SEAT),
                addendum(B, C, original_filing_seat=SEAT),
            ],
            links=[{"link": "Link 1", "artefact": "notes.txt", "cited_digest": B}],
        )
        link = result["superseded_links"][0]
        self.assertEqual(link["checked_digest"], B)
        self.assertEqual(link["successor_digest"], C)
        self.assertEqual(link["terminal_digest"], C)

    def test_corrected_bytes_are_checked_only_as_a_new_intake(self):
        result = handle(
            [addendum(A, B, original_filing_seat=SEAT)],
            links=[{"link": "Link 1", "artefact": "notes.txt", "cited_digest": A}],
        )
        link = result["superseded_links"][0]
        self.assertEqual(
            link["corrected_bytes_route"],
            "new intake under the cure route",
        )
        text = ah.addendum_handling_filed_text(result)
        self.assertIn("new intake", text)
        self.assertIn("never under the original link authority", text)

    def test_link_citing_the_terminal_digest_is_no_discrepancy(self):
        result = handle(
            [addendum(A, B, original_filing_seat=SEAT)],
            links=[{"link": "Link 1", "artefact": "notes.txt", "cited_digest": B}],
        )
        self.assertEqual(result["superseded_links"], [])
        self.assertEqual(result["discrepancy_entries"], [])


class ChangedBytesTests(unittest.TestCase):
    MEMBERS = {"notes.txt": "The notes artefact body, altered.\n"}
    RECORDED = None

    def members(self):
        return [
            {"name": name, "content": content}
            for name, content in self.MEMBERS.items()
        ]

    def recorded(self):
        return canonical.git_blob_digest(b"The notes artefact body.\n")

    def test_bytes_changed_with_no_addendum_is_not_a_clean_pass(self):
        result = handle(
            [],
            members=self.members(),
            links=[
                {
                    "link": "Link 1",
                    "artefact": "notes.txt",
                    "recorded_digest": self.recorded(),
                }
            ],
        )
        self.assertEqual(len(result["changed_bytes_without_addendum"]), 1)
        changed = result["changed_bytes_without_addendum"][0]
        self.assertEqual(changed["recorded_digest"], self.recorded())
        self.assertEqual(
            changed["recomputed_digest"],
            canonical.git_blob_digest(
                self.MEMBERS["notes.txt"].encode("utf-8")
            ),
        )
        self.assertTrue(changed["no_addendum"])
        self.assertEqual(len(result["discrepancy_entries"]), 1)
        text = ah.addendum_handling_filed_text(result)
        self.assertIn("no addendum", text)
        self.assertIn("correction", text)
        self.assertIn("not a clean pass", text)

    def test_bytes_changed_with_a_covering_addendum_are_not_changed_without(self):
        recomputed = canonical.git_blob_digest(
            self.MEMBERS["notes.txt"].encode("utf-8")
        )
        result = handle(
            [
                addendum(
                    self.recorded(),
                    recomputed,
                    original_filing_seat=SEAT,
                )
            ],
            members=self.members(),
            links=[
                {
                    "link": "Link 1",
                    "artefact": "notes.txt",
                    "recorded_digest": self.recorded(),
                }
            ],
        )
        self.assertEqual(result["changed_bytes_without_addendum"], [])
        self.assertEqual(len(result["superseded_links"]), 1)


class FilerTests(unittest.TestCase):
    def test_filer_failing_the_roster_test_is_not_followed(self):
        result = handle(
            [addendum(A, B, seat="Seat Gamma", original_filing_seat="Seat Gamma")]
        )
        disposition = result["addenda"][0]
        self.assertFalse(disposition["followed"])
        self.assertEqual(disposition["failed_test"], "roster authorisation")
        entry = result["discrepancy_entries"][0]
        self.assertEqual(entry["discrepancy_form_name"], "unauthorised filing")
        self.assertIn("roster", entry["governing_element_reference"])
        self.assertEqual(result["chains"], [])
        text = ah.addendum_handling_filed_text(result)
        self.assertIn("unauthorised filing", text)
        self.assertIn("roster", text)

    def test_filer_failing_the_identity_test_is_not_followed(self):
        result = handle(
            [addendum(A, B, seat="Seat Beta", original_filing_seat=SEAT)]
        )
        disposition = result["addenda"][0]
        self.assertFalse(disposition["followed"])
        self.assertEqual(
            disposition["failed_test"],
            "identity match against the original filing seat",
        )
        entry = result["discrepancy_entries"][0]
        self.assertEqual(entry["discrepancy_form_name"], "unauthorised filing")
        self.assertIn("identity match", entry["governing_element_reference"])
        self.assertEqual(result["chains"], [])
        text = ah.addendum_handling_filed_text(result)
        self.assertIn("unauthorised filing", text)
        self.assertIn("identity match", text)

    def test_identity_falls_back_to_the_producer_identity(self):
        result = handle(
            [
                addendum(
                    A,
                    B,
                    seat="Seat Beta",
                    original_filing_seat=None,
                    producer_identity="Seat Beta",
                )
            ]
        )
        self.assertTrue(result["addenda"][0]["followed"])
        self.assertEqual(
            result["addenda"][0]["identity_reference"],
            "producer identity recorded for that material in the packet",
        )

    def test_identity_failing_against_the_producer_identity_is_not_followed(self):
        result = handle(
            [
                addendum(
                    A,
                    B,
                    seat=SEAT,
                    original_filing_seat=None,
                    producer_identity="Seat Beta",
                )
            ]
        )
        disposition = result["addenda"][0]
        self.assertFalse(disposition["followed"])
        self.assertEqual(
            disposition["failed_test"],
            "identity match against the producer identity",
        )

    def test_identity_references_may_stand_in_top_level_maps(self):
        result = ah.handle_addenda(
            [addendum(A, B)],
            authorised_seats=[SEAT],
            original_filing_seats={A: SEAT},
        )
        self.assertTrue(result["addenda"][0]["followed"])
        result = ah.handle_addenda(
            [addendum(A, B)],
            authorised_seats=[SEAT],
            producer_identities={A: "Seat Beta"},
        )
        self.assertFalse(result["addenda"][0]["followed"])

    def test_no_roster_state_leaves_the_filer_unchecked_and_not_followed(self):
        result = ah.handle_addenda(
            [addendum(A, B, original_filing_seat=SEAT)],
            authorised_seats=None,
        )
        self.assertFalse(result["addenda"][0]["followed"])
        self.assertEqual(result["discrepancy_entries"], [])
        self.assertIn(
            "roster authorisation for addendum filers",
            result["unchecked_elements"],
        )

    def test_unauthorised_addendum_creates_no_supersession(self):
        result = handle(
            [addendum(A, B, seat="Seat Gamma", original_filing_seat="Seat Gamma")],
            links=[{"link": "Link 1", "artefact": "notes.txt", "cited_digest": A}],
        )
        self.assertEqual(result["superseded_links"], [])


class LabellingAndLaterIntakeTests(unittest.TestCase):
    def test_labelled_late_completion_is_reported_late_and_never_a_pass(self):
        result = handle(
            [
                addendum(
                    A,
                    B,
                    original_filing_seat=SEAT,
                    labelled_late=True,
                    missed_property="filed before the gate opened",
                )
            ]
        )
        self.assertEqual(len(result["labelling_reports"]), 1)
        report = result["labelling_reports"][0]
        self.assertEqual(report["missed_property"], "filed before the gate opened")
        self.assertEqual(report["reported_as"], "labelled late")
        self.assertFalse(report["converted_to_pass"])
        self.assertFalse(report["is_pass"])
        text = ah.addendum_handling_filed_text(result)
        self.assertIn("late", text)
        self.assertIn("filed before the gate opened", text)
        self.assertIn("not a pass", text)

    def test_addendum_in_a_later_intake_is_treated_in_that_intake_only(self):
        result = handle(
            [addendum(A, B, original_filing_seat=SEAT, arrives_in_intake="intake-2")],
            current_intake="intake-1",
        )
        disposition = result["addenda"][0]
        self.assertFalse(disposition["followed"])
        self.assertTrue(disposition["later_intake_only"])
        self.assertEqual(len(result["later_intake_addenda"]), 1)
        self.assertFalse(result["earlier_report_edited"])
        self.assertEqual(result["chains"], [])
        text = ah.addendum_handling_filed_text(result)
        self.assertIn("later intake", text)
        self.assertIn("new intake", text)
        self.assertIn(A, text)
        self.assertIn(B, text)
        self.assertIn("earlier report stands unedited", text)

    def test_addendum_in_the_same_intake_is_treated_here(self):
        result = handle(
            [addendum(A, B, original_filing_seat=SEAT, arrives_in_intake="intake-1")],
            current_intake="intake-1",
        )
        self.assertTrue(result["addenda"][0]["followed"])
        self.assertEqual(result["later_intake_addenda"], [])


class FiledTextTests(unittest.TestCase):
    def test_valid_addendum_text_names_both_digests_and_the_filer_claim(self):
        result = handle([addendum(A, B, original_filing_seat=SEAT)])
        text = ah.addendum_handling_filed_text(result)
        self.assertIn(A, text)
        self.assertIn(B, text)
        self.assertIn("filer claim", text)

    def test_no_text_states_a_correction_time_as_a_checked_fact(self):
        result = handle([addendum(A, B, original_filing_seat=SEAT)])
        text = ah.addendum_handling_filed_text(result)
        self.assertIn("never a checked fact", text)
        self.assertNotIn("correction time: checked fact", text)

    def test_reason_and_correction_time_stand_as_filer_claims_in_the_result(self):
        result = handle([addendum(A, B, original_filing_seat=SEAT)])
        disposition = result["addenda"][0]
        self.assertEqual(disposition["reason_strength"], "filer claim")
        self.assertEqual(
            disposition["correction_time_strength"],
            "filer claim, never a checked fact",
        )

    def test_package_reexports_the_handling_surface(self):
        self.assertIs(ic.handle_addenda, ah.handle_addenda)
        self.assertIs(
            ic.addendum_handling_filed_text, ah.addendum_handling_filed_text
        )
        self.assertIs(ic.follow_addendum_chain, ah.follow_addendum_chain)


if __name__ == "__main__":
    unittest.main()
