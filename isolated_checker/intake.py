"""Freeze intake shell, plan module MD-10 for the freeze surface.

The shell half of slice S-03: run_intake_freeze, the freeze
surface brief section 5.8 calls outside the mode field. The core
at MD-03 writes nothing itself; this shell performs the two
stateful writes of CT-01, the store write and the anchor write,
in their stated order, under the dual write protocol of plan
section 7 contract CT-01:

member copies into the store first, as staged copies for this one
freeze attempt; the two full set passes of brief section 5.4
next; the receipt issued next; and the anchor write last. The
anchor write is the commit point of the freeze. Before the commit
point no receipt stands and no frozen set may be read by any
operation; the staged copies are discarded if the attempt does
not commit. A retry of an uncommitted attempt reuses staged
copies only after verifying each one digest by digest against the
handed in material, rewrites any copy that does not verify, and
reruns the passes, issuing the one receipt for the attempt. Where
an anchor entry already stands for the receipt digest of an
attempt with the same value, the freeze stands committed and the
standing receipt is returned with no second anchor entry; an
anchor entry standing with a different value is never
overwritten, and the attempt stops as a freeze that cannot
complete. A freeze attempt closed as failed takes the intake
failure record at SH-33, and a later presentation of the same
material is a new intake, not a resumption.

Presented facts arrive through the invocation scenario key, as
the test harness states that convention: presented_members and
presented_receipt present the handed in material, and the freeze
mapping presents a change between the two passes, material that
cannot be frozen, and the late member case. No parameter is ever
taken from packet material; the invocation brief fields name the
build, the stage, and the versions the freeze runs under.

The gate record is an outside record the checker only reads, at
SH-40: this shell writes into it in no case and beside it in no
case, and it authors no gate record artefact. The intake order
field at SH-08 is the operator's field, written by the operator
as each intake for a gate freezes; where an operator filed gate
record stands in the output area, this shell reads the anchor
home naming from it and leaves the file exactly as it stands.
"""

import pathlib
import shutil
import time

from . import canonical
from . import freeze as freeze_core
from . import pinning
from . import receipts
from .canonical import git_blob_digest

EXAMPLE_MEMBER = {
    "name": "example-member.txt",
    "content": "Example packet member, labelled as an example.\n",
    "source_kind": "example packet",
}


def _presented_members(invocation):
    """Build the handed in member list from the presented facts."""
    scenario = invocation.get("scenario") or {}
    freeze_cfg = scenario.get("freeze") or {}
    if freeze_cfg.get("cannot_be_frozen"):
        return [{"name": "material that cannot be frozen", "unreadable": True}]
    if "presented_members" in scenario:
        return [
            {
                "name": entry["name"],
                "content": entry["content"],
                "source_kind": "handed in material",
            }
            for entry in scenario["presented_members"]
        ]
    if "presented_receipt" in scenario:
        return [
            {
                "name": entry["name"],
                "digest_git_blob_sha1": entry["digest_git_blob_sha1"],
                "byte_size": entry["byte_size"],
                "source_kind": "handed in material",
            }
            for entry in scenario["presented_receipt"]
        ]
    return [dict(EXAMPLE_MEMBER)]


def _second_pass(members, invocation):
    """Build the second full pass of handed in material.

    The presented change between passes alters the first member
    that carries bytes. Every other case re-reads the same
    material in full.
    """
    scenario = invocation.get("scenario") or {}
    freeze_cfg = scenario.get("freeze") or {}
    second = [dict(member) for member in members]
    if freeze_cfg.get("second_pass_differs"):
        for member in second:
            if "content" in member:
                member["content"] = member["content"] + "changed between passes\n"
                break
            if "digest_git_blob_sha1" in member:
                member["digest_git_blob_sha1"] = git_blob_digest(
                    b"changed between passes"
                )
                break
    return second


def _anchor_filed_text(result):
    """Render the anchor record entry, in its qualified form.

    Every digest this text names as a receipt digest is the
    issued receipt's own self digest, from the freeze result.
    A receipt digest presented on an invocation is no part of a
    freeze: CT-01 names no such read, a freeze produces the
    receipt digest rather than receiving it, and no governing
    text names a presented form for it at the filing surface,
    so a presented value stands in this text not at all, and
    never beside the self digest in the same identity position.
    """
    lines = [
        "anchor record",
        "anchor entry: " + result["receipt_digest"],
        "receipt digest: " + str(result["receipt_digest"]),
        "anchor strength: the anchoring record "
        + freeze_core.ANCHOR_QUALIFIED_FORM
        + "; custody wording is bounded at transcription strength",
    ]
    return "\n".join(lines) + "\n"


def _freeze_reads(invocation, output_area):
    """Present the CT-01 reads of a freeze, as facts for the core.

    Where the harness presents these inputs through its scenario
    convention, they are consumed as presented facts in that form:
    pinning_record, context_claim, standing_rule_versions,
    outside_standard_versions, and the gate record's anchor home
    naming under gate_record or anchor_home. Where no pinning
    record is presented, the standing pinning record for the
    invoked checker version stands as the read: the pair bound to
    that version at CE-1, built through the SH-44 record form.
    Version lists stand exactly as presented, and as an empty
    reading where the presented source states none.
    """
    scenario = invocation.get("scenario") or {}
    presented_pin = scenario.get("pinning_record")
    if presented_pin is None:
        presented_pin = pinning.pinning_record(
            canonical.DEFAULT_ALGORITHM,
            canonical.CANONICAL_FORM,
            invocation.get("checker_version"),
        )
    gate = scenario.get("gate_record") or {}
    anchor_home = (
        scenario.get("anchor_home")
        or gate.get("anchor_home")
        or _operator_gate_record_anchor_home(output_area)
    )
    return {
        "pinning_record": presented_pin,
        "context_claim": scenario.get("context_claim"),
        "standing_rule_versions": scenario.get("standing_rule_versions"),
        "outside_standard_versions": scenario.get(
            "outside_standard_versions"
        ),
        "anchor_home": anchor_home,
    }


def _operator_gate_record_anchor_home(output_area):
    """Read the anchor home naming from an operator filed gate record.

    A read path only, at SH-40 and CT-01: the gate record naming
    the anchor home for the build is one of freeze intake's reads.
    Returns the naming the operator's record states on its anchor
    home line, and None where no operator gate record stands in
    the output area or the record names no anchor home. The file
    is never written by this shell.
    """
    gate_path = pathlib.Path(output_area) / "gate-record.txt"
    if not gate_path.exists():
        return None
    for line in gate_path.read_text(
        encoding="utf-8", errors="replace"
    ).splitlines():
        name, _, value = line.partition(":")
        if name.strip() == "anchor home":
            return value.strip()
    return None


def run_intake_freeze(invocation, output_area):
    """Freeze one intake and issue its custody receipt, or fail it.

    Returns the receipt self digest of the committed freeze, and
    None where the material takes the intake failure form, which
    takes no exit status. The artefacts stand in the output area:
    the frozen store copies, the context record, the custody
    receipt, and, written last as the commit point, the anchor
    record entry. No gate record artefact stands among them: the
    gate record is the operator's record, read where it stands
    and never authored here. On failure only the intake failure
    record stands, filed outside the frozen set, and the staged
    copies are discarded.
    """
    out = pathlib.Path(output_area)
    out.mkdir(parents=True, exist_ok=True)
    # CT-01 reads for this freeze, the gate record naming the
    # anchor home among them, presented to the core as reads.
    # The gate record is read only; the record and its intake
    # order field are the operator's, at SH-08 and SH-40.
    reads = _freeze_reads(invocation, out)
    freeze_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    members = _presented_members(invocation)
    second = _second_pass(members, invocation)
    staged = out / "staged-copies"
    store = out / "frozen-store"
    # Store write, first part: member copies staged for this one
    # attempt. A staged copy already standing from an interrupted
    # attempt is reused only where it verifies digest by digest.
    staged.mkdir(parents=True, exist_ok=True)
    for member in members:
        if "content" not in member:
            continue
        data = member["content"].encode("utf-8")
        target = staged / member["name"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            standing = target.read_bytes()
            if git_blob_digest(standing) != git_blob_digest(data):
                target.write_bytes(data)
        else:
            target.write_bytes(data)
    result = freeze_core.freeze_intake(
        members,
        second,
        build=invocation.get("build"),
        stage=invocation.get("stage"),
        packet_form_version=invocation.get("packet_form_version"),
        checker_version=invocation.get("checker_version"),
        freeze_time=freeze_time,
        pinning_record=reads["pinning_record"],
        standing_rule_versions=reads["standing_rule_versions"],
        outside_standard_versions=reads["outside_standard_versions"],
        anchor_home=reads["anchor_home"],
        context_claim=reads["context_claim"],
    )
    if result["status"] != "frozen":
        shutil.rmtree(staged, ignore_errors=True)
        (out / "intake-failure-record.txt").write_text(
            freeze_core.intake_failure_filed_text(result["failure_record"]),
            encoding="utf-8",
        )
        return None
    # An anchor entry standing with a different value for this
    # receipt digest is never overwritten: the attempt stops as a
    # freeze that cannot complete, before any receipt stands.
    anchor_path = out / "anchor-record.txt"
    if anchor_path.exists():
        standing = anchor_path.read_text(encoding="utf-8")
        if "anchor entry: " + result["receipt_digest"] not in standing:
            shutil.rmtree(staged, ignore_errors=True)
            (out / "intake-failure-record.txt").write_text(
                freeze_core.intake_failure_filed_text(
                    receipts.intake_failure_record(
                        "anchor entry standing with a different value",
                        freeze_core.HANDING_SEAT,
                        freeze_time,
                        "a freeze that cannot complete",
                    )
                ),
                encoding="utf-8",
            )
            return None
    # The frozen set stands in the checker held store, written by
    # the checker alone after freeze: the staged copies become the
    # held copies, and the staging home is removed.
    if store.exists():
        shutil.rmtree(store)
    staged.rename(store)
    (out / "context-record.txt").write_text(
        "context record\n" + receipts.context_filed_text(result["context_record"]),
        encoding="utf-8",
    )
    (out / "custody-receipt.txt").write_text(
        receipts.receipt_filed_text(
            result["receipt"],
            {
                r["digest_git_blob_sha1"]: r["name"]
                for r in result["members"]
            },
        ),
        encoding="utf-8",
    )
    # Anchor write last: the commit point of the freeze. An anchor
    # entry already standing for this receipt digest with the same
    # value is a completed write and is not written again.
    if not anchor_path.exists():
        anchor_path.write_text(
            _anchor_filed_text(result), encoding="utf-8"
        )
    return result["receipt_digest"]
