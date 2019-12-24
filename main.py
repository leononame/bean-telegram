import logging
import sys

from config import Config
from beancount import loader
from beancount.core.data import Open as Account


def get_accounts(fname: str) -> list:
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


def main():
    c = Config.load()
    if err := c.check():
        print(err)
        exit(1)
    print(get_accounts(c.bean_file))
    exit(0)


if __name__ == "__main__":
    main()

