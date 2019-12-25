import beans
import logging
import config
import bot


def main():
    logging.basicConfig(
        level=config.log_lvl,
        format="%(name)s [%(levelname)s] [%(asctime)s]: %(message)s",
    )
    if err := config.check():
        logging.error(err)
        exit(1)

    bot.connect()

    exit(0)


if __name__ == "__main__":
    main()
