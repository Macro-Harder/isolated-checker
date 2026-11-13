"""The runner over the three checks, plan module MD-05, slice S-05.

This module is the composition home of run_all_checks, standing
beside the shared machinery at checks.py, in the form the
operation modules take at the operation seam: a composition
module depends on the modules it composes. It depends on the
shared machinery and on each of the three check modules, at top
level, and nothing it composes depends on it, so the dependency
direction inside the MD-05 split runs one way, the three check
modules depending on the shared machinery module and this runner
depending on all four, as the split's one way direction states.
The runner stood inside checks.py until Step 14 finding T14-16:
a composition function inside the machinery module importing its
own consumers closed a static import cycle, and deferring those
imports to call time changed when the dependency was taken, not
whether it stood. No import in this module stands below module
level.

The runner composes no run outcome and no exit status: that
composition belongs to MD-06 and stands with its owning slice.
"""

from . import checks
from .authenticity import check_authenticity
from .chain import check_chain
from .completeness import check_completeness
from .reading import ReadingCounter


def run_all_checks(
    members,
    receipt_members=None,
    receipt_member_names=None,
    links=(),
    roster=None,
    layout=None,
    required_records=(),
    sources=(),
    pairs=(),
    ledger_transitions=(),
    one_sided_items=(),
    carried_unexplained_count=0,
    required_elements=(),
    denominator_outside_bundle=True,
    has_steps=False,
    determination_supported=True,
    counter=None,
):
    """Run the three checks in R-80 order over one frozen set.

    The runner the operation modules compose over: authenticity,
    chain, and completeness, each in its own module, each consuming
    the shared machinery in checks.py and the same counter, so the
    digest computation count a report carries counts every
    recomputation the three checks made. The collision twin naming
    over the receipt's members stands with the authenticity result,
    the check whose per item recomputation the twin condition
    defeats: twin entries fail that check where it otherwise
    passed. No run outcome or exit status is composed here: that
    composition belongs to MD-06 and stands with its owning slice.
    """
    if counter is None:
        counter = ReadingCounter()
    authenticity = check_authenticity(
        members,
        links=links,
        roster=roster,
        layout=layout,
        required_records=required_records,
        sources=sources,
        receipt_member_names=receipt_member_names,
        determination_supported=determination_supported,
        counter=counter,
    )
    chain = check_chain(
        members,
        pairs=pairs,
        ledger_transitions=ledger_transitions,
        one_sided_items=one_sided_items,
        carried_unexplained_count=carried_unexplained_count,
        receipt_member_names=receipt_member_names,
        determination_supported=determination_supported,
        counter=counter,
    )
    completeness = check_completeness(
        members,
        layout=layout,
        required_elements=required_elements,
        denominator_outside_bundle=denominator_outside_bundle,
        has_steps=has_steps,
        determination_supported=determination_supported,
        receipt_member_names=receipt_member_names,
        counter=counter,
    )
    collision_entries = (
        checks.collision_twin_entries(receipt_members)
        if receipt_members is not None
        else []
    )
    if collision_entries and authenticity["verdict"] == checks.VERDICT_PASS:
        authenticity = dict(authenticity)
        authenticity["verdict"] = checks.VERDICT_FAIL
        authenticity["outcome_word"] = checks.OUTCOME_PARTIAL
        authenticity["discrepancy_entries"] = (
            list(authenticity["discrepancy_entries"]) + collision_entries
        )
    return {
        "checks": [authenticity, chain, completeness],
        "collision_entries": collision_entries,
        "counter": counter,
    }
