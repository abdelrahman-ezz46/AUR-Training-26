"""Demo script: exercises every requirement end-to-end.

Run with:  python main.py    (from inside this task_3/ folder)
"""

from __future__ import annotations

from datetime import date

from database import Database
from enums import ItemStatus
from exceptions import ItemNotAvailableError
from items import Book, DVD, LibraryItem, Magazine
from library import Library


def section(title: str) -> None:
    print(f"\n{'-' * 60}\n{title}\n{'-' * 60}")


def main() -> None:
    # 1) Load the collection. Database does the file I/O and hands back
    #    plain dicts; Library turns each dict into the right LibraryItem
    #    subclass via from_dict's registry dispatch.
    section("Loading database.txt")
    db = Database("database.txt")
    library = Library(database=db)
    library.load_from_database()
    for item in library.list_all():
        print(" ", item)  # uses __str__, e.g. "Dune (Book) — Available"

    # 4) Comparable & printable: sorted() with no key=, plus repr().
    section("sorted(items) with no key= (requirement 4)")
    for item in sorted(library):
        print(" ", item)
    print("repr() of the first item:", repr(library.list_all()[0]))

    # 2 & 3) Encapsulation + enum-driven status transitions.
    section("Encapsulation (requirement 2) + ItemStatus enum (requirement 3)")
    dune = library.find_by_title("Dune")[0]
    print("Before:", dune)
    try:
        dune.status = ItemStatus.LOST  # type: ignore[misc]
        print("!! this should never print - status has no setter")
    except AttributeError as exc:
        print("As expected, direct assignment is blocked:", exc)

    library.checkout("Dune", borrower="Alice")
    print("After checkout:", dune, "| due:", dune.due_date)

    try:
        library.checkout("Dune", borrower="Bob")
    except ItemNotAvailableError as exc:
        print("Checking out an already-checked-out item correctly raises:", exc)

    library.return_item("Dune")
    print("After return:", dune)

    inception = library.find_by_title("Inception")[0]
    inception.mark_lost()
    print("After marking lost:", inception)

    # 1) Polymorphism: each subclass carries its own loan period.
    section("Polymorphic loan periods (requirement 1)")
    for cls in (Book, DVD, Magazine):
        print(f"  {cls.__name__}.LOAN_PERIOD_DAYS = {cls.LOAN_PERIOD_DAYS}")

    # 6) Static method: ISBN-13 checksum validation.
    section("Book.is_valid_isbn (requirement 6, static method)")
    good_isbn = "9780441013593"  # Dune
    bad_isbn = "9780441013590"
    print(f"  is_valid_isbn({good_isbn!r}) -> {Book.is_valid_isbn(good_isbn)}")
    print(f"  is_valid_isbn({bad_isbn!r}) -> {Book.is_valid_isbn(bad_isbn)}")
    print(f"  is_valid_isbn('not-an-isbn') -> {Book.is_valid_isbn('not-an-isbn')}")

    # 5) Alternative constructor: from_dict directly, without going
    #    through the database file at all.
    section("LibraryItem.from_dict (requirement 5)")
    new_book = LibraryItem.from_dict(
        {
            "type": "Book",
            "title": "Foundation",
            "author": "Isaac Asimov",
            "isbn": "9780553293357",
            "status": "AVAILABLE",
        }
    )
    print(" ", repr(new_book))
    library.add_item(new_book)

    # 8) Open/Closed Principle: define a brand new item type right here,
    #    in application code, and prove Library/from_dict need no edits.
    section("Open/Closed Principle: adding AudioBook (requirement 8)")

    class AudioBook(LibraryItem):
        LOAN_PERIOD_DAYS = 10

        def __init__(self, title: str, narrator: str, status: ItemStatus = ItemStatus.AVAILABLE) -> None:
            super().__init__(title, status)
            self.narrator = narrator

        def to_dict(self) -> dict[str, str]:
            data = super().to_dict()
            data.update(narrator=self.narrator)
            return data

        @classmethod
        def _build_from_dict(cls, data: dict[str, str]) -> "AudioBook":
            return cls(
                title=data["title"],
                narrator=data["narrator"],
                status=ItemStatus(data.get("status", ItemStatus.AVAILABLE.value)),
            )

    # No edits anywhere above were needed for this to work:
    audiobook = LibraryItem.from_dict(
        {"type": "AudioBook", "title": "Dune (audio)", "narrator": "Scott Brick", "status": "AVAILABLE"}
    )
    library.add_item(audiobook)
    print("  Registered types now:", sorted(LibraryItem._registry))
    print("  New item works polymorphically:", audiobook, "| loan period:", audiobook.LOAN_PERIOD_DAYS)

    # 7) Single Responsibility: save back out through Database, Library
    #    never touching the file itself.
    section("Saving back through Database (requirement 7)")
    library.save_to_database()
    print("  database.txt now contains:")
    with open("database.txt", encoding="utf-8") as handle:
        for line in handle:
            print("   ", line.rstrip())

    section("Overdue check (bonus behaviour, not required)")
    print("  Overdue as of 2999-01-01:", [str(i) for i in library.list_overdue(date(2999, 1, 1))])

    db.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
