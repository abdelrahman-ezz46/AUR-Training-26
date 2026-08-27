"""Domain model: :class:`LibraryItem` and its concrete subclasses.

Design notes
------------
**Polymorphism.** :class:`LibraryItem` is an ``abc.ABC``. It defines the
shared behaviour (status transitions, comparison, printing, dict
(de)serialization) once; each subclass only supplies what is genuinely
different about it (its extra fields and its loan period).

**Encapsulation.** The status lives in ``self._status`` and is exposed
read-only via the ``status`` property (no setter). External code cannot do
``item.status = ItemStatus.LOST`` - Python raises ``AttributeError:
can't set attribute`` because no setter exists. The *only* way to change
status is through :meth:`checkout`, :meth:`return_item`, and
:meth:`mark_lost`, which also validate the transition.

**Open/Closed Principle.** New item types register themselves
automatically via ``__init_subclass__`` - the moment a subclass of
:class:`LibraryItem` is *defined* anywhere (even outside this file), it is
added to ``LibraryItem._registry`` under its class name. :meth:`from_dict`
dispatches through that registry. This means adding e.g. ``AudioBook``
never requires touching this file's dispatch logic, or ``Library`` - see
``tests/test_library_system.py::OpenClosedPrincipleTests`` for a worked
example that defines a brand new subclass and proves the rest of the
system needs zero edits to support it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Any, ClassVar

from enums import ItemStatus
from exceptions import (
    ItemAlreadyLostError,
    ItemNotAvailableError,
    ItemNotCheckedOutError,
    UnknownItemTypeError,
)


class LibraryItem(ABC):
    """Abstract base class for everything the library can lend out."""

    #: Days an item may be checked out for. Every concrete subclass MUST
    #: override this (enforced informally - see the module docstring; a
    #: subclass that forgets it will raise AttributeError the first time
    #: ``checkout()`` is called, which is caught by the test suite).
    LOAN_PERIOD_DAYS: ClassVar[int]

    #: type name -> concrete class, populated automatically by
    #: __init_subclass__. Keyed on the class's own __name__, which is also
    #: exactly the "type=" value used in database.txt (e.g. "Book").
    _registry: ClassVar[dict[str, type["LibraryItem"]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        LibraryItem._registry[cls.__name__] = cls

    def __init__(self, title: str, status: ItemStatus = ItemStatus.AVAILABLE) -> None:
        if not title or not title.strip():
            raise ValueError("title is required")
        self.title = title
        self._status = status
        self._due_date: date | None = None
        self._borrower: str | None = None

    # -- Encapsulated state -------------------------------------------------

    @property
    def status(self) -> ItemStatus:
        """Read-only. Use checkout()/return_item()/mark_lost() to change it."""
        return self._status

    @property
    def due_date(self) -> date | None:
        """Read-only. Set when checked out, cleared on return/loss."""
        return self._due_date

    @property
    def borrower(self) -> str | None:
        """Read-only. Who currently has the item checked out, if anyone."""
        return self._borrower

    # -- State transitions (the only way to change status) ------------------

    def checkout(self, borrower: str | None = None, *, on: date | None = None) -> None:
        """Check the item out. Raises ItemNotAvailableError if it isn't
        currently AVAILABLE (e.g. already checked out, or lost)."""
        if self._status is not ItemStatus.AVAILABLE:
            raise ItemNotAvailableError(
                f"Cannot check out {self.title!r}: currently {self._status.value}."
            )
        start = on or date.today()
        self._status = ItemStatus.CHECKED_OUT
        self._due_date = start + timedelta(days=self.LOAN_PERIOD_DAYS)
        self._borrower = borrower

    def return_item(self) -> None:
        """Return a checked-out item. Raises ItemNotCheckedOutError if the
        item isn't currently CHECKED_OUT."""
        if self._status is not ItemStatus.CHECKED_OUT:
            raise ItemNotCheckedOutError(
                f"Cannot return {self.title!r}: currently {self._status.value}."
            )
        self._status = ItemStatus.AVAILABLE
        self._due_date = None
        self._borrower = None

    def mark_lost(self) -> None:
        """Mark the item LOST from AVAILABLE or CHECKED_OUT. Raises
        ItemAlreadyLostError if it is already LOST."""
        if self._status is ItemStatus.LOST:
            raise ItemAlreadyLostError(f"{self.title!r} is already marked LOST.")
        self._status = ItemStatus.LOST
        self._due_date = None

    # -- Comparable & printable ----------------------------------------------

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, LibraryItem):
            return NotImplemented
        # casefold() rather than lower() - the Unicode-correct way to do
        # case-insensitive comparison, so sorted() puts "dune" and "Dune"
        # next to each other regardless of case.
        return self.title.casefold() < other.title.casefold()

    def __str__(self) -> str:
        return f"{self.title} ({type(self).__name__}) — {self._status}"

    def __repr__(self) -> str:
        # Built from to_dict() so every subclass's extra fields show up
        # automatically without each subclass needing its own __repr__.
        fields = ", ".join(
            f"{key}={value!r}" for key, value in self.to_dict().items() if key != "type"
        )
        return f"{type(self).__name__}({fields})"

    # -- Serialization --------------------------------------------------------

    def to_dict(self) -> dict[str, str]:
        """Common fields every item has. Subclasses override this, call
        ``super().to_dict()``, and add their own fields (template method
        pattern) - see Book/DVD/Magazine below."""
        return {
            "type": type(self).__name__,
            "title": self.title,
            "status": self._status.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "LibraryItem":
        """Alternative constructor: build the correct concrete subclass
        from a parsed database.txt row, dispatching through the
        subclass registry (no if/elif chain - see module docstring)."""
        item_type = data.get("type")
        target_cls = LibraryItem._registry.get(item_type) if item_type else None
        if target_cls is None:
            raise UnknownItemTypeError(f"No registered LibraryItem subclass for type {item_type!r}")
        return target_cls._build_from_dict(data)

    @classmethod
    @abstractmethod
    def _build_from_dict(cls, data: dict[str, str]) -> "LibraryItem":
        """Subclass hook: pull this type's own fields out of ``data`` and
        construct an instance. Kept separate from from_dict() so the
        dispatch logic (above) lives in exactly one place."""
        raise NotImplementedError


class Book(LibraryItem):
    """A book. Tracks author and ISBN; loan period is 21 days."""

    LOAN_PERIOD_DAYS = 21

    def __init__(
        self,
        title: str,
        author: str,
        isbn: str = "",
        status: ItemStatus = ItemStatus.AVAILABLE,
        *,
        validate_isbn: bool = True,
    ) -> None:
        super().__init__(title, status)
        if not author or not author.strip():
            raise ValueError("author is required")
        self.author = author
        self.isbn = isbn
        if validate_isbn and isbn and not Book.is_valid_isbn(isbn):
            raise ValueError(f"Invalid ISBN-13 checksum: {isbn!r}")

    @staticmethod
    def is_valid_isbn(isbn: str) -> bool:
        """Validate an ISBN-13 checksum.

        We validate ISBN-13 (not ISBN-10): it is the current standard for
        newly published books, and it is what the sample data in the task
        PDF uses (``9780441013593`` for Dune - 13 digits).

        Algorithm: multiply each of the 13 digits by an alternating
        weight of 1, 3, 1, 3, ..., sum the results, and check the sum is
        divisible by 10. This is a @staticmethod (no self/cls) because the
        check is a pure function of the string - it doesn't need an
        instance or the class to do its job.

        Hyphens and spaces are stripped before checking (real-world ISBNs
        are usually printed as "978-0-441-01359-3"). Malformed input
        (wrong length, non-digit characters, wrong type) returns False
        rather than raising, per the spec.
        """
        if not isinstance(isbn, str):
            return False
        cleaned = isbn.replace("-", "").replace(" ", "")
        if len(cleaned) != 13 or not cleaned.isdigit():
            return False
        total = sum((1 if index % 2 == 0 else 3) * int(digit) for index, digit in enumerate(cleaned))
        return total % 10 == 0

    def to_dict(self) -> dict[str, str]:
        data = super().to_dict()
        data.update(author=self.author, isbn=self.isbn)
        return data

    @classmethod
    def _build_from_dict(cls, data: dict[str, str]) -> "Book":
        return cls(
            title=data["title"],
            author=data["author"],
            isbn=data.get("isbn", ""),
            status=ItemStatus(data.get("status", ItemStatus.AVAILABLE.value)),
        )


class DVD(LibraryItem):
    """A DVD. Tracks director; loan period is 5 days (short - popular new
    releases turn over faster)."""

    LOAN_PERIOD_DAYS = 5

    def __init__(
        self,
        title: str,
        director: str,
        status: ItemStatus = ItemStatus.AVAILABLE,
    ) -> None:
        super().__init__(title, status)
        if not director or not director.strip():
            raise ValueError("director is required")
        self.director = director

    def to_dict(self) -> dict[str, str]:
        data = super().to_dict()
        data.update(director=self.director)
        return data

    @classmethod
    def _build_from_dict(cls, data: dict[str, str]) -> "DVD":
        return cls(
            title=data["title"],
            director=data["director"],
            status=ItemStatus(data.get("status", ItemStatus.AVAILABLE.value)),
        )


class Magazine(LibraryItem):
    """A magazine issue. Tracks the issue label (e.g. "2026-08"); loan
    period is 14 days."""

    LOAN_PERIOD_DAYS = 14

    def __init__(
        self,
        title: str,
        issue: str,
        status: ItemStatus = ItemStatus.AVAILABLE,
    ) -> None:
        super().__init__(title, status)
        if not issue or not issue.strip():
            raise ValueError("issue is required")
        self.issue = issue

    def to_dict(self) -> dict[str, str]:
        data = super().to_dict()
        data.update(issue=self.issue)
        return data

    @classmethod
    def _build_from_dict(cls, data: dict[str, str]) -> "Magazine":
        return cls(
            title=data["title"],
            issue=data["issue"],
            status=ItemStatus(data.get("status", ItemStatus.AVAILABLE.value)),
        )
