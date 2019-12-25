import telegram
import config
import re
import logging
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    PicklePersistence,
)
from telegram import Update


_re = re.compile(r"^(\d+)[\.,]?(\d{1,2})?$")
_log = logging.getLogger("bot")


def connect():
    p = PicklePersistence(config.db_dir + "/bot.data")

    updater = Updater(config.telegram_api_token, use_context=True, persistence=p)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler("start", start)
    dispatcher.add_handler(start_handler)

    tx_handler = MessageHandler(Filters.text, tx)
    dispatcher.add_handler(tx_handler)
    updater.start_polling()


def start(update: Update, context: CallbackContext):
    """The command /start registers a new admin with the bot and can only be run once"""
    context.bot.send_message(chat_id=update.effective_chat.id, text="Registering...")


def tx(update: Update, context: CallbackContext):
    """This handler handles incoming messages. It is intended to parse a message for spendin.
    and process it. The format is `Amount Description #tags [Expense Account]. Valid examples are:
    1.23 Some description
    10 Another description
    14.99 Entrance Museum #madrid2019 #vacation
    2.99 Supermarket [Groceries]"""
    parts = update.message.text.split(" ")
    if len(parts) < 2:
        print_help(update, context)
        return
    amount = parse_amount(parts[0])
    if amount == 0:
        _log.debug(
            "Chat with {}. Message incorrect [{}]".format(
                update.effective_user.id, update.message.text
            )
        )
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Couldn't parse amount."
        )
        return
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Amount: {}".format(amount)
    )


def parse_amount(input: str) -> int:
    if m := _re.match(input):
        amount = int(m.group(1)) * 100
        if cents := m.group(2):
            if len(cents) == 1:
                cents += "0"
            amount += int(cents)
        _log.debug("Amount '{}' parsed to value {}".format(input, amount))
        return amount
    _log.warn("Amount '{}' not parseable".format(input))
    return 0


def print_help(update: Update, context: CallbackContext):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="""I couldn't understand your message. Please send a valid message:
2.99 Coffee
15 Drinks for party
.5 Metro #trip2019
25,93 Groceries""",
    )
