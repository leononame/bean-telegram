import logging
import config


def get(name: str) -> logging.Logger:
    if not name:
        raise ValueError("name cannot be empty")
    logging.basicConfig()
    l = logging.getLogger(name)
    l.setLevel(config.log_lvl)
    return l
