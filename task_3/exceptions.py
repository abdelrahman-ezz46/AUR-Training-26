"""Custom exceptions for the library system.

Raising specific exception types (rather than a bare ``ValueError`` or
``Exception``) lets calling code distinguish *why* an operation failed and
react accordingly (e.g. a UI layer could catch ``ItemNotAvailableError`` and
show "already checked out" instead of a generic error).
"""

from __future__ import annotations


class LibraryError(Exception):
    """Base class for every error raised by this package."""


class ItemNotAvailableError(LibraryError):
    """Raised when :meth:`items.LibraryItem.checkout` is called on an item
    that is not currently :attr:`enums.ItemStatus.AVAILABLE`."""


class ItemNotCheckedOutError(LibraryError):
    """Raised when :meth:`items.LibraryItem.return_item` is called on an
    item that is not currently :attr:`enums.ItemStatus.CHECKED_OUT`."""


class ItemAlreadyLostError(LibraryError):
    """Raised when :meth:`items.LibraryItem.mark_lost` is called on an item
    that is already :attr:`enums.ItemStatus.LOST`."""


class UnknownItemTypeError(LibraryError):
    """Raised by :meth:`items.LibraryItem.from_dict` when the ``type`` field
    does not match any registered :class:`items.LibraryItem` subclass."""


class ItemNotFoundError(LibraryError):
    """Raised by :class:`library.Library` when an operation references a
    title that is not in the collection."""
