import logging
import os

import sync


def _must_get(name: str) -> str:
    """Get a value from env. If it's empty or undefined, exit the application with status ``1``."""
    tpl = "Configuration error: {} is invalid ({})."
    v = os.environ.get(name)
    if not v:
        logging.getLogger("config").error(tpl.format(name, "value is empty"))
        exit(1)
    return v


# beancount settings
bean_path = _must_get("BEAN_PATH")
"""The path to your beancount folder."""
bean_main_file = _must_get("BEAN_MAIN_FILE")
"""The name of the main beancount file expressed as relative path to `bean_path``."""
bean_currency = _must_get("BEAN_CURRENCY")
"""The currency string used for your accounts, e.g. EUR or USD."""
# telegram settings
telegram_api_token = _must_get("TELEGRAM_API_TOKEN")
"""Telegram API token for your bot."""
# Logging information
db_dir = os.environ.get("DB_DIR") or "/var/lib/beanbot"
"""The directory in which persistent data will be stored."""
verbose = os.environ.get("LOG_VERBOSE") in ["True", "true", "1"]
"""Indicates whether verbose logging is activated."""
log_lvl = logging.DEBUG if verbose else logging.INFO
"""Current log level used in all loggers."""
# Synchronation settings
synchronizer = sync.Sync(bean_path)
if os.environ.get("SYNC_METHOD") == "dav":
    # DAV settings
    dpath = _must_get("DAV_PATH")
    droot = _must_get("DAV_ROOT")
    duser = _must_get("DAV_USER")
    dpass = _must_get("DAV_PASS")
    dhost = _must_get("DAV_HOST")
    synchronizer = sync.DavSync(bean_path, dpath, droot, duser, dpass, dhost)

if os.environ.get("SYNC_METHOD") == "git":
    synchronizer = sync.GitSync(
        bean_path,
    )
