"""Shared gate module, plan module MD-15, slice S-07.

This module alone owns the gating precedence at XR-02, stated in
brief sections 5.9 and 5.10. It takes an invocation and the standing
records the gating passage reads, as fixed in the run's snapshot at
first read, and returns exactly one determination: a refusal case
at SH-32, the no bound values state at SH-29, dry standing at
SH-20, or proceed to the called operation. It writes nothing,
issues no report, and takes no exit status of its own: the
resulting artefact of a gating determination belongs to the shape
that states it, produced by the operation module.

The precedence, limb by limb, in its fixed order:

1. Output area validation refusal: an output area standing inside
   the frozen set, inside the packet sources, inside the anchor
   record, naming an existing report, or, for a dry run, the gate
   evidence home, is refused before any check runs.
2. Refusal on a declared version: a version standing under a
   defective or quarantine declaration is refused.
3. The no bound values state: a verdict seeking invocation whose
   record states no bound values takes that state, outside the
   exit statuses.
4. Dry standing: a version that is not calibrated takes dry
   standing, forced, with its three companions.
5. The not current case, in refusal form: a version that is not
   the current version determination is refused.
6. Proceed to the called operation.

A snapshot is taken by the caller at the first read of invocation;
this module reads the snapshot only, so a change during the run to
any governing record takes effect from the next invocation and
never alters the run in progress.
"""

REFUSAL_OUTPUT_AREA = "refusal_output_area"
REFUSAL_DECLARATION = "refusal_declaration"
NO_BOUND_VALUES = "no_bound_values"
DRY_STANDING = "dry_standing"
REFUSAL_NOT_CURRENT = "refusal_not_current"
PROCEED = "proceed"

_OUTPUT_REFUSAL_WORDS = {
    "inside_frozen_set": "frozen set",
    "inside_packet_sources": "packet sources",
    "inside_anchor_record": "anchor record",
    "names_existing_report": "existing report",
    "gate_evidence_home": "gate evidence home",
}


def gating_determination(invocation, snapshot):
    """Return the one gating determination for a run.

    snapshot carries the standing fixed at first read:
    calibration_state, declaration_state, version_current, and the
    output_relation the output area validation reads. The
    invocation carries the bound values and ruling reference and
    the mode. The return is a mapping naming the determination
    kind and the facts its artefact states.
    """
    relation = snapshot.get("output_relation", "valid")
    if relation in _OUTPUT_REFUSAL_WORDS:
        return {
            "kind": REFUSAL_OUTPUT_AREA,
            "output_relation": relation,
            "refused_because": _OUTPUT_REFUSAL_WORDS[relation],
        }
    declaration = snapshot.get("declaration_state", "none")
    if declaration in ("defective", "quarantined"):
        return {
            "kind": REFUSAL_DECLARATION,
            "declaration_state": declaration,
        }
    mode = invocation.get("mode", "verdict")
    if mode not in ("calibration", "fixity") and invocation.get("bound_values") is None:
        return {"kind": NO_BOUND_VALUES}
    if snapshot.get("calibration_state", "calibrated") != "calibrated":
        return {
            "kind": DRY_STANDING,
            "calibration_state": snapshot.get("calibration_state"),
        }
    if not snapshot.get("version_current", True):
        return {"kind": REFUSAL_NOT_CURRENT}
    return {"kind": PROCEED}
