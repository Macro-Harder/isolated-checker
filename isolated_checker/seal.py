"""Seal phase, plan module MD-04, slice S-04.

Owns the seal comparison set of contract XR-01, resting on brief
sections 5.4 and 5.5: receipt recomputation against members,
anchor comparison, and sequence comparison against the intake
order field. It is one owning phase with one emission form,
called by every operation module that reads a frozen set and
issues a report or a verdict, and it is not reimplemented inside
any of them. The seven operations it opens stand named once, in
SEAL_OPERATIONS.

The seal consumes the frozen intake exactly as the cured freeze
surface issues it. The custody receipt is a record in the SH-06
form built through the MD-02 seam at receipts.custody_receipt and
completed under the self digest omission at CE-3; no filed
digest in it is trusted, under XR-03, and the receipt self digest
is recomputed here before any comparison rests on it. Member
digests are recomputed from member bytes through the data only
reading layer of MD-16, never taken from a presented digest: a
member presented by digest and byte size only, with no bytes to
recompute from, fails the member digest comparison, in the form
the cured freeze established for the same presentation. The
anchor entry is consumed in the SH-07 form receipts.anchor_entry
builds, the intake order in the SH-08 item form, and the pinning
comparison of SH-44 stands already made at freeze, in pinning.py;
this phase mints no pin and rewrites no receipt.

Emission. A broken seal takes the one emission form of brief
section 5.5: a discrepancy report without a verdict, or, for the
recheck, its recheck report in verdict run form, carrying the
custody gap as a chain discrepancy in its own right, the receipt
digest, and the seal comparison that failed, at exit status 1
where the receipt comparison supports the determination and at
exit status 2 where it supports none. The report record stands
in the SH-13 form and each custody gap entry in the SH-14 form,
both built through the MD-02 seam with their required fields
stated per form, in the pattern the cure wave established across
the package. No verdict field stands in the seal break report:
the checks have not run, and no verdict issues over bytes the
receipt does not describe.

Neighbouring event forms, stated once here as plan statement
P1-S04-1 charges, so later slices cite one home. The intake
failure form is the SH-33 record at receipts.intake_failure_record,
delivered with freeze intake and cited here, never rebuilt. The
seal break form is the SH-13 and SH-14 pair this module builds.
The fixity mismatch form is the SH-37 store discrepancy record
this module builds at fixity_mismatch_record: a custody gap
against the store only, issuing no discrepancy report and taking
no exit status, as brief section 5.5 states; the fixity operation
that writes it into the store record stands with its own slice
and cites this form.

Counting hooks for the resource bounds of slice S-13 stand in
this phase, as statement P1-S13-3 requires: a hook for every byte
the seal phase reads, carried by the reading counter the caller
may pass in, which the reading layer notes member by member and
which this phase notes for the receipt recomputation. No bound
value is named or applied here.
"""

from . import canonical, shapes
from .reading import ReadingCounter, read_member
from .shapes import ShapeError

SEAL_OPERATIONS = (
    "verdict run",
    "rerun",
    "appeal run",
    "cure run",
    "corrected run",
    "dry run",
    "CH7 recheck",
)

OUTCOME_CUSTODY_GAP = "custody gap"

COMPARISON_MEMBER_DIGEST = "member digest comparison"
COMPARISON_MEMBER_PRESENCE = "member presence comparison"
COMPARISON_ANCHOR = "anchor comparison"
COMPARISON_RECEIPT_RECOMPUTATION = "receipt recomputation"
COMPARISON_BUILD_STAGE = "receipt build and stage comparison"
COMPARISON_SEQUENCE = "sequence comparison"

# The sequence cases that stand undetermined where no intake
# order record stands for a gate, reported unchecked by name in
# the form brief section 5.4 and shape SH-08 state.
SEQUENCE_UNCHECKED_NAMES = ("receipt chain ends early", "whole intake removal")

# The neighbouring intake failure form, cited to its one home.
INTAKE_FAILURE_FORM_HOME = "receipts.intake_failure_record (SH-33)"


def intake_order_item(sequence_position, receipt_digest):
    """Build one intake order item in the SH-08 form.

    The intake order field at SH-08 is a gate record field the
    operator writes as each intake for a gate freezes; its items
    carry a sequence position and a receipt digest, and this
    builder is the form the seal phase reads those items in,
    built and required through the MD-02 seam.
    """
    if not isinstance(sequence_position, int) or sequence_position < 1:
        raise ShapeError("SH-08 sequence position is not a count from 1")
    record = {
        "sequence_position": sequence_position,
        "receipt_digest": receipt_digest,
    }
    return shapes.validate("SH-08", record, shapes.VOCABULARY["SH-08"])


def custody_gap_entry(
    entry_number,
    governing_element_reference,
    subject_name,
    subject_digest,
    receipt_position,
):
    """Build one custody gap discrepancy entry in the SH-14 form.

    The entry is the custody gap carried as a chain discrepancy in
    its own right: its check is chain, its discrepancy category is
    custody gap, and its defect kind code stands absent valued,
    because the custody gap naming source is the outcome passages
    themselves and no kind code is invented for it, as plan Q2
    states. The fields Q2 requires on every entry stand required
    through the seam: entry number, check, discrepancy category,
    subject identification, root cause key, and governing element
    reference. The root cause key is a text key over the check,
    the governing element reference, and the cause name, as Q4
    states the key's parts, and subject identity does not stand
    in it. A subject is identified by digest where a digest
    exists for it, with its receipt position where it is a member;
    a subject with a name and no digest stands not located.
    """
    if subject_digest is None and subject_name is None:
        raise ShapeError(
            "SH-14 custody gap entry names no subject element: "
            "a subject digest or a subject name stands required"
        )
    identification = {
        "identification_form": "digest" if subject_digest else "not located",
        "digest": subject_digest,
        "receipt_position": receipt_position,
    }
    for name in identification:
        if name not in shapes.SUBJECT_IDENTIFICATION_FIELDS:
            raise ShapeError(
                "SH-14 subject identification carries an unnamed field: " + name
            )
    record = {
        "entry_number": entry_number,
        "check": "chain",
        "discrepancy_category": OUTCOME_CUSTODY_GAP,
        "discrepancy_form_name": None,
        "defect_kind_code": None,
        "subject_identification": identification,
        "root_cause_key": (
            "chain:" + governing_element_reference + ":" + OUTCOME_CUSTODY_GAP
        ),
        "governing_element_reference": governing_element_reference,
        "quoted_found_value": None,
        "one_sided_classification_heading": None,
        "pending_counterpart_record_reference": None,
        "routes_tried": None,
    }
    return shapes.validate(
        "SH-14",
        record,
        (
            "entry_number",
            "check",
            "discrepancy_category",
            "subject_identification",
            "root_cause_key",
            "governing_element_reference",
        ),
    )


def seal_break_report(custody_receipt_digest, discrepancy_entries, unchecked_elements=()):
    """Build the seal break report record in the SH-13 form.

    The one emission form for a broken seal: a discrepancy report
    without a verdict. The custody receipt digest, the discrepancy
    list carrying the custody gap entries, and the unchecked
    elements stand in it; every verdict field stands absent
    valued, because the seal phase runs before any check and no
    verdict issues over a broken set. Built and required through
    the MD-02 seam.
    """
    record = {
        "custody_receipt_digest": custody_receipt_digest,
        "authenticity_verdict": None,
        "chain_verdict": None,
        "completeness_verdict": None,
        "discrepancy_list": list(discrepancy_entries),
        "binding_fields": None,
        "unchecked_elements": list(unchecked_elements),
        "recorded_gap_elements": [],
        "resource_counts": None,
        "calibration_state": None,
        "honest_limits_fields": None,
    }
    return shapes.validate(
        "SH-13",
        record,
        ("custody_receipt_digest", "discrepancy_list", "unchecked_elements"),
    )


def fixity_mismatch_record(
    checked_set_receipt_digest,
    member_identification,
    digest_expected,
    digest_found,
    rotation_cursor=None,
):
    """Build a fixity mismatch record in the SH-37 form.

    The neighbouring event form section 5.5 states once: a fixity
    mismatch is a custody gap against the store only, recorded in
    the store record, issuing no discrepancy report and taking no
    exit status. Its store discrepancy names the receipt, the
    member, the digest expected, and the digest found, under the
    CE-2A names for SH-37, built and required through the MD-02
    seam. The fixity operation and the store record it writes
    into stand with their own slice and cite this form.
    """
    for label, value in (
        ("member identification", member_identification),
        ("digest expected", digest_expected),
        ("digest found", digest_found),
    ):
        if value is None:
            raise ShapeError("SH-37 store discrepancy carries no " + label)
    discrepancy = {
        "receipt_digest": checked_set_receipt_digest,
        "member_identification": member_identification,
        "digest_expected": digest_expected,
        "digest_found": digest_found,
    }
    for name in discrepancy:
        if name not in shapes.STORE_DISCREPANCY_FIELDS:
            raise ShapeError(
                "SH-37 store discrepancy carries an unnamed field: " + name
            )
    record = {
        "checked_set_receipt_digest": checked_set_receipt_digest,
        "result_word": OUTCOME_CUSTODY_GAP,
        "store_discrepancy": discrepancy,
        "rotation_cursor": rotation_cursor,
    }
    return shapes.validate(
        "SH-37",
        record,
        ("checked_set_receipt_digest", "result_word", "store_discrepancy"),
    )


def _failure(comparison, supported, subject_name, subject_digest, position, detail):
    return {
        "comparison": comparison,
        "supported": supported,
        "subject_name": subject_name,
        "subject_digest": subject_digest,
        "receipt_position": position,
        "detail": detail,
    }


def _member_failures(receipt, members, receipt_member_names, counter, receipt_recomputes):
    """Compare the set as read against the receipt, member by member.

    Every member's digest is recomputed from its bytes through
    the reading layer. Returns the failures, the unchecked member
    names, and the count of members checked.
    """
    failures = []
    unchecked = []
    actual = []
    if isinstance(members, dict):
        members = [
            {"name": name, "content": content}
            for name, content in members.items()
        ]
    for member in members:
        name = str(member.get("name", ""))
        if member.get("content") is None:
            # A member presented in digest only form, with no
            # bytes: nothing stands to recompute from, and no
            # presented digest is trusted.
            failures.append(
                _failure(
                    COMPARISON_MEMBER_DIGEST,
                    receipt_recomputes,
                    name,
                    member.get("digest_git_blob_sha1"),
                    None,
                    "member bytes cannot be had: the member was "
                    "presented by digest and byte size only, with "
                    "no bytes to recompute from",
                )
            )
            continue
        reading = read_member(member, counter)
        if reading["unchecked"]:
            unchecked.append(name)
            continue
        actual.append(
            {
                "name": name,
                "digest_git_blob_sha1": reading["digest_git_blob_sha1"],
                "byte_size": reading["byte_size"],
            }
        )
    names = list(receipt_member_names) if receipt_member_names else []
    standing = list(actual)
    for position, entry in enumerate(receipt["members"], start=1):
        wanted = (entry["member_digest"], entry["member_byte_size"])
        match = None
        for candidate in standing:
            if (candidate["digest_git_blob_sha1"], candidate["byte_size"]) == wanted:
                match = candidate
                break
        if match is not None:
            standing.remove(match)
            continue
        receipt_name = names[position - 1] if position - 1 < len(names) else None
        if receipt_name is not None and receipt_name in unchecked:
            continue
        altered = None
        if receipt_name is not None:
            for candidate in standing:
                if candidate["name"] == receipt_name:
                    altered = candidate
                    break
        if altered is not None:
            standing.remove(altered)
            failures.append(
                _failure(
                    COMPARISON_MEMBER_DIGEST,
                    receipt_recomputes,
                    receipt_name,
                    altered["digest_git_blob_sha1"],
                    position,
                    "the member digest recomputed from the member "
                    "bytes does not match the receipt entry",
                )
            )
        else:
            failures.append(
                _failure(
                    COMPARISON_MEMBER_PRESENCE,
                    receipt_recomputes,
                    receipt_name,
                    entry["member_digest"],
                    position,
                    "a member the receipt names does not stand in "
                    "the set as read",
                )
            )
    for candidate in standing:
        failures.append(
            _failure(
                COMPARISON_MEMBER_PRESENCE,
                receipt_recomputes,
                candidate["name"],
                candidate["digest_git_blob_sha1"],
                None,
                "a member stands in the set that the receipt does "
                "not name",
            )
        )
    return failures, unchecked, len(actual)


def check_seal(
    receipt,
    members,
    receipt_member_names=None,
    anchor_entry=None,
    anchor_digest=None,
    intake_order=None,
    invocation_build=None,
    invocation_stage=None,
    operation="verdict run",
    counter=None,
):
    """Run the pre run seal check over one frozen set.

    receipt is the custody receipt record in the SH-06 form, as
    the cured freeze surface issues it. members are the members
    of the set as read, each a mapping carrying its name and its
    bytes under content, in any order; receipt_member_names,
    where the caller holds them, are the member names in receipt
    order, parallel to the receipt's member entries, as the
    freeze result and the store production carry them.
    anchor_entry is the anchor record entry in the SH-07 form, or
    anchor_digest the anchored receipt digest as read, either
    standing for the anchor comparison. intake_order is the
    intake order field's items in the SH-08 form, or None where
    no intake order record stands for the gate.
    invocation_build and invocation_stage, where supplied, are
    compared against the receipt build and stage, as brief
    section 5.5 states for a run whose receipt build or stage
    differs from the invocation.

    Returns a result carrying the status, intact or broken seal;
    on a broken seal, the custody gap outcome word, the exit
    status the outcome table states for the custody case, the
    seal comparisons that failed, one SH-14 custody gap entry per
    failure in receipt order, and the SH-13 seal break report
    record; the unchecked elements by name, including the
    sequence cases no intake order record determines; the
    position the sequence comparison was made against, for the
    run statement's seal comparison position field; whether the
    receipt recomputed; and the reading counter.
    """
    if operation not in SEAL_OPERATIONS:
        raise ShapeError(
            "XR-01 seal phase opens no operation named: " + str(operation)
        )
    if counter is None:
        counter = ReadingCounter()
    if not isinstance(receipt, dict):
        receipt = {}
    receipt_digest = receipt.get("self_digest")
    failures = []
    unchecked = []

    # Receipt recomputation stands first: the self digest is
    # recomputed over the canonical form with the self digest
    # field omitted, under CE-3 and CE-4, and no comparison below
    # rests on a filed digest this recomputation does not support.
    receipt_recomputes = False
    receipt_well_formed = True
    try:
        shapes.validate("SH-06", dict(receipt), shapes.VOCABULARY["SH-06"])
    except (ShapeError, KeyError):
        receipt_well_formed = False
    if receipt_well_formed:
        counter.note_digest()
        receipt_recomputes = (
            canonical.receipt_self_digest(receipt) == receipt_digest
        )
    if not receipt_well_formed or not receipt_recomputes:
        failures.append(
            _failure(
                COMPARISON_RECEIPT_RECOMPUTATION,
                False,
                None,
                receipt_digest,
                None,
                "the custody receipt digest does not recompute "
                "from the receipt record",
            )
        )
        return _broken_result(
            operation, receipt_digest, failures, unchecked,
            receipt_recomputes, receipt.get("sequence_position"), counter,
        )

    # Member comparison, against the receipt entries in receipt
    # order, every digest recomputed from bytes.
    member_failures, member_unchecked, _checked = _member_failures(
        receipt, members, receipt_member_names, counter, receipt_recomputes
    )
    failures.extend(member_failures)
    unchecked.extend(member_unchecked)

    # Anchor comparison: the anchored receipt digest against the
    # receipt digest this recomputation supports.
    anchored_digest = None
    if anchor_entry is not None:
        shapes.validate("SH-07", dict(anchor_entry), shapes.VOCABULARY["SH-07"])
        anchored_digest = anchor_entry["anchored_receipt_digest"]
    elif anchor_digest is not None:
        anchored_digest = anchor_digest
    if anchored_digest is None:
        failures.append(
            _failure(
                COMPARISON_ANCHOR,
                False,
                None,
                receipt_digest,
                None,
                "the anchor is missing: no anchor entry stands "
                "for the receipt digest",
            )
        )
    elif anchored_digest != receipt_digest:
        in_order = intake_order is not None and any(
            item.get("receipt_digest") == anchored_digest
            for item in intake_order
            if isinstance(item, dict)
        )
        detail = (
            "the anchor belongs to another intake"
            if in_order
            else "the anchor conflicts with the receipt digest"
        )
        failures.append(
            _failure(
                COMPARISON_ANCHOR,
                receipt_recomputes,
                None,
                anchored_digest,
                None,
                detail,
            )
        )

    # Receipt build and stage against the invocation, where the
    # invocation names them.
    if (
        invocation_build is not None and invocation_build != receipt["build"]
    ) or (
        invocation_stage is not None and invocation_stage != receipt["stage"]
    ):
        failures.append(
            _failure(
                COMPARISON_BUILD_STAGE,
                receipt_recomputes,
                None,
                receipt_digest,
                receipt["sequence_position"],
                "the receipt build or stage differs from the "
                "invocation build or stage",
            )
        )

    # Sequence comparison, against the intake order field where
    # one stands, and against the receipt alone in the first
    # receipt case the brief states.
    position = receipt["sequence_position"]
    predecessor = receipt["predecessor_receipt_digest"]
    if position == 1 and predecessor is not None:
        failures.append(
            _failure(
                COMPARISON_SEQUENCE,
                True,
                None,
                receipt_digest,
                position,
                "a first receipt that claims a predecessor takes "
                "the custody gap outcome from the receipt alone",
            )
        )
    if position > 1 and predecessor is None:
        failures.append(
            _failure(
                COMPARISON_SEQUENCE,
                receipt_recomputes,
                None,
                receipt_digest,
                position,
                "a receipt after the first carries no predecessor "
                "receipt digest",
            )
        )
    if intake_order is None:
        unchecked.extend(SEQUENCE_UNCHECKED_NAMES)
    else:
        items = [
            shapes.validate("SH-08", dict(item), shapes.VOCABULARY["SH-08"])
            for item in intake_order
        ]
        by_position = {
            item["sequence_position"]: item["receipt_digest"] for item in items
        }
        if receipt_digest not in by_position.values():
            failures.append(
                _failure(
                    COMPARISON_SEQUENCE,
                    receipt_recomputes,
                    None,
                    receipt_digest,
                    position,
                    "whole intake removal: the receipt stands in "
                    "no item of the intake order field",
                )
            )
        elif by_position.get(position) != receipt_digest:
            failures.append(
                _failure(
                    COMPARISON_SEQUENCE,
                    receipt_recomputes,
                    None,
                    receipt_digest,
                    position,
                    "the receipt digest at its sequence position "
                    "does not match the intake order field",
                )
            )
        elif position > 1:
            if (position - 1) not in by_position:
                failures.append(
                    _failure(
                        COMPARISON_SEQUENCE,
                        receipt_recomputes,
                        None,
                        receipt_digest,
                        position,
                        "the receipt chain ends early against the "
                        "intake order field: no earlier intake "
                        "stands in the order",
                    )
                )
            elif predecessor != by_position[position - 1]:
                failures.append(
                    _failure(
                        COMPARISON_SEQUENCE,
                        receipt_recomputes,
                        None,
                        receipt_digest,
                        position,
                        "the predecessor receipt digest does not "
                        "match the intake order field",
                    )
                )

    if failures:
        return _broken_result(
            operation, receipt_digest, failures, unchecked,
            receipt_recomputes, position, counter,
        )
    return {
        "status": "intact",
        "operation": operation,
        "outcome_word": None,
        "exit_status": None,
        "receipt_digest": receipt_digest,
        "receipt_recomputes": receipt_recomputes,
        "determination_supported": True,
        "failed_comparisons": [],
        "failures": [],
        "discrepancy_entries": [],
        "report": None,
        "unchecked_elements": unchecked,
        "seal_comparison_position": position,
        "counter": counter,
    }


def _broken_result(operation, receipt_digest, failures, unchecked, receipt_recomputes, position, counter):
    """Assemble the broken seal result in the one emission form."""
    ordered = sorted(
        enumerate(failures),
        key=lambda pair: (
            pair[1]["receipt_position"] is None,
            pair[1]["receipt_position"] or 0,
            pair[0],
        ),
    )
    failures = [failure for _index, failure in ordered]
    entries = [
        custody_gap_entry(
            number,
            failure["comparison"],
            failure["subject_name"],
            failure["subject_digest"],
            failure["receipt_position"],
        )
        for number, failure in enumerate(failures, start=1)
    ]
    supported = any(failure["supported"] for failure in failures)
    return {
        "status": "broken seal",
        "operation": operation,
        "outcome_word": OUTCOME_CUSTODY_GAP,
        "exit_status": 1 if supported else 2,
        "receipt_digest": receipt_digest,
        "receipt_recomputes": receipt_recomputes,
        "determination_supported": supported,
        "failed_comparisons": list(
            dict.fromkeys(failure["comparison"] for failure in failures)
        ),
        "failures": failures,
        "discrepancy_entries": entries,
        "report": seal_break_report(receipt_digest, entries, unchecked),
        "unchecked_elements": unchecked,
        "seal_comparison_position": position,
        "counter": counter,
    }


def seal_break_filed_text(result):
    """Render a broken seal result in its filed report form.

    The filed form of the one emission: the custody gap as a chain
    discrepancy in its own right, the receipt digest, and the seal
    comparison that failed for each entry, with its subject named
    where a name stands. No verdict line stands in it.
    """
    lines = [
        "discrepancy report",
        "outcome: " + OUTCOME_CUSTODY_GAP,
        "check: chain",
        "receipt digest: " + str(result["receipt_digest"]),
    ]
    for number, failure in enumerate(result["failures"], start=1):
        subject = failure["subject_name"] or failure["subject_digest"] or "receipt"
        lines.append(
            "discrepancy " + str(number) + ": " + OUTCOME_CUSTODY_GAP
            + "; " + str(subject)
            + "; seal comparison failed: " + failure["comparison"]
            + "; " + failure["detail"]
        )
    for name in result["unchecked_elements"]:
        lines.append("unchecked: " + str(name))
    lines.append("verdict: no verdict issued")
    lines.append("exit status: " + str(result["exit_status"]))
    return "\n".join(lines) + "\n"
