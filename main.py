import logging
import sys

from beancount import loader
from beancount.core.data import Open as Account

def get_accounts(fname: str) -> list:
	entries, errors, options_map = loader.load_file(fname,
            log_timings=logging.info,
            log_errors=sys.stderr)
	if errors:
		return None
	expenses = options_map['name_expenses']
	accounts = [e.account.split(expenses+":")[1] for e in entries if type(e) is Account and e.account.startswith(expenses)]
	return accounts
