"""Read interface forms, plan statement P1-S01-5.

Slice S-01 delivers three forms and their return forms only: the
calibration state read interface form IF-CAL, the version history
determination read interface form IF-VER, and the invocation input
form for the layout IF-LAY. It does not deliver the duties that
produce the records behind them. Each function takes presented
records in the record forms this slice delivers and returns the
form its brief passage states and no wider form.
"""

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
