"""Read interface forms, plan statement P1-S01-5.

Slice S-01 delivers three forms and their return forms only: the
calibration state read interface form IF-CAL, the version history
determination read interface form IF-VER, and the invocation input
form for the layout IF-LAY. It does not deliver the duties that
produce the records behind them. Each function takes presented
records in the record forms this slice delivers and returns the
form its brief passage states and no wider form.
"""

from .calibration import calibration_passes
from .shapes import ShapeError


def layout_input_form(invocation):
    """IF-LAY: the layout naming an invocation carries.

    An invocation names the layout by digest and version, as brief
    sections 5.6 and 5.7 state. The return is that naming only,
    with the layout itself standing as an invocation input of
    unstated provenance.
    """
    for field in ("layout_digest", "layout_version"):
        if field not in invocation or invocation[field] is None:
            raise ShapeError(
                "IF-LAY invocation does not name the layout by " + field
            )
    return {
        "layout_digest": invocation["layout_digest"],
        "layout_version": invocation["layout_version"],
    }


def calibration_state_form(
    latest_record, covering, suite_register=None, digest_fn=None
):
    """IF-CAL: derive the calibration state from a presented record.

    Inputs are the latest calibration record, in the SH-22 record
    form, covering the checker version, the fixture suite version,
    the packet form version and the layout form version named in
    covering, together with the suite register reading that names
    the current suite version and its pre recorded digest, as
    brief section 5.9 states that reading. The return is the
    calibration state field value, derived as brief section 5.19
    states: calibrated where the latest covering record is a pass
    covering all four versions and not calibrated in every other
    case, together with the digest of the record the value was
    derived from, for the snapshot a run records. The record digest
    is computed by the canonical module under CE-4; a caller may
    supply digest_fn until that module lands in this slice.
    """
    covers = (
        latest_record["checker_version"] == covering["checker_version"]
        and latest_record["fixture_suite_version"]
        == covering["fixture_suite_version"]
        and latest_record["packet_form_version"]
        == covering["packet_form_version"]
        and latest_record["layout_form_version"]
        == covering["layout_form_version"]
    )
    register_agrees = True
    if suite_register is not None:
        register_agrees = (
            latest_record["fixture_suite_version"]
            == suite_register["current_suite_version"]
            and latest_record["suite_digest"]
            == suite_register["pre_recorded_suite_digest"]
        )
    state = (
        "calibrated"
        if covers and register_agrees and calibration_passes(latest_record)
        else "not calibrated"
    )
    if digest_fn is None:
        from .canonical import calibration_citation_digest

        digest_fn = calibration_citation_digest
    return {
        "calibration_state": state,
        "calibration_record_digest": digest_fn(latest_record),
    }
