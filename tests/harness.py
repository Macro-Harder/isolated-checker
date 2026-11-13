"""Test harness for the isolated checker suite.

This module states the interface the Step 14 build must satisfy, in the
form the design brief states it, and the fixture loading helpers the
behaviour tests use. It contains no checker logic of its own.

The interface. The build delivers an importable package named
isolated_checker exposing a function with this shape:

    run_invocation(invocation: dict, output_area: pathlib.Path) -> int

The invocation dict carries the invocation fields of brief section 5.7:

    build               the build the run serves
    stage               the stage the run serves
    receipt_digest      the custody receipt digest, the only way the
                        frozen set is identified to the run
    layout_digest       the layout, identified by digest
    layout_version      the layout, identified by version
    checker_version     the checker version invoked
    packet_form_version the packet form version invoked
    mode                one of the seven mode values in MODES below
    anchor_digest       the anchor digest for the receipt
    bound_values        a dict with the four bound keys in BOUND_KEYS,
                        or None where no bound values are in force
    bound_ruling_ref    the reference to the ruling that set the bound
                        values, or None where no bound values are in force
    output_area         the output area for the report, as text, naming
                        the same area the output_area argument names

Mode rerun adds the field original_run_statement_digest, a named field
of brief section 5.8. Mode calibration names the checker version and
the fixture suite version to be calibrated in the version fields, as
brief section 5.8 states; the suite version field is named
fixture_suite_version in this harness. Mode fixity names the kept sets
by receipt digest in the receipt field, as brief section 5.8 states;
this harness names that field kept_set_receipt_digests. Modes appeal and cure add the field
original_report_digest, and mode cure adds discrepancy_numbers, as
brief section 5.8 states. A corrected run is a verdict mode run by a
corrected checker version; beside the brief fields it extends, this
harness states one convention field for it,
defective_run_statement_digest, naming the defective run statement the
corrected run answers, by digest. Freeze intake and the CH7 recheck
are called outside the mode field, as brief section 5.8 states,
through the run_intake_freeze and run_recheck helpers below, which
delegate to the same package when the build provides them and strip
the mode field before delegating. The recheck helper requires its two
added inputs by name, the original run statement digest and the filed
gate record, and states the gate record output home for the recheck
outcome entry beside the output area that holds its report.

Bound values. No value for any bound under register item O-63 stands
named in this suite as a bound value in force. The default invocation
carries no bound values and no ruling reference, which is the no bound
values state the gating module pins. A run that needs bound values
receives test bounds only, through test_bound_values below, carrying
TEST_BOUND_RULING_REF and stated in the test record for a named trial
only; test bounds govern that trial only and never stand as values a
verdict run runs under outside that trial.

The function writes the report and the run statement into the output
area, by the one completion act of brief section 5.22, and returns the
exit status from the outcome table of brief sections 5.11 and 5.12.
The statuses are 0, 1, 2, 3 and 4, with the meanings STATUSES states.

Endings that take no exit status. Brief section 5.14 names the classes
that take no status: the no bound values state, a refused invocation on
a declared version, an intake failure, an interrupted run, a fixity
outcome and a calibration outcome. The not current refusal of brief
section 5.10 and an output area validation refusal of the same section
also take no exit status. For every such ending this harness states
that run_invocation returns None, so that no numeric status is ever
invented for an ending the brief leaves statusless. The single
resulting artefact the governing passage states still stands in the
output area or in its stated home, and the tests assert on it.

Presented facts. The packet contract stands banked in the brief, so no
test in this suite builds a real packet. A test instead presents the
facts its case turns on through one extra invocation key, scenario,
whose subkeys are a test surface convention of this harness and not
brief fields. The build reads the brief fields for the run itself and
reads scenario only as the presented state of the records and material
the brief says a run consults: the seal state of the presented set,
the per check presented outcomes, the gating record states of brief
section 5.9, mid run changes, varied conditions, kept sets for fixity,
addendum presentations and route presentations. Every scenario key a
test uses is named in that test module docstring. A scenario key never
changes a brief field, and no expected outcome in this suite is taken
from scenario wording: each expected status and outcome word is fixed
in advance from the brief rule text.

Material presentations. Where a module docstring names a case as a
material case, the scenario carries material instead of a derived
state: presented_members and presented_receipt, built by
material_scenario below, give the member bytes a run reads and the
receipt entries it compares them against, each receipt entry carrying
the git blob SHA-1 digest and the byte size of its member bytes, so a
wrong comparison over that material fails the test. Cases that keep a
presented state form are named in their module docstrings as
composition only and are not derivation pins.

Artefact discovery. The brief prescribes no output file names, so the
load bearing cases locate an artefact by its content signature, with
artefact_with_signature below, or by the citation a record carries,
and assert content on that artefact, not on the joined text of an
area. Name fragment helpers remain for cases that turn on the absence
of an artefact kind in an area.

Red state. While no checker package exists, run_invocation,
run_intake_freeze and run_recheck raise AssertionError naming the
missing implementation, at call time and never at import or collection
time, so each calling test fails individually and the suite red state
counts real pinned behaviours.

Fixture loading. The fixture suite built beside this harness stands in
the fixtures directory. These helpers depend on that suite only
through two files: fixtures/INDEX.json, and each fixture expected.json
file the index names. Nothing else about the suite layout is assumed.
"""

import hashlib
import json
import pathlib

MODES = (
    "verdict",
    "dry",
    "rerun",
    "calibration",
    "fixity",
    "appeal",
    "cure",
)

INVOCATION_FIELDS = (
    "build",
    "stage",
    "receipt_digest",
    "layout_digest",
    "layout_version",
    "checker_version",
    "packet_form_version",
    "mode",
    "anchor_digest",
    "bound_values",
    "bound_ruling_ref",
    "output_area",
)

ADDED_FIELDS = {
    "rerun": ("original_run_statement_digest",),
    "appeal": ("original_report_digest",),
    "cure": ("original_report_digest", "discrepancy_numbers"),
    "verdict": ("defective_run_statement_digest",),
    "calibration": ("fixture_suite_version",),
    "fixity": ("kept_set_receipt_digests",),
}

BOUND_KEYS = (
    "total_size_bytes",
    "member_count",
    "nesting_depth",
    "read_volume_bytes",
)

STATUSES = {
    0: "pass, with any recorded gap carried in the report",
    1: "FAIL with stage PARTIAL",
    2: "no determination supported",
    3: "bound abort",
    4: "dry run",
}

MISSING_IMPLEMENTATION = (
    "missing implementation: the isolated_checker package and its "
    "run_invocation function do not exist yet; the Step 14 build has "
    "not landed, so this pinned behaviour cannot run"
)

TEST_BOUND_RULING_REF = (
    "test bound stated in the test record for this named trial only; "
    "it governs this trial only and is not a ruling setting a bound value"
)


def _digest(label):
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _blob_digest(data):
    header = b"blob " + str(len(data)).encode("utf-8") + b"\x00"
    return hashlib.sha1(header + data).hexdigest()


def test_bound_values():
    """Return the test bounds for the named harness ordinary run trial.

    These values stand in the test bound form only: they are stated
    here in the test record for the trial named harness ordinary run,
    carry TEST_BOUND_RULING_REF, govern a run that states them for
    that trial only, and are not values for any bound under O-63.
    """
    return {
        "total_size_bytes": 10000000,
        "member_count": 1000,
        "nesting_depth": 64,
        "read_volume_bytes": 50000000,
    }


def with_test_bounds(invocation):
    """State the harness ordinary run trial test bounds on an invocation."""
    invocation["bound_values"] = test_bound_values()
    invocation["bound_ruling_ref"] = TEST_BOUND_RULING_REF
    return invocation


def base_invocation(output_area, **overrides):
    """Build a complete invocation in the brief section 5.7 form.

    The defaults describe one ordinary verdict run over an intact
    presented set whose three checks pass, carrying no bound values,
    which is the no bound values state. A test that needs a verdict
    standing run states test bounds through with_test_bounds or by
    passing bound values in the test bound form for its named trial.
    A test overrides only the fields and scenario facts its case
    turns on.
    """
    invocation = {
        "build": "isolated-checker-test-build",
        "stage": "step-gate-1",
        "receipt_digest": _digest("receipt:base"),
        "layout_digest": _digest("layout:base"),
        "layout_version": "layout-form-1",
        "checker_version": "checker-1.0.0",
        "packet_form_version": "packet-form-1",
        "mode": "verdict",
        "anchor_digest": _digest("anchor:base"),
        "bound_values": None,
        "bound_ruling_ref": None,
        "output_area": str(output_area),
        "scenario": {},
    }
    scenario = dict(invocation["scenario"])
    for key, value in overrides.items():
        if key == "scenario":
            scenario.update(value)
        else:
            invocation[key] = value
    invocation["scenario"] = scenario
    return invocation


def verdict_invocation(output_area, **overrides):
    """Build a verdict standing invocation carrying the trial test bounds."""
    invocation = base_invocation(output_area, **overrides)
    if invocation.get("bound_values") is None and "bound_values" not in overrides:
        with_test_bounds(invocation)
    return invocation


def material_scenario(members, receipt_members=None, **extra):
    """Present a frozen set as material, with its receipt entries.

    members maps a member name to its text content as the run reads
    it. receipt_members maps a member name to the text content the
    custody receipt was issued over; it defaults to members, the
    intact case. Each receipt entry carries the member name, the git
    blob SHA-1 digest of the receipt content and its byte size, so
    the seal comparison runs over presented material.
    """
    if receipt_members is None:
        receipt_members = members
    presented_members = [
        {"name": name, "content": members[name]}
        for name in sorted(members)
    ]
    presented_receipt = []
    for name in sorted(receipt_members):
        data = receipt_members[name].encode("utf-8")
        presented_receipt.append(
            {
                "name": name,
                "digest_git_blob_sha1": _blob_digest(data),
                "byte_size": len(data),
            }
        )
    scenario = {
        "presented_members": presented_members,
        "presented_receipt": presented_receipt,
    }
    scenario.update(extra)
    return scenario


def _load_checker():
    try:
        import isolated_checker
    except ImportError:
        return None
    return isolated_checker


def run_invocation(invocation, output_area):
    """Run one invocation through the checker, when it exists.

    Raises AssertionError naming the missing implementation while no
    checker package exists, so the calling test fails on its own.
    """
    package = _load_checker()
    if package is None or not hasattr(package, "run_invocation"):
        raise AssertionError(MISSING_IMPLEMENTATION)
    pathlib.Path(output_area).mkdir(parents=True, exist_ok=True)
    return package.run_invocation(invocation, pathlib.Path(output_area))


def run_intake_freeze(invocation, output_area):
    """Call freeze intake, which brief section 5.8 calls outside the mode field.

    The mode field is stripped before delegating, so a freeze call as
    this harness builds it carries no mode a build could key on.
    """
    package = _load_checker()
    if package is None or not hasattr(package, "run_intake_freeze"):
        raise AssertionError(
            "missing implementation: isolated_checker.run_intake_freeze "
            "does not exist yet; the Step 14 build has not landed"
        )
    pathlib.Path(output_area).mkdir(parents=True, exist_ok=True)
    call = {key: value for key, value in invocation.items() if key != "mode"}
    return package.run_intake_freeze(call, pathlib.Path(output_area))


def run_recheck(invocation, output_area, original_run_statement_digest=None, gate_record=None):
    """Call the CH7 recheck, which brief section 5.8 calls outside the mode field.

    The two added inputs the recheck passage names are required here
    by name: the original run statement digest and the filed gate
    record. The mode field is stripped before delegating. The report
    stands in the output area and the outcome entry stands in the
    gate record, whose home is stated on the call as gate_record_home
    naming the same area the gate record stands in.
    """
    if original_run_statement_digest is None:
        raise ValueError(
            "run_recheck requires original_run_statement_digest, "
            "the original run statement digest the recheck passage names"
        )
    if gate_record is None:
        raise ValueError(
            "run_recheck requires gate_record, "
            "the filed gate record the recheck passage names"
        )
    package = _load_checker()
    if package is None or not hasattr(package, "run_recheck"):
        raise AssertionError(
            "missing implementation: isolated_checker.run_recheck "
            "does not exist yet; the Step 14 build has not landed"
        )
    pathlib.Path(output_area).mkdir(parents=True, exist_ok=True)
    call = {key: value for key, value in invocation.items() if key != "mode"}
    call["original_run_statement_digest"] = original_run_statement_digest
    call["gate_record"] = gate_record
    call["gate_record_home"] = str(output_area)
    return package.run_recheck(call, pathlib.Path(output_area))


def artefacts(output_area):
    """List every file standing in an output area, sorted by name."""
    root = pathlib.Path(output_area)
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file())


def artefact_texts(output_area):
    """Read every artefact in an output area as text, keyed by file name."""
    texts = {}
    for path in artefacts(output_area):
        texts[path.name] = path.read_text(encoding="utf-8", errors="replace")
    return texts


def combined_text(output_area):
    """Join the text of every artefact in an output area."""
    return "\n".join(artefact_texts(output_area).values())


def artefact_with_signature(output_area, signature):
    """Return the one artefact whose text carries a content signature.

    Discovery is by content signature, in the brief discovery form,
    not by file name. Returns None where no artefact carries the
    signature, and raises AssertionError where more than one does.
    """
    matches = []
    for path in artefacts(output_area):
        text = path.read_text(encoding="utf-8", errors="replace")
        if signature in text:
            matches.append((path, text))
    if len(matches) > 1:
        raise AssertionError(
            "content signature names more than one artefact: " + signature
        )
    if not matches:
        return None
    return matches[0]


def signature_text(output_area, signature):
    """Return the text of the artefact a content signature names, or empty."""
    found = artefact_with_signature(output_area, signature)
    if found is None:
        return ""
    return found[1]


def json_artefacts(output_area):
    """Parse every JSON artefact in an output area, keyed by file name."""
    parsed = {}
    for path in artefacts(output_area):
        if path.suffix == ".json":
            try:
                parsed[path.name] = json.loads(
                    path.read_text(encoding="utf-8", errors="replace")
                )
            except ValueError:
                continue
    return parsed


def record_fields(text):
    """Parse a record artefact text into its ordered field names.

    A record artefact states one field per line in the form
    field name, a colon, then the field value. This helper returns
    the field names in the order the lines state them, for the field
    by field form tests.
    """
    fields = []
    for line in text.splitlines():
        if ":" in line:
            fields.append(line.split(":", 1)[0].strip())
    return fields


def equivalence_signature(output_area):
    """Summarise an output area for rerun and determinism comparison.

    The signature covers the equivalence part only, in the split of
    brief section 5.15, and it is built at field level: a line stands
    in the signature only where its field, the text before the first
    colon on that line, is one of the equivalence part fields that
    section states. Those fields are the binding fields, stated by
    that name and by the names of their constituents (checker
    version, receipt digest, frozen set, layout digest, layout
    version or layout identity and version, packet form version, and
    bound values with their ruling), the run mode, the exit status,
    the three check verdicts (authenticity, chain and completeness,
    by check name or as verdict fields), the discrepancy list, the
    unchecked list and the recorded gap list in full, including
    their numbered entries, the limits fields, including one field
    per limit, the calibration state, the bound outcome and the
    digest computation count. A line stating no equivalence part
    field contributes nothing, wherever it stands, and the run
    varying fields the brief places outside the equivalence part
    (run time, elapsed time and platform read count) state no
    equivalence part field, so no such line stands either.

    An artefact carrying the comparison record signature is a
    comparison record and contributes no line at all, categorically,
    whatever else its text carries, including any mention of the
    equivalence part. An artefact carrying no equivalence part
    wording likewise contributes no line.

    No line carries the name of the file it stands in, and no order
    in the signature rests on a file name or on the partition of
    the kept lines among artefacts: every kept line from every
    artefact stands in one pooled list, and that list is ordered
    line by line by the content of each line itself, so moving the
    same kept lines between artefacts, under any file names and in
    any grouping, and reordering kept lines inside an artefact,
    leaves the signature unchanged, while a difference in any kept
    line, including a kept line added, removed or duplicated,
    changes it. Two runs agree exactly when their signatures are
    equal.
    """
    equivalence_fields = {
        "equivalence part",
        "binding fields",
        "checker version",
        "receipt digest",
        "frozen set",
        "layout digest",
        "layout version",
        "layout identity and version",
        "packet form version",
        "bound values",
        "bound values and ruling",
        "bound ruling",
        "run mode",
        "exit status",
        "authenticity",
        "chain",
        "completeness",
        "authenticity verdict",
        "chain verdict",
        "completeness verdict",
        "check verdicts",
        "discrepancy list",
        "unchecked list",
        "recorded gap list",
        "limits fields",
        "limits field",
        "limit fields",
        "limit field",
        "calibration state",
        "bound outcome",
        "digest computation count",
    }
    numbered_fields = ("discrepancy", "unchecked", "recorded gap", "limit")
    kept_lines = []
    for path in artefacts(output_area):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "comparison record" in text:
            continue
        if "equivalence part" not in text:
            continue
        for line in text.splitlines():
            if ":" not in line:
                continue
            field = line.split(":", 1)[0].strip().lower()
            stem, _, tail = field.rpartition(" ")
            if field in equivalence_fields or (
                stem in numbered_fields and tail.isdigit()
            ):
                kept_lines.append(line.strip())
    kept_lines.sort()
    return "\n".join(kept_lines)


def fixtures_root(root=None):
    if root is not None:
        return pathlib.Path(root)
    return pathlib.Path(__file__).resolve().parent / "fixtures"


def load_fixture_index(root=None):
    """Load fixtures/INDEX.json, the suite index built beside this harness."""
    index_path = fixtures_root(root) / "INDEX.json"
    if not index_path.exists():
        raise AssertionError(
            "missing fixture suite: " + str(index_path) + " does not exist; "
            "the fixture suite seat has not delivered the suite index"
        )
    return json.loads(index_path.read_text(encoding="utf-8"))


def fixture_entries(root=None):
    """Return the index entries as a list, whatever mapping shape wraps them."""
    index = load_fixture_index(root)
    if isinstance(index, list):
        return index
    for key in ("fixtures", "entries", "suite"):
        if isinstance(index, dict) and isinstance(index.get(key), list):
            return index[key]
    if isinstance(index, dict):
        return [
            {"id": key, **value} if isinstance(value, dict) else {"id": key}
            for key, value in index.items()
        ]
    return []


def fixture_id(entry):
    for key in ("id", "fixture_id", "name", "kind"):
        if entry.get(key):
            return str(entry[key])
    return ""


def fixture_dir(entry, root=None):
    """Resolve the directory holding one fixture expected.json file."""
    base = fixtures_root(root)
    for key in ("path", "dir", "directory", "location"):
        if entry.get(key):
            candidate = base / str(entry[key])
            if (candidate / "expected.json").exists():
                return candidate
            if candidate.name == "expected.json" and candidate.exists():
                return candidate.parent
    ident = fixture_id(entry)
    for candidate in (base / ident, base):
        if (candidate / "expected.json").exists():
            return candidate
    raise AssertionError(
        "missing fixture expected file: no expected.json found for fixture "
        + (ident or repr(entry)) + " under " + str(base)
    )


def load_expected(entry, root=None):
    """Load one fixture expected.json file, as the index names it."""
    path = fixture_dir(entry, root) / "expected.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_all_expected(root=None):
    """Load every fixture the index names, as id and expected record pairs."""
    pairs = []
    for entry in fixture_entries(root):
        pairs.append((fixture_id(entry), load_expected(entry, root)))
    return pairs
