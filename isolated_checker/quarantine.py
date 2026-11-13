"""Quarantine record forms, shape SH-30.

Slice S-01, third record family. The full field list form is brief
section 5.24: the marking placed in a current home carries the
report digest of the report that failed the material, the
discrepancies it must answer, and the failure wording. A record of
a failure, as distinct from an ingestion of failed material,
carries the report digest, the failure wording, and the failed
material identification, and no failed content beyond the minimum
a reader needs to identify the material.
"""

from . import shapes


def quarantine_record(report_digest, discrepancies_to_answer, failure_wording):
    """Build a quarantine marking record in the SH-30 form."""
    record = {
        "report_digest": report_digest,
        "discrepancies_to_answer": list(discrepancies_to_answer),
        "failure_wording": failure_wording,
    }
    return shapes.validate(
        "SH-30",
        record,
        ("report_digest", "discrepancies_to_answer", "failure_wording"),
    )


def quarantine_filed_text(record):
    """Render a quarantine marking in its filed form, brief order."""
    discrepancies = "; ".join(
        str(number) for number in record["discrepancies_to_answer"]
    )
    return shapes.render_fields(
        [
            ("report digest", record["report_digest"]),
            ("discrepancies", discrepancies),
            ("failure wording", record["failure_wording"]),
        ]
    )


def failure_record(report_digest, failure_wording, material_digest, material_kind):
    """Build a record of a failure in the SH-30 form."""
    record = {
        "report_digest": report_digest,
        "failure_wording": failure_wording,
        "failed_material_identification": {
            "material_digest": material_digest,
            "material_kind": material_kind,
        },
    }
    return shapes.validate(
        "SH-30",
        record,
        ("report_digest", "failure_wording", "failed_material_identification"),
    )


def failure_filed_text(record):
    """Render a record of a failure in its filed form."""
    identification = record["failed_material_identification"]
    return shapes.render_fields(
        [
            ("report digest", record["report_digest"]),
            ("failure wording", record["failure_wording"]),
            (
                "failed material identification",
                identification["material_digest"]
                + " " + identification["material_kind"],
            ),
        ]
    )
