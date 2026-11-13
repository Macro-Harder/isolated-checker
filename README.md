# Isolated checker

## The problem it answers

A build closes its stages at gates, and a gate closes on evidence: records, links, digests, and reports filed by the work itself. That evidence can drift, break, or stop matching the material it claims to cover, and a reader checking it by hand cannot recompute every digest or follow every link across a whole packet. The isolated checker answers that problem. It freezes the material handed in for one step gate, issues a custody receipt for the frozen set, and runs three checks over the frozen set only, in a fixed order: authenticity, chain, and completeness. It reports what it checked, what it found, and what it did not check, so a gate decision rests on recomputed evidence rather than on the filings taken at face value.

## Who it serves

The audience is the gate boards and operators of a build: the operator who freezes an intake and runs the checker in the gate sequence, and the board that reads the discrepancy report and the run statement beside it and decides whether the stage closes. Every report names its unchecked elements, carries its limits with it, and cites the custody receipt and the run statement as one pair, so the board can see exactly what a verdict covers and what it does not.

## What stands in this repo

The checker is a small offline tool written in Python with the standard library only. It lives in the `isolated_checker` package. The test suite that pins its behaviour lives in `tests/`, beside the code it tests, and runs with one command from the repo root:

```sh
python3 -m unittest discover -s tests
```

The build is still in progress. The record forms, the data only reading layer, and freeze intake with custody receipt issue have landed; the remaining checks, run operations, and report forms land slice by slice, each against tests written before it.

## What the product will not do

- It carries no update machinery. A checker version changes only when a new version is installed and calibrated; nothing in the product updates itself or anything else.
- It is not a standing service. It runs when an operator invokes it for a gate, writes its report and run statement to the output area, and stops. It watches nothing, polls nothing, and holds no state between runs except the frozen sets and records its routes need.
- It makes no claim above the bounds its design carries. It checks the owned fields only, over the frozen set only, and every report states that fields outside the owned list are unchecked. It does not certify the quality of the work in a record, the identity of any person, the independence of the producers, or the truth of a stated reason. An unchecked element is never a pass, a dry run is never a verdict, and a digest match is never proof that the bytes are the bytes originally filed.
- It takes no instructions from the material it checks. Packet text is data only: a value to compare or to quote, never a direction. No parameter of a run is taken from packet material, and no member reference is followed outside the frozen set.
