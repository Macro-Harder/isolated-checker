"""Shape validation and record construction, plan module MD-02.

Owns the field lists of the shapes slice S-01 delivers, in the field
name vocabulary plan statement CE-2A fixes. A record is a plain dict
in that vocabulary. Construction rejects a field a shape does not
state, a duplicate cannot arise in a dict, and a value of the wrong
node kind under CE-2 is rejected by the canonical module at encoding
time. Every other module receives records only through the builders
in the record modules, which validate through this module, so a
malformed record is stopped at this seam with the record type, the
field, and the governing shape named in the error.
"""

ABSENT = None


class ShapeError(ValueError):
    """A record does not stand in the form its shape states."""


VOCABULARY = {
    "SH-05": (
        "build",
        "stage",
        "packet_form_version",
        "digest_algorithm",
        "canonical_form",
        "standing_rule_versions",
        "outside_standard_versions",
    ),
    "SH-06": (
        "build",
        "stage",
        "members",
        "freezing_seat",
        "handing_over_seat",
        "freeze_time",
        "sequence_position",
        "predecessor_receipt_digest",
        "context_record_digest",
        "self_digest",
    ),
    "SH-11": (
        "checker_version",
        "custody_receipt_digest",
        "run_computed_set_digest",
        "layout_digest",
        "layout_version",
        "fixture_suite_version",
        "outside_sources",
        "calibration_state",
        "calibration_record_digest",
        "bound_values",
        "bound_ruling_reference",
        "bound_outcome",
        "digest_algorithm",
        "canonical_form",
        "algorithm_trust_state",
        "operator_seat_identity",
        "roster_state_source_kind",
        "roster_state_source_identity",
        "intake_order_field_digest",
        "seal_comparison_position",
        "snapshot_digests",
        "version_standing",
        "declaration_state_read",
        "gate_record_digest_read_from",
        "defective_run_statement_digest",
        "report_digest",
        "self_digest",
    ),
    "SH-22": (
        "checker_version",
        "fixture_suite_version",
        "suite_digest",
        "packet_form_version",
        "layout_form_version",
        "kinds_covered_count",
        "deferred_kinds",
        "per_fixture_results",
        "per_check_counts",
        "seat_that_ran_it",
        "calibration_time",
        "pinning_record_digest",
    ),
    "SH-29": (
        "bound_entries",
        "bound_ruling_reference",
        "no_bound_values_wording",
    ),
    "SH-30": (
        "report_digest",
        "discrepancies_to_answer",
        "failure_wording",
        "failed_material_identification",
    ),
    "SH-35": (
        "original_digest",
        "corrected_digest",
        "correction_time",
        "correction_reason_filer_claim",
        "correcting_seat",
        "old_digest",
        "new_digest",
        "successor_algorithm",
    ),
    "SH-38-entry": (
        "checker_version",
        "time_became_current",
        "packet_form_versions_judged",
        "calibration_fixture_suite_version",
        "calibration_result",
        "declaration_state",
        "events",
    ),
    "SH-38-amendment": (
        "corrected_entry_citation",
    ),
    "SH-44": (
        "digest_algorithm",
        "canonical_form",
        "checker_version",
        "successor_ruling_reference",
    ),
}

MEMBER_FIELDS = ("member_digest", "member_byte_size", "source_kind")
SOURCE_FIELDS = ("source_kind", "source_identity")
RULE_VERSION_FIELDS = ("rule_name", "rule_version")
STANDARD_VERSION_FIELDS = ("standard_name", "standard_version")
SNAPSHOT_FIELDS = (
    "bound_values_and_ruling_digest",
    "latest_calibration_record_digest",
    "gate_record_declaration_state_digest",
    "version_history_determination_digest",
    "algorithm_trust_declaration_digest",
    "pinning_record_digest",
)
BOUND_ENTRY_FIELDS = ("bound_number", "bound_value", "bound_unit")
FIXTURE_RESULT_FIELDS = (
    "fixture_identity_digest",
    "times_run",
    "result_per_check",
    "disagreements",
    "wrongly_named_discrepancies",
)
EVENT_FIELDS = (
    "event_kind",
    "calibration_record_digest",
    "fixture_suite_version",
    "suite_digest",
    "event_result",
    "gate_record_digest",
)


def validate(shape, record):
    """Return the record, or raise ShapeError naming shape and field."""
    allowed = VOCABULARY[shape]
    for name in record:
        if name not in allowed:
            raise ShapeError(
                shape + " record carries a field its shape does not "
                "state: " + name
            )
    return record


def require(shape, record, fields):
    for name in fields:
        if name not in record:
            raise ShapeError(
                shape + " record is missing a field its shape "
                "states: " + name
            )
    return record


def render_fields(pairs):
    """Render a record in its filed form: one field per line.

    Each line is the field name, a colon, a space, and the value, in
    the order the pairs state them, which is the brief order of the
    record field list. Values are rendered by the record modules on
    one line each, so the filed form carries exactly the fields of
    its brief list and no other line.
    """
    lines = []
    for name, value in pairs:
        text = "" if value is None else str(value)
        if "\n" in text:
            raise ShapeError("filed value carries a newline: " + name)
        lines.append(name + ": " + text)
    return "\n".join(lines) + "\n"
