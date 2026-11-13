"""The isolated checker package.

Slice S-01 delivers the core record forms and pinned conventions
every later slice reads or writes. Later slices add the operation
surface; this package init re-exports the S-01 record builders,
renderers, interface forms, and the canonical encoding module as
they land, family by family.
"""

from .interfaces import layout_input_form
from .receipts import (
    context_filed_text,
    context_record,
    custody_receipt,
    member,
    receipt_filed_text,
)
from .run_statement import (
    bound_values_record,
    run_statement,
    run_statement_filed_text,
)
from .shapes import ShapeError

__all__ = [
    "ShapeError",
    "bound_values_record",
    "layout_input_form",
    "run_statement",
    "run_statement_filed_text",
    "context_filed_text",
    "context_record",
    "custody_receipt",
    "member",
    "receipt_filed_text",
]
