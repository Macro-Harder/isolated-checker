"""Outcome and report assembly, plan module MD-06, slice S-07 limb.

Owns the outcome precedence and composition order at SH-17 for the
run surface this slice builds: given the phases' facts (the seal
result, the three checks' verdict material, and the run's recorded
standings), it composes the run's one determination word and its
exit status. No other module in this slice composes a run
determination: the checks return their own verdict material, the
seal returns its own XR-01 emission, discovery returns facts only,
and MD-15 alone gates the exit status classes that take no status.

The composition order, as brief sections 5.11 and 5.12 state it:
dry standing first, then bound abort, then the custody gap of a
broken seal, then a pending CH7 state, then the check outcomes,
then a recorded gap carried at a passing status, then a clean
pass. A run which takes an exit status takes exactly one.
"""

OUTCOME_DRY = "dry run"
OUTCOME_BOUND = "bound abort"
OUTCOME_CUSTODY_GAP = "custody gap"
OUTCOME_PENDING = "pending"
OUTCOME_PARTIAL = "FAIL with stage PARTIAL"
OUTCOME_UNVERIFIABLE = "UNVERIFIABLE"
OUTCOME_RECORDED_GAP = "pass with recorded gap"
OUTCOME_PASS = "clean pass"


def compose_outcome(
    check_results=(),
    seal_result=None,
    recorded_gap=False,
    pending_ch7=False,
    bound_hit=False,
    dry=False,
):
    """Compose one run determination from the phases' facts.

    Returns a mapping with the determination word, the exit
    status, and the check verdicts in R-80 order as presented.
    Facts are read only: no check verdict is altered here, and a
    discovery classification is never an input to this composition.
    """
    verdicts = {}
    for result in check_results:
        verdicts[result["check"]] = result["verdict"]
    if dry:
        return {
            "determination": OUTCOME_DRY,
            "exit_status": 4,
            "check_verdicts": verdicts,
        }
    if bound_hit:
        return {
            "determination": OUTCOME_BOUND,
            "exit_status": 3,
            "check_verdicts": verdicts,
        }
    if seal_result is not None and seal_result.get("status") == "broken seal":
        return {
            "determination": OUTCOME_CUSTODY_GAP,
            "exit_status": seal_result["exit_status"],
            "check_verdicts": verdicts,
        }
    failing = [
        result
        for result in check_results
        if result["verdict"] in ("fail", "cannot run")
    ]
    if failing:
        supported = any(
            result.get("determination_supported", True) for result in failing
        )
        return {
            "determination": (
                OUTCOME_PARTIAL if supported else OUTCOME_UNVERIFIABLE
            ),
            "exit_status": 1 if supported else 2,
            "check_verdicts": verdicts,
        }
    if pending_ch7:
        return {
            "determination": OUTCOME_PENDING,
            "exit_status": 2,
            "check_verdicts": verdicts,
        }
    if recorded_gap:
        return {
            "determination": OUTCOME_RECORDED_GAP,
            "exit_status": 0,
            "check_verdicts": verdicts,
        }
    return {
        "determination": OUTCOME_PASS,
        "exit_status": 0,
        "check_verdicts": verdicts,
    }
