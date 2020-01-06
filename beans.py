import re
from dataclasses import dataclass, field
from datetime import date
from logging import getLogger
from os import makedirs
from os.path import dirname, exists, join
from typing import Dict, List, Optional

from beancount import loader
from beancount.core.data import Open as Account
from beancount.core.inventory import Inventory
from beancount.ops import balance, validation
from beancount.query.query import run_query
from beancount.scripts.format import align_beancount

import config


class Error(Exception):
    """This module's base error.

    Attributes:
        message (:obj: str): The error message.
    """

    def __init__(self, message: str):
        self.message = message


class LoadError(Error):
    """Exception raised for errors during loading the beancount file.

    Attributes:
        message (:obj: str): The error message.
    """

    def __init__(self, message: str):
        self.message = message


@dataclass
class Transaction:
    """Represents a single beancount transaction from one account to another.

    Attributes:
        narration (:obj: str): The transaction's narration.
        amount (:obj: int): The transaction's amount in your currency's smallest unit (e.g. Cents for EUR or USD). Must be a non-zero postive integer.
        credit_account (:obj: str): The account that's going to be credited the amount (i.e. -amount).
        debit_account (:obj: str): The account that's going to be debited the amount (i.e. +amount).
        tags (:obj: List[str]): A list of beancount tags that are going to be added to the transaction.
    """

    narration: str = ""
    credit_account: str = ""
    debit_account: str = ""
    amount: int = 0
    tags: List[str] = field(default_factory=lambda: [])

    def print(self) -> str:
        """Print the transaction as a beancount transaction. The tag ``#bot`` will always be added.
        
        Raises:
            ValueError: Some value is invalid and the transaction cannot be completed.
        """
        if not self.narration:
            raise ValueError("Narration cannot be empty")
        if not self.credit_account:
            raise ValueError("Credit account cannot be empty")
        if not self.debit_account:
            raise ValueError("Debit account cannot be empty")
        if not self.amount:
            raise ValueError("Amount cannot be 0")
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")

        self.tags.append("#bot")
        tagstr = " ".join(self.tags)

        # Our debit account is often an Expense account w/o prefix
        accts = get_accounts()
        if not self.debit_account in accts:
            _, errors, options_map = load()
            if errors:
                raise ValueError("Can't get debit account correctly")
            self.debit_account = options_map["name_expenses"] + ":" + self.debit_account
            if not self.debit_account in accts:
                raise ValueError("Debit account is invalid")

        tx = f"""
{date.today():%Y-%m-%d} * "{self.narration}" {tagstr}
    {self.credit_account} -{format_amount(self.amount)}
    {self.debit_account}"""
        return tx


def get_expense_accounts() -> List[str]:
    """Get all expense accounts. The accounts are sorted and will be stripped of the expense prefix.
    
    Returns:
        List[str]: List of expense accounts, stripped of expense prefix.
    
    Raises:
        LoadError: Error occurred while loading beancount files.
        Error: Some other error while loading the accounting data.
    """

    entries, errors, options_map = load()
    if errors:
        getLogger("beans").exception(
            f"Can't parse beancount data: errors present: {errors}"
        )
        ts = [type(e) for e in errors]
        if loader.LoadError in ts:
            es = [e.message for e in errors if type(e) == loader.LoadError]
            raise LoadError("Error while opening beancount file: " + ": ".join(es))
        else:
            raise Error("Error while opening beancount file.")

    # Expense prefix is usually Expenses:, but might be something else throught the options
    prefix = options_map["name_expenses"] + ":"
    # Filter for expense accounts and strip the prefix
    accounts = [
        e.account.split(prefix)[1]
        for e in entries
        if type(e) is Account and e.account.startswith(prefix)
    ]
    return sorted(accounts)


def get_accounts() -> List[str]:
    """Get all accounts that exist. The accounts are sorted.
    
    Returns:
        List[str]: List of accounts.
    
    Raises:
        LoadError: Error occurred while loading beancount files.
        Error: Some other error while loading the accounting data.
    """
    entries, errors, _ = load()
    if errors:
        getLogger("beans").exception(
            f"Can't parse beancount data: errors present: {errors}"
        )
        ts = [type(e) for e in errors]
        if loader.LoadError in ts:
            es = [e.message for e in errors if type(e) == loader.LoadError]
            raise LoadError("Error while opening beancount file: " + ": ".join(es))
        else:
            raise Error("Error while opening beancount file.")

    # Filter for Accounts
    accounts = [e.account for e in entries if type(e) is Account]
    return sorted(accounts)


def append_tx(tx: Transaction, fname: str) -> Dict:
    """Append a new transaction to a beancount file.

    Args:
        tx (:class: Transaction): The transaction to append.
        fname (:obj: str): The relative path (from your beancoutn folder) to the file used.

    Returns:
        A dict with the  balance of both accounts used after the transaction is completed,
        each balance mapped to "credit" and "debit" respectively. For example:

        {'credit': '127.05 EUR','debit': '158.09 EUR'}
    
    Raises:
        ValueError: A function parameter is not valid.
    """
    if not tx:
        raise ValueError("Transaction cannot be empty")
    if not fname:
        raise ValueError("File must be specified")

    data = ""
    old = ""
    fname = join(config.bean_path, fname)
    if not exists(dirname(fname)):
        makedirs(dirname(fname), 0o755)

    try:
        with open(fname, "r") as file:
            old = file.read()
    except FileNotFoundError:
        pass

    data = old + tx.print()
    data = align_beancount(data)
    with open(fname, "w") as file:
        file.write(data)
    entries, errs, options_map = load()
    # on error write old data
    if errs:
        with open(fname, "w") as file:
            file.write(old)
        raise ValueError("Data invalid: " + str(errs))

    # Get balances
    d = {}
    try:
        _, rows = run_query(
            entries, options_map, f"BALANCES WHERE account = '{tx.credit_account}'",
        )
        i: Inventory = rows[0][1]
        _, amount = i.popitem()
        d["credit"] = str(amount)

        _, rows = run_query(
            entries, options_map, f"BALANCES WHERE account = '{tx.debit_account}'",
        )
        i = rows[0][1]
        _, amount = i.popitem()
        d["debit"] = str(amount)
    except Exception:
        d["credit"] = "Could not determine amount"
        d["debit"] = "Could not determine amount"
    return d


def format_amount(input: int) -> str:
    """Format the amount into an amount string. This supposes that the currency
    has two units, e.g. Cents and Euros, and that 100 Cents equal 1 Euro.
    
    Example: ``1195`` is formatted into ``11.95 EUR`` (if your currency string is ``EUR``)
    """
    s = f"{int(input/100)}.{input%100} {config.bean_currency}"
    return s


def load():
    """Load the beancount file and return its entries, errors and options."""
    l = getLogger("beancount")
    entries, errors, options_map = loader.load_file(
        join(config.bean_path, config.bean_main_file),
        log_timings=l.debug,
        log_errors=l.error,
        extra_validations=validation.HARDCORE_VALIDATIONS,
    )
    if errors:
        l.error(f"Check failed: {errors}")
        return None, errors, None
    return entries, errors, options_map


def parse_tx(val: str) -> Transaction:
    """Parse a string into a transaction. The string format to parse looks something like this:
    
        AMOUNT NARRATION TAGS [EXPENSE ACCOUNT]
    
    Tags and Expense Account are optional fields. Valid example formats include:

        1.5 Coffee
        10 Entrance Musem #vacation
        200 Tablet [Expenses:Hardware]
        24.95 Restaurant Paris #vacation #vacation2019 [Expenses:Travels]
    
    Args:
        val (:obj: str): The string to parse.
    
    Returns:
        Transaction: The parsed transaction.

    Raises:
        ValueError: The input string is not parseable.
    """
    # Ignore symbols
    val = val[:-1] if val.endswith("!") else val
    val = val[2:] if val.startswith("❌ ") else val
    words = val.split(" ")
    amount = parse_amount(words[0])  # THrows err
    words = words[1:]
    narration: List[str] = []

    tx = Transaction(amount=amount)

    # Get the expense account if specified (last word is maybe expense account)
    if m := re.match(r"^\[(.+)\]$", words[-1]):
        tx.debit_account = m.group(1)  # type: ignore
        words = words[:-1]

    section = tx.tags
    # Parse tags and narration
    for w in reversed(words):
        if not w.startswith("#"):
            section = narration
        section.insert(0, w)
    tx.narration = " ".join(narration)

    return tx


def parse_amount(val: str) -> int:
    """Parse an input string to an integer amount. Example values include:
    15.96 parses to 1596
    14,5 parses to 1450
    12 parses to 1200
    
    Args:
        val (:obj: str): The string to parse.
        
    Raises:
        ValueError: The value provided is not parseable into an integer.
    """
    if m := re.match(r"^(\d+)[\.,]?(\d{1,2})?$", val):
        amount = int(m.group(1)) * 100  # type: ignore
        if cents := m.group(2):  # type: ignore
            if len(cents) == 1:
                cents += "0"
            amount += int(cents)
        getLogger("beans").debug("Amount '{}' parsed to value {}".format(val, amount))
        return amount
    getLogger("beans").warn("Amount '{}' not parseable".format(val))
    raise ValueError(f"Amount {val} is not parseable into money.")
