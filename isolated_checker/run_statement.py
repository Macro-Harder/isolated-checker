"""Run statement form, shape SH-11.

Slice S-01, second record family. The field list at brief section
5.17 is the single governing list for the whole brief, used without
subtraction. The statement is the run half of the run record pair
whose intake half is the custody receipt. It bears a digest of
itself, computed over its canonical form with the self digest field
omitted, under CE-3; this module carries that value, the canonical
module computes it, and the filed form stands in the brief list
order, which carries no self digest line: the statement is filed
under its self digest as its file name, under plan Q7.
"""

from . import shapes
from .shapes import ShapeError


def bound_values_record(bound_entries, bound_ruling_reference):
    """Build a bound values record in the SH-29 form.

    bound_entries holds one entry per bound, each a record with
    bound_number, bound_value, and bound_unit under CE-2A. No bound
    value is named by this module; values arrive only in a record
    a ruling has set, or in test bound form for a named trial.
    """
    entries = []
    for entry in bound_entries:
        for name in entry:
            if name not in shapes.BOUND_ENTRY_FIELDS:
                raise ShapeError(
                    "SH-29 bound entry carries an unnamed field: " + name
                )
        entries.append(dict(entry))
    record = {
        "bound_entries": entries,
        "bound_ruling_reference": bound_ruling_reference,
    }
    return shapes.validate("SH-29", record)


def run_statement(
    checker_version,
    custody_receipt_digest,
    run_computed_set_digest,
    layout_digest,
    layout_version,
    fixture_suite_version,
    outside_sources,
    calibration_state,
    calibration_record_digest,
    bound_values,
    bound_ruling_reference,
    bound_outcome,
    digest_algorithm,
    canonical_form,
    algorithm_trust_state,
    operator_seat_identity,
    roster_state_source_kind,
    roster_state_source_identity,
    intake_order_field_digest,
    seal_comparison_position,
    snapshot_digests,
    version_standing,
    declaration_state_read,
    gate_record_digest_read_from,
    defective_run_statement_digest,
    report_digest,
    self_digest=None,
):
    """Build a run statement record in the SH-11 form.

    The custody receipt digest and the run computed set digest are
    two distinct fields. The snapshot digests are the digests fixed
    at the first read of invocation, under SH-12, with the pinning
    record digest carried as the plan addition SH-12 states.
    """
    sources = []
    for source in outside_sources:
        for name in source:
            if name not in shapes.SOURCE_FIELDS:
                raise ShapeError(
                    "SH-11 outside source carries an unnamed field: " + name
                )
        sources.append(dict(source))
    snapshot = {}
    for name, value in snapshot_digests.items():
        if name not in shapes.SNAPSHOT_FIELDS:
            raise ShapeError(
                "SH-11 snapshot digests carry an unnamed field: " + name
            )
        snapshot[name] = value
    if calibration_state not in ("calibrated", "not calibrated"):
        raise ShapeError(
            "SH-11 calibration state is not a value at CE-2B: "
            + str(calibration_state)
        )
    record = {
        "checker_version": checker_version,
        "custody_receipt_digest": custody_receipt_digest,
        "run_computed_set_digest": run_computed_set_digest,
        "layout_digest": layout_digest,
        "layout_version": layout_version,
        "fixture_suite_version": fixture_suite_version,
        "outside_sources": sources,
        "calibration_state": calibration_state,
        "calibration_record_digest": calibration_record_digest,
        "bound_values": bound_values,
        "bound_ruling_reference": bound_ruling_reference,
        "bound_outcome": bound_outcome,
        "digest_algorithm": digest_algorithm,
        "canonical_form": canonical_form,
        "algorithm_trust_state": algorithm_trust_state,
        "operator_seat_identity": operator_seat_identity,
        "roster_state_source_kind": roster_state_source_kind,
        "roster_state_source_identity": roster_state_source_identity,
        "intake_order_field_digest": intake_order_field_digest,
        "seal_comparison_position": seal_comparison_position,
        "snapshot_digests": snapshot,
        "version_standing": version_standing,
        "declaration_state_read": declaration_state_read,
        "gate_record_digest_read_from": gate_record_digest_read_from,
        "defective_run_statement_digest": defective_run_statement_digest,
        "report_digest": report_digest,
        "self_digest": self_digest,
    }
    return shapes.validate("SH-11", record)


def _bound_line(record):
    values = record["bound_values"]
    if values is None:
        rendered = "no bound values in force"
    else:
        rendered = "; ".join(
            "bound " + str(e["bound_number"]) + " "
            + str(e["bound_value"]) + " " + str(e["bound_unit"])
            for e in values["bound_entries"]
        )
    return (
        rendered
        + "; ruling " + str(record["bound_ruling_reference"])
        + "; bound outcome " + str(record["bound_outcome"])
    )


def run_statement_filed_text(record):
    """Render a run statement in its filed form, brief order."""
    sources = "; ".join(
        s["source_kind"] + " " + s["source_identity"]
        for s in record["outside_sources"]
    )
    snapshot = "; ".join(
        name + " " + str(value)
        for name, value in record["snapshot_digests"].items()
    )
    defective = record["defective_run_statement_digest"]
    return shapes.render_fields(
        [
            ("checker version", record["checker_version"]),
            ("receipt digest", record["custody_receipt_digest"]),
            ("computed set digest", record["run_computed_set_digest"]),
            ("layout digest", record["layout_digest"]),
            ("outside sources", sources),
            (
                "calibration state",
                record["calibration_state"]
                + "; calibration record digest "
                + str(record["calibration_record_digest"]),
            ),
            ("bound values and ruling", _bound_line(record)),
            (
                "digest algorithm and canonical form",
                record["digest_algorithm"] + "; " + record["canonical_form"],
            ),
            ("algorithm trust state", record["algorithm_trust_state"]),
            ("operator seat", record["operator_seat_identity"]),
            (
                "layout identity and version",
                record["layout_digest"] + " " + record["layout_version"],
            ),
            ("fixture suite version", record["fixture_suite_version"]),
            (
                "roster state source",
                record["roster_state_source_kind"]
                + " " + record["roster_state_source_identity"],
            ),
            (
                "intake order field",
                record["intake_order_field_digest"]
                + "; position " + str(record["seal_comparison_position"]),
            ),
            ("snapshot digests", snapshot),
            (
                "version standing",
                record["version_standing"]
                + "; declaration state " + str(record["declaration_state_read"])
                + "; gate record digest "
                + str(record["gate_record_digest_read_from"]),
            ),
            (
                "defective run statement citation",
                defective if defective is not None else "absent",
            ),
            ("report digest", record["report_digest"]),
        ]
    )
