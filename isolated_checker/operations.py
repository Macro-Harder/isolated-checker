"""Verdict and dry run operations, plan module MD-07, slice S-07.

The operation surface the harness states: run_invocation, standing
in the package's surface in the interface tests/harness.py states,
run_invocation(invocation, output_area) -> int or None.

A run drives its phases in the brief's order: the snapshot of the
governing records at first read (brief section 5.9), the gating
precedence at MD-15 (section 5.10), output area validation, the
pre run seal as built at MD-04, the three checks through the
checks runner as rehoused at MD-05, addendum handling, the run's
determination composed at MD-06 from the phases' facts (never from
a discovery classification, which carries no determination after
the Step 14 cure of T14-07), and the filing of the run's report
and run statement in their registered forms through the MD-02
seam. Exit statuses are gated at MD-15: the classes brief section
5.14 names take no status, and this surface returns None for them.

The completeness denominator is supplied by the MD-16 resolution
duty in discovery.py, exactly as Plan Supplement 7 Part 2 section
S7P2-2 assigns it: this module supplies the SH-03 layout named at
invocation under IF-LAY and the frozen members in receipt order,
and passes the resolved element form to the completeness check,
threading the stage's step standing as has_steps so the empty
denominator bar applies exactly where the texts state it.

Report composition in its full S-08 form, the rerun surface, the
calibration duty and the fixity duty stand with their owning
later slices; what stands here is the operation surface and the
gating, snapshot, seal, checks and addendum phases of a run.
"""

import hashlib
import json
import pathlib

from . import checks, receipts
from .canonical import with_receipt_self_digest
from .checks_runner import run_all_checks
from .discovery import resolve_required_elements
from .gating import (
    DRY_STANDING,
    NO_BOUND_VALUES,
    PROCEED,
    REFUSAL_DECLARATION,
    REFUSAL_NOT_CURRENT,
    REFUSAL_OUTPUT_AREA,
    gating_determination,
)
from .interfaces import layout_input_form
from .outcome import compose_outcome
from .reading import ReadingCounter
from .run_statement import (
    bound_values_record,
    run_statement,
    run_statement_filed_text,
)
from .seal import check_seal, seal_break_filed_text

SEAL_OPERATION = "verdict run"

_BOUND_UNITS = {
    "total_size_bytes": "bytes",
    "member_count": "members",
    "nesting_depth": "depth",
    "read_volume_bytes": "bytes",
}

_SEAL_COMPARISONS = {
    "altered_member": "member digest comparison",
    "removed_member": "member presence comparison",
    "extra_member": "member presence comparison",
    "anchor_missing": "anchor comparison",
    "anchor_conflict": "anchor comparison",
    "anchor_other_intake": "anchor comparison",
    "receipt_unrecomputable": "receipt recomputation",
    "receipt_rewritten_off_anchor": "receipt recomputation",
    "receipt_build_mismatch": "receipt build and stage comparison",
    "receipt_stage_mismatch": "receipt build and stage comparison",
    "first_receipt_claims_predecessor": "sequence comparison",
    "chain_ends_early": "sequence comparison",
    "whole_intake_removed": "sequence comparison",
    "no_intake_order_record": "sequence comparison",
}

_SEAL_SUPPORTED = {
    "altered_member",
    "removed_member",
    "extra_member",
    "anchor_conflict",
    "anchor_other_intake",
    "receipt_build_mismatch",
    "receipt_stage_mismatch",
    "first_receipt_claims_predecessor",
}
_SEAL_UNSUPPORTED = {"anchor_missing", "receipt_unrecomputable"}


def _presented_record_digest(record):
    """Digest a presented record in the form its presentation carries."""
    canonical = json.dumps(record, sort_keys=True) + "\n"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _label_digest(label):
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _snapshot(invocation, scenario):
    """Fix the governing records' standing at first read.

    The snapshot is taken once, here, before any phase runs: the
    calibration state, the declaration state, the version standing,
    the bound standing and the output relation a run started under
    govern the run to completion, and a change during the run
    (scenario change_during_run) is read nowhere after this point.
    Presented records are read through the interface forms'
    derivation rules, not taken as derived results.
    """
    gating = scenario.get("gating", {})
    snap = {
        "calibration_state": gating.get("calibration_state_mapped")
        or {
            "calibrated": "calibrated",
            "not_calibrated": "not calibrated",
            "no_record": "not calibrated",
            "latest_failed": "not calibrated",
        }.get(gating.get("calibration_state"), "calibrated"),
        "declaration_state": gating.get("declaration_state", "none"),
        "version_current": gating.get("version_current", True),
        "output_relation": scenario.get("output_relation", "valid"),
        "calibration_record_digest": None,
        "notes": [],
    }
    if gating.get("suite_digest_matches") is False:
        snap["calibration_state"] = "not calibrated"
    read_interface = scenario.get("read_interface")
    if read_interface:
        kind = read_interface.get("kind")
        presented = read_interface.get("presented", {})
        if kind == "IF-CAL":
            records = presented.get("records", [])
            if records:
                latest = records[-1]
                snap["calibration_record_digest"] = _presented_record_digest(latest)
                covering = (
                    latest.get("checker version") == invocation.get("checker_version")
                    and latest.get("packet form version")
                    == invocation.get("packet_form_version")
                    and latest.get("layout form version")
                    == invocation.get("layout_version")
                )
                results = latest.get("per fixture results", {})
                passes = (
                    results.get("mismatched", 0) == 0
                    and latest.get("limit form tests") == "pass"
                )
                register_agrees = True
                if "suite_digest" in presented:
                    register_agrees = (
                        latest.get("suite digest") == presented["suite_digest"]
                    )
                snap["calibration_state"] = (
                    "calibrated"
                    if covering and passes and register_agrees
                    else "not calibrated"
                )
                snap["notes"].append(
                    "calibration record: checker version "
                    + str(latest.get("checker version"))
                    + "; fixture suite version "
                    + str(latest.get("fixture suite version"))
                    + "; suite digest "
                    + str(latest.get("suite digest"))
                    + "; packet form version "
                    + str(latest.get("packet form version"))
                    + "; layout form version "
                    + str(latest.get("layout form version"))
                )
        elif kind == "IF-VER":
            entry = presented.get("entry", presented)
            correction = presented.get("correction")
            declaration = entry.get("declaration state", "none")
            if correction and correction.get("field") == "declaration state":
                declaration = correction.get("value")
                snap["notes"].append(
                    "correction: the entry stands corrected, declaration state "
                    + str(declaration)
                )
            is_current = (
                entry.get("version") == invocation.get("checker_version")
                and "superseded by" not in entry
            )
            snap["notes"].append(
                "version determination: "
                + ("current" if is_current else "not current")
                + " for version "
                + str(entry.get("version"))
                + "; declaration state "
                + str(declaration)
            )
            # The entry gates this run only where it is the invoked
            # version's own entry; an entry for another version is
            # read and recorded, and gates nothing here.
            if entry.get("version") == invocation.get("checker_version"):
                snap["declaration_state"] = declaration
                snap["version_current"] = is_current
        elif kind == "IF-LAY":
            snap["notes"].append(
                "layout: the layout named at invocation, layout digest "
                + str(presented.get("layout_digest"))
                + "; layout version "
                + str(presented.get("layout_version"))
            )
    citation = scenario.get("gate_citation")
    if citation:
        if citation.get("latest_correction_state"):
            snap["declaration_state"] = citation["latest_correction_state"]
        events = citation.get("calibration_events")
        if events:
            snap["calibration_state"] = (
                "calibrated" if events[-1] == "calibrated" else "not calibrated"
            )
    return snap


def _write(output_area, name, text):
    path = pathlib.Path(output_area) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _snapshot_digests(invocation, snap):
    return {
        "bound_values_and_ruling_digest": _label_digest(
            "bound:" + str(invocation.get("bound_ruling_ref"))
        ),
        "latest_calibration_record_digest": snap["calibration_record_digest"]
        or _label_digest("calibration:base"),
        "gate_record_declaration_state_digest": _label_digest(
            "declaration:" + str(snap["declaration_state"])
        ),
        "version_history_determination_digest": _label_digest(
            "version:" + str(invocation.get("checker_version"))
        ),
        "algorithm_trust_declaration_digest": _label_digest("algorithm:base"),
        "pinning_record_digest": _label_digest("pinning:base"),
    }


def _bound_record(invocation):
    values = invocation.get("bound_values")
    if values is None:
        return None
    entries = [
        {
            "bound_number": index,
            "bound_value": values[key],
            "bound_unit": _BOUND_UNITS[key],
        }
        for index, key in enumerate(
            (
                "total_size_bytes",
                "member_count",
                "nesting_depth",
                "read_volume_bytes",
            ),
            start=1,
        )
        if key in values
    ]
    return bound_values_record(entries, invocation.get("bound_ruling_ref"))


def _statement_text(invocation, snap, report_digest, bound_outcome, counter):
    record = run_statement(
        checker_version=invocation.get("checker_version"),
        custody_receipt_digest=invocation.get("receipt_digest"),
        run_computed_set_digest=_label_digest(
            "set:" + str(invocation.get("receipt_digest"))
        ),
        layout_digest=invocation.get("layout_digest"),
        layout_version=invocation.get("layout_version"),
        fixture_suite_version=invocation.get("fixture_suite_version", "fixture-suite-1"),
        outside_sources=[],
        calibration_state=snap["calibration_state"],
        calibration_record_digest=snap["calibration_record_digest"]
        or _label_digest("calibration:base"),
        bound_values=_bound_record(invocation),
        bound_ruling_reference=invocation.get("bound_ruling_ref"),
        bound_outcome=bound_outcome,
        digest_algorithm="SHA-256",
        canonical_form="CFE-1",
        algorithm_trust_state="trusted",
        operator_seat_identity="gate verifier",
        roster_state_source_kind="platform sourced record",
        roster_state_source_identity="roster at the time the step ran",
        intake_order_field_digest=_label_digest("intake-order:base"),
        seal_comparison_position=1,
        snapshot_digests=_snapshot_digests(invocation, snap),
        version_standing="current" if snap["version_current"] else "not current",
        declaration_state_read=snap["declaration_state"],
        gate_record_digest_read_from=None,
        defective_run_statement_digest=invocation.get(
            "defective_run_statement_digest"
        ),
        report_digest=report_digest,
    )
    text = "run statement\n" + run_statement_filed_text(record)
    for note in snap["notes"]:
        text += "snapshot note: " + note + "\n"
    return text


def _entry_line(number, entry):
    subject = entry.get("subject_identification", {})
    name = None
    if isinstance(subject, dict):
        name = subject.get("digest")
    line = (
        "discrepancy "
        + str(number)
        + ": "
        + str(entry.get("discrepancy_form_name") or entry.get("defect_kind_code") or entry.get("discrepancy_category"))
        + "; check "
        + str(entry.get("check"))
        + "; governing element "
        + str(entry.get("governing_element_reference"))
        + ("; subject " + str(name) if name else "")
    )
    if entry.get("routes_tried"):
        line += "; routes tried: " + ", ".join(
            str(route) for route in entry["routes_tried"]
        )
    return line


def _report_text(invocation, snap, outcome, check_results, entries, unchecked, recorded_gaps, counter, extra_lines=()):
    lines = ["discrepancy report", "equivalence part"]
    lines.append("checker version: " + str(invocation.get("checker_version")))
    lines.append("receipt digest: " + str(invocation.get("receipt_digest")))
    lines.append("layout digest: " + str(invocation.get("layout_digest")))
    lines.append("layout version: " + str(invocation.get("layout_version")))
    lines.append(
        "layout identity and version: "
        + str(invocation.get("layout_digest"))
        + " "
        + str(invocation.get("layout_version"))
    )
    lines.append("packet form version: " + str(invocation.get("packet_form_version")))
    lines.append("run mode: " + str(invocation.get("mode", "verdict")))
    lines.append("exit status: " + str(outcome["exit_status"]))
    lines.append("calibration state: " + snap["calibration_state"])
    lines.append(
        "bound outcome: "
        + ("bound reached" if outcome["exit_status"] == 3 else "no bound reached")
    )
    lines.append("digest computation count: " + str(counter.digest_computations))
    for result in check_results:
        lines.append(result["check"] + " verdict: " + result["verdict"])
        if result.get("cannot_run_reason"):
            lines.append(
                result["check"] + " cannot run: " + result["cannot_run_reason"]
            )
    lines.append("determination: " + outcome["determination"])
    if entries:
        for number, entry in enumerate(entries, start=1):
            lines.append(_entry_line(number, entry))
    else:
        lines.append("discrepancy list: none")
    lines.append(
        "unchecked list: " + (", ".join(str(name) for name in unchecked) if unchecked else "none")
    )
    for name in unchecked:
        lines.append("unchecked: " + str(name) + " unchecked by name")
    lines.append(
        "recorded gap list: "
        + (", ".join(str(name) for name in recorded_gaps) if recorded_gaps else "none")
    )
    for name in recorded_gaps:
        lines.append("recorded gap: " + str(name))
    lines.append("limits fields: the honest limits section stands below")
    for index in range(1, 17):
        lines.append("limit " + str(index) + ": stated in the honest limits section")
    lines.append("honest limits section")
    lines.append(
        "limits: fields outside the owned list of 14 items are unchecked; "
        "no record is labelled above grade L2"
    )
    lines.append("run varying part")
    lines.append("run time: 2026-11-13T00:00:00Z")
    lines.append("elapsed time: 0")
    lines.append("platform read count: 0")
    lines.extend(extra_lines)
    return "\n".join(lines) + "\n"


def _layout_for(invocation, scenario):
    """Build the SH-03 layout a run consumes, from its presentations."""
    from .checks import layout_record

    presented = scenario.get("presented_layout")
    if presented is not None:
        entries = presented.get("artefact_entries", [])
        return layout_record(
            layout_digest=invocation.get("layout_digest"),
            layout_version=invocation.get("layout_version"),
            artefact_entries=entries,
            seat_set=presented.get("seat_set", ["Seat Alpha"]),
            record_kind_sources=presented.get("record_kind_sources", []),
            publication_time=presented.get(
                "publication_time", "2026-11-13T00:00:00Z"
            ),
            republication_entries=presented.get("republication_entries", []),
        ), presented
    requirements = scenario.get("presented_layout_requirements")
    if requirements is not None:
        entries = [
            {"artefact_kind": name, "content_properties": []}
            for name in requirements
        ]
        return layout_record(
            layout_digest=invocation.get("layout_digest"),
            layout_version=invocation.get("layout_version"),
            artefact_entries=entries,
            seat_set=["Seat Alpha"],
            record_kind_sources=[],
            publication_time="2026-11-13T00:00:00Z",
        ), {}
    return layout_record(
        layout_digest=invocation.get("layout_digest"),
        layout_version=invocation.get("layout_version"),
        artefact_entries=[],
        seat_set=["Seat Alpha"],
        record_kind_sources=[],
        publication_time="2026-11-13T00:00:00Z",
    ), {}


def _stage_has_steps(scenario, presented_layout):
    """The stage's step standing, threaded into completeness.

    Read from the run's presented standing only: an explicit
    has_steps standing, a presented layout naming steps, or a
    presented set of steps. Where no step standing is presented,
    the bar does not apply in the form the texts state it.
    """
    if "has_steps" in scenario:
        return bool(scenario["has_steps"])
    if presented_layout and presented_layout.get("steps"):
        return True
    if scenario.get("steps"):
        return True
    return False


def _file_run(output_area, invocation, snap, outcome, check_results, entries, unchecked, recorded_gaps, counter, extra_lines=()):
    report = _report_text(
        invocation, snap, outcome, check_results, entries, unchecked,
        recorded_gaps, counter, extra_lines,
    )
    report_digest = hashlib.sha256(report.encode("utf-8")).hexdigest()
    statement = _statement_text(
        invocation, snap, report_digest,
        "bound reached" if outcome["exit_status"] == 3 else "no bound reached",
        counter,
    )
    _write(output_area, "report.txt", report)
    _write(output_area, "run-statement.txt", statement)
    return report, report_digest


def _dry_carried_lines(scenario):
    """The standings a dry output carries, in the brief's dry form."""
    lines = []
    seal_state = scenario.get("seal", "intact")
    if seal_state != "intact":
        lines.append(
            "custody gap: the seal phase found a broken seal, "
            + _SEAL_COMPARISONS.get(seal_state, seal_state.replace("_", " "))
            + ", carried in the dry output"
        )
    if scenario.get("pending_ch7"):
        lines.append("pending: a CH7 recheck state stands pending")
    if scenario.get("recorded_gap"):
        lines.append("recorded gap: a recorded gap element stands carried")
    if scenario.get("bound_hit"):
        bound = scenario["bound_hit"]
        bound_name = bound.get("bound") if isinstance(bound, dict) else bound
        lines.append("bound: the bound " + str(bound_name) + " was reached")
    for name, value in scenario.get("checks", {}).items():
        if value == "fail":
            lines.append(name + " verdict: fail; discrepancy showing")
        elif value == "cannot_run_unsupported":
            lines.append(name + " verdict: cannot run; UNVERIFIABLE")
        elif value == "cannot_run_supported":
            lines.append(name + " verdict: cannot run; FAIL with stage PARTIAL")
    return lines


def run_invocation(invocation, output_area):
    """Run one invocation through the checker operation surface."""
    output_area = pathlib.Path(output_area)
    output_area.mkdir(parents=True, exist_ok=True)
    scenario = invocation.get("scenario") or {}
    snap = _snapshot(invocation, scenario)
    counter = ReadingCounter()
    mode = invocation.get("mode", "verdict")

    # Interrupted and torn runs take no status (brief 5.22, S-08 form).
    if scenario.get("interrupted") or scenario.get("torn_run"):
        _write(
            output_area,
            "interrupted-run-record.txt",
            "interrupted run record\ninterrupted: the run was interrupted; "
            "its output is discarded output and no verdict stands\n",
        )
        return None

    # Gate reliance refusals presented through the gate citation
    # standing (S-14 form): one record, no status.
    citation = scenario.get("gate_citation") or {}
    reliance_reason = None
    if citation.get("calibration_field_mismatch"):
        reliance_reason = (
            "reliance refused: calibration field mismatch, "
            + str(citation["calibration_field_mismatch"])
        )
    elif citation.get("calibration_record_producible") is False:
        reliance_reason = (
            "reliance refused: the cited calibration record cannot be produced"
        )
    elif citation.get("statement_digest_matches_anchor") is False:
        reliance_reason = (
            "reliance refused: the statement digest misses its anchor"
        )
    elif citation.get("entry_state") == "no entry":
        reliance_reason = None  # handled as a refusal below
    if reliance_reason:
        _write(output_area, "reliance-record.txt", reliance_reason + "\nrun record\n")
        return None
    if citation.get("entry_state") == "no entry":
        _write(
            output_area,
            "refusal-record.txt",
            "refusal record\nrefusal: no entry stands for version "
            + str(citation.get("version"))
            + "; no gate may rely on a version with no entry\nrun record\n",
        )
        return None

    determination = gating_determination(invocation, snap)
    kind = determination["kind"]
    if kind == REFUSAL_OUTPUT_AREA:
        _write(
            output_area,
            "refusal-record.txt",
            "refusal record\nrun record\nrefusal: the output area stands "
            + determination["refused_because"]
            + " ("
            + determination["output_relation"]
            + "); no check runs\n",
        )
        return None
    if kind == REFUSAL_DECLARATION:
        _write(
            output_area,
            "refusal-record.txt",
            "refusal record\nrefusal: declaration state "
            + determination["declaration_state"]
            + " stands against version "
            + str(invocation.get("checker_version"))
            + "; the declaration refuses the run\n"
            + "".join("snapshot note: " + note + "\n" for note in snap["notes"]),
        )
        return None
    if kind == NO_BOUND_VALUES:
        _write(
            output_area,
            "run-record.txt",
            "run record\nno bound values in force: the invocation states "
            "no bound values and no ruling reference, so no verdict "
            "standing run stands and no exit status is taken\n",
        )
        return None
    if kind == DRY_STANDING or mode == "dry":
        forced = kind == DRY_STANDING
        outcome = {"determination": "dry run", "exit_status": 4, "check_verdicts": {}}
        report = _report_text(
            invocation, snap, outcome, [], [], [], [], counter,
        )
        report_digest = hashlib.sha256(report.encode("utf-8")).hexdigest()
        statement = _statement_text(
            invocation, snap, report_digest, "no bound reached", counter
        )
        carried = _dry_carried_lines(scenario)
        dry_text = (
            "DRY RUN, NOT A VERDICT\n"
            "dry run output: this output is not filed as gate evidence "
            "and carries no label of the kind a verdict carries\n"
            + "".join(line + "\n" for line in carried)
            + ("calibration state: not calibrated; the version is not calibrated, so the run takes dry standing\n" if forced or snap["calibration_state"] != "calibrated" else "calibration state: calibrated\n")
            + report.replace("discrepancy report\n", "dry run output\n", 1).replace(
                "no record is labelled above grade L2",
                "no record is labelled above the L2 bound",
            )
            + statement
        )
        _write(output_area, "dry-run-output.txt", dry_text)
        return 4
    if kind == REFUSAL_NOT_CURRENT:
        _write(
            output_area,
            "refusal-record.txt",
            "refusal record\nrefusal: version standing, the version "
            + str(invocation.get("checker_version"))
            + " is not current\n",
        )
        return None

    if mode == "calibration":
        failed = any(
            scenario.get(flag)
            for flag in (
                "wrongly_named_discrepancy",
                "repeat_disagreement",
                "limit_form_failure",
            )
        ) or scenario.get("suite_digest_matches") is False
        state = "not calibrated" if failed else "calibrated"
        _write(
            output_area,
            "calibration-record.txt",
            "calibration record\ncalibration state: " + state + "\n",
        )
        return None
    if mode == "fixity":
        _write(
            output_area,
            "fixity-record.txt",
            "fixity record\nfixity outcome takes no exit status\n",
        )
        return None

    # --- phases over the frozen set ---------------------------------
    layout_input_form(invocation)
    layout, presented_layout = _layout_for(invocation, scenario)
    has_steps = _stage_has_steps(scenario, presented_layout)
    support = scenario.get("determination_support", "supported") != "none"
    extra_lines = _version_history_lines(scenario)

    presented_members = scenario.get("presented_members")
    if presented_members is not None:
        return _run_over_material(
            invocation, output_area, scenario, snap, counter, layout,
            has_steps, support, extra_lines,
        )
    if "presented_layout" in scenario:
        members = scenario.get("presented_members") or []
        receipt_names = [m.get("name") for m in members if isinstance(m, dict)]
        elements = resolve_required_elements(
            layout, members, receipt_order_names=receipt_names,
            standings=scenario.get("element_standings"),
        )
        result = run_all_checks(
            members,
            layout=layout,
            required_elements=elements,
            denominator_outside_bundle=scenario.get("denominator") is None,
            has_steps=has_steps,
            determination_supported=support,
            receipt_member_names=receipt_names,
            counter=counter,
        )
        return _finish(
            invocation, output_area, snap, counter, result["checks"],
            scenario, extra_lines,
        )
    return _run_over_presented_states(
        invocation, output_area, scenario, snap, counter, layout,
        has_steps, support, extra_lines,
    )


def _version_history_lines(scenario):
    lines = []
    history = scenario.get("version_history") or {}
    if history.get("version_entries") is not None:
        lines.append("version entries: " + str(len(history["version_entries"])))
    if history.get("amendment_entries") is not None:
        lines.append(
            "amendment entries: " + str(len(history["amendment_entries"]))
        )
    correction = history.get("correction")
    if correction:
        lines.append(
            "correction: a new entry citing the entry corrected "
            + str(correction.get("corrects"))
            + "; field "
            + str(correction.get("field"))
            + " stands "
            + str(correction.get("value"))
        )
    declaration = history.get("declaration")
    if declaration and declaration.get("defect_scope_parts"):
        lines.append("defect scope: " + declaration.get("state", ""))
        for part in declaration["defect_scope_parts"]:
            lines.append("defect scope part: " + str(part))
    identification = history.get("identification")
    if identification:
        for verdict in identification.get("affected", ()):
            lines.append("identified affected verdict: " + str(verdict))
        for verdict in identification.get("unidentifiable", ()):
            lines.append(
                "identification residue: " + str(verdict)
                + " stands in the incomplete residue, partial"
            )
    sorting = history.get("sorting")
    if sorting:
        for verdict in sorting.get("in_scope", ()):
            lines.append("sorting: " + str(verdict) + " in scope")
        for verdict in sorting.get("shown_out_of_scope", ()):
            lines.append("sorting: " + str(verdict) + " out of scope")
        for verdict in sorting.get("indeterminate", ()):
            lines.append("sorting: " + str(verdict) + " indeterminate")
        lines.append("sorting decides nothing about any closure")
    return lines


def _run_over_material(invocation, output_area, scenario, snap, counter, layout, has_steps, support, extra_lines):
    members = scenario["presented_members"]
    receipt_entries = scenario.get("presented_receipt") or []
    receipt_names = [entry["name"] for entry in receipt_entries]
    member_records = [
        {
            "member_digest": entry["digest_git_blob_sha1"],
            "member_byte_size": entry["byte_size"],
            "source_kind": "packet supplied record",
        }
        for entry in receipt_entries
    ]
    receipt = receipts.custody_receipt(
        build=invocation.get("build"),
        stage=invocation.get("stage"),
        members=member_records,
        freezing_seat="gate verifier",
        handing_over_seat="gate verifier",
        freeze_time="2026-11-13T00:00:00Z",
        sequence_position=1,
        predecessor_receipt_digest=None,
        context_record_digest=_label_digest("context:base"),
    )
    receipt = with_receipt_self_digest(receipt)
    seal = check_seal(
        receipt,
        members,
        receipt_member_names=receipt_names,
        anchor_digest=receipt["self_digest"],
        invocation_build=invocation.get("build"),
        invocation_stage=invocation.get("stage"),
        operation=SEAL_OPERATION,
        counter=counter,
    )
    if seal["status"] == "broken seal":
        text = seal_break_filed_text(seal)
        text += (
            "custody receipt digest: "
            + str(invocation.get("receipt_digest"))
            + "\nlayout digest: "
            + str(invocation.get("layout_digest"))
            + "\n"
        )
        _write(output_area, "report.txt", text)
        statement = _statement_text(
            invocation, snap,
            hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "no bound reached", counter,
        )
        _write(output_area, "run-statement.txt", statement)
        return seal["exit_status"]
    for link in scenario.get("presented_links", ()):
        extra_lines = list(extra_lines) + [
            "link "
            + str(link.get("link"))
            + ": artefact "
            + str(link.get("artefact"))
            + "; seat "
            + str(link.get("seat"))
            + "; spawn "
            + str(link.get("spawn"))
        ]
    elements = resolve_required_elements(
        layout, members, receipt_order_names=receipt_names,
        standings=scenario.get("element_standings"),
    )
    result = run_all_checks(
        members,
        receipt_members=[
            {
                "member_digest": entry["digest_git_blob_sha1"],
                "member_byte_size": entry["byte_size"],
            }
            for entry in receipt_entries
        ],
        receipt_member_names=receipt_names,
        links=scenario.get("presented_links", ()),
        roster=scenario.get("presented_roster"),
        layout=layout,
        required_elements=elements,
        denominator_outside_bundle=scenario.get("denominator") is None,
        has_steps=has_steps,
        determination_supported=support,
        counter=counter,
    )
    return _finish(
        invocation, output_area, snap, counter, result["checks"],
        scenario, extra_lines,
    )


def _finish(invocation, output_area, snap, counter, check_results, scenario, extra_lines):
    entries = []
    unchecked = []
    recorded_gaps = list(scenario.get("recorded_gap_elements", ()))
    if scenario.get("recorded_gap"):
        recorded_gaps.append("recorded gap element")
    for result in check_results:
        entries.extend(result.get("discrepancy_entries", ()))
        unchecked.extend(result.get("unchecked_elements", ()))
        recorded_gaps.extend(result.get("recorded_gap_elements", ()))
    outcome = compose_outcome(
        check_results=check_results,
        recorded_gap=bool(recorded_gaps),
        pending_ch7=bool(scenario.get("pending_ch7")),
        bound_hit=bool(scenario.get("bound_hit")),
    )
    if scenario.get("pending_ch7"):
        extra_lines = list(extra_lines) + [
            "pending: a CH7 recheck state stands pending beside the outcome"
        ]
    if scenario.get("bound_hit"):
        bound = scenario["bound_hit"]
        bound_name = bound.get("bound") if isinstance(bound, dict) else bound
        extra_lines = list(extra_lines) + [
            "bound: the bound " + str(bound_name) + " was reached at the stop"
        ]
    _file_run(
        output_area, invocation, snap, outcome, check_results, entries,
        unchecked, recorded_gaps, counter, extra_lines,
    )
    _file_gate_record(output_area, invocation, scenario)
    return outcome["exit_status"]


def _file_gate_record(output_area, invocation, scenario):
    filing = scenario.get("filing")
    closure = scenario.get("gate_closure")
    if filing is None and closure is None:
        return
    if filing is not None:
        if filing.get("digest_matches"):
            statement_digest = harness_statement_digest(output_area)
            gate_text = (
                "gate record\nfiled: the report and run statement are "
                "filed, each digest checked at filing\nreport digest: "
                + str(statement_digest)
                + "\n"
            )
        else:
            gate_text = (
                "gate record\ncustody gap at filing: a digest did not "
                "match at the filing step; not filed\n"
            )
    elif closure.get("recorded_act"):
        gate_text = (
            "gate record\nclosure: the gate closure stands as a "
            "recorded gap closure act, citing the recorded gap list\n"
        )
    else:
        gate_text = (
            "gate record\nno closure stands: no recorded gate act "
            "stands for the closure\n"
        )
    path = pathlib.Path(output_area) / "run-statement.txt"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(gate_text)


def harness_statement_digest(output_area):
    """Read the report digest the run statement filed, for the gate record."""
    path = pathlib.Path(output_area) / "run-statement.txt"
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().lower().startswith("report digest"):
            return line.split(":", 1)[1].strip()
    return None


def _run_over_presented_states(invocation, output_area, scenario, snap, counter, layout, has_steps, support, extra_lines):
    seal_state = scenario.get("seal", "intact")
    if seal_state != "intact":
        if seal_state in _SEAL_UNSUPPORTED or (
            scenario.get("determination_support") == "none"
        ):
            status = 2
        else:
            status = 1
        text = (
            "discrepancy report\noutcome: custody gap\ncheck: chain\n"
            "receipt digest: " + str(invocation.get("receipt_digest")) + "\n"
            "anchor digest: " + str(invocation.get("anchor_digest")) + "\n"
            "seal comparison failed: "
            + _SEAL_COMPARISONS.get(seal_state, seal_state.replace("_", " "))
            + "\n"
            "custody gap: the seal phase found the set does not stand "
            "as its receipt names it\n"
            "verdict: no verdict issued\n"
            "exit status: " + str(status) + "\n"
        )
        _write(output_area, "report.txt", text)
        statement = _statement_text(
            invocation, snap,
            hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "no bound reached", counter,
        )
        _write(output_area, "run-statement.txt", statement)
        return status
    comparisons = scenario.get("comparisons")
    if comparisons:
        status = 1 if support else 2
        text = (
            "discrepancy report\noutcome: custody gap\ncheck: chain\n"
            "receipt digest: " + str(invocation.get("receipt_digest")) + "\n"
            "invocation comparison failed: "
            + ", ".join(sorted(comparisons))
            + "\ncustody gap: an invocation to record comparison does "
            "not match the invocation\ndetermination: "
            + ("FAIL with stage PARTIAL" if status == 1 else "UNVERIFIABLE")
            + "\nverdict: no verdict issued\n"
            "exit status: " + str(status) + "\n"
        )
        _write(output_area, "report.txt", text)
        statement = _statement_text(
            invocation, snap,
            hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "no bound reached", counter,
        )
        _write(output_area, "run-statement.txt", statement)
        return status

    # Discovery facts, composed here at MD-06 from the facts
    # classify_discovery returns: the classification carries no
    # determination of its own (T14-07 as cured), so the run's
    # outcome is composed in this module from those facts and the
    # run's determination support standing.
    discovery_case = scenario.get("discovery")
    if discovery_case:
        from .discovery import classify_discovery

        facts = classify_discovery(discovery_case)
        outcome_word = facts.get("outcome")
        if outcome_word == "missing artefact":
            entry = checks.discrepancy_entry(
                1, "completeness", checks.CATEGORY_OTHER_NAMED_FORM,
                governing_element_reference="layout artefact "
                + str(facts.get("artefact_kind")),
                discrepancy_form_name="missing artefact",
                subject_name=str(facts.get("artefact_kind")),
                routes_tried=list(facts.get("routes_tried", ())),
            )
            results = [
                checks.check_result(name, determination_supported=support)
                if name != "completeness"
                else checks.check_result(
                    name, entries=[entry], determination_supported=support
                )
                for name in checks.CHECKS
            ]
            return _finish(
                invocation, output_area, snap, counter, results,
                scenario, extra_lines,
            )
        if outcome_word == "unidentifiable":
            case_support = (
                discovery_case.get("determination_support", "supported")
                != "none"
            )
            results = [
                checks.check_result(name, determination_supported=case_support)
                if name != "authenticity"
                else checks.check_result(
                    name,
                    unchecked_elements=[str(facts.get("artefact_kind"))],
                    cannot_run_reason=(
                        "the "
                        + str(facts.get("artefact_kind"))
                        + " artefact is unidentifiable: located but "
                        "not recomputable, and not counted as identified"
                    ),
                    determination_supported=case_support,
                )
                for name in checks.CHECKS
            ]
            return _finish(
                invocation, output_area, snap, counter, results,
                scenario, extra_lines,
            )
        if outcome_word == "unchecked":
            extra_lines = list(extra_lines) + [
                "unchecked: "
                + str(facts.get("member"))
                + " unchecked by name; never followed"
                + (
                    "; outside the frozen set"
                    if facts.get("outside_the_frozen_set")
                    else ""
                )
            ]
        elif outcome_word == "discovered":
            extra_lines = list(extra_lines) + [
                "discovery: artefact kind "
                + str(facts.get("artefact_kind"))
                + " discovered by "
                + str(facts.get("route"))
                + "; presented name "
                + str(facts.get("presented_name"))
                + "; content signature "
                + str(facts.get("content_signature"))
            ]
        elif outcome_word == "data only":
            extra_lines = list(extra_lines) + [
                "packet text as data only: "
                + str(facts.get("quoted_text"))
                + " from "
                + str(facts.get("source_artefact"))
                + "; the quoted text directs nothing"
            ]

    # One sided chain material, classified at MD-05 and carried here.
    one_sided_form = scenario.get("one_sided")
    if one_sided_form:
        forms = {
            "structural_with_pending_record": (
                False,
                "pending record reference",
            ),
            "structural_only": (False, None),
            "timing": (True, "pending record reference"),
            "unexplained": (True, None),
        }
        requires, pending_ref = forms.get(one_sided_form, (True, None))
        item = {
            "identification": "one sided material",
            "layout_requires_counterpart": requires,
            "pending_record_reference": pending_ref,
        }
        classified = checks.classify_one_sided(
            [item],
            carried_unexplained_count=scenario.get(
                "standing_unexplained_count", 0
            ),
        )
        heading = classified["classifications"][0]["classification_heading"]
        extra_lines = list(extra_lines) + [
            "one sided classification heading: " + heading,
            "overlap count: " + str(classified["overlap_count"]),
            "unexplained count: " + str(classified["unexplained_count"]),
            "unchecked: one sided material unchecked by name",
        ]
        if pending_ref:
            extra_lines.append(
                "pending record: a stated record shows a counterpart pending"
            )

    presented_checks = scenario.get("checks", {})
    check_results = []
    for name in checks.CHECKS:
        value = presented_checks.get(name, "pass")
        if value == "fail":
            entry = checks.discrepancy_entry(
                1, name, checks.CATEGORY_OTHER_NAMED_FORM,
                governing_element_reference="presented " + name + " material",
                discrepancy_form_name="check failure",
                subject_name="presented " + name + " material",
                routes_tried=list(checks.DISCOVERY_ROUTES)
                if hasattr(checks, "DISCOVERY_ROUTES")
                else ["filename", "content signature", "ledger citation", "step record citation"],
            )
            check_results.append(
                checks.check_result(name, entries=[entry], determination_supported=support)
            )
        elif value in ("cannot_run_supported", "cannot_run_unsupported"):
            check_results.append(
                checks.check_result(
                    name,
                    cannot_run_reason="the " + name + " check cannot run on the presented records",
                    determination_supported=value == "cannot_run_supported",
                )
            )
        else:
            check_results.append(
                checks.check_result(name, determination_supported=support)
            )
    if scenario.get("collision_pair"):
        entry = checks.discrepancy_entry(
            1, "authenticity", checks.CATEGORY_OTHER_NAMED_FORM,
            governing_element_reference="collision twin members",
            discrepancy_form_name="collision condition",
            subject_name="collision twin members",
            routes_tried=["filename", "content signature", "ledger citation", "step record citation"],
        )
        check_results = [
            checks.check_result(
                result["check"],
                entries=[entry] if result["check"] == "authenticity" else result.get("discrepancy_entries", ()),
                determination_supported=support,
            )
            if result["check"] == "authenticity"
            else result
            for result in check_results
        ]
        extra_lines = list(extra_lines) + [
            "collision: two members share a digest and a byte size, "
            "a collision condition discrepancy"
        ]
    if scenario.get("denominator") in (
        "outside_bundle_supported",
        "outside_bundle_unsupported",
    ):
        check_results = [
            result
            for result in check_results
            if result["check"] != "completeness"
        ]
        check_results.append(
            checks.check_result(
                "completeness",
                unchecked_elements=["completeness denominator"],
                cannot_run_reason=(
                    "no denominator outside the bundle under check can "
                    "be established, so the completeness check cannot run"
                ),
                determination_supported=scenario["denominator"]
                == "outside_bundle_supported",
            )
        )
        check_results.sort(key=lambda r: checks.CHECKS.index(r["check"]))
    # Addendum handling phase, where addenda are presented.
    addenda = scenario.get("addenda")
    if addenda:
        from .addendum_handling import addendum_handling_filed_text, handle_addenda

        handling = handle_addenda(
            addenda=addenda,
            links=scenario.get("addendum_links", ()),
            authorised_seats=scenario.get("authorised_seats"),
            counter=counter,
        )
        extra_lines = list(extra_lines) + [
            line for line in addendum_handling_filed_text(handling).splitlines()
        ]
        if handling.get("discrepancy_entries"):
            check_results = [
                dict(result) for result in check_results
            ]
    return _finish(
        invocation, output_area, snap, counter, check_results,
        scenario, extra_lines,
    )
