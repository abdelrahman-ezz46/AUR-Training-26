"""Persistence layer: :class:`Database`.

Single Responsibility. This module knows exactly one thing: how to turn
the pipe-delimited lines of ``database.txt`` into ``list[dict[str, str]]``
and back. It deliberately has **no idea that ``Book``/``DVD``/``Magazine``
or even ``LibraryItem`` exist** - it never imports :mod:`items`. That is
what makes the split with :class:`library.Library` a genuine SRP split
rather than a cosmetic one: you could reuse ``Database`` to persist any
list-of-dicts data, and you could swap in a different storage backend for
``Library`` without this file caring what a "Book" is.

``Library`` turns dicts into ``LibraryItem`` objects (via
``LibraryItem.from_dict``) and back (via ``item.to_dict()``); this file
only ever sees the dicts.

Singleton (bonus). ``Database`` uses the classic ``__new__`` override so
that every ``Database(...)`` call anywhere in the process returns the same
object, and opens the backing file **once**, keeping a single ``r+`` file
handle for the lifetime of the program (reused via ``seek``/``truncate``
rather than being closed and reopened on every save/load).
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar


class Database:
    """Singleton responsible for save/load of the collection to/from a
    pipe-delimited text file, e.g. ``database.txt``."""

    _instance: ClassVar["Database | None"] = None

    def __new__(cls, filepath: str = "database.txt") -> "Database":
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._instance = instance
        return cls._instance

    def __init__(self, filepath: str = "database.txt") -> None:
        # __init__ runs every time Database(...) is called, even though
        # __new__ returns the shared instance - guard so we only open the
        # file once. A later Database("other.txt") call silently keeps
        # using the file that was opened first; that's the point of a
        # singleton with "one open connection".
        if self._initialized:
            return
        self.filepath = filepath
        path = Path(filepath)
        if not path.exists():
            path.touch()
        # 'r+' (read/write, no truncate) so the same handle can both read
        # the existing contents and overwrite them later via seek(0) +
        # truncate(), rather than closing and reopening the file for
        # every save()/load() call.
        self._file = path.open("r+", encoding="utf-8")
        self._initialized = True

    # -- Load / save ----------------------------------------------------------

    def load(self) -> list[dict[str, str]]:
        """Read every non-blank line of the file and parse it into a
        dict, e.g. "type=Book|title=Dune|..." ->
        {"type": "Book", "title": "Dune", ...}.

        Returns a list of dicts - deliberately *not* a list of LibraryItem
        objects, since this class has no knowledge of that hierarchy.
        Callers (Library) pass each dict to ``LibraryItem.from_dict``.
        """
        self._file.seek(0)
        records = []
        for raw_line in self._file:
            line = raw_line.strip()
            if not line:
                continue
            records.append(self._parse_line(line))
        return records

    def save(self, records: list[dict[str, str]]) -> None:
        """Overwrite the file with one pipe-delimited line per record."""
        self._file.seek(0)
        self._file.truncate()
        for record in records:
            self._file.write(self._serialize_line(record) + "\n")
        self._file.flush()

    # -- Line format ------------------------------------------------------------

    @staticmethod
    def _parse_line(line: str) -> dict[str, str]:
        fields: dict[str, str] = {}
        for chunk in line.split("|"):
            key, separator, value = chunk.partition("=")
            if not separator:
                continue  # skip malformed segments rather than raising
            fields[key.strip()] = value.strip()
        return fields

    @staticmethod
    def _serialize_line(record: dict[str, str]) -> str:
        return "|".join(f"{key}={value}" for key, value in record.items())

    # -- Lifecycle ------------------------------------------------------------

    def close(self) -> None:
        if not self._file.closed:
            self._file.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def __del__(self) -> None:  # pragma: no cover - best-effort cleanup
        try:
            self.close()
        except Exception:
            pass

    def __repr__(self) -> str:
        state = "closed" if self._file.closed else "open"
        return f"Database(filepath={self.filepath!r}, connection={state})"

    # -- Testing helper ---------------------------------------------------------

    @classmethod
    def _reset_singleton_for_tests(cls) -> None:
        """Not part of the public API. Tests need a fresh singleton
        pointed at a fresh temp file for isolation; production code
        should never call this."""
        if cls._instance is not None:
            cls._instance.close()
        cls._instance = None
