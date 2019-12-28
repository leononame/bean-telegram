import logging
import os

bean_path = os.environ.get("BEAN_PATH")
bean_main_file = os.environ.get("BEAN_MAIN_FILE")
bean_currency = os.environ.get("BEAN_CURRENCY")

telegram_api_token = os.environ.get("TELEGRAM_API_TOKEN")

db_dir = os.environ.get("DB_DIR") or "/var/lib/beanbot"
verbose = os.environ.get("LOG_VERBOSE") in ["True", "true", "1"]
log_lvl = logging.DEBUG if verbose else logging.INFO


def check() -> str:
    """Check if the configuration is in a valid state.
    Returns an error string otherwise.
    """
    tpl = "Configuration error: {} is invalid ({})."

    if not bean_currency:
        return tpl.format("BEAN_CURRENCY", "value is empty")
    if not bean_main_file:
        return tpl.format("BEAN_MAIN_FILE", "value is empty")
    if not bean_path:
        return tpl.format("BEAN_PATH", "value is empty")
    if not telegram_api_token:
        return tpl.format("TELEGRAM_API_TOKEN", "value is empty")

    return None
