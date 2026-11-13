"""Custody receipt and context record forms, shapes SH-06 and SH-05.

Slice S-01, first record family. The custody receipt field list is
brief section 5.3 and the context record field list is brief
section 5.28; the canonical field names are the CE-2A rows for
SH-06 and SH-05. Pairing runs in one direction only: the receipt
names the context record by digest, and the context record names
no receipt digest. The receipt self digest is a value computed
under the canonical module (plan module MD-01) with the self
digest field omitted, under CE-3; this module carries the value
and renders it, and the canonical module computes it.
"""

from . import shapes
from .shapes import ShapeError


def member(member_digest, member_byte_size, source_kind):
    """One receipt member entry, in the owned forms."""
    if not isinstance(member_byte_size, int) or member_byte_size < 0:
        raise ShapeError("SH-06 member byte size is not a count")
    return {
        "member_digest": member_digest,
        "member_byte_size": member_byte_size,
        "source_kind": source_kind,
    }


def custody_receipt(
    build,
    stage,
    members,
    freezing_seat,
    handing_over_seat,
    freeze_time,
    sequence_position,
    predecessor_receipt_digest,
    context_record_digest,
    self_digest=None,
):
    """Build a custody receipt record in the SH-06 form.

    sequence_position is the position in the intake order for its
    gate, a count from 1. The first receipt for a gate carries
    position 1 and no predecessor digest; every later receipt
    carries the digest of the receipt before it.
    """
    if not isinstance(sequence_position, int) or sequence_position < 1:
        raise ShapeError("SH-06 sequence position is not a count from 1")
    if sequence_position == 1 and predecessor_receipt_digest is not None:
        raise ShapeError(
            "SH-06 first receipt carries no predecessor digest"
        )
    if sequence_position > 1 and predecessor_receipt_digest is None:
        raise ShapeError(
            "SH-06 receipt after the first carries a predecessor digest"
        )
    record = {
        "build": build,
        "stage": stage,
        "members": [
            member(m["member_digest"], m["member_byte_size"], m["source_kind"])
            for m in members
        ],
        "freezing_seat": freezing_seat,
        "handing_over_seat": handing_over_seat,
        "freeze_time": freeze_time,
        "sequence_position": sequence_position,
        "predecessor_receipt_digest": predecessor_receipt_digest,
        "context_record_digest": context_record_digest,
        "self_digest": self_digest,
    }
    return shapes.validate("SH-06", record, shapes.VOCABULARY["SH-06"])


def anchor_entry(anchored_receipt_digest):
    """Build an anchor record entry in the SH-07 form.

    The CE-2A row for SH-07 names anchored_receipt_digest alone.
    The anchor entry value the freeze operation returns is this
    record, built and required through the MD-02 seam, and no
    other key stands in it.
    """
    record = {"anchored_receipt_digest": anchored_receipt_digest}
    return shapes.validate("SH-07", record, shapes.VOCABULARY["SH-07"])


def intake_failure_record(
    material_identity_best_available,
    handing_over_seat,
    failure_time,
    failure_description,
):
    """Build an intake failure record in the SH-33 form.

    The record names the material by the best identity available,
    the seat handing it over, the time, and the failure, in the
    CE-2A field names for SH-33, built and required through the
    MD-02 seam. It is filed outside the frozen set, is not a
    report, issues no verdict, and takes no exit status.
    """
    record = {
        "material_identity_best_available": material_identity_best_available,
        "handing_over_seat": handing_over_seat,
        "failure_time": failure_time,
        "failure_description": failure_description,
    }
    return shapes.validate("SH-33", record, shapes.VOCABULARY["SH-33"])


def receipt_filed_text(record):
    """Render a custody receipt in its filed form, brief order."""
    members = "; ".join(
        m["member_digest"] + " " + str(m["member_byte_size"])
        for m in record["members"]
    )
    sources = "; ".join(m["source_kind"] for m in record["members"])
    if record["sequence_position"] == 1:
        sequence = "first"
    else:
        sequence = (
            "position " + str(record["sequence_position"])
            + "; predecessor receipt digest "
            + str(record["predecessor_receipt_digest"])
        )
    handing = record["handing_over_seat"]
    return shapes.render_fields(
        [
            ("build", record["build"]),
            ("stage", record["stage"]),
            ("members", members),
            ("member sources", sources),
            ("frozen by seat", record["freezing_seat"]),
            ("handed over by seat", handing if handing is not None else "absent"),
            ("freeze time", record["freeze_time"]),
            ("sequence element", sequence),
            ("context record digest", record["context_record_digest"]),
            ("receipt self digest", record["self_digest"]),
        ]
    )


def _version_pairs(pairs, fields, shape):
    rendered = []
    for pair in pairs:
        for name in pair:
            if name not in fields:
                raise ShapeError(
                    shape + " version entry carries an unnamed field: " + name
                )
        rendered.append(dict(pair))
    return rendered


def context_record(
    build,
    stage,
    packet_form_version,
    digest_algorithm,
    canonical_form,
    standing_rule_versions,
    outside_standard_versions,
):
    """Build a context record in the SH-05 form.

    Carries the set intrinsic fields only: no receipt digest, no
    verdict, no grade, and none of the run specific fields, which
    live in the run statement. The algorithm and canonical form
    values stand as claims compared against the pair pinned
    outside the frozen set.
    """
    record = {
        "build": build,
        "stage": stage,
        "packet_form_version": packet_form_version,
        "digest_algorithm": digest_algorithm,
        "canonical_form": canonical_form,
        "standing_rule_versions": _version_pairs(
            standing_rule_versions, shapes.RULE_VERSION_FIELDS, "SH-05"
        ),
        "outside_standard_versions": _version_pairs(
            outside_standard_versions, shapes.STANDARD_VERSION_FIELDS, "SH-05"
        ),
    }
    return shapes.validate("SH-05", record, shapes.VOCABULARY["SH-05"])


def context_filed_text(record):
    """Render a context record in its filed form, brief order."""
    rules = "; ".join(
        p["rule_name"] + " " + p["rule_version"]
        for p in record["standing_rule_versions"]
    )
    standards = "; ".join(
        p["standard_name"] + " " + p["standard_version"]
        for p in record["outside_standard_versions"]
    )
    return shapes.render_fields(
        [
            ("build", record["build"]),
            ("stage", record["stage"]),
            ("packet form version", record["packet_form_version"]),
            (
                "digest algorithm and canonical form",
                record["digest_algorithm"] + "; " + record["canonical_form"],
            ),
            ("standing rules versions", rules),
            ("outside standards versions", standards),
        ]
    )
