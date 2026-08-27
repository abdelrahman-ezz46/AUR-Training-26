"""Warehouse stock manager.

Loads stock levels from stock.txt into a dictionary, then lets the user
add stock, remove stock, or view stock levels through a menu-driven
loop. Changes are written back to stock.txt when the user exits.
"""

STOCK_FILE = "stock.txt"


def load_stock(filename=STOCK_FILE):
    """Read `filename` and return its contents as a {name: quantity} dict.

    Handles a missing file and corrupted lines instead of crashing:
    a missing file starts an empty stock, and any line that isn't in
    "name,quantity" format is skipped with a warning.
    """
    stock = {}
    try:
        with open(filename, "r") as file:
            for line_number, raw_line in enumerate(file, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    name, quantity = line.split(",")
                    stock[name.strip().lower()] = int(quantity.strip())
                except ValueError:
                    print(
                        f"Warning: skipping corrupted line {line_number} "
                        f"in {filename}: {raw_line!r}"
                    )
    except FileNotFoundError:
        print(f"'{filename}' was not found. Starting with an empty stock.")
    return stock


def save_stock(stock, filename=STOCK_FILE):
    """Write the current stock dictionary back to `filename`."""
    with open(filename, "w") as file:
        for name, quantity in stock.items():
            file.write(f"{name},{quantity}\n")


def show_stock(stock):
    """Print the stock contents with a 1-based id before each name."""
    print("\nCurrent stock:")
    if not stock:
        print("  (empty)")
    else:
        for item_id, (name, quantity) in enumerate(stock.items(), start=1):
            print(f"{item_id}. {name}: {quantity}")
    print()


def resolve_item_name(stock, prompt, allow_new):
    """Ask for a stock name or id and return the matching lower-case name.

    A numeric entry is resolved against the id numbers shown by
    show_stock(). A text entry is lower-cased so "Banana" and "banana"
    refer to the same item. When allow_new is False, only names already
    present in `stock` are accepted; when True, an unrecognized name is
    returned as-is so the caller can create a new item.
    """
    while True:
        raw_input_value = input(prompt).strip()
        if not raw_input_value:
            print("Input can't be empty. Please try again.")
            continue

        if raw_input_value.isdigit():
            item_id = int(raw_input_value)
            names = list(stock.keys())
            if 1 <= item_id <= len(names):
                return names[item_id - 1]
            print(f"There is no item with id {item_id}. Please try again.")
            continue

        name = raw_input_value.lower()
        if not allow_new and name not in stock:
            print(f"'{name}' isn't in the stock yet. Please try again.")
            continue
        return name


def read_quantity(prompt, maximum=None):
    """Ask for a positive integer quantity, re-prompting until it's valid.

    When `maximum` is given, the value must not exceed it (used when
    removing stock, so the result never goes below zero).
    """
    while True:
        raw_input_value = input(prompt).strip()
        try:
            quantity = int(raw_input_value)
        except ValueError:
            print("Please enter a whole number.")
            continue
        if quantity <= 0:
            print("Please enter a number greater than 0.")
            continue
        if maximum is not None and quantity > maximum:
            print(f"Please enter a number no greater than {maximum}.")
            continue
        return quantity


def add_stock(stock):
    """Add to an existing item, or create a new one, then update `stock`."""
    show_stock(stock)
    name = resolve_item_name(
        stock,
        'Enter the stock name or id to add to (e.g. "banana" or "1"), '
        'or a new name (e.g. "dates") to create a new item: ',
        allow_new=True,
    )
    amount = read_quantity(f"Enter how much '{name}' stock to add: ")
    stock[name] = stock.get(name, 0) + amount
    print(f"'{name}' is now at {stock[name]}.")


def remove_stock(stock):
    """Remove from an existing item, then update `stock`."""
    show_stock(stock)
    if not stock:
        print("Stock is empty, there's nothing to remove.")
        return

    name = resolve_item_name(
        stock,
        'Enter the stock name or id to remove from (e.g. "banana" or "1"): ',
        allow_new=False,
    )
    amount = read_quantity(
        f"Enter how much '{name}' stock to remove: ", maximum=stock[name]
    )
    stock[name] -= amount
    print(f"'{name}' is now at {stock[name]}.")


def print_menu():
    """Print the 4 available menu options."""
    print("enter 1 to add stock")
    print("enter 2 to remove stock")
    print("enter 3 to show stock's contents")
    print("enter 4 to exit the program")


def read_menu_choice():
    """Read and validate the user's menu choice, returning it as an int."""
    while True:
        choice = input("> ").strip()
        if choice in ("1", "2", "3", "4"):
            return int(choice)
        print("Invalid choice. Please enter 1, 2, 3, or 4.")


def main():
    stock = load_stock()

    while True:
        print_menu()
        choice = read_menu_choice()

        if choice == 1:
            add_stock(stock)
        elif choice == 2:
            remove_stock(stock)
        elif choice == 3:
            show_stock(stock)
        elif choice == 4:
            save_stock(stock)
            print("Stock saved. Goodbye!")
            break


if __name__ == "__main__":
    main()
