import logging
import sys
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import List
from os import path
import os

from beancount import loader
from beancount.core.data import Open as Account
from beancount.scripts.format import align_beancount
from beancount.ops import validation

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
        m = format_amount(self.amount)

        _, errors, options_map = loader.load_file(
            path.join(config.bean_path, config.bean_main_file)
        )
        if errors:
            logging.getLogger("beans").error("Can't print tx: {}".format(errors))
            return ""
        exp = self.expense_account
        if not exp.startswith(options_map["name_expenses"]):
            exp = options_map["name_expenses"] + ":" + exp

        tx = f"""
{date.today():%Y-%m-%d} * "{self.narration}" {tagstr}
    {self.asset_account} {m}
    {exp}"""
        return tx


def get_expense_accounts() -> list:
    """Get the expense accounts of a beancount file. 
    The accounts are sorted and will be stripped of the expense prefix.
    """

    l = logging.getLogger("beancount")
    entries, errors, options_map = loader.load_file(
        path.join(config.bean_path, config.bean_main_file),
        log_timings=l.debug,
        log_errors=l.error,
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
    old = ""

    fname = path.join(config.bean_path, fname)

    if not path.exists(path.dirname(fname)):
        os.makedirs(os.path.dirname(fname), 0o755)

    with open(fname, "w+") as file:
        old = file.read()
        data = old + tx
        data = align_beancount(data)
        file.write(data)
    # on error write old data
    if errs := check():
        with open(fname, "w") as file:
            file.write(data)
            raise ValueError("Data invalid: " + str(errs))


def format_amount(input: int) -> str:
    m = "-{0}.{1} {2:s}".format(int(input / 100), input % 100, config.bean_currency)
    return m


def check():
    l = logging.getLogger("beancount")
    _, errors, _ = loader.load_file(
        path.join(config.bean_path, config.bean_main_file),
        log_errors=l.error,
        extra_validations=validation.HARDCORE_VALIDATIONS,
    )
    if errors:
        logging.getLogger("beans").error(f"Check failed: {errors}")
        return errors
    return None

