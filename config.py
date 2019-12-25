import os

from dataclasses import dataclass
from string import Template
import logging

telegram_api_token = os.environ.get("TELEGRAM_API_TOKEN")
db_dir = os.environ.get("DB_DIR") or "/var/lib/beanbot"
bean_append_file = os.environ.get("BEAN_APPEND_FILE")
bean_file = os.environ.get("BEAN_FILE")
verbose = os.environ.get("LOG_VERBOSE") in ["True", "true", "1"]
log_lvl = logging.DEBUG if verbose else logging.INFO


def check() -> str:
    """Check if the configuration is in a valid state.
    Returns an error string otherwise.
    """
    tpl = "Configuration error: {} is invalid ({})."

    if not bean_append_file:
        return tpl.format("BEAN_APPEND_FILE", "value is empty")
    if not bean_file:
        return tpl.format("BEAN_FILE", "value is empty")
    if not telegram_api_token:
        return tpl.format("TELEGRAM_API_TOKEN", "value is empty")

    return None

