"""Step 14 cure wave 1 pinning tests, added on the fix register's authority.

Each test class pins one triaged finding of design/steps/
step-14-fix-register.md, written test first: the test was run red
against the code as it stood before its finding's cure, and the
cure in the same commit turned it green. Classes land in register
order: T14-03, T14-04, T14-05, T14-08, T14-12.

Scenario keys used here, beside the harness's own: pinning_record,
a mapping in the SH-44 field names presenting the pinning record
the operator supplied for the freeze; context_claim, a mapping
with digest_algorithm and canonical_form presenting the context
record claim the freeze compares against the pin;
standing_rule_versions and outside_standard_versions, lists of
version pairs in the SH-05 item forms presenting the standing
rules and outside standards versions source; gate_record, a
mapping presenting the operator filed gate record state the
freeze reads, with anchor_home naming the anchor home.
"""

import pathlib
import tempfile
import unittest

import harness


class T1403GateRecordAuthorshipTests(unittest.TestCase):
    """T14-03: the checker writes no gate record, in no case."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "out"

    def freeze(self, **overrides):
        invocation = harness.base_invocation(self.out, **overrides)
        return harness.run_intake_freeze(invocation, self.out)

    def test_committed_freeze_produces_no_gate_record_artefact(self):
        result = self.freeze()
        self.assertIsNotNone(result)
        names = [path.name for path in harness.artefacts(self.out)]
        self.assertNotIn("gate-record.txt", names)
        self.assertIsNone(
            harness.artefact_with_signature(self.out, "gate record")
        )

    def test_operator_filed_gate_record_stands_unchanged_by_a_freeze(self):
        self.out.mkdir(parents=True, exist_ok=True)
        operator_text = (
            "gate record\n"
            "intake order: first; receipt digest operator-filed\n"
            "anchor home: operator-anchor-home\n"
        )
        gate_path = self.out / "gate-record.txt"
        gate_path.write_text(operator_text, encoding="utf-8")
        result = self.freeze()
        self.assertIsNotNone(result)
        self.assertEqual(
            gate_path.read_text(encoding="utf-8"), operator_text
        )


PIN = {
    "digest_algorithm": "SHA-512",
    "canonical_form": "CFE-1",
    "checker_version": "checker-1.0.0",
    "successor_ruling_reference": "successor ruling presented for this freeze",
}
RULE_VERSIONS = [{"rule_name": "standing rule alpha", "rule_version": "3"}]
STANDARD_VERSIONS = [
    {"standard_name": "outside standard beta", "standard_version": "7"}
]
MEMBERS = [
    {"name": "alpha.txt", "content": "alpha bytes\n", "source_kind": "handed in material"},
    {"name": "beta.txt", "content": "beta bytes\n", "source_kind": "handed in material"},
]


def core_freeze(**overrides):
    from isolated_checker import freeze

    call = {
        "build": "cure-build",
        "stage": "cure-stage",
        "packet_form_version": "packet-form-1",
        "checker_version": "checker-1.0.0",
        "freeze_time": "2026-11-13T00:00:00Z",
        "pinning_record": dict(PIN),
        "standing_rule_versions": [dict(p) for p in RULE_VERSIONS],
        "outside_standard_versions": [dict(p) for p in STANDARD_VERSIONS],
        "anchor_home": "operator-anchor-home",
        "context_claim": {
            "digest_algorithm": "SHA-512",
            "canonical_form": "CFE-1",
        },
    }
    call.update(overrides)
    return freeze.freeze_intake(
        [dict(m) for m in MEMBERS], [dict(m) for m in MEMBERS], **call
    )


class T1404PinningAndVersionsReadTests(unittest.TestCase):
    """T14-04: freeze reads its pinning and versions; it mints neither."""

    def test_presented_pin_and_versions_stand_in_the_context_record(self):
        result = core_freeze()
        self.assertEqual(result["status"], "frozen")
        context = result["context_record"]
        self.assertEqual(context["digest_algorithm"], "SHA-512")
        self.assertEqual(context["canonical_form"], "CFE-1")
        self.assertEqual(context["standing_rule_versions"], RULE_VERSIONS)
        self.assertEqual(
            context["outside_standard_versions"], STANDARD_VERSIONS
        )
        self.assertEqual(result["pinning_record"]["digest_algorithm"], "SHA-512")
        self.assertEqual(result["anchor_home"], "operator-anchor-home")

    def test_claim_disagreeing_with_the_pin_issues_no_receipt(self):
        result = core_freeze(
            context_claim={
                "digest_algorithm": "SHA-256",
                "canonical_form": "CFE-1",
            }
        )
        self.assertEqual(result["status"], "intake failure")
        self.assertNotIn("receipt", result)

    def test_freeze_without_a_pinning_record_read_issues_no_receipt(self):
        result = core_freeze(pinning_record=None)
        self.assertEqual(result["status"], "intake failure")
        self.assertNotIn("receipt", result)

    def test_shell_consumes_pin_and_versions_presented_as_facts(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = pathlib.Path(tmp.name) / "out"
        invocation = harness.base_invocation(
            out,
            scenario={
                "pinning_record": {
                    "digest_algorithm": "SHA-256",
                    "canonical_form": "CFE-1",
                    "checker_version": "checker-1.0.0",
                    "successor_ruling_reference": None,
                },
                "standing_rule_versions": RULE_VERSIONS,
                "outside_standard_versions": STANDARD_VERSIONS,
            },
        )
        result = harness.run_intake_freeze(invocation, out)
        self.assertIsNotNone(result)
        context = (out / "context-record.txt").read_text(encoding="utf-8")
        self.assertIn("standing rule alpha 3", context)
        self.assertIn("outside standard beta 7", context)

    def test_shell_freeze_on_a_pin_disagreeing_with_the_claim_fails(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = pathlib.Path(tmp.name) / "out"
        invocation = harness.base_invocation(
            out,
            scenario={
                "pinning_record": dict(PIN),
                "context_claim": {
                    "digest_algorithm": "SHA-256",
                    "canonical_form": "CFE-1",
                },
            },
        )
        result = harness.run_intake_freeze(invocation, out)
        self.assertIsNone(result)
        self.assertIn("intake failure", harness.combined_text(out))
        self.assertIsNone(
            harness.artefact_with_signature(out, "custody receipt")
        )


class T1405NoReceiptOverUnrecomputedDigestsTests(unittest.TestCase):
    """T14-05: no receipt over member digests never recomputed."""

    def digest_only_members(self):
        return [
            {
                "name": "ghost.txt",
                "digest_git_blob_sha1": "0" * 40,
                "byte_size": 999,
                "source_kind": "handed in material",
            }
        ]

    def test_core_digest_only_presentation_in_both_passes_issues_no_receipt(self):
        result = core_freeze()
        # core_freeze freezes real members; rebuild the call here
        # on digest only members in both passes.
        from isolated_checker import freeze

        call = {
            "build": "cure-build",
            "stage": "cure-stage",
            "packet_form_version": "packet-form-1",
            "checker_version": "checker-1.0.0",
            "freeze_time": "2026-11-13T00:00:00Z",
            "pinning_record": {
                "digest_algorithm": "SHA-256",
                "canonical_form": "CFE-1",
                "checker_version": "checker-1.0.0",
                "successor_ruling_reference": None,
            },
        }
        result = freeze.freeze_intake(
            self.digest_only_members(),
            self.digest_only_members(),
            **call,
        )
        self.assertEqual(result["status"], "intake failure")
        self.assertNotIn("receipt", result)

    def test_shell_presented_receipt_scenario_issues_no_receipt(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = pathlib.Path(tmp.name) / "out"
        entries = [
            {
                "name": "notes.txt",
                "digest_git_blob_sha1": harness._blob_digest(
                    b"The notes artefact body.\n"
                ),
                "byte_size": len(b"The notes artefact body.\n"),
            }
        ]
        invocation = harness.base_invocation(
            out, scenario={"presented_receipt": entries}
        )
        result = harness.run_intake_freeze(invocation, out)
        self.assertIsNone(result)
        self.assertIn("intake failure", harness.combined_text(out))
        self.assertIsNone(
            harness.artefact_with_signature(out, "custody receipt")
        )

    def test_real_content_member_still_freezes_on_its_recomputed_digest(self):
        result = core_freeze()
        self.assertEqual(result["status"], "frozen")
        digests = {
            entry["member_digest"] for entry in result["receipt"]["members"]
        }
        expected = {
            harness._blob_digest(b"alpha bytes\n"),
            harness._blob_digest(b"beta bytes\n"),
        }
        self.assertEqual(digests, expected)


class T1408Md02SeamTests(unittest.TestCase):
    """T14-08: operation outputs take their CE-2A registered forms."""

    def test_anchor_entry_stands_in_the_sh07_registered_form(self):
        from isolated_checker import shapes

        result = core_freeze()
        self.assertEqual(result["status"], "frozen")
        self.assertEqual(
            result["anchor_entry"],
            {"anchored_receipt_digest": result["receipt_digest"]},
        )
        self.assertEqual(
            set(result["anchor_entry"]), set(shapes.VOCABULARY["SH-07"])
        )
        self.assertIs(
            shapes.validate("SH-07", result["anchor_entry"]),
            result["anchor_entry"],
        )

    def test_intake_failure_record_stands_in_the_sh33_registered_form(self):
        from isolated_checker import freeze, shapes

        members = [{"name": "material that cannot be frozen", "unreadable": True}]
        result = freeze.freeze_intake(
            members,
            members,
            build="cure-build",
            stage="cure-stage",
            packet_form_version="packet-form-1",
            checker_version="checker-1.0.0",
            freeze_time="2026-11-13T00:00:00Z",
            pinning_record={
                "digest_algorithm": "SHA-256",
                "canonical_form": "CFE-1",
                "checker_version": "checker-1.0.0",
                "successor_ruling_reference": None,
            },
        )
        self.assertEqual(result["status"], "intake failure")
        record = result["failure_record"]
        self.assertEqual(set(record), set(shapes.VOCABULARY["SH-33"]))
        self.assertIs(shapes.validate("SH-33", record), record)
        filed = freeze.intake_failure_filed_text(record)
        self.assertIn("intake failure record", filed)
        self.assertIn(record["failure_description"], filed)

    def test_seam_rejects_a_key_in_no_ce2a_row_for_its_shape(self):
        from isolated_checker import shapes
        from isolated_checker.shapes import ShapeError

        with self.assertRaises(ShapeError):
            shapes.validate("SH-07", {"receipt_digest": "a" * 40})
        with self.assertRaises(ShapeError):
            shapes.validate(
                "SH-07",
                {"anchored_receipt_digest": "a" * 40, "anchor_strength": "x"},
            )

    def test_seam_rejects_a_record_missing_a_field_its_shape_states(self):
        from isolated_checker import shapes
        from isolated_checker.shapes import ShapeError

        with self.assertRaises(ShapeError):
            shapes.validate(
                "SH-33",
                {"material_identity_best_available": "material"},
                shapes.VOCABULARY["SH-33"],
            )
        with self.assertRaises(ShapeError):
            shapes.require(
                "SH-07", {}, shapes.VOCABULARY["SH-07"]
            )

    def test_seam_rejects_a_value_of_the_wrong_node_kind(self):
        from isolated_checker import shapes
        from isolated_checker.shapes import ShapeError

        with self.assertRaises(ShapeError):
            shapes.validate("SH-07", {"anchored_receipt_digest": 1.5})


class T1412PinningHomeAndReceiptRendererTests(unittest.TestCase):
    """T14-12: one home for SH-44 construction, one receipt renderer."""

    def test_pinning_record_is_built_in_its_md02_home_not_in_canonical(self):
        from isolated_checker import canonical, pinning
        import isolated_checker

        self.assertFalse(hasattr(canonical, "pinning_record"))
        record = pinning.pinning_record(
            "SHA-256", "CFE-1", "checker-1.0.0"
        )
        self.assertEqual(
            record,
            {
                "digest_algorithm": "SHA-256",
                "canonical_form": "CFE-1",
                "checker_version": "checker-1.0.0",
                "successor_ruling_reference": None,
            },
        )
        self.assertIs(isolated_checker.pinning_record, pinning.pinning_record)
        # The digest duty stays in the canonical core, at MD-01.
        self.assertEqual(
            canonical.pinning_citation_digest(record),
            canonical.record_digest("SH-44", record),
        )

    def test_the_shell_has_no_receipt_renderer_of_its_own(self):
        from isolated_checker import intake

        self.assertFalse(hasattr(intake, "_receipt_filed_text"))

    def test_filed_receipt_text_is_the_one_renderers_text(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = pathlib.Path(tmp.name) / "out"
        invocation = harness.base_invocation(out)
        result = harness.run_intake_freeze(invocation, out)
        self.assertIsNotNone(result)
        filed = (out / "custody-receipt.txt").read_text(encoding="utf-8")
        from isolated_checker import receipts

        names = {"example-member.txt"}
        self.assertTrue(filed.startswith("custody receipt\n"))
        self.assertIn("example-member.txt", filed)
        # The same renderer, given the record the core issued for
        # the same inputs at the filed freeze time, produces the
        # filed text exactly: one renderer, one form.
        from isolated_checker import freeze

        freeze_time = [
            line.split(": ", 1)[1]
            for line in filed.splitlines()
            if line.startswith("freeze time:")
        ][0]
        core = freeze.freeze_intake(
            [
                {
                    "name": "example-member.txt",
                    "content": "Example packet member, labelled as an example.\n",
                    "source_kind": "example packet",
                }
            ],
            [
                {
                    "name": "example-member.txt",
                    "content": "Example packet member, labelled as an example.\n",
                    "source_kind": "example packet",
                }
            ],
            build="isolated-checker-test-build",
            stage="step-gate-1",
            packet_form_version="packet-form-1",
            checker_version="checker-1.0.0",
            freeze_time=freeze_time,
            pinning_record={
                "digest_algorithm": "SHA-256",
                "canonical_form": "CFE-1",
                "checker_version": "checker-1.0.0",
                "successor_ruling_reference": None,
            },
        )
        self.assertEqual(core["status"], "frozen")
        rendered = receipts.receipt_filed_text(
            core["receipt"],
            {
                r["digest_git_blob_sha1"]: r["name"]
                for r in core["members"]
            },
        )
        self.assertEqual(filed, rendered)
        self.assertEqual(names, {"example-member.txt"})


if __name__ == "__main__":
    unittest.main()
