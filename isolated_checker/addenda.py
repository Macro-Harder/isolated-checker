"""Addendum form, shape SH-35.

Slice S-01, third record family. The field list is brief section
5.31: an addendum names the original digest, the corrected digest,
the time of the correction, the reason stated as the filer claim,
and the seat that filed the correction. The same form carries a
second digesting under a successor algorithm, binding the old and
new digests side by side, in the second digesting fields only.
A correction time in an addendum is a filer claim, never a
checked fact.
"""

from . import shapes
from .shapes import ShapeError


def addendum(
    original_digest,
    corrected_digest,
    correction_time,
    correction_reason_filer_claim,
    correcting_seat,
    old_digest=None,
    new_digest=None,
    successor_algorithm=None,
):
    """Build an addendum record in the SH-35 form."""
    second = (old_digest, new_digest, successor_algorithm)
    if any(value is not None for value in second) and not all(
        value is not None for value in second
    ):
        raise ShapeError(
            "SH-35 second digesting form carries all three of its "
            "fields or none"
        )
    record = {
        "original_digest": original_digest,
        "corrected_digest": corrected_digest,
        "correction_time": correction_time,
        "correction_reason_filer_claim": correction_reason_filer_claim,
        "correcting_seat": correcting_seat,
    }
    if all(value is not None for value in second):
        record["old_digest"] = old_digest
        record["new_digest"] = new_digest
        record["successor_algorithm"] = successor_algorithm
    return shapes.validate("SH-35", record)


def addendum_filed_text(record):
    """Render an addendum in its filed form, brief order."""
    return shapes.render_fields(
        [
            ("original digest", record["original_digest"]),
            ("corrected digest", record["corrected_digest"]),
            ("correction time", record["correction_time"]),
            ("reason", record["correction_reason_filer_claim"]),
            ("filed by seat", record["correcting_seat"]),
        ]
    )
