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
