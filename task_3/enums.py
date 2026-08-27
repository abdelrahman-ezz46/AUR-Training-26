"""Status vocabulary for library items.

Using an :class:`enum.Enum` here (instead of magic strings like ``"AVAILABLE"``
scattered through the codebase) buys us three things:

* Typos become ``AttributeError`` at the call site instead of silent bugs
  (``ItemStatus.AVAILBLE`` fails loudly; ``"AVAILBLE"`` would not).
* Comparisons are by identity (``is``), not by string equality, so there is
  no ambiguity about case ("Available" vs "AVAILABLE").
* The set of valid statuses is discoverable (``list(ItemStatus)``) and
  exhaustive - a linter/IDE can tell you if a branch forgets a case.

The member *values* are kept equal to the strings used in ``database.txt``
(e.g. ``ItemStatus.AVAILABLE.value == "AVAILABLE"``) purely so that
serialization (:meth:`ItemStatus.__str__`-free round trip via ``.value`` /
``ItemStatus(...)``) is a one-liner in :mod:`items`.
"""

from __future__ import annotations

from enum import Enum


class ItemStatus(Enum):
    """The lifecycle state of a single :class:`~items.LibraryItem`."""

    AVAILABLE = "AVAILABLE"
    CHECKED_OUT = "CHECKED_OUT"
    LOST = "LOST"

    def __str__(self) -> str:  # pragma: no cover - trivial
        # "CHECKED_OUT" -> "Checked Out" for human-readable display.
        return self.value.replace("_", " ").title()
