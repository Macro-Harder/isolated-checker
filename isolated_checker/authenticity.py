"""Authenticity check, plan module MD-05, slice S-05A.

The first of the three checks in R-80 order, resting on brief
section 5.6. Authenticity runs per item over the owned fields:
the digest recomputed from the artefact in hand against the digest
the link records, a citation that cannot be recomputed not
counting as an identified artefact; the spawn identity the link
records resolving to a spawn record that places the performer in
a seat the roster, in its state at the time the step ran,
authorised for that seat at that time, at the strength its source
carries; and each required record coming from the source the
layout names for its record kind. Where no roster state for the
step time can be produced, the spawn limb cannot run and the check
takes the cannot run form of the shared plumbing. A source that
cites itself as corroboration corroborates nothing and is never
an authenticity source: it stands unchecked by name and the
record it was offered for takes a discrepancy.

All material is consumed as recomputed through the reading layer
by the shared machinery in checks.py: no presented digest is
trusted, and the strength stated per source rests on the banked
posture at O-31 with C-21, as brief section 5.6 states, settling
no source route.
"""

from . import checks
from .discovery import DISCOVERY_ROUTES
from .reading import extract_link_fields

_ROSTER_UNCHECKED = "roster state for the step time"


def _is_full_digest(value):
    if not isinstance(value, str) or len(value) != 40:
        return False
    return all(char in "0123456789abcdef" for char in value)


def check_authenticity(
    members,
    links=(),
    roster=None,
    layout=None,
    required_records=(),
    sources=(),
    receipt_member_names=None,
    determination_supported=True,
    counter=None,
):
    """Run the authenticity check over one frozen set.

    members are the frozen set's members as the reading layer reads
    them. links are the link records whose owned fields the check
    reads: each names its artefact, the digest it records for it,
    and, where it carries one, its spawn binding (spawn identity
    and seat) with the source kind the spawn record carries.
    roster is the roster in its state at the time the step ran,
    mapping a seat to the spawn identities it authorised for that
    seat, or None where no roster state for the step time can be
    produced. layout is the SH-03 layout the invocation names.
    required_records name, per record, its kind, the member it
    stands in, and the source kind it actually came from. sources
    name outside sources offered to the run, each with its self
    citing standing where it stands.

    Returns the shared check result form: the verdict, the outcome
    word where one stands, the discrepancy entries in receipt
    order, the unchecked elements by name, and the strength each
    link's spawn binding was checked at.
    """
    readings, unchecked = checks.read_frozen_members(members, counter)
    by_name = checks.readings_by_name(readings)
    names = list(receipt_member_names) if receipt_member_names else sorted(by_name)

    def position_of(name):
        return names.index(name) + 1 if name in names else None

    pending = []

    def add(position, **kwargs):
        pending.append((position if position is not None else 1 << 30, len(pending), kwargs))

    strengths = {}
    notes = []
    cannot_run_reason = None

    for link in links:
        extracted = extract_link_fields(link)
        for name in extracted["unchecked"]:
            if name not in unchecked:
                unchecked.append(name)
        link_name = link.get("link") or link.get("artefact") or "link"
        artefact = link.get("artefact")
        recorded = link.get("recorded_digest")
        reading = by_name.get(artefact)
        position = position_of(artefact) if artefact else None
        if "spawn" in link or "seat" in link:
            strengths[link_name] = checks.spawn_strength(link.get("source_kind"))
        if reading is None:
            if artefact in unchecked:
                continue
            add(
                position,
                check="authenticity",
                category=checks.CATEGORY_OTHER_NAMED_FORM,
                form="missing artefact",
                governing=link_name + " subject",
                subject_name=artefact,
                routes_tried=list(DISCOVERY_ROUTES),
            )
        elif not _is_full_digest(recorded):
            add(
                position,
                check="authenticity",
                category=checks.CATEGORY_OTHER_NAMED_FORM,
                form="unidentifiable",
                governing=link_name + " citation",
                subject_name=artefact,
                identification_form=checks.IDENTIFICATION_UNIDENTIFIABLE,
            )
            cannot_run_reason = (
                "a citation that cannot be recomputed does not count "
                "as an identified artefact: " + str(artefact)
            )
        elif reading["digest_git_blob_sha1"] != recorded:
            add(
                position,
                check="authenticity",
                category=checks.CATEGORY_OTHER_NAMED_FORM,
                form="digest mismatch",
                governing=link_name + " subject digest",
                subject_digest=reading["digest_git_blob_sha1"],
                receipt_position=position,
            )
        if "spawn" in link or "seat" in link:
            if roster is None:
                cannot_run_reason = (
                    "no roster state for the step time can be produced, "
                    "so the spawn identity cannot be resolved"
                )
                if _ROSTER_UNCHECKED not in unchecked:
                    unchecked.append(_ROSTER_UNCHECKED)
            else:
                seat = link.get("seat")
                authorised = roster.get(seat, ())
                if link.get("spawn") not in authorised:
                    add(
                        position,
                        check="authenticity",
                        category=checks.CATEGORY_OTHER_NAMED_FORM,
                        form="spawn identity does not resolve to an authorised seat",
                        governing=link_name + " spawn binding",
                        subject_digest=(
                            reading["digest_git_blob_sha1"] if reading else None
                        ),
                        subject_name=artefact,
                        receipt_position=position,
                        routes_tried=list(DISCOVERY_ROUTES) if reading is None else None,
                    )

    for record in required_records:
        expected = checks.layout_source_for(layout, record["record_kind"])
        name = record.get("name")
        reading = by_name.get(name)
        position = position_of(name) if name else None
        if expected is None:
            label = "layout source for record kind " + str(record["record_kind"])
            if label not in unchecked:
                unchecked.append(label)
            continue
        if record.get("source_kind") != expected:
            add(
                position,
                check="authenticity",
                category=checks.CATEGORY_OTHER_NAMED_FORM,
                form="record did not come from the source the layout names",
                governing="layout source for record kind " + str(record["record_kind"]),
                subject_digest=reading["digest_git_blob_sha1"] if reading else None,
                subject_name=name,
                receipt_position=position,
                routes_tried=list(DISCOVERY_ROUTES) if reading is None else None,
            )

    for source in sources:
        if not source.get("self_citing"):
            continue
        name = source["name"]
        if name not in unchecked:
            unchecked.append(name)
        notes.append(
            "a self citing source corroborates nothing and is never "
            "an authenticity source: " + str(name)
        )
        reading = by_name.get(name)
        add(
            position_of(name),
            check="authenticity",
            category=checks.CATEGORY_OTHER_NAMED_FORM,
            form="self citing source",
            governing="corroboration offered by " + str(name),
            subject_digest=reading["digest_git_blob_sha1"] if reading else None,
            subject_name=name,
            receipt_position=position_of(name),
            routes_tried=list(DISCOVERY_ROUTES) if reading is None else None,
        )

    pending.sort(key=lambda item: (item[0], item[1]))
    entries = []
    for number, (_position, _seq, spec) in enumerate(pending, start=1):
        entries.append(
            checks.discrepancy_entry(
                number,
                spec["check"],
                spec["category"],
                governing_element_reference=spec["governing"],
                discrepancy_form_name=spec["form"],
                subject_digest=spec.get("subject_digest"),
                subject_name=spec.get("subject_name"),
                receipt_position=spec.get("receipt_position"),
                identification_form=spec.get("identification_form"),
                routes_tried=spec.get("routes_tried"),
            )
        )
    return checks.check_result(
        "authenticity",
        entries=entries,
        unchecked_elements=unchecked,
        cannot_run_reason=cannot_run_reason,
        determination_supported=determination_supported,
        extra={"strengths": strengths, "notes": notes},
    )
