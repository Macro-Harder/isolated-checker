"""Gate artefact discovery and the unidentifiable form, slice S-02.

Plan statement P1-S02-1, second part, resting on brief Decision 7
and brief section 5.6. A gate artefact is discovered by content
signature and by ledger or step record citation, in addition to
filename, so an artefact renamed or filed under an unexpected
name is still found by what it is and by what cites it.

An artefact that discovery still cannot locate takes the named
discovery outcome for a missing artefact: a discrepancy naming the
artefact kind and the discovery routes tried. An artefact that is
located but cannot be recomputed is reported as unidentifiable
under the decided vocabulary: it does not count as an identified
artefact. A truncated citation that cannot be recomputed does not
count as an identified artefact either, per Decision 7.

This module, MD-16, composes no run determination and no exit
status. What a check or a run takes from an unidentifiable
artefact is composed by MD-06 under the outcome precedence and
composition order at SH-17, and gated by MD-15, when the
operation surface lands at slice S-07, on the classification and
the discovery facts this module supplies.
"""

from .canonical import git_blob_digest

# The discovery routes, in the order this layer tries them.
DISCOVERY_ROUTES = (
    "filename",
    "content signature",
    "ledger citation",
    "step record citation",
)

CITATION_ROUTES = ("ledger citation", "step record citation")


def discover_artefact(candidates, signature=None, citations=()):
    """Discover one gate artefact among presented candidates.

    candidates are presented artefacts as dicts carrying a name, a
    text, and the citations that name them under cited_by. The
    routes are tried in DISCOVERY_ROUTES order: filename first,
    then content signature, then ledger or step record citation.
    Returns the artefact and the route that found it, or None with
    the routes tried where no route locates it.
    """
    for candidate in candidates:
        if signature is not None and candidate.get("name") == signature:
            return {"artefact": candidate, "route": "filename"}
    if signature is not None:
        for candidate in candidates:
            if signature in str(candidate.get("text", "")):
                return {"artefact": candidate, "route": "content signature"}
    for citation in citations:
        for candidate in candidates:
            if citation in candidate.get("cited_by", ()):
                route = (
                    "ledger citation"
                    if str(citation).startswith("ledger")
                    else "step record citation"
                )
                return {"artefact": candidate, "route": route}
    return {"artefact": None, "route": None, "routes_tried": list(DISCOVERY_ROUTES)}


def can_recompute(artefact):
    """True where an artefact digest recomputes from its bytes.

    An artefact carrying content and a recorded digest recomputes
    where the git blob digest of the content equals the recorded
    digest in full. A truncated or missing recorded digest never
    recomputes, and a located artefact that cannot be recomputed
    is unidentifiable, not identified.
    """
    content = artefact.get("content")
    recorded = artefact.get("digest_git_blob_sha1") or artefact.get("recorded_digest")
    if content is None or not recorded:
        return False
    data = content.encode("utf-8") if isinstance(content, str) else bytes(content)
    return git_blob_digest(data) == recorded


def classify_discovery(case):
    """Classify one presented discovery case, in S-02 terms.

    case is a presented state mapping in the harness discovery
    form: a form value with its named parts and no member bytes.
    The result names the presented case classification and the
    discovery facts, in MD-16 terms, in the words the brief states
    for the classification itself. It carries no run determination
    and no exit status of its own: run determinations are composed
    by MD-06 and exit statuses are gated by MD-15, when the
    operation surface lands at slice S-07, on facts of this kind.
    Whether the remaining records of a run support a determination
    is a fact of that run, read by the composing modules from the
    run's records, and no part of it is read or carried here.
    """
    form = case.get("form")
    if form == "renamed_artefact":
        return {
            "outcome": "discovered",
            "artefact_kind": case.get("artefact_kind"),
            "route": "content signature",
            "content_signature": case.get("content_signature"),
            "presented_name": case.get("presented_name"),
        }
    if form == "unlocatable_artefact":
        return {
            "outcome": "missing artefact",
            "artefact_kind": case.get("artefact_kind"),
            "routes_tried": list(case.get("routes_tried", ())),
        }
    if form == "unrecomputable_artefact":
        return {
            "outcome": "unidentifiable",
            "artefact_kind": case.get("artefact_kind"),
            "identified": False,
            "located": True,
            "recomputable": False,
        }
    if form in ("linked_member", "submodule_member"):
        return {
            "outcome": "unchecked",
            "member": case.get("member"),
            "unchecked_by_name": case.get("member"),
            "followed": False,
            "never_followed": True,
        }
    if form == "outside_path_member":
        return {
            "outcome": "unchecked",
            "member": case.get("member"),
            "unchecked_by_name": case.get("member"),
            "followed": False,
            "outside_the_frozen_set": True,
        }
    if form == "instruction_shaped_text":
        return {
            "outcome": "data only",
            "quoted_text": case.get("quoted_text"),
            "source_artefact": case.get("source_artefact"),
            "directs_nothing": True,
        }
    return {"outcome": "unknown discovery form", "form": form}


# ------------------------------------------------ MD-16 resolution duty
#
# The artefact kind to member resolution duty, assigned to this
# module by Plan Supplement 7 Part 2 section S7P2-2. It takes the
# SH-03 layout named at invocation under IF-LAY and the frozen set
# members in receipt order, resolves each layout artefact entry to
# the member its kind requires by the discovery routes above in
# their stated order, subject to the recompute test, and returns
# the denominator in the resolved element form completeness takes.
# It performs no completeness check, returns no verdict, no
# discrepancy entry and no counted determination, invents no member
# for a kind it cannot locate, and composes no run determination
# and no exit status: those belong to MD-05, MD-06 and MD-15.


def _member_name(member):
    if isinstance(member, dict):
        return member.get("name")
    return None


def _member_text(member):
    if isinstance(member, dict):
        content = member.get("content", member.get("text", ""))
    else:
        content = ""
    if isinstance(content, bytes):
        return content.decode("utf-8", errors="replace")
    return str(content)


def _kind_slugs(kind):
    text = str(kind).lower()
    return {
        text,
        text.replace(" ", "-"),
        text.replace(" ", "_"),
        text.replace(" ", ""),
    }


def _locate_member(entry, members):
    """Locate one entry's member by the routes, in stated order."""
    kind = entry.get("artefact_kind", entry.get("kind"))
    slugs = _kind_slugs(kind)
    # Route 1, filename: a member named for the kind, exactly, or by
    # a file stem naming the kind in slug form.
    for member in members:
        name = _member_name(member)
        if name is None:
            continue
        stem = name.rsplit(".", 1)[0].lower() if "." in name else name.lower()
        if name == kind or name.lower() in slugs or stem in slugs:
            return member, "filename"
    # Route 2, content signature: the signature the entry states, or
    # the kind itself, standing in the member's content.
    signature = entry.get("content_signature") or kind
    if signature:
        for member in members:
            if str(signature) in _member_text(member):
                return member, "content signature"
    # Route 3, ledger or step record citation: a citation the entry
    # states standing among the citations that name the member.
    citations = list(entry.get("citations", ()))
    if entry.get("citation"):
        citations.append(entry["citation"])
    for citation in citations:
        for member in members:
            cited_by = member.get("cited_by", ()) if isinstance(member, dict) else ()
            if citation in cited_by:
                route = (
                    "ledger citation"
                    if str(citation).startswith("ledger")
                    else "step record citation"
                )
                return member, route
    return None, None


def resolve_required_elements(
    layout,
    members,
    receipt_order_names=None,
    standings=None,
):
    """Resolve a layout's artefact entries to frozen set members.

    layout is the SH-03 layout record named at invocation; members
    are the frozen set members as presented, supplied through the
    MD-10 supply side, in receipt order where receipt_order_names
    names that order. standings, where supplied, parallels the
    layout entries and carries each entry's per element standings
    (a stated none standing, and for a truncated artefact the
    missing sections with their disposition) into the product
    unchanged; this duty adjudicates none of it.

    Returns one resolved element per artefact entry, in layout
    entry order, in the form completeness takes as its
    required_elements: the member it requires under name (the
    located member's name, or the kind itself where no member is
    located), its governing element reference (the layout artefact
    entry it arises under), the artefact content properties the
    layout states for its kind, any standing carried unchanged, and
    the located member and route where one stands. A located member
    that does not recompute stands unlocated, marked unidentifiable.
    """
    if layout is None:
        return []
    entries = layout.get("artefact_entries", ())
    ordered = list(members or ())
    if receipt_order_names:
        rank = {name: index for index, name in enumerate(receipt_order_names)}
        ordered.sort(
            key=lambda member: rank.get(_member_name(member), len(rank))
        )
    resolved = []
    for index, entry in enumerate(entries):
        kind = entry.get("artefact_kind", entry.get("kind"))
        member, route = _locate_member(entry, ordered)
        unidentifiable = False
        located_name = None
        if member is not None:
            has_digest = isinstance(member, dict) and (
                member.get("digest_git_blob_sha1")
                or member.get("recorded_digest")
            )
            if has_digest and not can_recompute(member):
                unidentifiable = True
                member, route = None, None
            else:
                located_name = _member_name(member)
        element = {
            "name": located_name if located_name is not None else kind,
            "governing_element_reference": "layout artefact " + str(kind),
            "artefact_kind": kind,
            "content_properties": list(entry.get("content_properties", ())),
            "located_member": located_name,
            "route": route,
            "unidentifiable": unidentifiable,
        }
        standing = None
        if standings is not None and index < len(standings):
            standing = standings[index]
        if standing is None and isinstance(entry, dict):
            standing = {
                name: entry[name]
                for name in ("stated_none", "missing_sections", "disposition")
                if name in entry
            } or None
        if standing:
            for name in ("stated_none", "missing_sections", "disposition"):
                if name in standing:
                    element[name] = standing[name]
        resolved.append(element)
    return resolved
