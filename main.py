import logging
import os
import sys

import beans
from bot import run
import config


def main():
    logging.basicConfig(
        level=config.log_lvl,
        format="%(name)s [%(levelname)s] [%(asctime)s]: %(message)s",
    )
    if err := config.check():
        logging.error(err)
        exit(1)

    try:
        os.mkdir(config.db_dir, 0o755)
    except FileExistsError:
        pass
    except Exception as e:
        logging.error("Couldn't create dir {}. Message: {}".format(config.db_dir, e))
        exit(1)

    run()

    exit(0)


if __name__ == "__main__":
    main()
