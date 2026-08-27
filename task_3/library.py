"""Collection management: :class:`Library`.

Single Responsibility. ``Library`` owns the in-memory collection and the
checkout/return workflow. It performs **zero raw file I/O** - no
``open()``, no ``read()``/``write()`` calls anywhere in this file. When it
needs to persist or restore the collection it delegates to an injected
:class:`database.Database` instance (composition - "Library may use a
Database instance"), which is the only place actual file handling lives.

Open/Closed Principle. Every method below operates on ``LibraryItem``
polymorphically (``item.checkout()``, ``item.status``, ``sorted(items)``,
...). None of them ever check ``isinstance(item, Book)`` or branch on a
type string, so adding a new ``LibraryItem`` subclass (e.g. ``AudioBook``)
requires no changes here at all.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Iterator

from enums import ItemStatus
from exceptions import ItemNotFoundError
from items import LibraryItem

if TYPE_CHECKING:
    from database import Database


class Library:
    """Manages a collection of :class:`~items.LibraryItem` objects and the
    checkout/return workflow. Does not read or write files itself."""

    def __init__(self, database: "Database | None" = None) -> None:
        self._items: list[LibraryItem] = []
        # Optional: Library MAY use a Database instance for persistence,
        # but never touches a file directly itself (see module docstring).
        self._database = database

    # -- Collection management -------------------------------------------------

    def add_item(self, item: LibraryItem) -> None:
        if not isinstance(item, LibraryItem):
            raise TypeError("Library only stores LibraryItem instances.")
        self._items.append(item)

    def remove_item(self, item: LibraryItem) -> None:
        self._items.remove(item)

    def find_by_title(self, title: str) -> list[LibraryItem]:
        """Case-insensitive exact match on title. Returns a list because a
        library can hold more than one copy of the same title."""
        needle = title.casefold()
        return [item for item in self._items if item.title.casefold() == needle]

    def _first_by_title(self, title: str) -> LibraryItem:
        matches = self.find_by_title(title)
        if not matches:
            raise ItemNotFoundError(f"No item titled {title!r} in the library.")
        return matches[0]

    def list_all(self) -> list[LibraryItem]:
        return sorted(self._items)

    def list_available(self) -> list[LibraryItem]:
        return sorted(item for item in self._items if item.status is ItemStatus.AVAILABLE)

    def list_overdue(self, as_of: date | None = None) -> list[LibraryItem]:
        as_of = as_of or date.today()
        return sorted(
            item
            for item in self._items
            if item.status is ItemStatus.CHECKED_OUT and item.due_date is not None and item.due_date < as_of
        )

    # -- Checkout workflow --------------------------------------------------

    def checkout(self, title: str, borrower: str | None = None) -> LibraryItem:
        """Check out the first AVAILABLE copy of ``title``. Raises
        ItemNotFoundError if there's no such title, or ItemNotAvailableError
        (propagated from LibraryItem.checkout) if every copy is unavailable."""
        matches = self.find_by_title(title)
        if not matches:
            raise ItemNotFoundError(f"No item titled {title!r} in the library.")
        available = next((item for item in matches if item.status is ItemStatus.AVAILABLE), None)
        target = available or matches[0]  # fall back to the first match so
        # the underlying ItemNotAvailableError carries a meaningful status
        target.checkout(borrower=borrower)
        return target

    def return_item(self, title: str) -> LibraryItem:
        matches = [item for item in self.find_by_title(title) if item.status is ItemStatus.CHECKED_OUT]
        if not matches:
            raise ItemNotFoundError(f"No checked-out item titled {title!r} in the library.")
        item = matches[0]
        item.return_item()
        return item

    def mark_lost(self, title: str) -> LibraryItem:
        item = self._first_by_title(title)
        item.mark_lost()
        return item

    # -- Persistence (delegated to Database; see module docstring) ------------

    def load_from_database(self) -> None:
        if self._database is None:
            raise RuntimeError("This Library has no Database configured.")
        self._items = [LibraryItem.from_dict(record) for record in self._database.load()]

    def save_to_database(self) -> None:
        if self._database is None:
            raise RuntimeError("This Library has no Database configured.")
        self._database.save([item.to_dict() for item in self._items])

    # -- Convenience -------------------------------------------------------

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[LibraryItem]:
        return iter(self.list_all())

    def __repr__(self) -> str:
        return f"Library({len(self._items)} item(s))"
