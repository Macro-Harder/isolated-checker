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
from isolated_checker import canonical, checks, receipts

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


if __name__ == "__main__":
    unittest.main()
