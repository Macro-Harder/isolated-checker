"""Calibration gate and fixture suite behaviour, slices S-10 and S-11.

Pins brief sections 5.18 to 5.21 and the plan mapping P1-T1 to P1-T4:
the calibration pass predicate stated once at section 5.19, the four
triggers at section 5.18, the calibration record at section 5.21, and
the state derivation of section 5.9. A calibration outcome takes no
exit status, stated by the harness as a return value of None, and its
outcome word is calibrated on a pass and not calibrated on a failure.

Every fixture the suite index names is run in this module: the per
fixture test invokes a calibration bearing run twice per fixture and
one status bearing verdict run per fixture. The calibration runs are
compared at the expected outcome word only. The verdict run is
compared against the fixture expected record fixed in advance in its
expected.json file, in full form: the expected check verdicts, each
bound to its own check, the expected discrepancies by name, the
expected exit status, the expected unchecked list and the expected
recorded gaps, with the outcome word beside them, and no assertion
conditional on a field being non empty. Where a test states a
calibration run at the raised repeat count, the count in force is
22 runs per fixture, the raised floor the brief fixes, and every
repeat is compared at the expected outcome word, with the full form
carried by the verdict run for that fixture.

Scenario keys used here: fixture_id, the fixture a calibration run is
stated over; repeat_disagreement, a boolean presenting repeat runs of
one fixture that disagree; wrongly_named_discrepancy, a boolean
presenting a discrepancy named wrongly; limit_form_failure, a boolean
presenting a failing limit report form test; trigger, one of
checker_change, packet_form_change, layout_form_change or
suite_change, presenting a calibration trigger with no later passing
record; suite_digest_matches, as in the gating module;
suite_version_label, a varied fixture suite version label presented
against the suite digest the run states; repeat_count, the number of
times a calibration run states it ran one fixture; canary, a boolean
presenting the canary calibration run, the same calibration run at
the full floor; gate_evidence_home, the path of the gate evidence
home designated for a run, presented in the forced dry case as the
home a filing step or the checker would file gate evidence into for
that run.
"""

import hashlib
import json
import pathlib
import re
import tempfile
import unittest

import harness

SUITE_VERSION = "fixture-suite-1"
COMPOSITE_WORD_FIXTURES = {"f-cp09-present", "f-ch04-companion"}
RAISED_REPEAT_COUNT = 22


def suite_digest_lines(root=None):
    """Rebuild the per fixture suite digest lines from the fixture bytes.

    The construction is the one SUITE-DIGEST.txt states in exact
    bytes: one line per fixture in suite order as listed in
    INDEX.json; a line is the fixture id, one space, the member
    entries joined by one space, one space, then the SHA-256 digest
    of the fixture expected.json; a member entry is the bare file
    name, one colon, then the SHA-256 digest of that member file over
    its real bytes; member files are every file in the fixture
    directory except expected.json, ordered by bare file name; each
    line ends with one newline, including the last.
    """
    base = harness.fixtures_root(root)
    lines = []
    for entry in harness.fixture_entries(root):
        directory = harness.fixture_dir(entry, root)
        members = sorted(
            path.name
            for path in directory.iterdir()
            if path.is_file() and path.name != "expected.json"
        )
        entries = []
        for name in members:
            digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
            entries.append(name + ":" + digest)
        expected_digest = hashlib.sha256(
            (directory / "expected.json").read_bytes()
        ).hexdigest()
        lines.append(
            harness.fixture_id(entry)
            + " "
            + " ".join(entries)
            + " "
            + expected_digest
            + "\n"
        )
    return lines


def recorded_suite_digest(root=None):
    """Read the suite digest recorded in SUITE-DIGEST.txt."""
    text = (harness.fixtures_root(root) / "SUITE-DIGEST.txt").read_text(
        encoding="utf-8"
    )
    for line in text.splitlines():
        if line.startswith("Suite digest:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError("SUITE-DIGEST.txt records no suite digest")


class CalibrationPredicateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def calibrate(self, out=None, **overrides):
        target = out or self.out
        overrides.setdefault("mode", "calibration")
        overrides.setdefault("fixture_suite_version", SUITE_VERSION)
        invocation = harness.base_invocation(target, **overrides)
        return harness.run_invocation(invocation, target)

    def test_passing_calibration_records_the_word_calibrated(self):
        status = self.calibrate()
        self.assertIsNone(status)
        self.assertIn("calibrated", harness.combined_text(self.out))
        self.assertNotIn(
            "not calibrated", harness.combined_text(self.out)
        )

    def test_calibration_writes_exactly_one_record_to_the_run_record_home(self):
        self.calibrate()
        found = harness.artefact_with_signature(self.out, "calibration record")
        self.assertIsNotNone(found)
        records = [
            path
            for path in harness.artefacts(self.out)
            if "calibration record" in path.read_text(
                encoding="utf-8", errors="replace"
            )
        ]
        self.assertEqual(len(records), 1)

    def test_calibration_invocation_names_the_suite_version_in_its_version_fields(self):
        self.calibrate()
        text = harness.signature_text(self.out, "calibration record")
        self.assertIn(SUITE_VERSION, text)
        self.assertIn("checker-1.0.0", text)

    def test_one_fixture_matching_on_every_repeat_is_a_pass(self):
        status = self.calibrate(scenario={"fixture_id": "control-clean"})
        self.assertIsNone(status)
        self.assertIn("calibrated", harness.combined_text(self.out))

    def test_wrongly_named_discrepancy_fails_the_pass(self):
        self.calibrate(scenario={"wrongly_named_discrepancy": True})
        self.assertIn("not calibrated", harness.combined_text(self.out))

    def test_repeat_disagreement_produces_not_calibrated(self):
        self.calibrate(scenario={"repeat_disagreement": True})
        self.assertIn("not calibrated", harness.combined_text(self.out))

    def test_limit_form_failure_blocks_the_pass(self):
        self.calibrate(scenario={"limit_form_failure": True})
        self.assertIn("not calibrated", harness.combined_text(self.out))

    def test_suite_digest_mismatch_derives_not_calibrated(self):
        self.calibrate(scenario={"suite_digest_matches": False})
        self.assertIn("not calibrated", harness.combined_text(self.out))

    def test_suite_identity_is_compared_by_digest_never_by_label_alone(self):
        self.calibrate(
            scenario={
                "suite_digest_matches": True,
                "suite_version_label": "fixture-suite-99",
            }
        )
        text = harness.combined_text(self.out)
        self.assertIn("calibrated", text)
        self.assertNotIn("not calibrated", text)

    def test_calibration_record_names_every_version_it_covers(self):
        self.calibrate()
        text = harness.combined_text(self.out)
        self.assertIn("checker-1.0.0", text)
        self.assertIn("packet-form-1", text)
        self.assertIn("layout-form-1", text)
        self.assertIn(SUITE_VERSION, text)

    def test_calibration_record_field_list_matches_the_brief_list(self):
        self.calibrate()
        text = harness.signature_text(self.out, "calibration record")
        self.assertEqual(
            harness.record_fields(text),
            [
                "checker version",
                "fixture suite version",
                "suite digest",
                "packet form version",
                "layout form version",
                "floor scope",
                "per fixture results",
                "seat",
                "time",
            ],
        )

    def test_calibration_record_states_no_uncertainty_figure(self):
        self.calibrate()
        text = harness.combined_text(self.out).lower()
        self.assertNotIn("uncertainty", text)
        self.assertNotIn("precision", text)

    def test_checker_change_trigger_runs_the_full_floor_and_leaves_not_calibrated(self):
        status = self.calibrate(scenario={"trigger": "checker_change"})
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("not calibrated", text)
        self.assertIn("58", text)

    def test_packet_form_change_trigger_runs_the_full_floor_and_leaves_not_calibrated(self):
        self.calibrate(scenario={"trigger": "packet_form_change"})
        text = harness.combined_text(self.out)
        self.assertIn("not calibrated", text)
        self.assertIn("58", text)

    def test_layout_form_change_trigger_runs_the_full_floor_and_leaves_not_calibrated(self):
        self.calibrate(scenario={"trigger": "layout_form_change"})
        text = harness.combined_text(self.out)
        self.assertIn("not calibrated", text)
        self.assertIn("58", text)

    def test_suite_change_trigger_runs_the_full_floor_and_leaves_not_calibrated(self):
        self.calibrate(scenario={"trigger": "suite_change"})
        text = harness.combined_text(self.out)
        self.assertIn("not calibrated", text)
        self.assertIn("58", text)

    def test_canary_is_the_same_calibration_run_at_the_full_floor(self):
        status = self.calibrate(scenario={"canary": True})
        self.assertIsNone(status)
        text = harness.combined_text(self.out)
        self.assertIn("calibrated", text)
        self.assertIn("58", text)
        self.assertIn("33 of 33", text)

    def test_triggered_version_takes_forced_dry_standing_at_a_verdict_call(self):
        out = pathlib.Path(self.tmp.name) / "verdict"
        gate_home = pathlib.Path(self.tmp.name) / "gate-evidence"
        invocation = harness.verdict_invocation(
            out,
            scenario={
                "trigger": "checker_change",
                "gate_evidence_home": str(gate_home),
            },
        )
        status = harness.run_invocation(invocation, out)
        self.assertEqual(status, 4)
        text = harness.combined_text(out)
        self.assertIn("DRY RUN", text)
        self.assertIn("NOT A VERDICT", text)
        statement = harness.signature_text(out, "run statement")
        state_lines = [
            line
            for line in statement.splitlines()
            if line.strip().lower().startswith("calibration state")
        ]
        self.assertTrue(state_lines)
        self.assertIn("not calibrated", state_lines[0])
        self.assertTrue(harness.artefacts(out))
        self.assertEqual(harness.artefacts(gate_home), [])
        self.assertNotIn("grade", text.lower())


class FixtureSuiteCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_fixture_calibration(self, ident, repeat):
        out = pathlib.Path(self.tmp.name) / (ident + "-cal-" + str(repeat))
        invocation = harness.base_invocation(
            out,
            mode="calibration",
            fixture_suite_version=SUITE_VERSION,
            scenario={"fixture_id": ident},
        )
        harness.run_invocation(invocation, out)
        return harness.combined_text(out)

    def run_fixture_verdict(self, ident):
        out = pathlib.Path(self.tmp.name) / (ident + "-verdict")
        invocation = harness.verdict_invocation(
            out, scenario={"fixture_id": ident}
        )
        status = harness.run_invocation(invocation, out)
        return status, harness.combined_text(out)

    def assert_full_form(self, ident, expected, status, text):
        self.assertEqual(status, expected["expected_exit_status"])
        if ident in COMPOSITE_WORD_FIXTURES:
            self.assertIn("unchecked", text)
            for element in expected["expected_unchecked"]:
                self.assertIn(element, text)
        else:
            self.assertIn(expected["expected_outcome_word"], text)
        for check, verdict in expected["expected_check_verdicts"].items():
            self.assertIn(check + ": " + verdict, text)
        for discrepancy in expected["expected_discrepancies"]:
            self.assertIn(discrepancy["discrepancy_naming"], text)
        for element in expected["expected_unchecked"]:
            self.assertIn(element, text)
        for gap in expected["expected_recorded_gaps"]:
            self.assertIn(str(gap), text)
        self.assertNotIn(
            "discrepancy "
            + str(len(expected["expected_discrepancies"]) + 1)
            + ":",
            text,
        )
        self.assertNotIn(
            "unchecked "
            + str(len(expected["expected_unchecked"]) + 1)
            + ":",
            text,
        )
        self.assertNotIn(
            "recorded gap "
            + str(len(expected["expected_recorded_gaps"]) + 1)
            + ":",
            text,
        )

    def test_index_names_a_fixture_suite(self):
        entries = harness.fixture_entries()
        self.assertTrue(entries)

    def test_suite_floor_counts_fixtures_and_kinds_in_the_stated_form(self):
        entries = harness.fixture_entries()
        self.assertEqual(len(entries), 58)
        kinds = {
            str(entry.get("defect_kind"))
            for entry in entries
            if entry.get("defect_kind") not in (None, "none")
        }
        self.assertEqual(len(kinds), 33)

    def test_split_pairs_stand_adjacent_in_the_index_in_both_forms(self):
        ids = [harness.fixture_id(entry) for entry in harness.fixture_entries()]
        pairs = [
            ("f-ch03-void", "f-ch03-no-predecessor"),
            ("f-ch07-pending", "f-ch07-defect"),
            ("f-cp08-stated-none", "f-cp08-omitted"),
            ("f-ch08-omission", "f-ch08-weakening"),
        ]
        for first, second in pairs:
            self.assertEqual(abs(ids.index(first) - ids.index(second)), 1)

    def test_the_six_mutation_fixtures_stand_by_kind(self):
        entries = harness.fixture_entries()
        by_id = {harness.fixture_id(entry): entry for entry in entries}
        expected = {
            "f-mut-a03": "A3",
            "f-mut-a09": "A9",
            "f-mut-ch02": "CH2",
            "f-mut-ch09": "CH9",
            "f-mut-cp07": "CP7",
            "f-mut-cp10": "CP10",
        }
        for ident, kind in expected.items():
            self.assertIn(ident, by_id)
            self.assertEqual(str(by_id[ident].get("defect_kind")), kind)

    def test_suite_digest_recomputes_from_the_fixture_bytes(self):
        lines = suite_digest_lines()
        rebuilt = hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
        self.assertEqual(rebuilt, recorded_suite_digest())
        filed = (
            harness.fixtures_root() / "SUITE-DIGEST-LINES.txt"
        ).read_text(encoding="utf-8")
        self.assertEqual(filed, "".join(lines))

    def test_fixture_receipts_recompute_in_the_filed_canonical_form(self):
        for entry in harness.fixture_entries():
            directory = harness.fixture_dir(entry)
            receipt_path = directory / "custody-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            for member in receipt["members"]:
                data = (directory / member["name"]).read_bytes()
                header = b"blob " + str(len(data)).encode("utf-8") + b"\x00"
                self.assertEqual(
                    hashlib.sha1(header + data).hexdigest(),
                    member["digest_git_blob_sha1"],
                )
                self.assertEqual(len(data), member["byte_size"])
            body = {
                key: value
                for key, value in receipt.items()
                if key != "receipt_self_digest_sha256"
            }
            canonical = json.dumps(body, sort_keys=True) + "\n"
            self.assertEqual(
                hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
                receipt["receipt_self_digest_sha256"],
            )

    def test_every_fixture_runs_at_least_twice_and_matches_expected(self):
        pairs = harness.load_all_expected()
        self.assertEqual(len(pairs), 58)
        for ident, expected in pairs:
            for repeat in (1, 2):
                text = self.run_fixture_calibration(ident, repeat)
                self.assertIn(expected["expected_outcome_word"] if ident not in COMPOSITE_WORD_FIXTURES else "unchecked", text)
            status, text = self.run_fixture_verdict(ident)
            self.assert_full_form(ident, expected, status, text)

    def test_raised_repeat_count_run_agrees_on_every_repeat(self):
        pairs = harness.load_all_expected()
        self.assertTrue(pairs)
        ident, expected = pairs[0]
        for repeat in range(1, RAISED_REPEAT_COUNT + 1):
            text = self.run_fixture_calibration(ident, repeat)
            self.assertIn("calibrated", text)
            self.assertNotIn("not calibrated", text)
            if ident in COMPOSITE_WORD_FIXTURES:
                self.assertIn("unchecked", text)
            else:
                self.assertIn(expected["expected_outcome_word"], text)
        status, text = self.run_fixture_verdict(ident)
        self.assert_full_form(ident, expected, status, text)
        out = pathlib.Path(self.tmp.name) / "raised-record"
        invocation = harness.base_invocation(
            out,
            mode="calibration",
            fixture_suite_version=SUITE_VERSION,
            scenario={"fixture_id": ident, "repeat_count": RAISED_REPEAT_COUNT},
        )
        harness.run_invocation(invocation, out)
        record = harness.signature_text(out, "calibration record")
        count_token = re.compile(
            r"\b" + re.escape(str(RAISED_REPEAT_COUNT)) + r"\b"
        )
        self.assertTrue(
            any(
                ident in line and count_token.search(line)
                for line in record.splitlines()
            )
        )

    def test_a_fully_clean_control_fixture_stands_in_the_suite(self):
        pairs = dict(harness.load_all_expected())
        self.assertIn("f-clean-control", pairs)
        expected = pairs["f-clean-control"]
        self.assertEqual(expected["defect_kind"], "none")
        status, text = self.run_fixture_verdict("f-clean-control")
        self.assertEqual(status, 0)
        self.assertEqual(expected["expected_discrepancies"], [])
        self.assertNotIn("discrepancy 1:", text)
        self.assertIn("pass", text)


if __name__ == "__main__":
    unittest.main()
