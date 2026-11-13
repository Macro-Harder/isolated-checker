"""Shape validation and record construction, plan module MD-02.

Owns the field lists of the shapes slice S-01 delivers, in the field
name vocabulary plan statement CE-2A fixes. A record is a plain dict
in that vocabulary. Construction through this seam rejects a field
a shape does not state, a field name that stands in no row of the
vocabulary, a record missing a field its shape states, and a value
of the wrong node kind under CE-2; a duplicate cannot arise in a
dict. Every other module receives records only through the builders
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
    "SH-07": (
        "anchored_receipt_digest",
    ),
    "SH-08": (
        "sequence_position",
        "receipt_digest",
    ),
    "SH-13": (
        "custody_receipt_digest",
        "authenticity_verdict",
        "chain_verdict",
        "completeness_verdict",
        "discrepancy_list",
        "binding_fields",
        "unchecked_elements",
        "recorded_gap_elements",
        "resource_counts",
        "calibration_state",
        "honest_limits_fields",
    ),
    "SH-14": (
        "entry_number",
        "check",
        "discrepancy_category",
        "discrepancy_form_name",
        "defect_kind_code",
        "subject_identification",
        "root_cause_key",
        "governing_element_reference",
        "quoted_found_value",
        "one_sided_classification_heading",
        "pending_counterpart_record_reference",
        "routes_tried",
    ),
    "SH-37": (
        "checked_set_receipt_digest",
        "result_word",
        "store_discrepancy",
        "rotation_cursor",
    ),
    "SH-33": (
        "material_identity_best_available",
        "handing_over_seat",
        "failure_time",
        "failure_description",
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
        "checker_version",
        "time_became_current",
        "packet_form_versions_judged",
        "calibration_fixture_suite_version",
        "calibration_result",
        "declaration_state",
        "events",
    ),
    "SH-44": (
        "digest_algorithm",
        "canonical_form",
        "checker_version",
        "successor_ruling_reference",
    ),
    "SH-03": (
        "layout_digest",
        "layout_version",
        "artefact_entries",
        "seat_set",
        "record_kind_sources",
        "publication_time",
        "republication_entries",
    ),
    "SH-16": (
        "classified_item_identification",
        "classification_heading",
        "pending_counterpart_record_reference",
    ),
    "SH-42-source": (
        "source_kind",
        "source_identity",
    ),
    "SH-42-spawn": (
        "spawn_identity",
        "performer_seat",
        "roster_authorisation_record_reference",
    ),
}

ARTEFACT_ENTRY_FIELDS = ("artefact_kind", "content_properties")
RECORD_KIND_SOURCE_FIELDS = ("record_kind", "source_kind")
REPUBLICATION_FIELDS = ("republication_time", "republished_version")
SPAWN_REFERENCE_FIELDS = (
    "spawn_identity",
    "performer_seat",
    "roster_authorisation_record_reference",
)

MEMBER_FIELDS = ("member_digest", "member_byte_size", "source_kind")
SUBJECT_IDENTIFICATION_FIELDS = (
    "identification_form",
    "digest",
    "receipt_position",
)
STORE_DISCREPANCY_FIELDS = (
    "receipt_digest",
    "member_identification",
    "digest_expected",
    "digest_found",
)
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


def _check_node_kind(shape, name, value):
    """Reject a value of the wrong node kind under CE-2.

    CE-2 states six node kinds: record, list, text, count, truth,
    and absent. A count is a non negative integer, and no other
    Python kind stands for a node at this seam.
    """
    if value is None or isinstance(value, (bool, str, list, tuple, dict)):
        return
    if isinstance(value, int):
        if value < 0:
            raise ShapeError(
                shape + " record field " + name + " carries a "
                "negative count, which CE-2 states no node kind for"
            )
        return
    raise ShapeError(
        shape + " record field " + name + " carries a value of a "
        "kind CE-2 does not state: " + type(value).__name__
    )


def validate(shape, record, require_fields=None):
    """Return the record, or raise ShapeError naming shape and field.

    The seam's stated rejections, at MD-02: a field the shape does
    not state, or a field name in no CE-2A row for the shape; a
    value of the wrong node kind under CE-2; and, where the
    building form states its required fields through
    require_fields, a field that form states standing missing,
    through require. A shape row can carry more than one form, as
    SH-30 and SH-35 do, and each builder states the required
    fields of the form it builds.
    """
    allowed = VOCABULARY[shape]
    for name in record:
        if name not in allowed:
            raise ShapeError(
                shape + " record carries a field its shape does not "
                "state: " + name
            )
    if require_fields is not None:
        require(shape, record, require_fields)
    for name, value in record.items():
        _check_node_kind(shape, name, value)
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
