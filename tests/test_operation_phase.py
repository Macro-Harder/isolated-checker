"""Direct tests for slice S-07, the operation surface.

Written test first for behaviour the Step 13 suite's pins do not
reach in process: the MD-16 artefact kind to member resolution duty
of Plan Supplement 7 Part 2 section S7P2-2 (its routes, its
recompute test, its carried standings, and its bars), and the
has_steps threading the second Lead Engineer review names at O2-3
(the operation passes the stage's step standing into the
completeness consumption, so an empty resolved denominator for a
stage that has steps takes the cannot run form and never a silent
pass).
"""

import pathlib
import tempfile
import unittest

import harness
from isolated_checker import discovery


MEMBERS = [
    {"name": "links.txt", "content": "Link 1 names notes.txt.\n"},
    {"name": "notes.txt", "content": "The notes artefact body.\n"},
    {"name": "step-record.txt", "content": "Step record sections.\n"},
]


def layout(entries):
    return {
        "layout_digest": "layout-digest",
        "layout_version": "layout-1",
        "artefact_entries": entries,
        "seat_set": ["Seat Alpha"],
        "record_kind_sources": [],
        "publication_time": "2026-11-13T00:00:00Z",
        "republication_entries": [],
    }


class ResolutionDutyTests(unittest.TestCase):
    def test_filename_route_locates_the_member_a_kind_requires(self):
        elements = discovery.resolve_required_elements(
            layout([{"artefact_kind": "notes.txt", "content_properties": []}]),
            MEMBERS,
            receipt_order_names=["links.txt", "notes.txt", "step-record.txt"],
        )
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0]["name"], "notes.txt")
        self.assertEqual(elements[0]["located_member"], "notes.txt")
        self.assertEqual(elements[0]["route"], "filename")

    def test_content_signature_route_locates_by_what_the_member_is(self):
        elements = discovery.resolve_required_elements(
            layout(
                [
                    {
                        "artefact_kind": "notes artefact",
                        "content_properties": [],
                        "content_signature": "notes artefact body",
                    }
                ]
            ),
            MEMBERS,
        )
        self.assertEqual(elements[0]["located_member"], "notes.txt")
        self.assertEqual(elements[0]["route"], "content signature")

    def test_citation_route_locates_by_a_ledger_citation(self):
        members = [dict(member) for member in MEMBERS]
        members[2] = dict(
            members[2], name="artefact-9.txt", cited_by=["ledger:step-record"]
        )
        elements = discovery.resolve_required_elements(
            layout(
                [
                    {
                        "artefact_kind": "step record",
                        "content_properties": [],
                        "citations": ["ledger:step-record"],
                    }
                ]
            ),
            members,
        )
        self.assertEqual(elements[0]["located_member"], "artefact-9.txt")
        self.assertIn(elements[0]["route"], ("ledger citation", "step record citation"))

    def test_unlocated_kind_names_the_kind_and_no_member(self):
        elements = discovery.resolve_required_elements(
            layout([{"artefact_kind": "missing kind", "content_properties": []}]),
            MEMBERS,
        )
        self.assertEqual(elements[0]["name"], "missing kind")
        self.assertIsNone(elements[0]["located_member"])

    def test_standings_are_carried_unchanged(self):
        elements = discovery.resolve_required_elements(
            layout([{"artefact_kind": "notes.txt", "content_properties": []}]),
            MEMBERS,
            standings=[
                {
                    "stated_none": True,
                    "missing_sections": ["C"],
                    "disposition": "recorded_gap",
                }
            ],
        )
        self.assertTrue(elements[0]["stated_none"])
        self.assertEqual(elements[0]["missing_sections"], ["C"])
        self.assertEqual(elements[0]["disposition"], "recorded_gap")

    def test_unrecomputable_located_member_stands_unlocated(self):
        members = [
            {
                "name": "notes.txt",
                "content": "The notes artefact body.\n",
                "digest_git_blob_sha1": "0" * 40,
            }
        ]
        elements = discovery.resolve_required_elements(
            layout([{"artefact_kind": "notes.txt", "content_properties": []}]),
            members,
        )
        self.assertIsNone(elements[0]["located_member"])
        self.assertTrue(elements[0]["unidentifiable"])

    def test_resolution_returns_no_determination_or_status(self):
        elements = discovery.resolve_required_elements(
            layout([{"artefact_kind": "notes.txt", "content_properties": []}]),
            MEMBERS,
        )
        for element in elements:
            self.assertNotIn("determination", element)
            self.assertNotIn("exit_status", element)
            self.assertNotIn("verdict", element)

    def test_layout_entry_order_is_kept(self):
        elements = discovery.resolve_required_elements(
            layout(
                [
                    {"artefact_kind": "step-record.txt", "content_properties": []},
                    {"artefact_kind": "links.txt", "content_properties": []},
                ]
            ),
            MEMBERS,
        )
        self.assertEqual(
            [element["name"] for element in elements],
            ["step-record.txt", "links.txt"],
        )


class HasStepsThreadingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def run_layout(self, steps):
        invocation = harness.verdict_invocation(
            self.out,
            scenario={
                "presented_layout": {
                    "artefact_entries": [],
                    "steps": steps,
                },
                "presented_members": [],
            },
        )
        return harness.run_invocation(invocation, self.out)

    def test_empty_denominator_for_a_stage_with_steps_cannot_run(self):
        status = self.run_layout(["step 1", "step 2"])
        self.assertIn(status, (1, 2))
        text = harness.combined_text(self.out)
        self.assertIn("completeness", text)
        self.assertIn("cannot run", text)

    def test_empty_denominator_without_steps_is_no_silent_pass_case(self):
        # With no steps standing, the empty denominator bar does not
        # apply in the form the texts state it; the run completes.
        status = self.run_layout([])
        self.assertEqual(status, 0)


if __name__ == "__main__":
    unittest.main()
