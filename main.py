import beans
import logging
import config
import bot


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] [%(asctime)s] %(name)s: %(message)s",
    )
    if err := config.check():
        logging.error(err)
        exit(1)

    logging.basicConfig(level=config.log_lvl)

    bot.connect()

    exit(0)


if __name__ == "__main__":
    main()
