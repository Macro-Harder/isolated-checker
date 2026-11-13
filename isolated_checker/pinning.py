"""Pinning record form, shape SH-44, plan module MD-02.

The record family home of the pinning record: the record that
carries the pinned pair every digest in the product is computed
under, one record per checker version. Construction of each
record type from its stated fields is the duty plan Part 2
section 6 assigns to MD-02, landed as one file per record family;
the canonical core at MD-01 takes record values in the primitive
types only and owns encoding and digest computation, so the
SH-44 builder stands here, not in canonical.py. The pinning
record's citation digest stays a canonical duty, at
canonical.pinning_citation_digest under CE-4.
"""

from . import shapes


def pinning_record(
    digest_algorithm, canonical_form, checker_version,
    successor_ruling_reference=None,
):
    """Build a pinning record in the SH-44 form.

    Fields: the digest algorithm name; the canonical form name;
    the checker version the pair is bound to; and a successor
    ruling reference, present only where a ruling has put a
    successor algorithm in force for that version, and absent
    valued otherwise.
    """
    record = {
        "digest_algorithm": digest_algorithm,
        "canonical_form": canonical_form,
        "checker_version": checker_version,
        "successor_ruling_reference": successor_ruling_reference,
    }
    return shapes.validate("SH-44", record, shapes.VOCABULARY["SH-44"])
