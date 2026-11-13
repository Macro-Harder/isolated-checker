"""Chain check, plan module MD-05, slice S-05B.

The second of the three checks in R-80 order, resting on brief
section 5.6. Chain runs as matching on shared materials, digest
for digest, across adjacent steps, across the stage boundary, and
along each ledger transition a closure claim relies on, including
its date and time of day. An additional input is not by itself a
chain failure. Material appearing on one side of a comparison only
is classified under the three headings the shared machinery states
at SH-16, in the precedence brief section 5.6 fixes, with the
overlap count carried separately and the standing count of
unexplained items carried from report to report; the
classification changes no outcome and states no default for SQ-5
inside O-56. The custody gap the seal phase carries as a chain
discrepancy in its own right stands in the seal module, not here:
this check forms no custody entry.

Both sides of every comparison are consumed as recomputed through
the reading layer by the shared machinery in checks.py: a digest
presented with a member is never trusted, and a side that does not
stand in the frozen set is not located, in the Q2 form.
"""

from . import checks
from .discovery import DISCOVERY_ROUTES


def check_chain(
    members,
    pairs=(),
    ledger_transitions=(),
    one_sided_items=(),
    carried_unexplained_count=0,
    receipt_member_names=None,
    determination_supported=True,
    counter=None,
):
    """Run the chain check over one frozen set.

    pairs name shared material joins: each names its governing
    element reference and the member on each side of the join, the
    two sides standing for the same shared material across adjacent
    steps or across the stage boundary. ledger_transitions name
    the same matching along a ledger transition, each carrying the
    date and time of day each side records for it where it records
    one. one_sided_items name material appearing on one side of a
    comparison only, in the SH-16 item form the shared machinery
    classifies. carried_unexplained_count is the standing count of
    unexplained items the previous report carried.

    Returns the shared check result form, with the one sided
    classifications, the overlap count, the standing unexplained
    count, and the additional inputs (members no join names) that
    are not by themselves a chain failure.
    """
    readings, unchecked = checks.read_frozen_members(members, counter)
    by_name = checks.readings_by_name(readings)
    names = list(receipt_member_names) if receipt_member_names else sorted(by_name)

    def position_of(name):
        return names.index(name) + 1 if name in names else None

    pending = []

    def add(position, **kwargs):
        pending.append((position if position is not None else 1 << 30, len(pending), kwargs))

    def run_join(join, is_transition):
        left = by_name.get(join["left"])
        right = by_name.get(join["right"])
        governing = join["governing_element_reference"]
        for side_name, side in ((join["left"], left), (join["right"], right)):
            if side is None:
                if side_name in unchecked:
                    continue
                add(
                    position_of(side_name),
                    form="missing artefact",
                    governing=governing,
                    subject_name=side_name,
                    routes_tried=list(DISCOVERY_ROUTES),
                )
        if left is None or right is None:
            return
        if left["digest_git_blob_sha1"] != right["digest_git_blob_sha1"]:
            add(
                position_of(join["left"]),
                form="shared material digest mismatch",
                governing=governing,
                subject_digest=left["digest_git_blob_sha1"],
                subject_name=join["left"],
                receipt_position=position_of(join["left"]),
            )
        if is_transition:
            left_time = join.get("left_time")
            right_time = join.get("right_time")
            if left_time is not None and right_time is not None and left_time != right_time:
                add(
                    position_of(join["left"]),
                    form="ledger transition time mismatch",
                    governing=governing,
                    subject_digest=left["digest_git_blob_sha1"],
                    subject_name=join["left"],
                    receipt_position=position_of(join["left"]),
                )

    for join in pairs:
        run_join(join, False)
    for join in ledger_transitions:
        run_join(join, True)

    joined = set()
    for join in list(pairs) + list(ledger_transitions):
        joined.add(join["left"])
        joined.add(join["right"])
    additional_inputs = [name for name in names if name not in joined]

    classified = checks.classify_one_sided(
        list(one_sided_items), carried_unexplained_count
    )
    all_unchecked = list(unchecked)
    for name in classified["unchecked_elements"]:
        if name not in all_unchecked:
            all_unchecked.append(name)

    pending.sort(key=lambda item: (item[0], item[1]))
    entries = []
    for number, (_position, _seq, spec) in enumerate(pending, start=1):
        entries.append(
            checks.discrepancy_entry(
                number,
                "chain",
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
        "chain",
        entries=entries,
        unchecked_elements=all_unchecked,
        determination_supported=determination_supported,
        extra={
            "classifications": classified["classifications"],
            "overlap_count": classified["overlap_count"],
            "unexplained_count": classified["unexplained_count"],
            "additional_inputs": additional_inputs,
        },
    )
