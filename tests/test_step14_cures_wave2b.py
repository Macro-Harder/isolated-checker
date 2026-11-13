"""Step 14 cure wave 2b pinning tests, added on the fix register's authority.

Each test class pins one triaged finding of design/steps/
step-14-fix-register.md, written test first: the test was run red
against the code as it stood before its finding's cure, and the
cure in the same commit turned it green. Classes land in register
order: T14-16, T14-17, T14-18, T14-20.
"""

import ast
import pathlib
import subprocess
import sys
import unittest

import isolated_checker as ic
from isolated_checker import canonical, checks, receipts, seal
from isolated_checker.reading import ReadingCounter
from isolated_checker.shapes import ShapeError

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
PACKAGE = REPO_ROOT / "isolated_checker"

MEMBERS = {
    "links.txt": "Link 1 names notes.txt for Seat Alpha.\n",
    "notes.txt": "The notes artefact body.\n",
    "step-record.txt": "Step record sections 1 to 3.\n",
}


def member_list(members=MEMBERS):
    return [
        {"name": name, "content": members[name]} for name in sorted(members)
    ]


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


def import_targets(tree):
    """Every module an import statement in the tree names, at any depth."""
    targets = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            targets.append(node.module or "")
            targets.extend(alias.name for alias in node.names)
    return targets


def nested_imports(tree):
    """Import statements standing below module level in the tree."""
    top = {id(node) for node in tree.body}
    found = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)) and id(node) not in top:
            found.append(node)
    return found


CONSUMERS = ("authenticity", "chain", "completeness")


class T1416NoImportCycleTests(unittest.TestCase):
    """T14-16: checks.py imports none of its consumers, in any position."""

    def checks_tree(self):
        return ast.parse((PACKAGE / "checks.py").read_text(encoding="utf-8"))

    def test_checks_module_imports_none_of_the_three_check_modules(self):
        targets = import_targets(self.checks_tree())
        for name in CONSUMERS:
            self.assertNotIn(name, targets)
            self.assertNotIn("isolated_checker." + name, targets)

    def test_no_import_below_module_level_in_the_check_family(self):
        for filename in (
            "checks.py",
            "authenticity.py",
            "chain.py",
            "completeness.py",
            "checks_runner.py",
        ):
            path = PACKAGE / filename
            self.assertTrue(path.exists(), filename)
            tree = ast.parse(path.read_text(encoding="utf-8"))
            self.assertEqual(nested_imports(tree), [], filename)

    def test_each_check_module_still_consumes_the_shared_machinery(self):
        for name in CONSUMERS:
            tree = ast.parse(
                (PACKAGE / (name + ".py")).read_text(encoding="utf-8")
            )
            top_level = [
                node
                for node in tree.body
                if isinstance(node, (ast.Import, ast.ImportFrom))
            ]
            self.assertTrue(top_level, name)
            self.assertIn("checks", import_targets(ast.Module(body=top_level, type_ignores=[])))
        self.assertTrue(callable(checks.check_result))
        self.assertTrue(callable(checks.discrepancy_entry))

    def test_the_runner_stands_in_no_part_of_checks_module(self):
        self.assertFalse(hasattr(checks, "run_all_checks"))

    def test_runner_home_depends_on_machinery_and_all_three_checks(self):
        tree = ast.parse((PACKAGE / "checks_runner.py").read_text(encoding="utf-8"))
        targets = import_targets(tree)
        self.assertIn("checks", targets)
        for name in CONSUMERS:
            self.assertIn(name, targets)

    def test_runner_runs_the_three_checks_in_r80_order_over_one_counter(self):
        from isolated_checker import checks_runner

        self.assertIs(ic.run_all_checks, checks_runner.run_all_checks)
        result = checks_runner.run_all_checks(
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

    def test_package_loads_in_every_check_family_import_order(self):
        for first in ("checks", "authenticity", "chain", "completeness", "checks_runner"):
            proc = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import isolated_checker." + first + "\n"
                    "import isolated_checker\n"
                    "print(isolated_checker.run_all_checks is not None)",
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, first + ": " + proc.stderr)
            self.assertIn("True", proc.stdout)


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


def run_seal(receipt, members=MEMBERS, **kwargs):
    kwargs.setdefault("anchor_entry", receipts.anchor_entry(receipt["self_digest"]))
    kwargs.setdefault(
        "intake_order",
        [seal.intake_order_item(1, receipt["self_digest"])],
    )
    return seal.check_seal(
        receipt=receipt,
        members=member_list(members),
        receipt_member_names=sorted(members),
        **kwargs,
    )


class T1417InvocationComparisonsTests(unittest.TestCase):
    """T14-17: no run outcome words from MD-05; one outcome source."""

    def compare(self, **overrides):
        values = dict(
            invocation_layout_digest="sha256:aa",
            layout_read_digest="sha256:aa",
            invocation_layout_version="layout-1",
            layout_read_version="layout-1",
            invocation_packet_form_version="packet-form-1",
            context_packet_form_version="packet-form-1",
            layout_as_used_digest="sha256:aa",
            layout_as_used_version="layout-1",
            run_checker_version="checker-1.0",
            invocation_checker_version="checker-1.0",
        )
        values.update(overrides)
        return checks.invocation_comparisons(**values)

    def test_mismatch_returns_the_comparison_in_md05_terms_only(self):
        failures = self.compare(layout_read_digest="sha256:bb")
        self.assertEqual(len(failures), 1)
        self.assertEqual(
            failures[0],
            {
                "comparison": "layout digest comparison",
                "invocation_value": "sha256:aa",
                "read_value": "sha256:bb",
            },
        )

    def test_no_outcome_word_stands_on_any_mismatch(self):
        mismatches = [
            {"layout_read_digest": "sha256:bb"},
            {"layout_read_version": "layout-2"},
            {"context_packet_form_version": "packet-form-2"},
            {"layout_as_used_digest": "sha256:cc"},
            {"layout_as_used_version": "layout-3"},
            {"run_checker_version": "checker-9.9.9"},
        ]
        for overrides in mismatches:
            failures = self.compare(**overrides)
            self.assertEqual(len(failures), 1, overrides)
            failure = failures[0]
            self.assertEqual(
                set(failure), {"comparison", "invocation_value", "read_value"}
            )
            self.assertNotIn("outcome_word", failure)
            self.assertNotIn("determination_supported", failure)
            for word in (
                checks.OUTCOME_CUSTODY_GAP,
                checks.OUTCOME_PARTIAL,
                checks.OUTCOME_UNVERIFIABLE,
            ):
                self.assertNotIn(word, failure.values())

    def test_matching_invocation_compares_clean(self):
        self.assertEqual(self.compare(), [])

    def test_signature_takes_no_support_or_outcome_inputs(self):
        import inspect

        params = set(inspect.signature(checks.invocation_comparisons).parameters)
        for name in (
            "determination_supported",
            "remaining_support",
            "invocation_build",
            "invocation_stage",
            "receipt_build",
            "receipt_stage",
        ):
            self.assertNotIn(name, params)

    def test_function_source_names_no_outcome_word_and_no_build_stage_pair(self):
        import inspect

        source = inspect.getsource(checks.invocation_comparisons)
        self.assertNotIn("outcome_word", source)
        self.assertNotIn("OUTCOME_", source)
        self.assertNotIn("receipt build", source)
        self.assertNotIn("receipt stage", source)
        self.assertNotIn("determination_supported", source)
        self.assertNotIn("remaining_support", source)

    def test_build_and_stage_pairs_stand_in_the_seals_home_only(self):
        checks_source = (PACKAGE / "checks.py").read_text(encoding="utf-8")
        self.assertNotIn("receipt build comparison", checks_source)
        self.assertNotIn("receipt stage comparison", checks_source)
        self.assertEqual(
            seal.COMPARISON_BUILD_STAGE, "receipt build and stage comparison"
        )

    def test_seal_takes_a_build_mismatch_at_its_one_comparison(self):
        result = run_seal(build_receipt(), invocation_build="another-build")
        self.assertEqual(result["status"], "broken seal")
        self.assertEqual(result["exit_status"], 1)
        self.assertEqual(
            result["failed_comparisons"], [seal.COMPARISON_BUILD_STAGE]
        )
        entry = result["discrepancy_entries"][0]
        self.assertEqual(entry["discrepancy_category"], "custody gap")
        self.assertEqual(
            entry["governing_element_reference"], seal.COMPARISON_BUILD_STAGE
        )


class T1418SubjectlessReceiptTests(unittest.TestCase):
    """T14-18: a receipt with no self digest takes the emission at 2."""

    def assert_subjectless_emission(self, result):
        self.assertEqual(result["status"], "broken seal")
        self.assertEqual(result["outcome_word"], "custody gap")
        self.assertEqual(result["exit_status"], 2)
        self.assertFalse(result["determination_supported"])
        self.assertFalse(result["receipt_recomputes"])
        self.assertIsNone(result["receipt_digest"])
        self.assertEqual(
            result["failed_comparisons"], [seal.COMPARISON_RECEIPT_RECOMPUTATION]
        )
        report = result["report"]
        self.assertIsNone(report["custody_receipt_digest"])
        self.assertIsNone(report["authenticity_verdict"])
        self.assertIsNone(report["chain_verdict"])
        self.assertIsNone(report["completeness_verdict"])
        self.assertEqual(report["discrepancy_list"], result["discrepancy_entries"])
        self.assertEqual(len(result["discrepancy_entries"]), 1)
        entry = result["discrepancy_entries"][0]
        self.assertEqual(entry["entry_number"], 1)
        self.assertEqual(entry["check"], "chain")
        self.assertEqual(entry["discrepancy_category"], "custody gap")
        self.assertIsNone(entry["defect_kind_code"])
        self.assertEqual(
            entry["governing_element_reference"],
            seal.COMPARISON_RECEIPT_RECOMPUTATION,
        )
        self.assertEqual(
            entry["root_cause_key"], "chain:receipt recomputation:custody gap"
        )
        self.assertEqual(
            entry["subject_identification"],
            {
                "identification_form": "unidentifiable",
                "digest": None,
                "receipt_position": None,
            },
        )

    def test_receipt_with_no_self_digest_key_takes_status_2(self):
        receipt = build_receipt()
        del receipt["self_digest"]
        result = seal.check_seal(
            receipt=receipt,
            members=member_list(),
            receipt_member_names=sorted(MEMBERS),
        )
        self.assert_subjectless_emission(result)

    def test_empty_receipt_takes_status_2(self):
        result = seal.check_seal(receipt={}, members=[])
        self.assert_subjectless_emission(result)

    def test_absent_valued_self_digest_takes_status_2(self):
        receipt = dict(build_receipt(), self_digest=None)
        result = seal.check_seal(
            receipt=receipt,
            members=member_list(),
            receipt_member_names=sorted(MEMBERS),
        )
        self.assert_subjectless_emission(result)

    def test_filed_text_renders_for_a_subjectless_receipt(self):
        receipt = build_receipt()
        del receipt["self_digest"]
        result = seal.check_seal(receipt=receipt, members=member_list())
        text = seal.seal_break_filed_text(result)
        self.assertIn("receipt recomputation", text)
        self.assertIn("exit status: 2", text)
        self.assertIn("verdict: no verdict issued", text)

    def test_subjectless_entry_stands_directly_in_its_form(self):
        entry = seal.custody_gap_entry(
            1, seal.COMPARISON_RECEIPT_RECOMPUTATION, None, None, None
        )
        self.assertEqual(
            entry["subject_identification"]["identification_form"],
            "unidentifiable",
        )
        self.assertEqual(
            entry["root_cause_key"], "chain:receipt recomputation:custody gap"
        )

    def test_present_but_wrong_digest_keeps_its_pinned_behaviour(self):
        receipt = dict(
            build_receipt(), self_digest=canonical.raw_digest(b"forged")
        )
        result = run_seal(
            receipt, anchor_entry=receipts.anchor_entry(receipt["self_digest"])
        )
        self.assertEqual(result["exit_status"], 2)
        self.assertEqual(
            result["failed_comparisons"], [seal.COMPARISON_RECEIPT_RECOMPUTATION]
        )
        entry = result["discrepancy_entries"][0]
        self.assertEqual(
            entry["subject_identification"]["identification_form"], "digest"
        )
        self.assertEqual(
            entry["subject_identification"]["digest"], receipt["self_digest"]
        )
        self.assertEqual(
            result["report"]["custody_receipt_digest"], receipt["self_digest"]
        )

    def test_subjectless_guard_stands_for_the_other_comparisons(self):
        for comparison in (
            seal.COMPARISON_MEMBER_DIGEST,
            seal.COMPARISON_MEMBER_PRESENCE,
            seal.COMPARISON_ANCHOR,
            seal.COMPARISON_BUILD_STAGE,
            seal.COMPARISON_SEQUENCE,
        ):
            with self.assertRaises(ShapeError):
                seal.custody_gap_entry(1, comparison, None, None, None)


if __name__ == "__main__":
    unittest.main()
