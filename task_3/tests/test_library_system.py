"""Test suite for the library system.

Run from inside task_3/ with either:
    python -m unittest discover -s tests
    pytest tests/

Each test class is labelled with the task-spec requirement number(s) it
covers, so a failure points straight at which requirement broke.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

# Make `import items`, `import database`, etc. work regardless of how/where
# this file is invoked from (unittest discover, pytest, or run directly).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import Database
from enums import ItemStatus
from exceptions import (
    ItemAlreadyLostError,
    ItemNotAvailableError,
    ItemNotCheckedOutError,
    ItemNotFoundError,
    UnknownItemTypeError,
)
from items import Book, DVD, LibraryItem, Magazine
from library import Library


class PolymorphismTests(unittest.TestCase):
    """Requirement 1."""

    def test_each_subclass_has_its_own_loan_period(self):
        self.assertEqual(Book.LOAN_PERIOD_DAYS, 21)
        self.assertEqual(DVD.LOAN_PERIOD_DAYS, 5)
        self.assertEqual(Magazine.LOAN_PERIOD_DAYS, 14)

    def test_checkout_uses_the_subclasss_own_period(self):
        book = Book("Dune", "Frank Herbert", "9780441013593")
        dvd = DVD("Inception", "Christopher Nolan")
        today = date(2026, 1, 1)
        book.checkout(on=today)
        dvd.checkout(on=today)
        self.assertEqual(book.due_date, date(2026, 1, 22))
        self.assertEqual(dvd.due_date, date(2026, 1, 6))

    def test_library_item_cannot_be_instantiated_directly(self):
        with self.assertRaises(TypeError):
            LibraryItem("Untitled")  # type: ignore[abstract]


class EncapsulationTests(unittest.TestCase):
    """Requirement 2."""

    def test_status_has_no_public_setter(self):
        book = Book("Dune", "Frank Herbert", "9780441013593")
        with self.assertRaises(AttributeError):
            book.status = ItemStatus.LOST  # type: ignore[misc]

    def test_checkout_then_return_round_trip(self):
        book = Book("Dune", "Frank Herbert", "9780441013593")
        self.assertIs(book.status, ItemStatus.AVAILABLE)
        book.checkout(borrower="Alice")
        self.assertIs(book.status, ItemStatus.CHECKED_OUT)
        self.assertEqual(book.borrower, "Alice")
        self.assertIsNotNone(book.due_date)
        book.return_item()
        self.assertIs(book.status, ItemStatus.AVAILABLE)
        self.assertIsNone(book.due_date)
        self.assertIsNone(book.borrower)

    def test_cannot_checkout_an_already_checked_out_item(self):
        book = Book("Dune", "Frank Herbert", "9780441013593")
        book.checkout()
        with self.assertRaises(ItemNotAvailableError):
            book.checkout()

    def test_cannot_return_an_item_that_isnt_checked_out(self):
        book = Book("Dune", "Frank Herbert", "9780441013593")
        with self.assertRaises(ItemNotCheckedOutError):
            book.return_item()

    def test_mark_lost_from_available_or_checked_out(self):
        book = Book("Dune", "Frank Herbert", "9780441013593")
        book.mark_lost()
        self.assertIs(book.status, ItemStatus.LOST)

        dvd = DVD("Inception", "Christopher Nolan")
        dvd.checkout()
        dvd.mark_lost()
        self.assertIs(dvd.status, ItemStatus.LOST)

    def test_cannot_mark_lost_twice(self):
        book = Book("Dune", "Frank Herbert", "9780441013593")
        book.mark_lost()
        with self.assertRaises(ItemAlreadyLostError):
            book.mark_lost()


class ItemStatusEnumTests(unittest.TestCase):
    """Requirement 3."""

    def test_members(self):
        self.assertEqual(
            {member.name for member in ItemStatus},
            {"AVAILABLE", "CHECKED_OUT", "LOST"},
        )

    def test_str_is_human_readable(self):
        self.assertEqual(str(ItemStatus.CHECKED_OUT), "Checked Out")


class ComparableAndPrintableTests(unittest.TestCase):
    """Requirement 4."""

    def test_sorted_with_no_key(self):
        items = [
            Book("Zodiac", "Robert Graysmith", validate_isbn=False),
            Book("Dune", "Frank Herbert", "9780441013593"),
            Magazine("apple weekly", "2026-08"),
        ]
        titles = [item.title for item in sorted(items)]
        self.assertEqual(titles, ["apple weekly", "Dune", "Zodiac"])

    def test_str_format_matches_spec_example(self):
        book = Book("Dune", "Frank Herbert", "9780441013593")
        self.assertEqual(str(book), "Dune (Book) — Available")

    def test_repr_is_unambiguous_and_includes_subclass_fields(self):
        book = Book("Dune", "Frank Herbert", "9780441013593")
        text = repr(book)
        self.assertIn("Book(", text)
        self.assertIn("title='Dune'", text)
        self.assertIn("isbn='9780441013593'", text)


class FromDictToDictTests(unittest.TestCase):
    """Requirement 5."""

    def test_from_dict_dispatches_to_the_right_subclass(self):
        book = LibraryItem.from_dict(
            {
                "type": "Book",
                "title": "Dune",
                "author": "Frank Herbert",
                "isbn": "9780441013593",
                "status": "AVAILABLE",
            }
        )
        dvd = LibraryItem.from_dict(
            {"type": "DVD", "title": "Inception", "director": "Christopher Nolan", "status": "CHECKED_OUT"}
        )
        magazine = LibraryItem.from_dict(
            {"type": "Magazine", "title": "National Geographic", "issue": "2026-08", "status": "AVAILABLE"}
        )
        self.assertIsInstance(book, Book)
        self.assertIsInstance(dvd, DVD)
        self.assertIsInstance(magazine, Magazine)
        self.assertIs(dvd.status, ItemStatus.CHECKED_OUT)

    def test_unknown_type_raises(self):
        with self.assertRaises(UnknownItemTypeError):
            LibraryItem.from_dict({"type": "Scroll", "title": "Ancient Text"})

    def test_to_dict_from_dict_round_trip(self):
        original = Book("Dune", "Frank Herbert", "9780441013593")
        rebuilt = LibraryItem.from_dict(original.to_dict())
        self.assertEqual(original.to_dict(), rebuilt.to_dict())


class IsbnValidationTests(unittest.TestCase):
    """Requirement 6."""

    KNOWN_INVALID = "9780441013590"  # Dune's ISBN with the check digit broken

    def test_valid_isbn13(self):
        self.assertTrue(Book.is_valid_isbn("9780441013593"))  # Dune, from the spec's sample data

    def test_valid_isbn13_with_hyphens(self):
        self.assertTrue(Book.is_valid_isbn("978-0-441-01359-3"))

    def test_invalid_checksum(self):
        self.assertFalse(Book.is_valid_isbn(self.KNOWN_INVALID))

    def test_wrong_length(self):
        self.assertFalse(Book.is_valid_isbn("12345"))

    def test_non_digit_characters(self):
        self.assertFalse(Book.is_valid_isbn("978044101359X"))

    def test_non_string_input(self):
        self.assertFalse(Book.is_valid_isbn(9780441013593))  # type: ignore[arg-type]

    def test_static_method_takes_no_self_or_cls(self):
        # Callable straight off the class with just the ISBN argument -
        # proof there's no implicit self/cls binding.
        self.assertTrue(Book.__dict__["is_valid_isbn"].__class__ is staticmethod)

    def test_book_constructor_rejects_invalid_isbn_by_default(self):
        with self.assertRaises(ValueError):
            Book("Dune", "Frank Herbert", self.KNOWN_INVALID)

    def test_book_constructor_can_skip_validation(self):
        book = Book("Mystery Book", "Unknown", self.KNOWN_INVALID, validate_isbn=False)
        self.assertEqual(book.isbn, self.KNOWN_INVALID)


class DatabaseTests(unittest.TestCase):
    """Requirement 7 (persistence half) + bonus (singleton)."""

    def setUp(self):
        Database._reset_singleton_for_tests()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.db_path = str(Path(self._tmpdir.name) / "database.txt")

    def tearDown(self):
        Database._reset_singleton_for_tests()

    def test_is_a_singleton(self):
        first = Database(self.db_path)
        second = Database("ignored-because-already-initialized.txt")
        self.assertIs(first, second)
        self.assertEqual(second.filepath, self.db_path)

    def test_save_then_load_round_trip(self):
        db = Database(self.db_path)
        records = [
            {
                "type": "Book",
                "title": "Dune",
                "author": "Frank Herbert",
                "isbn": "9780441013593",
                "status": "AVAILABLE",
            },
            {"type": "DVD", "title": "Inception", "director": "Christopher Nolan", "status": "CHECKED_OUT"},
        ]
        db.save(records)
        self.assertEqual(db.load(), records)

    def test_load_on_missing_file_creates_it_and_returns_empty(self):
        db = Database(self.db_path)
        self.assertEqual(db.load(), [])

    def test_database_never_imports_items_module(self):
        # SRP check: Database must stay ignorant of the LibraryItem
        # hierarchy - it only deals in dicts and text.
        import database

        self.assertNotIn("items", vars(database))


class LibrarySrpTests(unittest.TestCase):
    """Requirement 7 (collection-management half) + requirement 8 wiring."""

    def setUp(self):
        Database._reset_singleton_for_tests()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.db_path = str(Path(self._tmpdir.name) / "database.txt")

    def tearDown(self):
        Database._reset_singleton_for_tests()

    def test_add_checkout_return_find_list_available(self):
        library = Library()
        library.add_item(Book("Dune", "Frank Herbert", "9780441013593"))
        library.add_item(DVD("Inception", "Christopher Nolan"))

        self.assertEqual(len(library), 2)
        self.assertEqual(len(library.find_by_title("dune")), 1)  # case-insensitive
        self.assertEqual(len(library.list_available()), 2)

        checked_out = library.checkout("Dune", borrower="Alice")
        self.assertIs(checked_out.status, ItemStatus.CHECKED_OUT)
        self.assertEqual(len(library.list_available()), 1)

        library.return_item("Dune")
        self.assertEqual(len(library.list_available()), 2)

    def test_checkout_missing_title_raises(self):
        library = Library()
        with self.assertRaises(ItemNotFoundError):
            library.checkout("Nonexistent")

    def test_save_and_load_round_trip_through_database(self):
        db = Database(self.db_path)
        library = Library(database=db)
        library.add_item(Book("Dune", "Frank Herbert", "9780441013593"))
        library.add_item(Magazine("National Geographic", "2026-08"))
        library.save_to_database()

        reloaded = Library(database=db)
        reloaded.load_from_database()
        self.assertEqual(
            sorted(item.title for item in reloaded),
            ["Dune", "National Geographic"],
        )

    def test_library_has_no_file_io_of_its_own(self):
        # SRP check: Library's source should not call the builtin open()
        # itself - all persistence goes through Database. Parsed with ast
        # (not a substring search) so mentioning "open()" in a docstring
        # explaining this rule doesn't trip a false positive.
        import ast
        import inspect

        import library

        tree = ast.parse(inspect.getsource(library))
        open_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open"
        ]
        self.assertEqual(open_calls, [])


class OpenClosedPrincipleTests(unittest.TestCase):
    """Requirement 8: adding a new item type needs a new subclass only."""

    def test_new_subclass_is_auto_registered_and_works_with_library(self):
        class AudioBook(LibraryItem):
            LOAN_PERIOD_DAYS = 10

            def __init__(self, title, narrator, status=ItemStatus.AVAILABLE):
                super().__init__(title, status)
                self.narrator = narrator

            def to_dict(self):
                data = super().to_dict()
                data.update(narrator=self.narrator)
                return data

            @classmethod
            def _build_from_dict(cls, data):
                return cls(
                    title=data["title"],
                    narrator=data["narrator"],
                    status=ItemStatus(data.get("status", ItemStatus.AVAILABLE.value)),
                )

        self.assertIn("AudioBook", LibraryItem._registry)

        built = LibraryItem.from_dict(
            {"type": "AudioBook", "title": "Dune (audio)", "narrator": "Scott Brick", "status": "AVAILABLE"}
        )
        self.assertIsInstance(built, AudioBook)

        # Library (written long before AudioBook existed) needs no changes.
        library = Library()
        library.add_item(built)
        library.checkout("Dune (audio)")
        self.assertIs(built.status, ItemStatus.CHECKED_OUT)
        self.assertEqual(built.due_date - date.today(), timedelta(days=10))


if __name__ == "__main__":
    unittest.main()
