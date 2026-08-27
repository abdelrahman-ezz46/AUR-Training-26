# Task 3 — A Small Library Management System

A simplified library system modelling books, DVDs, and magazines: who has
what checked out, when it's due, and how the collection is persisted to
disk. Built for AUR Training '26, Software Phase II, Task 3 (Advanced
Python / OOP).

## Running it

No third-party dependencies — standard library only. From inside this
`task_3/` folder:

```bash
python main.py                        # end-to-end demo of every requirement
python -m unittest discover -s tests   # run the test suite (35 tests)
# or, if you have pytest installed:
pytest tests/
```

## Layout

```
task_3/
├── enums.py       ItemStatus (AVAILABLE / CHECKED_OUT / LOST)
├── exceptions.py  Custom exceptions (ItemNotAvailableError, etc.)
├── items.py       LibraryItem (abstract) + Book, DVD, Magazine
├── database.py    Database — singleton, save/load database.txt
├── library.py     Library — collection + checkout/return workflow
├── database.txt   Sample data (the example from the task spec)
├── main.py        Demo script exercising every requirement
└── tests/
    └── test_library_system.py
```

## Design decisions

**Encapsulation (req. 2).** `status` is exposed as a read-only `@property`
with no setter, so `item.status = ItemStatus.LOST` raises `AttributeError`
at the point of misuse rather than silently working. The only way to
change status is `checkout()` / `return_item()` / `mark_lost()`, which
validate the transition and raise a specific exception
(`ItemNotAvailableError`, `ItemNotCheckedOutError`, `ItemAlreadyLostError`)
when it isn't legal.

**Open/Closed Principle (req. 8).** `LibraryItem` uses the
`__init_subclass__` hook to auto-register every subclass into a
`type name -> class` dict the moment it's *defined*, anywhere. `from_dict`
dispatches through that registry instead of an `if/elif` chain. Practical
effect: adding a new item type (see `AudioBook` in `main.py` and in
`tests/test_library_system.py::OpenClosedPrincipleTests`) is *only*
writing the subclass — `Library` and the dispatch logic in `LibraryItem`
never change.

**Single Responsibility (req. 7).** `Database` only knows how to turn
`database.txt`'s pipe-delimited lines into `list[dict[str, str]]` and
back — it never imports `items.py` and has no idea `Book` exists.
`Library` owns the collection and checkout workflow and performs zero raw
file I/O; it delegates to an injected `Database` via
`load_from_database()` / `save_to_database()`, which convert dicts to/from
`LibraryItem` objects using `from_dict()` / `to_dict()`. That conversion
knowledge lives in `LibraryItem`, not `Database` — so `Database` stays
reusable for any list-of-dicts data, and `Library` stays swappable to a
different storage backend. Both structural claims ("`Database` never
imports `items`", "`Library` never calls `open()`") are asserted directly
in the test suite, not just by convention.

**Bonus: singleton (`Database`).** Implemented with the classic `__new__`
override — every `Database(...)` call in the process returns the same
object. True to "one open connection to the file": the backing file is
opened once in mode `"r+"` and reused via `seek()`/`truncate()` for every
subsequent `save()`/`load()`, rather than being closed and reopened each
time. `close()` / `__enter__` / `__exit__` are provided for graceful
shutdown (`main.py` calls `db.close()` at the end).

**Comparable & printable (req. 4).** `__lt__` compares `title.casefold()`
(Unicode-correct case-insensitive comparison) so `sorted(items)` works
with no `key=`. `__str__` matches the spec's example format exactly:
`"Dune (Book) — Available"`. `__repr__` is built from `to_dict()`, so it
automatically includes each subclass's extra fields (`author`/`isbn` for
`Book`, `director` for `DVD`, `issue` for `Magazine`) without every
subclass needing to write its own `__repr__`.

**Static method / ISBN (req. 6).** `Book.is_valid_isbn` validates
**ISBN-13** (not ISBN-10) — that's the standard in current use, and it's
what the task spec's own sample data uses (Dune's ISBN,
`9780441013593`, is 13 digits and checksum-valid, which the test suite
checks explicitly). The algorithm: strip hyphens/spaces, multiply each of
the 13 digits by alternating weights 1, 3, 1, 3, ..., and check the sum is
divisible by 10. It takes a single `isbn: str` argument — no `self` or
`cls` — and returns `False` for malformed input (wrong length, non-digit
characters, wrong type) rather than raising. `Book.__init__` calls it by
default (`validate_isbn: bool = True`, overridable) so the check is wired
into real usage, not just a standalone utility.

**Alternative constructor (req. 5).** `LibraryItem.from_dict(data)` reads
`data["type"]`, looks the type up in the registry described above, and
delegates to that subclass's `_build_from_dict(data)`, which pulls out
just the fields relevant to that subclass (e.g. `Book` needs
`author`/`isbn`; `DVD` needs `director`; neither needs the other's
fields) and constructs the instance. `Database.load()` returns exactly
`list[dict]` — parsed but not yet turned into objects — so
`LibraryItem.from_dict(d)` can be called on each element, per the task
spec's hint.

## Notes

- `checkout()` optionally takes a `borrower` name and records a `due_date`
  (`checkout date + LOAN_PERIOD_DAYS`), reflecting the "loans" mentioned in
  the task overview, without introducing a full `Member` class the spec
  never actually asks for.
- `Library.list_overdue()` is a small bonus on top of the required API
  (`add_item`, `checkout`, `return_item`, `find_by_title`,
  `list_available`), included because the due-date tracking above makes it
  essentially free.
