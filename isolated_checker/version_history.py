"""Version history entry and event forms, shape SH-38.

Slice S-01, fourth record family. The entry and event fields are
brief section 8.1. Entries of two kinds are kept distinct: a
version entry, one for each checker version that may issue
verdicts for a build, and an amendment entry, a correction that
does not count as a version entry and stands as a new entry
citing the entry it corrects, carrying that entry in its
corrected standing. The original entry stands unedited. The
record is append only in form and carries no stated protection
against in place editing; no function here spends it at a
stronger strength.
"""

from . import shapes
from .shapes import ShapeError


def calibration_event(
    calibration_record_digest, fixture_suite_version, suite_digest, event_result
):
    """One calibration event of a version entry, brief 8.1."""
    return {
        "event_kind": "calibration",
        "calibration_record_digest": calibration_record_digest,
        "fixture_suite_version": fixture_suite_version,
        "suite_digest": suite_digest,
        "event_result": event_result,
        "gate_record_digest": None,
    }


def declaration_event(gate_record_digest):
    """One declaration event of a version entry, brief 8.1."""
    return {
        "event_kind": "declaration",
        "calibration_record_digest": None,
        "fixture_suite_version": None,
        "suite_digest": None,
        "event_result": None,
        "gate_record_digest": gate_record_digest,
    }


def _event(entry):
    for name in entry:
        if name not in shapes.EVENT_FIELDS:
            raise ShapeError(
                "SH-38 event carries an unnamed field: " + name
            )
    if entry["event_kind"] not in ("calibration", "declaration"):
        raise ShapeError(
            "SH-38 event kind is not a value the shape states: "
            + str(entry["event_kind"])
        )
    return dict(entry)


def version_entry(
    checker_version,
    time_became_current,
    packet_form_versions_judged,
    calibration_fixture_suite_version,
    calibration_result,
    declaration_state,
    events,
):
    """Build a version entry in the SH-38 form.

    The entry level suite version and result fields carry the
    latest calibration event for the version, as brief 8.1 states.
    """
    record = {
        "checker_version": checker_version,
        "time_became_current": time_became_current,
        "packet_form_versions_judged": list(packet_form_versions_judged),
        "calibration_fixture_suite_version": calibration_fixture_suite_version,
        "calibration_result": calibration_result,
        "declaration_state": declaration_state,
        "events": [_event(event) for event in events],
    }
    return shapes.validate("SH-38-entry", record, shapes.VOCABULARY["SH-38-entry"])


def amendment_entry(corrected_entry_citation, corrected_entry):
    """Build an amendment entry citing the entry it corrects.

    The citation names the corrected entry by its checker version,
    the identifier the entry form carries. The amendment carries
    the corrected entry in full, under the entry fields, and the
    original entry stands unedited.
    """
    record = {"corrected_entry_citation": corrected_entry_citation}
    record.update(version_entry(**{
        name: corrected_entry[name]
        for name in (
            "checker_version",
            "time_became_current",
            "packet_form_versions_judged",
            "calibration_fixture_suite_version",
            "calibration_result",
            "declaration_state",
            "events",
        )
    }))
    return shapes.validate("SH-38-amendment", record, shapes.VOCABULARY["SH-38-amendment"])


def is_amendment(record):
    return "corrected_entry_citation" in record


def corrected_entries(records):
    """Return version entries as corrected by their amendments.

    A gate reading a pinned version reads the original entry as
    corrected by its latest correction, so the latest amendment
    citing an entry supplies that entry standing.
    """
    entries = {}
    order = []
    for record in records:
        if is_amendment(record):
            cited = record["corrected_entry_citation"]
            corrected = {
                name: record[name]
                for name in shapes.VOCABULARY["SH-38-entry"]
            }
            if cited not in entries:
                order.append(cited)
            entries[cited] = corrected
        else:
            key = record["checker_version"]
            if key not in entries:
                order.append(key)
            entries[key] = dict(record)
    return [entries[key] for key in order]


def _calibration_events_text(record):
    rendered = []
    for event in record["events"]:
        if event["event_kind"] == "calibration":
            rendered.append(
                event["calibration_record_digest"]
                + "; suite version " + str(event["fixture_suite_version"])
                + "; suite digest " + str(event["suite_digest"])
                + "; result " + str(event["event_result"])
            )
    return "; ".join(rendered)


def _declaration_events_text(record):
    rendered = []
    for event in record["events"]:
        if event["event_kind"] == "declaration":
            rendered.append(str(event["gate_record_digest"]))
    return "; ".join(rendered)


def version_entry_filed_text(record):
    """Render a version entry in its filed form, brief order."""
    return shapes.render_fields(
        [
            ("version", record["checker_version"]),
            ("became current time", record["time_became_current"]),
            (
                "packet form versions",
                "; ".join(record["packet_form_versions_judged"]),
            ),
            (
                "calibration suite version and result",
                str(record["calibration_fixture_suite_version"])
                + "; result " + str(record["calibration_result"]),
            ),
            ("declaration state", record["declaration_state"]),
            ("calibration events", _calibration_events_text(record)),
            ("declaration events", _declaration_events_text(record)),
        ]
    )


def amendment_filed_text(record):
    """Render an amendment entry in its filed form."""
    return shapes.render_fields(
        [("corrected entry citation", record["corrected_entry_citation"])]
    )
