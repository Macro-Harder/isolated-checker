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
artefact, and the check that needed it takes FAIL with stage
PARTIAL at exit status 1 where the remaining records support a
determination and UNVERIFIABLE at exit status 2 where they support
none. A truncated citation that cannot be recomputed does not
count as an identified artefact either, per Decision 7.
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
    The result names the S-02 outcome for the case, in the words
    the brief states for it, so the run surface of later slices
    composes statuses from it without rederiving the reading rule.
    Determination support is read from the case where the brief
    outcome turns on it, and from no other place.
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
        supported = case.get("determination_support") == "supported"
        return {
            "outcome": "unidentifiable",
            "artefact_kind": case.get("artefact_kind"),
            "identified": False,
            "determination": (
                "FAIL with stage PARTIAL" if supported else "UNVERIFIABLE"
            ),
            "exit_status": 1 if supported else 2,
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
