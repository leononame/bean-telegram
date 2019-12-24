import os

from dataclasses import dataclass
from string import Template
import logging


bean_append_file = os.environ.get("BEAN_APPEND_FILE")
bean_file = os.environ.get("BEAN_FILE")
verbose = os.environ.get("LOG_VERBOSE") in ["True", "true", "1"]
log_lvl = logging.DEBUG if verbose else logging.INFO


def check() -> str:
    """Check if the configuration is in a valid state.
    Returns an error string otherwise.
    """
    tpl = "Configuration error: {} is invalid. (value:{})"

    if not bean_append_file:
        return tpl.format("BEAN_APPEND_FILE", bean_append_file)
    if not bean_file:
        return tpl.format("BEAN_FILE", bean_file)

    return None

