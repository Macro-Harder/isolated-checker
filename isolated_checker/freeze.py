"""Freeze intake core, plan module MD-03, slice S-03.

Owns contract CT-01 in its core part, resting on brief sections
5.2 to 5.4 and the freeze intake contract in brief section 11.
This module writes nothing itself: it receives handed in material
as member byte strings with source kinds, in two full passes, and
returns the frozen set, the context record, the custody receipt,
and the anchor entry value, or an intake failure record value.
The shell performs the store write and the anchor write it is
handed, under the dual write protocol at CT-01, with the anchor
write as the commit point.

Freeze order, as brief section 5.4 states it: member enumeration
is closed first; each member is read and copied; a second full
pass follows, compared digest by digest against the copies; the
receipt issues only on equality of the two passes. Any difference
between the two passes is an intake failure and no receipt
issues. Material that cannot be frozen takes the intake failure
record at SH-33, filed outside the frozen set, with no report and
no exit status. One custody receipt per committed freeze, at the
moment the intake set is frozen, and never a second receipt or a
second anchor entry for one committed freeze.

No parameter is taken from packet material: every input to this
module is a named intake input supplied by the operator side, and
member bytes are read through the data only reading layer of
slice S-02. Counting hooks for the resource bounds of slice S-13
are landed with this slice reading path, as statement P1-S13-3
requires, through the reading counter the caller may pass in.

The reads CT-01 names stand as inputs of this module, not as
values it makes: the pinning record at SH-44, the standing rules
and outside standards versions source, and the anchor home naming
the gate record states. The context record claims are compared
against the pinning record as SH-44 states, claim against pin: a
claim that disagrees with the pin, or a freeze called with no
pinning record read, issues no receipt and takes the intake
failure form. The context record is built with the standing rule
and outside standard version lists exactly as read.
"""

from . import canonical, pinning, receipts
from .reading import ReadingCounter, read_member

# The qualified form of the anchor duty, brief section 5.3, stated
# once here and carried wherever the anchor is relied on.
ANCHOR_QUALIFIED_FORM = (
    "detects accident and casual rewriting, not a determined editor"
)

FREEZING_SEAT = "gate verifier"
HANDING_SEAT = "producer seat"


def _pass_readings(members, counter):
    """Read one full pass of handed in material, data only.

    Every member's digest is recomputed from its bytes through
    the reading layer, on both passes, as MD-03, brief section
    5.4, and XR-03 state: freeze intake receives member byte
    strings, and no presented digest is ever carried into a
    reading as a substitute for recomputation. A member presented
    without bytes, by digest and byte size only, cannot be
    frozen: its bytes cannot be had, so it takes the intake
    failure form. An unreadable member, and an uncovered member
    form the reading layer will not read, cannot be frozen.
    """
    readings = []
    for member in members:
        if member.get("unreadable"):
            readings.append(
                {
                    "name": str(member.get("name", "unnamed material")),
                    "cannot_be_frozen": True,
                    "failure": "material cannot be read",
                }
            )
            continue
        if member.get("content") is None:
            readings.append(
                {
                    "name": str(member.get("name", "unnamed material")),
                    "cannot_be_frozen": True,
                    "failure": (
                        "member bytes cannot be had: the member was "
                        "presented by digest and byte size only, with "
                        "no bytes to recompute from"
                    ),
                }
            )
            continue
        reading = read_member(member, counter)
        if reading["unchecked"]:
            readings.append(
                {
                    "name": reading["name"],
                    "cannot_be_frozen": True,
                    "failure": (
                        "member form is uncovered and cannot be frozen: "
                        + reading["form"]
                    ),
                }
            )
            continue
        readings.append(
            {
                "name": reading["name"],
                "cannot_be_frozen": False,
                "digest_git_blob_sha1": reading["digest_git_blob_sha1"],
                "byte_size": reading["byte_size"],
                "source_kind": member.get("source_kind", "handed in material"),
                "content": reading["content"],
            }
        )
    return readings


def freeze_intake(
    members_first_pass,
    members_second_pass,
    build,
    stage,
    packet_form_version,
    checker_version,
    freeze_time,
    freezing_seat=FREEZING_SEAT,
    handing_over_seat=HANDING_SEAT,
    sequence_position=1,
    predecessor_receipt_digest=None,
    counter=None,
    pinning_record=None,
    standing_rule_versions=None,
    outside_standard_versions=None,
    anchor_home=None,
    context_claim=None,
):
    """Run freeze intake over two full passes of handed in material.

    Returns a frozen result carrying the member copies, the
    context record and its digest, the custody receipt carrying
    its self digest, and the anchor entry value; or an intake
    failure result carrying the intake failure record value at
    SH-33 and the names of any members whose two passes diverge.
    The retry and staged copy rules of CT-01 stand in the shell:
    a retry of an uncommitted attempt reuses staged copies only
    after verifying each one digest by digest, and this core is
    rerun for the attempt, issuing the one receipt for it.

    pinning_record is the pinning record at SH-44 as read, in its
    field form; standing_rule_versions and
    outside_standard_versions are the version lists as read from
    the standing versions source; anchor_home is the anchor home
    naming the gate record states; context_claim, where supplied,
    presents the digest algorithm and canonical form the set
    claims, and where it is not supplied the claim is the pair
    bound to the checker version. The claim is compared against
    the pin before any receipt issues, as SH-44 states.
    """
    if counter is None:
        counter = ReadingCounter()
    # Member enumeration is closed first: the two passes must name
    # the same members, in the same order of enumeration.
    first = _pass_readings(members_first_pass, counter)
    for reading in first:
        if reading["cannot_be_frozen"]:
            return _failure(
                reading["name"], handing_over_seat, freeze_time,
                reading["failure"], [],
            )
    second = _pass_readings(members_second_pass, counter)
    for reading in second:
        if reading["cannot_be_frozen"]:
            return _failure(
                reading["name"], handing_over_seat, freeze_time,
                reading["failure"], [],
            )
    divergent = []
    if [r["name"] for r in first] != [r["name"] for r in second]:
        divergent = sorted(
            {r["name"] for r in first} ^ {r["name"] for r in second}
        )
    else:
        for one, two in zip(first, second):
            if (
                one["digest_git_blob_sha1"] != two["digest_git_blob_sha1"]
                or one["byte_size"] != two["byte_size"]
            ):
                divergent.append(one["name"])
    if divergent:
        return _failure(
            ", ".join(divergent), handing_over_seat, freeze_time,
            "the two full set passes of the freeze differ", divergent,
        )
    # Equality of the two passes stands, and the pin comparison
    # of SH-44 stands next, before any receipt issues: the
    # context record claim is compared against the pinning record
    # as read, never against a record minted here.
    if pinning_record is None:
        return _failure(
            "pinning record", handing_over_seat, freeze_time,
            "no pinning record was read for this freeze", [],
        )
    pin = pinning.pinning_record(
        pinning_record["digest_algorithm"],
        pinning_record["canonical_form"],
        pinning_record["checker_version"],
        pinning_record.get("successor_ruling_reference"),
    )
    if context_claim is None:
        claim = {
            "digest_algorithm": canonical.DEFAULT_ALGORITHM,
            "canonical_form": canonical.CANONICAL_FORM,
        }
    else:
        claim = {
            "digest_algorithm": context_claim["digest_algorithm"],
            "canonical_form": context_claim["canonical_form"],
        }
    if (
        pin["checker_version"] != checker_version
        or claim["digest_algorithm"] != pin["digest_algorithm"]
        or claim["canonical_form"] != pin["canonical_form"]
    ):
        return _failure(
            "context record claim", handing_over_seat, freeze_time,
            "the context record claim does not match the pinning record",
            [],
        )
    # The receipt may issue. Members stand in the receipt in
    # receipt order, by member name. The context record carries
    # the claimed pair, now compared, and the version lists
    # exactly as read.
    ordered = sorted(first, key=lambda reading: reading["name"])
    context = receipts.context_record(
        build,
        stage,
        packet_form_version,
        claim["digest_algorithm"],
        claim["canonical_form"],
        list(standing_rule_versions) if standing_rule_versions else [],
        list(outside_standard_versions) if outside_standard_versions else [],
    )
    context_digest = canonical.record_digest("SH-05", context)
    receipt = receipts.custody_receipt(
        build,
        stage,
        [
            {
                "member_digest": reading["digest_git_blob_sha1"],
                "member_byte_size": reading["byte_size"],
                "source_kind": reading["source_kind"],
            }
            for reading in ordered
        ],
        freezing_seat,
        handing_over_seat,
        freeze_time,
        sequence_position,
        predecessor_receipt_digest,
        context_digest,
    )
    receipt = canonical.with_receipt_self_digest(receipt)
    receipt_digest = receipt["self_digest"]
    anchor_entry = receipts.anchor_entry(receipt_digest)
    return {
        "status": "frozen",
        "members": ordered,
        "context_record": context,
        "context_digest": context_digest,
        "receipt": receipt,
        "receipt_digest": receipt_digest,
        "anchor_entry": anchor_entry,
        "pinning_record": pin,
        "anchor_home": anchor_home,
        "counter": counter,
    }


def _failure(material, handing_over_seat, freeze_time, failure, divergent):
    """The intake failure result, record form at SH-33.

    The failure record is built through the MD-02 record form at
    receipts.intake_failure_record, in the CE-2A field names for
    SH-33, never as a plain dict in unregistered keys.
    """
    return {
        "status": "intake failure",
        "failure_record": receipts.intake_failure_record(
            material, handing_over_seat, freeze_time, failure
        ),
        "divergent_members": divergent,
    }


def intake_failure_filed_text(record):
    """Render an intake failure record in its filed form, SH-33.

    The record is filed outside the frozen set. It is not a
    report, issues no verdict, and takes no exit status.
    """
    lines = [
        "intake failure record",
        "material: " + str(record["material_identity_best_available"]),
        "handed over by seat: " + str(record["handing_over_seat"]),
        "time: " + str(record["failure_time"]),
        "failure: " + str(record["failure_description"]),
    ]
    return "\n".join(lines) + "\n"
