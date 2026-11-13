"""Canonical form and digest core, plan module MD-01.

The pinned digest and canonical form convention of brief section
5.4, as encoded by plan statements CE-2, CE-3, and CE-4. The
canonical encoding is Canonical Field Encoding 1, CFE-1: one
encoding for all record types. This module is a pure core: it
takes record values and returns bytes or digests, reads no file,
no clock, and no platform state, and the same inputs give the
same outputs on any host.

The pinned pair, the digest algorithm and the canonical form
name, is bound to the checker version and its calibration record
under the version bound branch CE-1 records, carried in the
pinning record at SH-44, and no value inside the frozen set
chooses it. The algorithm is supplied as a value to every digest
function here, exactly as MD-01 states.
"""

import hashlib

from . import shapes
from .shapes import ShapeError

PRODUCT_NAME = "isolated-checker-canonical-form"
CANONICAL_FORM = "CFE-1"
DEFAULT_ALGORITHM = "SHA-256"

_ALGORITHMS = {
    "SHA-256": hashlib.sha256,
    "SHA-1": hashlib.sha1,
    "SHA-512": hashlib.sha512,
}


def _algorithm(name):
    try:
        return _ALGORITHMS[name]
    except KeyError:
        raise ShapeError(
            "CE-4 pinned algorithm is not one this module applies: "
            + str(name)
        )


def encode_node(value):
    """Encode one node value under CE-2, returning bytes."""
    if value is None:
        return b"N;"
    if isinstance(value, bool):
        return b"B1;" if value else b"B0;"
    if isinstance(value, int):
        if value < 0:
            raise ShapeError("CE-2 count node carries a negative value")
        return b"I" + str(value).encode("ascii") + b";"
    if isinstance(value, str):
        data = value.encode("utf-8")
        return b"S" + str(len(data)).encode("ascii") + b":" + data
    if isinstance(value, (list, tuple)):
        parts = [b"L" + str(len(value)).encode("ascii") + b":"]
        for item in value:
            parts.append(encode_node(item))
        return b"".join(parts)
    if isinstance(value, dict):
        names = sorted(value, key=lambda name: name.encode("utf-8"))
        parts = [b"M" + str(len(names)).encode("ascii") + b":"]
        for name in names:
            parts.append(encode_node(name))
            parts.append(encode_node(value[name]))
        return b"".join(parts)
    raise ShapeError(
        "CE-2 has no node kind for a value of type "
        + type(value).__name__
    )


def encode_record(record_type, fields):
    """Encode a whole record under CE-2, header text nodes first."""
    return b"".join(
        [
            encode_node(PRODUCT_NAME),
            encode_node(CANONICAL_FORM),
            encode_node(record_type),
            encode_node(dict(fields)),
        ]
    )


class _Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def read_until(self, marker):
        end = self.data.index(marker, self.pos)
        text = self.data[self.pos:end]
        self.pos = end + 1
        return text

    def node(self):
        kind = chr(self.data[self.pos])
        self.pos += 1
        if kind == "N":
            self.pos += 1
            return None
        if kind == "B":
            value = self.data[self.pos] == ord("1")
            self.pos += 2
            return value
        if kind == "I":
            return int(self.read_until(b";"))
        if kind == "S":
            length = int(self.read_until(b":"))
            raw = self.data[self.pos:self.pos + length]
            self.pos += length
            return raw.decode("utf-8")
        if kind == "L":
            count = int(self.read_until(b":"))
            return [self.node() for _ in range(count)]
        if kind == "M":
            count = int(self.read_until(b":"))
            record = {}
            for _ in range(count):
                name = self.node()
                record[name] = self.node()
            return record
        raise ShapeError("CE-2 byte form carries an unknown node kind")


def decode_record(data):
    """Decode a whole record encoding, returning its type and fields."""
    reader = _Reader(data)
    product = reader.node()
    form = reader.node()
    record_type = reader.node()
    if product != PRODUCT_NAME or form != CANONICAL_FORM:
        raise ShapeError("CE-2 encoding header does not name CFE-1")
    fields = reader.node()
    if reader.pos != len(data):
        raise ShapeError("CE-2 encoding carries trailing bytes")
    return record_type, fields


def raw_digest(data, algorithm=DEFAULT_ALGORITHM):
    """Raw application of the pinned algorithm to bytes, CE-4."""
    return _algorithm(algorithm)(data).hexdigest()


def record_digest(record_type, fields, algorithm=DEFAULT_ALGORITHM, omit=()):
    """Digest a whole record encoding, with fields omitted by name.

    The omission is the CE-3 form: an omitted field is not present
    in the record node, the field count excludes it, and no absent
    node stands in its place.
    """
    kept = {
        name: value for name, value in fields.items() if name not in omit
    }
    return raw_digest(encode_record(record_type, kept), algorithm)


def receipt_self_digest(record, algorithm=DEFAULT_ALGORITHM):
    """The custody receipt self digest, CE-4 row for SH-06."""
    return record_digest("SH-06", record, algorithm, omit=("self_digest",))


def with_receipt_self_digest(record, algorithm=DEFAULT_ALGORITHM):
    """Return a receipt record carrying its computed self digest."""
    completed = dict(record)
    completed["self_digest"] = receipt_self_digest(record, algorithm)
    return completed


def run_statement_self_digest(record, algorithm=DEFAULT_ALGORITHM):
    """The run statement self digest, CE-4 row for SH-11."""
    return record_digest("SH-11", record, algorithm, omit=("self_digest",))


def with_run_statement_self_digest(record, algorithm=DEFAULT_ALGORITHM):
    """Return a run statement record carrying its self digest."""
    completed = dict(record)
    completed["self_digest"] = run_statement_self_digest(record, algorithm)
    return completed


def calibration_citation_digest(record, algorithm=DEFAULT_ALGORITHM):
    """The calibration record citation digest, CE-4 row for SH-22.

    Every field the record carries is present and no field is
    omitted, because no self digest field stands in the record.
    """
    return record_digest("SH-22", record, algorithm)


def pinning_record(
    digest_algorithm, canonical_form, checker_version,
    successor_ruling_reference=None,
):
    """Build a pinning record in the SH-44 form."""
    record = {
        "digest_algorithm": digest_algorithm,
        "canonical_form": canonical_form,
        "checker_version": checker_version,
        "successor_ruling_reference": successor_ruling_reference,
    }
    return shapes.validate("SH-44", record, shapes.VOCABULARY["SH-44"])


def pinning_citation_digest(record, algorithm=DEFAULT_ALGORITHM):
    """The pinning record citation digest, CE-4 row for SH-44."""
    return record_digest("SH-44", record, algorithm)


def context_claim_matches(context, pinning):
    """Compare a context record claim against the pinned pair.

    The context record values for algorithm and canonical form
    stand as claims compared against the pair pinned outside the
    frozen set, as brief section 5.4 states.
    """
    return (
        context["digest_algorithm"] == pinning["digest_algorithm"]
        and context["canonical_form"] == pinning["canonical_form"]
    )


def git_blob_digest(data):
    """A content digest over artefact bytes, in the owned form.

    Git blob framing, then SHA-1. This family is not a CFE-1
    computation and the pinned pair does not govern it.
    """
    header = b"blob " + str(len(data)).encode("ascii") + b"\x00"
    return hashlib.sha1(header + data).hexdigest()


member_digest = git_blob_digest


def set_digest(members, algorithm=DEFAULT_ALGORITHM):
    """The run computed set digest, CE-4 row for RT-04.

    Computed over the member digests and byte sizes in receipt
    order, each member a record node holding its member digest as
    text and its member byte size as a count.
    """
    record = {
        "members": [
            {
                "member_digest": entry["member_digest"],
                "member_byte_size": entry["member_byte_size"],
            }
            for entry in members
        ]
    }
    return record_digest("set-digest-input", record, algorithm)


def _fixture_identity_fields(fixture):
    return {
        "defect_kind_code": fixture["defect_kind_code"],
        "form_class": fixture["form_class"],
        "fixture_packet_member_list": [
            {
                "member_digest": entry["member_digest"],
                "member_byte_size": entry["member_byte_size"],
            }
            for entry in fixture["fixture_packet_member_list"]
        ],
        "expected_outcome_record": fixture["expected_outcome_record"],
    }


def fixture_identity_digest(fixture, algorithm=DEFAULT_ALGORITHM):
    """The fixture identity digest, CE-4 row for RT-02, plan Q5."""
    return record_digest(
        "fixture-identity", _fixture_identity_fields(fixture), algorithm
    )


def suite_digest(fixtures, algorithm=DEFAULT_ALGORITHM):
    """The suite digest, CE-4 row for RT-03, plan Q5.

    Computed over the fixture packets and their expected outcome
    records together, in suite order. The suite digest is not a
    digest of identity digest texts, and no fixture is digested
    twice in its construction.
    """
    record = {
        "fixtures": [_fixture_identity_fields(f) for f in fixtures]
    }
    return record_digest("suite-digest-input", record, algorithm)


def equivalence_equal(first, second, algorithm=DEFAULT_ALGORITHM):
    """Equivalence comparison of two equivalence parts, CE-4.

    Two equivalence parts agree exactly where their whole record
    encodings are byte equal, each part encoded as a whole record
    under the registered name equivalence-part, RT-01. The
    algorithm argument stands unused: the comparison is byte
    equality, not a digest.
    """
    return encode_record("equivalence-part", first) == encode_record(
        "equivalence-part", second
    )
