import logging
import re
from typing import Dict
import uuid

import beans
import config
import telegram
from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    ParseMode,
)
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    PicklePersistence,
    Updater,
)

# This regular expression matches an amount in text
_re = re.compile(r"^(\d+)[\.,]?(\d{1,2})?$")
_log = logging.getLogger("bot")


def run():
    p = PicklePersistence(config.db_dir + "/bot.data")
    # Get bot updater and dispatcher
    updater = Updater(config.telegram_api_token, use_context=True, persistence=p)
    dispatcher = updater.dispatcher

    # Register error handler
    dispatcher.add_error_handler(log_err)

    # Answer to regular messages
    tx_handler = MessageHandler(Filters.text, tx)
    dispatcher.add_handler(tx_handler)

    # Handle callbacks (i.e. the button responses)
    # select the expense account
    account_handler = CallbackQueryHandler(select_account, pattern=r"^account=")
    dispatcher.add_handler(account_handler)

    start_handler = CommandHandler("start", start)
    dispatcher.add_handler(start_handler)

    # Start bot
    updater.start_polling()
    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


def log_err(update: Update, context: CallbackContext):
    _log.error(
        "Error of type {} handled: {}.".format(type(context.error), context.error)
    )


def start(update: Update, context: CallbackContext):
    """The command /start registers a new admin with the bot and can only be run once"""
    context.bot.send_message(chat_id=update.effective_chat.id, text="Registering...")


def select_account(update: Update, context: CallbackContext):
    try:
        query: CallbackQuery = update.callback_query
        data = query.data.split("=")
        cb = get_callback(context, data[1])
        tx = get_tx(context, cb["tx"])
        tx.asset_account = "Assets:EUR:Cash"
        tx.expense_account = cb["account"]
        beans.append_tx(str(tx), config.bean_append_file)
        msg = "✅ `{}`: `{}`".format(tx.expense_account, beans.format_amount(tx.amount),)
        # TODO: delete callback and transaction
        update.effective_message.edit_text(text=msg, parse_mode=ParseMode.MARKDOWN)
        save_narration(context, tx.narration, tx.expense_account)
    except Exception as e:
        update.effective_message.edit_text(
            text="An error occurred, I couldn't find your data. Please try again!"
        )
        _log.error(
            "{} in select_account: {}. User: {}. Query: {}. Callback: {}.".format(
                type(e), e, update.effective_user, query.data, cb
            )
        )

    return None


def tx(update: Update, context: CallbackContext):
    """This handler handles incoming messages. It is intended to parse a message for spending."""
    parts = update.message.text.split(" ")
    if len(parts) < 2:
        print_help(update, context)
        return
    # Get amount
    amount = parse_amount(parts[0])
    parts = parts[1:]
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

    t = beans.Transaction(amount=amount)

    # Get all the data.
    data = {"narration": [], "tags": [], "account": ""}
    # Get the expense account if specified (last element has format [ACCOUNT])
    if m := re.match(r"^\[(.+)\]$", parts[-1]):
        data["account"] = m.group(1)
        parts = parts[:-1]
    # Parse tags and narrative
    section = "tags"
    for p in reversed(parts):
        if not p.startswith("#"):
            section = "narration"
        data[section].insert(0, p)
    t.narration = " ".join(data["narration"])
    t.tags = data["tags"]
    t.expense_account = data["account"]
    save_tx(context, t)

    # Select account
    if not t.expense_account:
        # If the same narration has already been used
        if acct := get_narration(context, t.narration):
            t.expense_account = acct
            save_tx(context, t)
            update.message.reply_markdown(
                text="Write to expense account `{}`".format(acct),
                quote=True,
                reply_markup=InlineKeyboardMarkup.from_row(
                    [
                        InlineKeyboardButton("No", callback_data="1"),
                        InlineKeyboardButton("Yes", callback_data="2"),
                    ],
                ),
            )
            return
        # Choose account
        accts = beans.get_expense_accounts()
        btns = []
        for a in accts:
            cb = {"tx": str(t.id), "account": a, "id": uuid.uuid4()}
            save_callback(context, cb)
            callback_data = "account={}".format(str(cb["id"]))
            btns.append(InlineKeyboardButton(a, callback_data=callback_data))
        update.message.reply_markdown(
            text="Please choose an account",
            quote=True,
            reply_markup=InlineKeyboardMarkup.from_column(btns),
        )

    # Everything ok
    elif t.expense_account in beans.get_expense_accounts():
        # TODO: confirm transaction
        pass
    else:
        # TODO: show error message
        pass


def parse_amount(input: str) -> int:
    """Parse an amount string into the amount in cents. Returns 0 on error.
    1.29 to 129
    1,3 to 130
    1 to 100"""
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
    """Return an error message."""
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="""I couldn't understand your message. Please send a valid message:
2.99 Coffee
15 Drinks for party
.5 Metro #trip2019
25,93 Groceries""",
    )


def get_tx(context: CallbackContext, uid: str) -> beans.Transaction:
    d = context.user_data.get("transactions")
    if d == None:
        return None
    t = d.get(uid)
    return t


def get_callback(context: CallbackContext, uid: str) -> Dict:
    d = context.user_data.get("callbacks")
    if d == None:
        return None
    t = d.get(uid)
    return t


def get_narration(context: CallbackContext, narration: str) -> str:
    d = context.user_data.get("narrations")
    if d == None:
        return None
    t = d.get(narration)
    return t


def save_tx(context: CallbackContext, tx: beans.Transaction):
    d = context.user_data.get("transactions")
    if d == None:
        context.user_data["transactions"] = {}
        d = context.user_data["transactions"]
    d[str(tx.id)] = tx


def save_callback(context: CallbackContext, data: Dict) -> uuid.UUID:
    d = context.user_data.get("callbacks")
    if d == None:
        context.user_data["callbacks"] = {}
        d = context.user_data["callbacks"]
    if not data["id"]:
        data["id"] = uuid.uuid4()
    d[str(data["id"])] = data
    return data["id"]


def save_narration(context: CallbackContext, narration: str, account: str):
    d = context.user_data.get("narrations")
    if d == None:
        context.user_data["narrations"] = {}
        d = context.user_data["narrations"]
    d[narration] = account
