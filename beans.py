import logging
import sys
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import List

from beancount import loader
from beancount.core.data import Open as Account
from beancount.scripts.format import align_beancount

import config


@dataclass
class Transaction:
    narration: str = ""
    expense_account: str = ""
    asset_account: str = ""
    amount: int = 0
    tags: List[str] = field(default_factory=lambda: [])
    id: uuid.UUID = field(default_factory=uuid.uuid4)  # To identify the tx internally

    def __str__(self):
        if not self.narration:
            raise ValueError("Narration cannot be empty")
        if not self.expense_account:
            raise ValueError("Expense account cannot be empty")
        if not self.asset_account:
            raise ValueError("Asset account cannot be empty")
        if not self.amount:
            raise ValueError("Amount cannot be 0.")
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")

        self.tags.append("#bot")
        tagstr = " ".join(self.tags)

        # Create amount string
        m = "-{0}.{1} {2:s}".format(int(self.amount / 100), self.amount % 100, "EUR")

        _, errors, options_map = loader.load_file(config.bean_file)
        if errors:
            logging.getLogger("beans").error("Can't print tx: {}".format(errors))
            return ""
        if not self.expense_account.startswith(options_map["name_expenses"]):
            self.expense_account = (
                options_map["name_expenses"] + ":" + self.expense_account
            )

        tx = f"""
{date.today():%Y-%m-%d} * "{self.narration}" {tagstr}
    {self.asset_account} {m}
    {self.expense_account}"""
        return tx


def get_expense_accounts() -> list:
    """Get the expense accounts of a beancount file. 
    The accounts are sorted and will be stripped of the expense prefix.
    """

    l = logging.getLogger("beancount")
    entries, errors, options_map = loader.load_file(
        config.bean_file, log_timings=l.debug, log_errors=l.error
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
