import logging
import sys
from datetime import date

from config import Config
from beancount import loader
from beancount.core.data import Open as Account
from beancount.scripts.format import align_beancount


def get_expense_accounts(fname: str) -> list:
    """Get the expense accounts of a beancount file. 
    The accounts are sorted and will be stripped of the expense prefix.
    """
    entries, errors, options_map = loader.load_file(
        fname, log_timings=logging.info, log_errors=sys.stderr
    )
    if errors:
        return None
    # Expense prefix is usually Expenses:, but might be something else throught the options
    prefix = options_map["name_expenses"] + ":"
    # Filter for expense accounts and strip the prefix
    accounts = [
        e.account.split(prefix)[1]
        for e in entries
        if type(e) is Account and e.account.startswith(prefix)
    ]
    return sorted(accounts)


def create_tx(
    narr: str, exp_acct: str, asset_acct: str, amount: int, currency: str, tag: str = ""
) -> str:
    """Create a new transaction string for beancount. The transaction will
    have the flag '*'.
    
    Args:
        narr: Narration of the transaction.
        exp_acct: Expense account to which the transaction will be written.
        asset_acct: ASset account from which the transaction will be taken.
        amount: Amount as cents (or whatever the smallest unit is called in your currency).
        currency: Name of the currency in beancount.
        tag: An optional taglist, comma separated. The tag 'bot' will always be added.
    """
    if not narr:
        raise ValueError("Narration cannot be empty")
    if not exp_acct:
        raise ValueError("Expense account cannot be empty")
    if not asset_acct:
        raise ValueError("Asset account cannot be empty")
    if not amount:
        raise ValueError("Amount cannot be 0.")
    if amount < 0:
        raise ValueError("Amount cannot be negative")
    if not currency:
        raise ValueError("Currency cannot be empty.")

    # Create list of tags
    tags = ["bot"]
    if tag:
        tags.extend(tag.split(","))
    tagstr = " ".join([f"#{t}" for t in tags])

    # Create amount string
    m = "-{0}.{1} {2:s}".format(int(amount / 100), amount % 100, currency)

    tx = f"""
{date.today():%Y-%m-%d} * "{narr}" {tagstr}
    {asset_acct} {m}
    {exp_acct}"""

    return tx


def append_tx(tx: str, fname: str) -> None:
    """Append the transaction string to the specified file."""
    if not tx:
        raise ValueError("Transaction cannot be empty")
    if not fname:
        raise ValueError("File must be specified")
    data = ""
    with open(fname) as file:
        data = file.read() + tx
        data = align_beancount(data)
    with open(fname, "w") as file:
        file.write(data)


def main():
    c = Config.load()
    if err := c.check():
        print(err)
        exit(1)

    tx = create_tx("narration", "Expenses:Viaje", "Assets:EUR:Leo:Cash", 2498, "EUR")
    append_tx(tx, c.bean_append_file)
    exit(0)


if __name__ == "__main__":
    main()

