"""Data only reading and owned field extraction, slice S-02.

The reading layer the check component uses, plan statement
P1-S02-1. Members are read only from the frozen set. Fields are
read at the positions the owned field list names: the 14 items of
brief Decision 8, taken from the grill decisions register section
11.1, exhaustively and no others. Packet text is treated as a
value to compare or to quote and never as a direction: this module
returns text as data in every path, and no text read here is ever
executed, followed, or obeyed. No member reference is followed
outside the frozen set.

This module sits at the reading seam plan Part 2 draws: the shell
adapters of MD-10 supply member bytes from the frozen set store,
and the checks of MD-05 consume what this layer extracts. Counting
hooks for the resource bounds of slice S-13 are landed with this
slice reading path, as statement P1-S13-3 requires: a counter
passed in by the caller records members read, bytes read, and
digest computations, and no bound value is named or applied here.
"""

from .canonical import git_blob_digest

# The owned field list of brief Decision 8, the 14 items of the
# grill decisions register section 11.1, in list order. A field on
# this list is checked wherever it appears; a field not on this
# list is not checked, and reports state that fields outside the
# owned list are unchecked.
OWNED_FIELDS = (
    "link subject digests and byte sizes",
    "link predicate type and predicate content",
    "spawn bindings",
    "roster entries",
    "step inputs and step outputs",
    "gate record required fields",
    "push verification entries",
    "path ledger transitions",
    "packet membership",
    "layout denominators",
    "trace element sets and marks",
    "brainstew frontmatter citations",
    "derived record figures",
    "checker report binding fields",
)

OWNED_FIELD_COUNT = 14

# Member forms the checker does not cover, brief Decision 18. Each
# is reported unchecked by name and never as a pass, and no
# reference in such a member is followed outside the frozen set.
FORM_ORDINARY = "ordinary member"
FORM_LINKED = "linked member"
FORM_OUTSIDE_PATH = "path pointing outside the frozen set"
FORM_SUBMODULE = "submodule style entry"

UNCOVERED_FORMS = (FORM_LINKED, FORM_OUTSIDE_PATH, FORM_SUBMODULE)


class ReadingCounter:
    """Counting hooks for slice S-13, landed with this reading path.

    Counts only: members read, bytes read, digest computations,
    and the deepest member nesting traversed. No bound value is
    named, compared, or enforced in this module.
    """

    def __init__(self):
        self.members_read = 0
        self.bytes_read = 0
        self.digest_computations = 0
        self.max_depth = 0

    def note_member(self, byte_size, depth=0):
        self.members_read += 1
        self.bytes_read += byte_size
        if depth > self.max_depth:
            self.max_depth = depth

    def note_digest(self):
        self.digest_computations += 1


def member_form(member):
    """Name the form of one presented member, brief Decision 18.

    A member presented with an explicit form keeps it. Otherwise a
    member carrying a link target is a linked member, a member
    whose name points outside the set is an outside path, and a
    member marked as a submodule entry is a submodule style entry.
    Every other member is an ordinary member of the frozen set.
    """
    form = member.get("form")
    if form in UNCOVERED_FORMS or form == FORM_ORDINARY:
        return form
    if member.get("link_target") is not None or member.get("target"):
        return FORM_LINKED
    if member.get("submodule"):
        return FORM_SUBMODULE
    name = str(member.get("name", ""))
    if name.startswith("../") or name.startswith("/") or "/../" in name:
        return FORM_OUTSIDE_PATH
    return FORM_ORDINARY


def is_uncovered(member):
    """True where the member form is one the checker does not cover."""
    return member_form(member) in UNCOVERED_FORMS


def read_member(member, counter=None):
    """Read one member of the frozen set, data only.

    Returns a dict with the member name, its bytes, its git blob
    digest recomputed from those bytes, and its byte size. An
    uncovered member form is never read and never followed: it
    returns the unchecked by name result of brief Decision 18,
    carrying the member name and its form, and no bytes.
    """
    form = member_form(member)
    name = str(member.get("name", ""))
    if form in UNCOVERED_FORMS:
        return {
            "name": name,
            "form": form,
            "unchecked": True,
            "unchecked_by_name": name,
            "followed": False,
            "content": None,
            "digest_git_blob_sha1": None,
            "byte_size": None,
        }
    content = member.get("content", "")
    data = content.encode("utf-8") if isinstance(content, str) else bytes(content)
    if counter is not None:
        counter.note_member(len(data), depth=int(member.get("depth", 0)))
        counter.note_digest()
    return {
        "name": name,
        "form": form,
        "unchecked": False,
        "unchecked_by_name": None,
        "followed": False,
        "content": data,
        "digest_git_blob_sha1": git_blob_digest(data),
        "byte_size": len(data),
    }


def read_members(members, counter=None):
    """Read a frozen set member list, in the order presented.

    Returns the readings in presentation order and the unchecked
    list: every uncovered member form, by name and by form, in the
    order the members stand. No reading in the result was followed
    outside the frozen set.
    """
    readings = [read_member(member, counter) for member in members]
    unchecked = [
        {"name": reading["name"], "form": reading["form"]}
        for reading in readings
        if reading["unchecked"]
    ]
    return {"readings": readings, "unchecked": unchecked}


def parse_record_fields(text):
    """Parse a filed record text into its fields, data only.

    A filed record states one field per line in the form field
    name, a colon, then the field value. This reader returns the
    fields in file order as name and value pairs and reads no
    field as an instruction, whatever its value says.
    """
    fields = []
    for line in text.splitlines():
        if ":" in line:
            name, _, value = line.partition(":")
            fields.append((name.strip(), value.strip()))
    return fields


def extract_owned_fields(record, owned=OWNED_FIELDS):
    """Extract the owned fields of one record, at their positions.

    record maps a field item name to the value read for it. Only
    items on the owned list are extracted, each at the position
    the owned list names for it, in owned list order. Keys present
    in the record that stand outside the owned list are not read:
    they are returned by name in the unchecked list, because a
    field outside the owned list is an unchecked field.
    """
    extracted = {}
    for position, item in enumerate(owned, start=1):
        if item in record:
            extracted[item] = {"position": position, "value": record[item]}
    unchecked = [name for name in record if name not in owned]
    return {"fields": extracted, "unchecked": unchecked}


def extract_link_fields(link):
    """Extract the owned fields of one presented link record.

    The link subject digest and byte size (owned item 1), the link
    predicate type and content (owned item 2), and the spawn
    binding the link records (owned item 3) are read at their named
    positions in the presented link. Every other key the link
    carries is returned by name as unchecked and is not read.
    """
    record = {}
    if "recorded_digest" in link or "artefact" in link:
        record["link subject digests and byte sizes"] = {
            "artefact": link.get("artefact"),
            "recorded_digest": link.get("recorded_digest"),
        }
    if "link" in link:
        record["link predicate type and predicate content"] = link.get("link")
    if "spawn" in link or "seat" in link:
        record["spawn bindings"] = {
            "spawn": link.get("spawn"),
            "seat": link.get("seat"),
        }
    extracted = extract_owned_fields(record)
    known = {"artefact", "recorded_digest", "link", "spawn", "seat"}
    extra = [name for name in link if name not in known]
    return {"fields": extracted["fields"], "unchecked": extracted["unchecked"] + extra}


# Words that make a text instruction shaped. The list is a reading
# aid only: shaped text is still data, and shaping changes nothing
# about how the text is treated.
_INSTRUCTION_MARKERS = (
    "close the",
    "run ",
    "execute",
    "ignore",
    "delete",
    "approve",
    "merge",
    "publish",
)


def looks_instruction_shaped(text):
    """True where a text reads as an instruction to a reader."""
    lowered = str(text).lower()
    return any(marker in lowered for marker in _INSTRUCTION_MARKERS)


def treat_as_data(text, source_artefact=None, source_digest=None):
    """Take packet text as a value, never as a direction.

    Returns the quoting form the report duty uses: the text itself
    as packet text, attributed to its source artefact by digest in
    filer claim language, marked as directing nothing. The text is
    compared or quoted by callers; it is never carried out.
    """
    return {
        "packet_text": str(text),
        "source_artefact": source_artefact,
        "source_digest": source_digest,
        "attribution": "filer claim",
        "directs_nothing": True,
        "instruction_shaped": looks_instruction_shaped(text),
    }
