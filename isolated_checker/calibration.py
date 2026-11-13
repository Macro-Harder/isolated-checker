"""Calibration record form, shape SH-22.

Slice S-01, third record family. The record form is brief section
5.21. The record carries no self digest field: its citation digest
is the CFE-1 record digest of the record as a whole, computed by
the canonical module under CE-4 with no field omitted. The
pinning record digest field is the plan assembled field SH-22
states, fixing the pair the calibration run proceeded under; it
stands in the canonical record and not as a line of the filed
form, whose field list is the brief list.
"""

from . import shapes
from .shapes import ShapeError

CHECK_NAMES = ("authenticity", "chain", "completeness")
PASS_RESULT = "pass"


def fixture_result(
    fixture_identity_digest,
    times_run,
    result_per_check,
    disagreements=None,
    wrongly_named_discrepancies=None,
):
    """One per fixture part entry of a calibration record."""
    results = []
    for item in result_per_check:
        if item["check"] not in CHECK_NAMES:
            raise ShapeError(
                "SH-22 result per check names an unknown check: "
                + str(item["check"])
            )
        results.append({"check": item["check"], "result": item["result"]})
    return {
        "fixture_identity_digest": fixture_identity_digest,
        "times_run": times_run,
        "result_per_check": results,
        "disagreements": list(disagreements or []),
        "wrongly_named_discrepancies": list(wrongly_named_discrepancies or []),
    }


def calibration_record(
    checker_version,
    fixture_suite_version,
    suite_digest,
    packet_form_version,
    layout_form_version,
    kinds_covered_count,
    deferred_kinds,
    per_fixture_results,
    seat_that_ran_it,
    calibration_time,
    pinning_record_digest,
    per_check_counts=None,
):
    """Build a calibration record in the SH-22 form."""
    fixtures = []
    for entry in per_fixture_results:
        for name in entry:
            if name not in shapes.FIXTURE_RESULT_FIELDS:
                raise ShapeError(
                    "SH-22 per fixture result carries an unnamed field: "
                    + name
                )
        fixtures.append(dict(entry))
    if per_check_counts is None:
        per_check_counts = [
            {
                "check": check,
                "count": sum(
                    1
                    for entry in fixtures
                    for item in entry["result_per_check"]
                    if item["check"] == check and item["result"] == PASS_RESULT
                ),
            }
            for check in CHECK_NAMES
        ]
    record = {
        "checker_version": checker_version,
        "fixture_suite_version": fixture_suite_version,
        "suite_digest": suite_digest,
        "packet_form_version": packet_form_version,
        "layout_form_version": layout_form_version,
        "kinds_covered_count": kinds_covered_count,
        "deferred_kinds": list(deferred_kinds),
        "per_fixture_results": fixtures,
        "per_check_counts": per_check_counts,
        "seat_that_ran_it": seat_that_ran_it,
        "calibration_time": calibration_time,
        "pinning_record_digest": pinning_record_digest,
    }
    return shapes.validate("SH-22", record)


def calibration_passes(record):
    """The pass predicate over a calibration record, brief 5.19.

    A pass stands where every fixture matches its expected outcome
    on every repeat run of it: every result per check is a pass,
    and no fixture carries a disagreement or a wrongly named
    discrepancy.
    """
    for entry in record["per_fixture_results"]:
        if entry["disagreements"] or entry["wrongly_named_discrepancies"]:
            return False
        for item in entry["result_per_check"]:
            if item["result"] != PASS_RESULT:
                return False
    return True


def calibration_filed_text(record):
    """Render a calibration record in its filed form, brief order."""
    deferred = (
        "; ".join(record["deferred_kinds"])
        if record["deferred_kinds"]
        else "none"
    )
    floor = (
        str(record["kinds_covered_count"]) + " of 33; deferred kinds "
        + deferred
    )
    fixtures = "; ".join(
        entry["fixture_identity_digest"]
        + " ran " + str(entry["times_run"]) + " times: "
        + ", ".join(
            item["check"] + " " + item["result"]
            for item in entry["result_per_check"]
        )
        + "; disagreements " + str(len(entry["disagreements"]))
        + "; wrongly named discrepancies "
        + str(len(entry["wrongly_named_discrepancies"]))
        for entry in record["per_fixture_results"]
    )
    return shapes.render_fields(
        [
            ("checker version", record["checker_version"]),
            ("fixture suite version", record["fixture_suite_version"]),
            ("suite digest", record["suite_digest"]),
            ("packet form version", record["packet_form_version"]),
            ("layout form version", record["layout_form_version"]),
            ("floor scope", floor),
            ("per fixture results", fixtures),
            ("seat", record["seat_that_ran_it"]),
            ("time", record["calibration_time"]),
        ]
    )
