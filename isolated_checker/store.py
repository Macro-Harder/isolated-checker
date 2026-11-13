"""Store production, stage one of the store duties, slice S-03.

Plan statement P1-S03-5. The store component at the head of brief
section 5 holds frozen sets and run records for as long as rerun
and appeal routes need them, and freeze intake in slice S-03 is
what places a frozen set in that holding, in the checker held
store, written by the checker alone after freeze.

Stage one is the whole of the store behaviour slice S-12
consumes: on a call naming a held set by its custody receipt
digest, which brief section 5.7 states is the only way the set is
identified to a run, the store produces the set exactly as its
receipt names it, member by member on digest and byte size, or
the production fails in the named form for a set that cannot be
produced in its receipt form, including a set withdrawn from the
store, and no rebuilt or substituted set is offered in its
place.

The remaining store duties stand at slice S-15 and build on this
stage: the scheduled fixity checks, the selection rule, the
mismatch form, and the suspension of routes. None of them is
claimed here.
"""

PRODUCTION_FAILURE_FORM = "cannot be produced in its receipt form"


def produce_held_set(receipt_digest, receipt_members, held_members=None,
                     withdrawn=False):
    """Produce one held set by its custody receipt digest.

    receipt_members are the members the custody receipt names, in
    receipt order, each with its member name, its digest, and its
    byte size. held_members, where supplied, are the members the
    store actually holds, in the same entry form; where a held
    member is missing, or its digest or byte size differs from
    the receipt entry, the set cannot be produced in its receipt
    form. A withdrawn set takes the same production failure. The
    failure offers no rebuilt or substituted set.
    """
    if withdrawn:
        return {
            "status": "production failure",
            "receipt_digest": receipt_digest,
            "failure": PRODUCTION_FAILURE_FORM,
            "reason": "the set has been withdrawn from the store",
            "substitute_offered": False,
            "members": [],
        }
    if held_members is not None:
        held = {entry["name"]: entry for entry in held_members}
        for entry in receipt_members:
            standing = held.get(entry["name"])
            if standing is None:
                return _mismatch(receipt_digest, entry["name"])
            if (
                standing["digest_git_blob_sha1"] != entry["digest_git_blob_sha1"]
                or int(standing["byte_size"]) != int(entry["byte_size"])
            ):
                return _mismatch(receipt_digest, entry["name"])
    return {
        "status": "produced",
        "receipt_digest": receipt_digest,
        "members": [
            {
                "name": entry["name"],
                "digest_git_blob_sha1": entry["digest_git_blob_sha1"],
                "byte_size": int(entry["byte_size"]),
            }
            for entry in receipt_members
        ],
        "substitute_offered": False,
    }


def _mismatch(receipt_digest, member_name):
    return {
        "status": "production failure",
        "receipt_digest": receipt_digest,
        "failure": PRODUCTION_FAILURE_FORM,
        "reason": "member does not stand in its receipt form: " + member_name,
        "substitute_offered": False,
        "members": [],
    }


def produced_set_filed_text(production):
    """Render a produced set, member by member, in receipt order."""
    lines = ["produced set", "receipt digest: " + str(production["receipt_digest"])]
    for entry in production["members"]:
        lines.append(
            entry["name"] + " " + entry["digest_git_blob_sha1"]
            + " " + str(entry["byte_size"])
        )
    return "\n".join(lines) + "\n"


class HeldStore:
    """The checker held store, stage one: holding and production.

    Sets enter the store at freeze, keyed by their custody
    receipt digest. Production is by receipt digest only. A set
    may be withdrawn, after which it takes the production failure
    and is never rebuilt or substituted.
    """

    def __init__(self):
        self._sets = {}
        self._withdrawn = set()

    def hold(self, receipt_digest, receipt_members, held_members=None):
        """Place one frozen set in the store, as freeze intake does."""
        self._sets[receipt_digest] = {
            "receipt_members": list(receipt_members),
            "held_members": held_members,
        }
        self._withdrawn.discard(receipt_digest)

    def withdraw(self, receipt_digest):
        """Withdraw one held set from the store."""
        self._withdrawn.add(receipt_digest)

    def produce(self, receipt_digest):
        """Produce one held set, or take the production failure."""
        standing = self._sets.get(receipt_digest)
        if standing is None:
            return {
                "status": "production failure",
                "receipt_digest": receipt_digest,
                "failure": PRODUCTION_FAILURE_FORM,
                "reason": "no set stands in the store under that receipt digest",
                "substitute_offered": False,
                "members": [],
            }
        return produce_held_set(
            receipt_digest,
            standing["receipt_members"],
            standing["held_members"],
            withdrawn=receipt_digest in self._withdrawn,
        )
