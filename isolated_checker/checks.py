"""The three checks, shared machinery, plan module MD-05, slice S-05.

This module is the one owner of what the three checks hold in
common, landed first in the slice sequence the Step 14 record's
mapping states: the layout form at SH-03 the checks read as an
invocation input, the spawn and outside source reference forms at
SH-42, the discrepancy entry form at SH-14 under plan Q2, the one
sided classification at SH-16, the invocation to record
comparisons of brief section 5.6, the collision twin naming, and
the determination plumbing each check returns its verdict in. The
three checks themselves stand in their own modules beside this
one (authenticity.py, chain.py, completeness.py), each part of
MD-05, each consuming this machinery and no other copy of it.
The runner over the three checks stands in checks_runner.py,
beside this module: it depends on this machinery and on the
three checks, and this module imports none of its consumers, in
any position, so the dependency direction inside the split runs
one way, as Step 14 finding T14-16 cures it.

Every check in MD-05 is a function of the frozen set and the named
invocation inputs only. Member material is consumed only as
recomputed through the reading layer of MD-16: a presented digest
is never trusted as a substitute for recomputation, under XR-03,
and no filed digest, previous verdict, or previous run output is
trusted either. The checks consult outside material only as source
references at SH-42 supplied by the caller; a check never fetches,
never follows a reference outside the frozen set, and never names
a source the run did not consult. Counting hooks for the resource
bounds of slice S-13 stand in the reading path this module shares,
as statement P1-S13-3 requires, through the reading counter the
caller may pass in; no bound value is named or applied here.

Where the checks meet the harness surface, the Step 13 harness's
filed conventions govern presentation, as register entry T14-10's
ruling distinguishes: this core takes records and material in
their record forms and states no scenario key and no presented
state form, and it composes no run determination or exit status,
those belonging to MD-06 and MD-15. Discovery's classify_discovery
carriage as landed stands untouched by this slice, per register
entries T14-07 and T14-10: the checks compose their own outcomes
in their own modules, not through it.
"""

from . import shapes
from .reading import ReadingCounter, read_member
from .shapes import ShapeError

CHECKS = ("authenticity", "chain", "completeness")

VERDICT_PASS = "pass"
VERDICT_FAIL = "fail"
VERDICT_CANNOT_RUN = "cannot run"

OUTCOME_PARTIAL = "FAIL with stage PARTIAL"
OUTCOME_UNVERIFIABLE = "UNVERIFIABLE"
OUTCOME_CUSTODY_GAP = "custody gap"

CATEGORY_KIND = "kind"
CATEGORY_CUSTODY_GAP = "custody gap"
CATEGORY_OTHER_NAMED_FORM = "other named form"

IDENTIFICATION_DIGEST = "digest"
IDENTIFICATION_NOT_LOCATED = "not located"
IDENTIFICATION_UNIDENTIFIABLE = "unidentifiable"

HEADING_STRUCTURAL = "structural"
HEADING_TIMING = "timing"
HEADING_UNEXPLAINED = "unexplained"

STRENGTH_FULL_BINDING = "full spawn binding"
STRENGTH_TRANSCRIPTION = "transcription consistency"

_FULL_BINDING_SOURCES = ("runtime captured record", "platform sourced record")


# ---------------------------------------------------------------- layout, SH-03


def layout_record(
    layout_digest,
    layout_version,
    artefact_entries,
    seat_set,
    record_kind_sources,
    publication_time,
    republication_entries=(),
):
    """Build a layout record in the SH-03 form, plan Q3.

    The layout is the denominator the completeness check reads and
    the source naming the authenticity check reads, supplied as an
    invocation input named by digest and version through IF-LAY.
    Its provenance is not part of this form and is settled nowhere
    here, as brief section 5.6 states. Built and required through
    the MD-02 seam under the CE-2A names for SH-03.
    """
    entries = []
    for entry in artefact_entries:
        for name in entry:
            if name not in shapes.ARTEFACT_ENTRY_FIELDS:
                raise ShapeError(
                    "SH-03 artefact entry carries an unnamed field: " + name
                )
        entries.append(
            {
                "artefact_kind": entry["artefact_kind"],
                "content_properties": list(entry.get("content_properties", ())),
            }
        )
    sources = []
    for source in record_kind_sources:
        for name in source:
            if name not in shapes.RECORD_KIND_SOURCE_FIELDS:
                raise ShapeError(
                    "SH-03 record kind source carries an unnamed field: " + name
                )
        sources.append(
            {
                "record_kind": source["record_kind"],
                "source_kind": source["source_kind"],
            }
        )
    republications = []
    for entry in republication_entries:
        for name in entry:
            if name not in shapes.REPUBLICATION_FIELDS:
                raise ShapeError(
                    "SH-03 republication entry carries an unnamed field: " + name
                )
        republications.append(
            {
                "republication_time": entry["republication_time"],
                "republished_version": entry["republished_version"],
            }
        )
    record = {
        "layout_digest": layout_digest,
        "layout_version": layout_version,
        "artefact_entries": entries,
        "seat_set": list(seat_set),
        "record_kind_sources": sources,
        "publication_time": publication_time,
        "republication_entries": republications,
    }
    return shapes.validate("SH-03", record, shapes.VOCABULARY["SH-03"])


def layout_source_for(layout, record_kind):
    """The source kind the layout names for a record kind, or None."""
    if layout is None:
        return None
    for source in layout["record_kind_sources"]:
        if source["record_kind"] == record_kind:
            return source["source_kind"]
    return None


# ------------------------------------------------------- references, SH-42


def outside_source_reference(source_kind, source_identity):
    """Build an outside source reference in the SH-42 form."""
    record = {"source_kind": source_kind, "source_identity": source_identity}
    for name in record:
        if name not in shapes.SOURCE_FIELDS:
            raise ShapeError(
                "SH-42 outside source reference carries an unnamed field: " + name
            )
    return shapes.validate(
        "SH-42-source", record, shapes.VOCABULARY["SH-42-source"]
    )


def spawn_reference(spawn_identity, performer_seat, roster_authorisation_record_reference):
    """Build a spawn record reference in the SH-42 form.

    The identity form the authenticity check uses: a spawn identity
    resolving to a record that places the performer in a seat the
    roster, in its state at the time the step ran, authorised for
    that seat at that time. No spawn record field list stands in
    this shape, that thin place standing open inside O-56.
    """
    record = {
        "spawn_identity": spawn_identity,
        "performer_seat": performer_seat,
        "roster_authorisation_record_reference": roster_authorisation_record_reference,
    }
    for name in record:
        if name not in shapes.SPAWN_REFERENCE_FIELDS:
            raise ShapeError(
                "SH-42 spawn reference carries an unnamed field: " + name
            )
    return shapes.validate("SH-42-spawn", record, shapes.VOCABULARY["SH-42-spawn"])


def spawn_strength(source_kind):
    """The authenticity strength a source kind carries, brief 5.6.

    Full spawn binding only where the record is a runtime captured
    or platform sourced record, and transcription consistency where
    the record is a transcription inside a packet supplied record.
    """
    if source_kind in _FULL_BINDING_SOURCES:
        return STRENGTH_FULL_BINDING
    return STRENGTH_TRANSCRIPTION


# ------------------------------------------------- discrepancy entries, SH-14


def discrepancy_entry(
    entry_number,
    check,
    discrepancy_category,
    governing_element_reference,
    discrepancy_form_name=None,
    defect_kind_code=None,
    subject_digest=None,
    subject_name=None,
    receipt_position=None,
    identification_form=None,
    quoted_found_value=None,
    one_sided_classification_heading=None,
    pending_counterpart_record_reference=None,
    routes_tried=None,
):
    """Build one discrepancy entry in the SH-14 form, plan Q2.

    The fields Q2 requires on every entry stand required through
    the seam: entry number, check, discrepancy category, subject
    identification, root cause key, and governing element
    reference. The naming stands in one of Q2's three forms: a kind
    entry carries its defect kind code from the taxonomy and no
    form name; a custody gap entry carries the custody gap category
    with its code absent valued; an other named form entry carries
    the governing passage's form name with its code absent valued.
    No fourth naming source exists, and no code is invented for an
    entry whose naming fits none of the three.

    Subject identification keeps the two no digest cases apart, as
    EX-10 keeps them: not located, where the artefact cannot be
    located, with the routes tried required on such an entry; and
    unidentifiable, only where the artefact is located but its
    citation cannot be recomputed. Where the subject is a frozen
    set member, its receipt position stands beside its digest, so
    collision twins carry distinct identifications. The root cause
    key is the text key over check, governing element reference,
    and cause name under Q4; subject identity stands in no key.
    """
    if check not in CHECKS:
        raise ShapeError("SH-14 entry names no check of the three: " + str(check))
    if discrepancy_category == CATEGORY_KIND:
        if defect_kind_code is None:
            raise ShapeError(
                "SH-14 kind entry carries no defect kind code: "
                "a kind entry requires its taxonomy code under Q2"
            )
        if discrepancy_form_name is not None:
            raise ShapeError(
                "SH-14 kind entry carries a form name beside its code"
            )
        cause_name = defect_kind_code
    elif discrepancy_category == CATEGORY_CUSTODY_GAP:
        if defect_kind_code is not None or discrepancy_form_name is not None:
            raise ShapeError(
                "SH-14 custody gap entry carries a code or a form name: "
                "its naming source is the custody gap form itself under Q2"
            )
        cause_name = CATEGORY_CUSTODY_GAP
    elif discrepancy_category == CATEGORY_OTHER_NAMED_FORM:
        if discrepancy_form_name is None:
            raise ShapeError(
                "SH-14 other named form entry carries no form name: "
                "the governing passage's form name stands required under Q2"
            )
        if defect_kind_code is not None:
            raise ShapeError(
                "SH-14 other named form entry carries a defect kind code"
            )
        cause_name = discrepancy_form_name
    else:
        raise ShapeError(
            "SH-14 entry carries a discrepancy category Q2 does not state: "
            + str(discrepancy_category)
        )
    if identification_form is None:
        identification_form = (
            IDENTIFICATION_DIGEST if subject_digest else IDENTIFICATION_NOT_LOCATED
        )
    if identification_form not in (
        IDENTIFICATION_DIGEST,
        IDENTIFICATION_NOT_LOCATED,
        IDENTIFICATION_UNIDENTIFIABLE,
    ):
        raise ShapeError(
            "SH-14 subject identification carries a form Q2 does not state: "
            + str(identification_form)
        )
    if identification_form == IDENTIFICATION_DIGEST and not subject_digest:
        raise ShapeError(
            "SH-14 subject identified by digest carries no digest"
        )
    if identification_form == IDENTIFICATION_NOT_LOCATED and routes_tried is None:
        raise ShapeError(
            "SH-14 not located entry carries no routes tried: "
            "the routes tried field stands required on such an entry under Q2"
        )
    if subject_digest is None and subject_name is None:
        raise ShapeError(
            "SH-14 entry names no subject element: a subject digest "
            "or a subject name stands required"
        )
    identification = {
        "identification_form": identification_form,
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
        "check": check,
        "discrepancy_category": discrepancy_category,
        "discrepancy_form_name": discrepancy_form_name,
        "defect_kind_code": defect_kind_code,
        "subject_identification": identification,
        "root_cause_key": (
            check + ":" + str(governing_element_reference) + ":" + cause_name
        ),
        "governing_element_reference": governing_element_reference,
        "quoted_found_value": quoted_found_value,
        "one_sided_classification_heading": one_sided_classification_heading,
        "pending_counterpart_record_reference": pending_counterpart_record_reference,
        "routes_tried": list(routes_tried) if routes_tried is not None else None,
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


def collision_twin_entries(receipt_members, first_entry_number=1):
    """Name each collision twin pair in a frozen set, brief 5.6.

    Two members in one frozen set that share a digest and a byte
    size are named as a collision condition discrepancy, one entry
    per member of the pair, with neither member substituted: the
    digest comparison alone cannot tell the two members apart.
    Each entry's subject identification carries its receipt
    position beside the shared digest, so the twins stand as
    distinct subjects. The entries are authenticity entries: the
    per item digest recomputation is that check's limb, and it is
    the comparison the twin condition defeats.
    """
    groups = {}
    for position, entry in enumerate(receipt_members, start=1):
        key = (entry["member_digest"], entry["member_byte_size"])
        groups.setdefault(key, []).append(position)
    entries = []
    number = first_entry_number
    for (digest, _size), positions in groups.items():
        if len(positions) < 2:
            continue
        for position in positions:
            entries.append(
                discrepancy_entry(
                    number,
                    "authenticity",
                    CATEGORY_OTHER_NAMED_FORM,
                    discrepancy_form_name="collision condition",
                    governing_element_reference="collision twin pair at receipt position "
                    + str(position),
                    subject_digest=digest,
                    receipt_position=position,
                )
            )
            number += 1
    return entries


# ------------------------------------------- one sided classification, SH-16


def classification_record(identification, heading, pending_reference=None):
    """Build one one sided classification record in the SH-16 form."""
    record = {
        "classified_item_identification": identification,
        "classification_heading": heading,
        "pending_counterpart_record_reference": pending_reference,
    }
    return shapes.validate("SH-16", record, shapes.VOCABULARY["SH-16"])


def classify_one_sided(items, carried_unexplained_count=0):
    """Classify one sided chain material under the SH-16 headings.

    Each item takes exactly one heading, in the precedence brief
    section 5.6 fixes: structural, where the layout provision cited
    per item requires no counterpart for that kind, with a stated
    record showing a counterpart pending carried beside the heading
    and counted in the overlap count; timing, where the structural
    showing cannot be made and a stated record shows the counterpart
    is pending in the CH7 sense; and unexplained, as the residue.
    The classification changes no outcome and states no default for
    SQ-5 inside O-56. Every item is also an unchecked element by
    name, and the standing count of unexplained items is carried
    from report to report: the count returned is the carried count
    plus this run's unexplained items.
    """
    classifications = []
    overlap = 0
    unexplained_here = 0
    unchecked = []
    for item in items:
        pending = item.get("pending_record_reference")
        if not item["layout_requires_counterpart"]:
            heading = HEADING_STRUCTURAL
            if pending is not None:
                overlap += 1
        elif pending is not None:
            heading = HEADING_TIMING
        else:
            heading = HEADING_UNEXPLAINED
            unexplained_here += 1
        classifications.append(
            classification_record(
                item["identification"],
                heading,
                pending if heading == HEADING_STRUCTURAL else None,
            )
        )
        unchecked.append(item["identification"])
    return {
        "classifications": classifications,
        "overlap_count": overlap,
        "unexplained_count": carried_unexplained_count + unexplained_here,
        "unchecked_elements": unchecked,
    }


# ------------------------------------------- invocation to record comparisons


def invocation_comparisons(
    invocation_layout_digest,
    invocation_layout_version,
    layout_read_digest,
    layout_read_version,
    invocation_build,
    invocation_stage,
    receipt_build,
    receipt_stage,
    context_packet_form_version,
    invocation_packet_form_version,
    layout_as_used_digest,
    layout_as_used_version,
    run_checker_version,
    invocation_checker_version,
    determination_supported,
    remaining_support,
):
    """The invocation to record comparisons of brief section 5.6.

    A run compares, before any check verdict is formed: the
    invocation layout digest and version against the layout read;
    the invocation build and stage against the receipt build and
    stage; the packet form version in the frozen set context record
    against the invocation packet form version; and the layout
    identity and version as used and the checker version as carried
    in the run statement against the invocation values for them.
    Each mismatch takes the custody gap outcome where the
    comparison itself supports that determination, and otherwise
    the outcome for a check that cannot run: FAIL with stage
    PARTIAL where the remaining records support a determination and
    UNVERIFIABLE where they support none. No verdict issues where
    any of these comparisons does not match the invocation; the
    composition of that bar into a run outcome belongs to the
    operation modules, and this function returns the failures.
    """
    pairs = [
        ("layout digest comparison", invocation_layout_digest, layout_read_digest),
        ("layout version comparison", invocation_layout_version, layout_read_version),
        ("receipt build comparison", invocation_build, receipt_build),
        ("receipt stage comparison", invocation_stage, receipt_stage),
        (
            "packet form version comparison",
            invocation_packet_form_version,
            context_packet_form_version,
        ),
        ("layout identity as used comparison", invocation_layout_digest, layout_as_used_digest),
        ("layout version as used comparison", invocation_layout_version, layout_as_used_version),
        ("checker version comparison", invocation_checker_version, run_checker_version),
    ]
    if determination_supported:
        outcome = OUTCOME_CUSTODY_GAP
    elif remaining_support:
        outcome = OUTCOME_PARTIAL
    else:
        outcome = OUTCOME_UNVERIFIABLE
    failures = []
    for comparison, invoked, read in pairs:
        if invoked != read:
            failures.append(
                {
                    "comparison": comparison,
                    "invocation_value": invoked,
                    "read_value": read,
                    "outcome_word": outcome,
                    "determination_supported": determination_supported,
                }
            )
    return failures


# ------------------------------------------------------- frozen set reading


def read_frozen_members(members, counter=None):
    """Read the frozen set's members through the reading layer.

    Every member's digest is recomputed from its bytes by MD-16;
    no presented digest stands in any reading. Uncovered member
    forms are never read and never followed: they return as
    unchecked names, in presentation order. Returns the readings
    and the unchecked names.
    """
    if counter is None:
        counter = ReadingCounter()
    readings = []
    unchecked = []
    items = members
    if isinstance(members, dict):
        items = [
            {"name": name, "content": content}
            for name, content in members.items()
        ]
    for member in items:
        reading = read_member(member, counter)
        readings.append(reading)
        if reading["unchecked"]:
            unchecked.append(reading["name"])
    return readings, unchecked


def readings_by_name(readings):
    """Index checked readings by member name, unchecked excluded."""
    return {
        reading["name"]: reading
        for reading in readings
        if not reading["unchecked"]
    }


# --------------------------------------------------- determination plumbing


def check_result(
    check,
    entries=(),
    unchecked_elements=(),
    cannot_run_reason=None,
    determination_supported=True,
    recorded_gap_elements=(),
    extra=None,
):
    """Assemble one check's verdict material in the shared form.

    The determination plumbing the three checks hold in common: a
    check with discrepancy entries fails; a check that cannot run
    carries its blocking reason with the support the remaining
    records give a determination, in the O-39 words FAIL with stage
    PARTIAL where they support one and UNVERIFIABLE where they
    support none; a check with neither passes. The outcome words
    here are the check's own material: the composition of check
    outcomes into a run exit status belongs to MD-06 and stands
    with its owning slice.
    """
    entries = list(entries)
    if cannot_run_reason is not None:
        verdict = VERDICT_CANNOT_RUN
        outcome_word = (
            OUTCOME_PARTIAL if determination_supported else OUTCOME_UNVERIFIABLE
        )
    elif entries:
        verdict = VERDICT_FAIL
        outcome_word = OUTCOME_PARTIAL
    else:
        verdict = VERDICT_PASS
        outcome_word = None
    result = {
        "check": check,
        "verdict": verdict,
        "outcome_word": outcome_word,
        "determination_supported": determination_supported,
        "cannot_run_reason": cannot_run_reason,
        "discrepancy_entries": entries,
        "unchecked_elements": list(unchecked_elements),
        "recorded_gap_elements": list(recorded_gap_elements),
    }
    if extra:
        result.update(extra)
    return result
