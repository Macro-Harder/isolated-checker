"""Completeness check, plan module MD-05, slice S-05C.

The third of the three checks in R-80 order, resting on brief
section 5.6. Completeness runs against the layout named at
invocation as denominator, covering steps against links, packet
members and record parts with a stated none counted as present and
an omitted part counted as missing, artefact content properties
stated in the layout, and traces and rosters against the same
denominator. Where no denominator outside the bundle under check
can be established, the check cannot run against an outside
denominator and takes the cannot run form of the shared plumbing,
FAIL with stage PARTIAL where the remaining records support a
determination and UNVERIFIABLE where they support none, and the
checker does not check a packet against itself in silence. A
layout whose denominator is empty for a stage that has steps
cannot run either, routed through the same form. A truncation
whose digests stay true is reported against the content trace
where that is its disposition, and stands as a recorded gap
element where it is adjudicated to stand.

The denominator elements are the layout's artefact entries
resolved to the members they name, supplied in that resolved form
with the layout itself, whose source naming the authenticity
check reads from the same record. The provenance of the layout
stands banked under O-30 and is settled nowhere here.
"""

from . import checks
from .discovery import DISCOVERY_ROUTES


def check_completeness(
    members,
    layout=None,
    required_elements=(),
    denominator_outside_bundle=True,
    has_steps=False,
    determination_supported=True,
    receipt_member_names=None,
    counter=None,
):
    """Run the completeness check over one frozen set.

    required_elements are the denominator in resolved form: each
    names the member it requires, the governing element reference
    it arises under, whether it stands as a stated none (counted
    as present), the artefact content properties the layout states
    for it, and, for a truncated artefact, the sections its claimed
    outline names that do not stand present, with the disposition
    the case carries, content_trace or recorded_gap.

    Returns the shared check result form, with the elements counted
    present by a stated none named, and any recorded gap elements
    the dispositions produce.
    """
    if layout is None or not denominator_outside_bundle:
        return checks.check_result(
            "completeness",
            unchecked_elements=["completeness denominator"],
            cannot_run_reason=(
                "no denominator outside the bundle under check can "
                "be established, so the completeness check cannot run "
                "against an outside denominator"
            ),
            determination_supported=determination_supported,
            extra={"counted_present": [], "notes": []},
        )
    if not required_elements and has_steps:
        return checks.check_result(
            "completeness",
            unchecked_elements=["completeness denominator"],
            cannot_run_reason=(
                "the layout denominator is empty for a stage that "
                "has steps, so no completeness determination stands"
            ),
            determination_supported=determination_supported,
            extra={"counted_present": [], "notes": []},
        )
    readings, unchecked = checks.read_frozen_members(members, counter)
    by_name = checks.readings_by_name(readings)
    names = list(receipt_member_names) if receipt_member_names else sorted(by_name)

    def position_of(name):
        return names.index(name) + 1 if name in names else None

    pending = []
    counted_present = []
    recorded_gaps = []
    notes = []

    def add(position, **kwargs):
        pending.append((position if position is not None else 1 << 30, len(pending), kwargs))

    for element in required_elements:
        name = element["name"]
        governing = element["governing_element_reference"]
        reading = by_name.get(name)
        if element.get("stated_none"):
            counted_present.append(name)
            continue
        if reading is None:
            if name in unchecked:
                continue
            add(
                position_of(name),
                form="missing artefact",
                governing=governing,
                subject_name=name,
                routes_tried=list(DISCOVERY_ROUTES),
            )
            continue
        content_text = reading["content"].decode("utf-8", errors="replace")
        for prop in element.get("content_properties", ()):
            if prop not in content_text:
                add(
                    position_of(name),
                    form="artefact content property missing",
                    governing=governing,
                    subject_digest=reading["digest_git_blob_sha1"],
                    subject_name=name,
                    receipt_position=position_of(name),
                )
        missing_sections = element.get("missing_sections", ())
        if missing_sections:
            if element.get("disposition") == "recorded_gap":
                recorded_gaps.append(name)
            else:
                notes.append(
                    "truncation reported against the content trace: "
                    + str(name)
                    + " is missing sections "
                    + ", ".join(missing_sections)
                    + " of its claimed outline"
                )
                add(
                    position_of(name),
                    form="truncation",
                    governing=governing,
                    subject_digest=reading["digest_git_blob_sha1"],
                    subject_name=name,
                    receipt_position=position_of(name),
                )

    pending.sort(key=lambda item: (item[0], item[1]))
    entries = []
    for number, (_position, _seq, spec) in enumerate(pending, start=1):
        entries.append(
            checks.discrepancy_entry(
                number,
                "completeness",
                checks.CATEGORY_OTHER_NAMED_FORM,
                governing_element_reference=spec["governing"],
                discrepancy_form_name=spec["form"],
                subject_digest=spec.get("subject_digest"),
                subject_name=spec.get("subject_name"),
                receipt_position=spec.get("receipt_position"),
                routes_tried=spec.get("routes_tried"),
            )
        )
    return checks.check_result(
        "completeness",
        entries=entries,
        unchecked_elements=unchecked,
        determination_supported=determination_supported,
        recorded_gap_elements=recorded_gaps,
        extra={"counted_present": counted_present, "notes": notes},
    )
