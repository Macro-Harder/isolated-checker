"""Addendum handling, plan module MD-05, slice S-06.

The checker side of the late entry addendum form, resting on
brief sections 5.31 and 5.32 and plan statements P1-S06-1 to
P1-S06-4, criterion A8. The addendum record form itself stands at
slice S-01 in addenda.py, in the SH-35 form; this module is the
handling of such records inside check reading, exercised over the
check reading slice S-05 delivers, and it builds no second copy
of that form and no second copy of the discrepancy entry form:
addendum records are taken in through the MD-02 seam in the
SH-35 form, with the fields its form states required per form,
and every discrepancy this handling reports is built through
the shared SH-14 builder in checks.py, in the other named form
plan Q2 states for the addendum passages, carrying the governing
passage's form name and no defect kind code.

The successor and consequence rule of brief section 5.32, stated
once there, is the whole rule this module applies. At most one
successor stands per digest per packet. Chains are followed to
one terminal digest; a chain that forks or cycles is reported
as a discrepancy naming the digests at the fork or in the cycle,
and no terminal digest is taken. A link citing a superseded
digest is reported naming both digests, the superseded digest
and the successor digest, stating the digest the link was
checked against, which is the cited digest: the corrected bytes
are checked only as a new intake under the cure route, never
under the original link authority. Bytes that changed with no
addendum standing in the packet are reported under the existing
defect kinds, in the digest mismatch form the checks already
use, and are never absorbed as a clean pass because the current
bytes recompute. An addendum arriving in a later intake is
treated in that later intake only: this handling never edits an
earlier report, and the result states that standing in terms.
Labelling is reported as labelling: an openly labelled late
completion is reported as late against the property it missed,
and the label is converted into a pass in no count and no
wording. A reason in an addendum is a filer claim, never a
checked fact, and a correction time in an addendum is a filer
claim, never a checked fact: the filed text of this handling
states both in that form, as the governing texts state them,
and never rests on the reason value carrying the words itself.

The two filer tests of brief section 5.32 run in their stated
order on every addendum treated in this intake. First, the
filer seat is checked against the roster authorisation: the
authorised seats are a named input of the handling, in the form
the roster check for spawn records already uses, a mapping by
seat or a collection of seats. Second, the filer identity is
matched against the seat recorded as filing the original
artefact in the custody receipt for its intake or, where that
record names none, against the producer identity recorded for
that material in the packet. An addendum failing either test
takes the unauthorised filing outcome and is not followed: it
creates no successor, no chain, and no supersession. Where no
roster authorisation input stands, or neither identity
reference stands, the missing input is named unchecked and the
addendum is not followed, and no unauthorised outcome is
invented for a test that could not run.

Traversal counting for the resource bounds of slice S-13 is
landed with this slice, as statement P1-S13-3 requires: a
reading counter the caller may pass in records the deepest
addendum chain traversal, counting only, and no bound value is
named, compared, or applied here. Material is consumed only as
recomputed through the reading layer: where members are
supplied, their digests are recomputed by the shared reading
path of the checks, and no presented digest is trusted. This
module composes no run determination and no exit status: that
composition belongs to MD-06 and stands with its owning slice.
"""

from . import checks, shapes
from .reading import ReadingCounter
from .shapes import ShapeError

DEFAULT_PACKET = "packet"

SH35_REQUIRED = (
    "original_digest",
    "corrected_digest",
    "correction_time",
    "correction_reason_filer_claim",
    "correcting_seat",
)
SH35_SECOND_DIGESTING = ("old_digest", "new_digest", "successor_algorithm")
CONTEXT_FIELDS = (
    "packet",
    "arrives_in_intake",
    "original_filing_seat",
    "producer_identity",
    "labelled_late",
    "missed_property",
)

REASON_STRENGTH = "filer claim"
CORRECTION_TIME_STRENGTH = "filer claim, never a checked fact"
CORRECTED_BYTES_ROUTE = "new intake under the cure route"
_UNAUTHORISED_FORM = "unauthorised filing"
_ROSTER_UNCHECKED = "roster authorisation for addendum filers"


def validate_addendum(presentation):
    """Take one presented addendum in through the MD-02 seam.

    Returns the addendum record in the SH-35 form and nothing
    wider: the five fields brief section 5.31 states stand
    required per form through shapes.validate, and the second
    digesting fields of the successor algorithm form stand all
    or none, as slice S-01 states them. Presentation context
    (the packet, the intake it arrives in, the identity
    references, a late label) is not record material and stands
    in no field of the record.
    """
    extracted = {}
    for name in shapes.VOCABULARY["SH-35"]:
        if name in presentation:
            extracted[name] = presentation[name]
    shapes.validate("SH-35", extracted, SH35_REQUIRED)
    second = [name for name in SH35_SECOND_DIGESTING if name in extracted]
    if second and len(second) != len(SH35_SECOND_DIGESTING):
        raise ShapeError(
            "SH-35 second digesting form carries all three of its "
            "fields or none"
        )
    return extracted


def _authorised_seat_set(authorised_seats):
    if authorised_seats is None:
        return None
    if isinstance(authorised_seats, dict):
        return set(authorised_seats)
    if isinstance(authorised_seats, str):
        return {authorised_seats}
    return set(authorised_seats)


def filer_test_results(record, authorised_seats, original_filing_seat, producer_identity):
    """Run the two filer tests of brief section 5.32, in order.

    Returns the standing of each test, the first failed test in
    the stated order where one fails, and the identity reference
    the second test matched against. A test whose input does not
    stand is reported as not checked, with its missing input
    named by the caller as unchecked; it is not reported as
    passed and not reported as failed.
    """
    seat = record["correcting_seat"]
    authorised = _authorised_seat_set(authorised_seats)
    if authorised is None:
        roster = "not checked"
    elif seat in authorised:
        roster = "pass"
    else:
        roster = "fail"
    if original_filing_seat is not None:
        reference = original_filing_seat
        reference_name = (
            "seat recorded as filing the original artefact in the "
            "custody receipt for its intake"
        )
        failed_name = "identity match against the original filing seat"
    elif producer_identity is not None:
        reference = producer_identity
        reference_name = "producer identity recorded for that material in the packet"
        failed_name = "identity match against the producer identity"
    else:
        reference = None
        reference_name = None
        failed_name = None
    if reference is None:
        identity = "not checked"
    elif seat == reference:
        identity = "pass"
    else:
        identity = "fail"
    failed_test = None
    if roster == "fail":
        failed_test = "roster authorisation"
    elif identity == "fail":
        failed_test = failed_name
    return {
        "roster_authorisation": roster,
        "identity_match": identity,
        "identity_reference": reference_name,
        "failed_test": failed_test,
    }


def follow_addendum_chain(start_digest, successors):
    """Follow one addendum chain to one terminal digest.

    successors maps a digest in one packet to the corrected
    digests claimed for it by followed addenda, in presentation
    order. The follow stops at a digest with no successor (the
    terminal digest), at a digest with more than one claimed
    successor (a fork, naming the digests at the fork), or at a
    digest already on the path (a cycle, naming the digests in
    the cycle). A fork and a cycle take no terminal digest. The
    depth returned is the number of addendum steps traversed,
    the traversal count slice S-13 reads.
    """
    path = [start_digest]
    seen = {start_digest: 0}
    depth = 0
    current = start_digest
    fork = None
    cycle = []
    terminal = None
    while True:
        claimed = list(successors.get(current, ()))
        if len(claimed) > 1:
            fork = {"digest": current, "claimed_successors": claimed}
            break
        if not claimed:
            terminal = current
            break
        following = claimed[0]
        depth += 1
        if following in seen:
            cycle = path[seen[following]:]
            break
        path.append(following)
        seen[following] = len(path) - 1
        current = following
    return {
        "start_digest": start_digest,
        "path": path,
        "terminal_digest": terminal,
        "depth": depth,
        "fork": fork,
        "cycle_digests": cycle,
    }


def handle_addenda(
    addenda=(),
    links=(),
    members=None,
    authorised_seats=None,
    original_filing_seats=None,
    producer_identities=None,
    current_intake=None,
    receipt_member_names=None,
    counter=None,
):
    """Handle the addenda of one packet inside check reading.

    addenda are presented addendum records in the SH-35 form,
    each optionally carrying presentation context beside the
    record fields: packet (the packet the successor limit is
    counted per, one packet where none is stated),
    arrives_in_intake, original_filing_seat and
    producer_identity (the two identity references of the
    second filer test, the receipt seat where it stands and
    the producer identity otherwise), and labelled_late with
    missed_property for an openly labelled late completion.
    links name the links of the packet, each with its link
    name, its artefact, and the digest it cites, under
    cited_digest or recorded_digest. members, where supplied,
    are the frozen set's members, consumed only as recomputed
    through the reading layer, for the changed bytes case.
    authorised_seats is the roster authorisation input of the
    first filer test. original_filing_seats and
    producer_identities, where supplied, map an original
    digest to the identity references of the second filer
    test, for presentations carrying no reference of their
    own. current_intake names the intake this
    handling treats: an addendum arriving in another intake is
    treated in that intake only.

    Returns the dispositions of every addendum presented, the
    chains followed, the fork and cycle standings, the
    superseded links with the digest each was checked against,
    the changed bytes standing with no addendum, the labelling
    reports, the later intake addenda, the discrepancy entries
    in the SH-14 form, the unchecked elements by name, and the
    deepest traversal depth counted. No earlier report is
    edited by this handling, in any case.
    """
    if counter is None:
        counter = ReadingCounter()
    unchecked = []
    dispositions = []
    later_intake_addenda = []
    labelling_reports = []
    pending_entries = []

    def add_entry(check, form, governing, subject_digest=None, subject_name=None):
        pending_entries.append(
            {
                "check": check,
                "form": form,
                "governing": governing,
                "subject_digest": subject_digest,
                "subject_name": subject_name,
            }
        )

    followed = []
    for presentation in addenda:
        record = validate_addendum(presentation)
        context = {name: presentation.get(name) for name in CONTEXT_FIELDS}
        packet = context["packet"] or DEFAULT_PACKET
        disposition = {
            "record": record,
            "packet": packet,
            "followed": False,
            "later_intake_only": False,
            "failed_test": None,
            "identity_reference": None,
            "filer_tests": None,
            "second_digesting": (
                {name: record[name] for name in SH35_SECOND_DIGESTING}
                if all(name in record for name in SH35_SECOND_DIGESTING)
                else None
            ),
            "original_receipt_rewritten": False,
            "reason_strength": REASON_STRENGTH,
            "correction_time_strength": CORRECTION_TIME_STRENGTH,
        }
        dispositions.append(disposition)
        arrives = context["arrives_in_intake"]
        if (
            arrives is not None
            and current_intake is not None
            and arrives != current_intake
        ):
            disposition["later_intake_only"] = True
            later_intake_addenda.append(
                {
                    "original_digest": record["original_digest"],
                    "corrected_digest": record["corrected_digest"],
                    "arrives_in_intake": arrives,
                    "treated_in_intake": arrives,
                }
            )
            continue
        receipt_seat = context["original_filing_seat"]
        if receipt_seat is None and original_filing_seats:
            receipt_seat = original_filing_seats.get(record["original_digest"])
        producer = context["producer_identity"]
        if producer is None and producer_identities:
            producer = producer_identities.get(record["original_digest"])
        context["original_filing_seat"] = receipt_seat
        context["producer_identity"] = producer
        tests = filer_test_results(
            record,
            authorised_seats,
            receipt_seat,
            producer,
        )
        disposition["filer_tests"] = tests
        disposition["identity_reference"] = tests["identity_reference"]
        if tests["roster_authorisation"] == "not checked":
            if _ROSTER_UNCHECKED not in unchecked:
                unchecked.append(_ROSTER_UNCHECKED)
            continue
        if tests["identity_match"] == "not checked":
            name = (
                "identity reference for the original artefact at "
                + str(record["original_digest"])
            )
            if name not in unchecked:
                unchecked.append(name)
            continue
        if tests["failed_test"] is not None:
            disposition["failed_test"] = tests["failed_test"]
            if tests["failed_test"] == "roster authorisation":
                governing = (
                    "roster authorisation test for the addendum "
                    "filed by seat " + str(record["correcting_seat"])
                )
            elif context["original_filing_seat"] is not None:
                governing = (
                    "identity match against the seat recorded as "
                    "filing the original artefact in the custody "
                    "receipt for its intake"
                )
            else:
                governing = (
                    "identity match against the producer identity "
                    "recorded for that material in the packet"
                )
            add_entry(
                "authenticity",
                _UNAUTHORISED_FORM,
                governing,
                subject_digest=record["original_digest"],
            )
            continue
        disposition["followed"] = True
        followed.append((packet, record))
        if context["labelled_late"]:
            labelling_reports.append(
                {
                    "original_digest": record["original_digest"],
                    "corrected_digest": record["corrected_digest"],
                    "missed_property": context["missed_property"],
                    "reported_as": "labelled late",
                    "converted_to_pass": False,
                    "is_pass": False,
                }
            )

    successors_by_packet = {}
    for packet, record in followed:
        packet_map = successors_by_packet.setdefault(packet, {})
        claimed = packet_map.setdefault(record["original_digest"], [])
        if record["corrected_digest"] not in claimed:
            claimed.append(record["corrected_digest"])

    chains = []
    forks = []
    cycles = []
    seen_forks = set()
    seen_cycles = set()
    max_depth = 0

    def note_follow(packet, start):
        nonlocal max_depth
        result = follow_addendum_chain(
            start, successors_by_packet.get(packet, {})
        )
        if result["depth"] > max_depth:
            max_depth = result["depth"]
        if result["fork"] is not None:
            key = (packet, result["fork"]["digest"])
            if key not in seen_forks:
                seen_forks.add(key)
                fork = {
                    "packet": packet,
                    "digest": result["fork"]["digest"],
                    "claimed_successors": result["fork"]["claimed_successors"],
                }
                forks.append(fork)
                add_entry(
                    "chain",
                    "fork",
                    "addendum chain fork at digest "
                    + str(fork["digest"])
                    + " with claimed successors "
                    + ", ".join(fork["claimed_successors"]),
                    subject_digest=fork["digest"],
                )
        if result["cycle_digests"]:
            key = (packet, tuple(result["cycle_digests"]))
            if key not in seen_cycles:
                seen_cycles.add(key)
                cycles.append(
                    {"packet": packet, "digests": result["cycle_digests"]}
                )
                add_entry(
                    "chain",
                    "cycle",
                    "addendum chain cycle through digests "
                    + ", ".join(result["cycle_digests"]),
                    subject_digest=result["cycle_digests"][0],
                )
        return result

    for packet, packet_map in successors_by_packet.items():
        corrected = {
            corrected
            for claimed in packet_map.values()
            for corrected in claimed
        }
        heads = [digest for digest in packet_map if digest not in corrected]
        if not heads and packet_map:
            heads = [next(iter(packet_map))]
        for head in heads:
            result = note_follow(packet, head)
            chains.append(
                {
                    "packet": packet,
                    "start_digest": result["start_digest"],
                    "path": result["path"],
                    "terminal_digest": result["terminal_digest"],
                    "depth": result["depth"],
                }
            )

    superseded_links = []
    for link in links:
        cited = link.get("cited_digest", link.get("recorded_digest"))
        if cited is None:
            continue
        packet = link.get("packet") or DEFAULT_PACKET
        packet_map = successors_by_packet.get(packet, {})
        if cited not in packet_map:
            continue
        result = note_follow(packet, cited)
        if result["fork"] is not None or result["cycle_digests"]:
            continue
        successor = packet_map[cited][0]
        link_name = link.get("link") or link.get("artefact") or "link"
        superseded_links.append(
            {
                "link": link_name,
                "artefact": link.get("artefact"),
                "cited_digest": cited,
                "successor_digest": successor,
                "terminal_digest": result["terminal_digest"],
                "checked_digest": cited,
                "corrected_bytes_route": CORRECTED_BYTES_ROUTE,
            }
        )
        add_entry(
            "authenticity",
            "superseded link",
            str(link_name)
            + " cites a superseded digest: successor digest "
            + str(successor)
            + ", checked digest "
            + str(cited),
            subject_digest=cited,
        )

    changed_bytes = []
    if members is not None:
        readings, member_unchecked = checks.read_frozen_members(members, counter)
        for name in member_unchecked:
            if name not in unchecked:
                unchecked.append(name)
        by_name = checks.readings_by_name(readings)
        names = (
            list(receipt_member_names)
            if receipt_member_names
            else sorted(by_name)
        )
        for link in links:
            artefact = link.get("artefact")
            recorded = link.get("recorded_digest", link.get("cited_digest"))
            reading = by_name.get(artefact)
            if reading is None or recorded is None:
                continue
            recomputed = reading["digest_git_blob_sha1"]
            if recomputed == recorded:
                continue
            packet = link.get("packet") or DEFAULT_PACKET
            packet_map = successors_by_packet.get(packet, {})
            if packet_map.get(recorded) and recomputed in packet_map[recorded]:
                continue
            link_name = link.get("link") or artefact or "link"
            changed_bytes.append(
                {
                    "artefact": artefact,
                    "recorded_digest": recorded,
                    "recomputed_digest": recomputed,
                    "no_addendum": True,
                    "reported_under": "existing defect kinds",
                    "absorbed_as_clean_pass": False,
                }
            )
            add_entry(
                "authenticity",
                "digest mismatch",
                str(link_name) + " subject digest",
                subject_digest=recomputed,
            )

    if max_depth > counter.max_depth:
        counter.max_depth = max_depth

    entries = []
    for number, spec in enumerate(pending_entries, start=1):
        entries.append(
            checks.discrepancy_entry(
                number,
                spec["check"],
                checks.CATEGORY_OTHER_NAMED_FORM,
                governing_element_reference=spec["governing"],
                discrepancy_form_name=spec["form"],
                subject_digest=spec["subject_digest"],
                subject_name=spec["subject_name"],
            )
        )

    return {
        "addenda": dispositions,
        "chains": chains,
        "forks": forks,
        "cycles": cycles,
        "superseded_links": superseded_links,
        "changed_bytes_without_addendum": changed_bytes,
        "labelling_reports": labelling_reports,
        "later_intake_addenda": later_intake_addenda,
        "discrepancy_entries": entries,
        "unchecked_elements": unchecked,
        "max_traversal_depth": max_depth,
        "counter": counter,
        "earlier_report_edited": False,
    }


def addendum_handling_filed_text(result):
    """Render one handling result in its filed text form.

    Every addendum the handling reports stands in the form the
    governing texts state it: both digests named where a link
    cites a superseded digest, with the digest checked stated;
    the reason and the correction time stated as filer claims,
    never as checked facts; a fork and a cycle naming their
    digests with no terminal digest taken; an unauthorised
    filing naming the test it failed; a labelled late completion
    reported as late and never as a pass; and a later intake
    addendum treated in that intake only, with the earlier
    report standing unedited.
    """
    lines = ["addendum handling"]
    for disposition in result["addenda"]:
        record = disposition["record"]
        if disposition["later_intake_only"]:
            lines.append(
                "later intake: an addendum naming original digest "
                + str(record["original_digest"])
                + " and corrected digest "
                + str(record["corrected_digest"])
                + " arrives in a later intake and is treated in "
                "that later intake only; it is a new intake "
                "matter; the earlier report stands unedited"
            )
            continue
        if disposition["failed_test"] is not None:
            lines.append(
                "unauthorised filing: the addendum filed by seat "
                + str(record["correcting_seat"])
                + " for original digest "
                + str(record["original_digest"])
                + " is not followed; failed test: "
                + str(disposition["failed_test"])
            )
            continue
        if not disposition["followed"]:
            continue
        lines.append(
            "addendum: original digest: "
            + str(record["original_digest"])
            + "; corrected digest: "
            + str(record["corrected_digest"])
            + "; correction time: "
            + str(record["correction_time"])
            + "; reason: "
            + str(record["correction_reason_filer_claim"])
            + "; filed by seat: "
            + str(record["correcting_seat"])
        )
        lines.append(
            "filer claim: the reason in an addendum is a filer "
            "claim, never a checked fact, and the correction "
            "time in an addendum is a filer claim, never a "
            "checked fact"
        )
        if disposition["second_digesting"] is not None:
            second = disposition["second_digesting"]
            lines.append(
                "second digesting: old digest "
                + str(second["old_digest"])
                + " and new digest "
                + str(second["new_digest"])
                + " bound side by side under successor algorithm "
                + str(second["successor_algorithm"])
                + "; the original receipt is never rewritten"
            )
    for chain in result["chains"]:
        line = (
            "addendum chain: "
            + " -> ".join(str(digest) for digest in chain["path"])
            + "; traversal depth: "
            + str(chain["depth"])
        )
        if chain["terminal_digest"] is not None:
            line += "; terminal digest: " + str(chain["terminal_digest"])
        else:
            line += "; no terminal digest"
        lines.append(line)
    for fork in result["forks"]:
        lines.append(
            "fork: digest "
            + str(fork["digest"])
            + "; claimed successors: "
            + ", ".join(str(digest) for digest in fork["claimed_successors"])
            + "; no terminal digest"
        )
        if len(fork["claimed_successors"]) == 2:
            lines.append(
                "two addenda claiming to succeed the same digest: "
                + str(fork["digest"])
                + "; no terminal digest"
            )
    for cycle in result["cycles"]:
        lines.append(
            "cycle: digests "
            + ", ".join(str(digest) for digest in cycle["digests"])
            + "; no terminal digest"
        )
    for link in result["superseded_links"]:
        lines.append(
            "superseded link: "
            + str(link["link"])
            + " cites "
            + str(link["cited_digest"])
            + "; successor digest: "
            + str(link["successor_digest"])
            + "; terminal digest: "
            + str(link["terminal_digest"])
            + "; checked digest: "
            + str(link["checked_digest"])
            + "; corrected bytes are checked only as a new "
            "intake under the cure route, never under the "
            "original link authority"
        )
    for changed in result["changed_bytes_without_addendum"]:
        lines.append(
            "correction with no addendum: "
            + str(changed["artefact"])
            + " recorded "
            + str(changed["recorded_digest"])
            + " and recomputed "
            + str(changed["recomputed_digest"])
            + "; no addendum stands in the packet; the change "
            "is reported under the existing defect kinds and "
            "is not a clean pass"
        )
    for report in result["labelling_reports"]:
        lines.append(
            "labelled late completion: reported as late against "
            + str(report["missed_property"])
            + "; labelling is reported as labelling and is not "
            "a pass; the label is converted into a pass in no "
            "count and no wording"
        )
    return "\n".join(lines) + "\n"
