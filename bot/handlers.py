from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    ParseMode,
)
from telegram.ext import CallbackContext
import logging
import re
import config
import beans
from typing import List
from .storage import (
    ConversationState,
    get_state,
    save_state,
    pop_state,
    save_narration_account,
    get_narration_account,
)

_log = logging.getLogger("bot")


def _parse_message(msg: str) -> beans.Transaction:
    words = msg.split(" ")
    amount = _parse_amount(words[0])
    words = words[1:]
    tx = beans.Transaction(amount=amount)
    narration = []

    # Get the expense account if specified (last word has format [ACCOUNT])
    if m := re.match(r"^\[(.+)\]$", words[-1]):
        tx.expense_account = m.group(1)
        words = words[:-1]

    section = tx.tags
    # Parse tags and narration
    for w in reversed(words):
        if not w.startswith("#"):
            section = narration
        section.insert(0, w)
    tx.narration = " ".join(narration)
    return tx


def _parse_amount(val: str) -> int:
    """Parse an amount string into the amount in cents."""
    if m := re.match(r"^(\d+)[\.,]?(\d{1,2})?$", val):
        amount = int(m.group(1)) * 100
        if cents := m.group(2):
            if len(cents) == 1:
                cents += "0"
            amount += int(cents)
        _log.debug("Amount '{}' parsed to value {}".format(val, amount))
        return amount
    _log.warn("Amount '{}' not parseable".format(val))
    raise ValueError(f"Amount {val} is not parseable into money.")


def _err_handler(update: Update, context: CallbackContext):
    """Standard error handler."""
    _log.error("_log_err: {}: {}.".format(type(context.error), context.error))


def _create_tx(update: Update, context: CallbackContext):
    """This handler handles incoming messages. It is intended to parse a message for spending."""
    try:
        tx = _parse_message(update.message.text)
    except Exception as e:
        _log.debug(
            f"{type(e)} in message parsing: {e}. Original message: `{update.message.text}`"
        )
        update.effective_message.reply_text(text="I don't understand this.", quote=True)
        update.effective_message.reply_text(text="❌ " + update.effective_message.text)
        return

    state = ConversationState(
        update.effective_message.message_id,
        accounts=_get_options(""),
        current_path="",
        tx=tx,
    )
    if not state.tx.expense_account:
        if acct := get_narration_account(context, state.tx.narration):
            state.tx.expense_account = acct
            save_state(context, state)
            update.message.reply_markdown(
                text=f"Use account `{acct}`",
                quote=True,
                reply_markup=InlineKeyboardMarkup.from_row(
                    [
                        InlineKeyboardButton(
                            "No", callback_data=f"accounts:{state.id}:back"
                        ),
                        InlineKeyboardButton(
                            "Yes", callback_data=f"confirm:{state.id}"
                        ),
                    ]
                ),
            )
            return

        save_state(context, state)
        update.message.reply_markdown(
            text="Please choose an account", quote=True, reply_markup=(_get_btns(state))
        )
    elif state.tx.expense_account in beans.get_expense_accounts():
        # TODO: create directly
        pass
    else:
        update.effective_message.reply_text(
            quote=True, text="The account you specified doesn't exist."
        )
        update.effective_message.reply_text(text="❌ " + update.message.text)


def _commit_tx(update: Update, context: CallbackContext):
    try:
        state = pop_state(
            context, str(update.effective_message.reply_to_message.message_id)
        )
        msg = "✅ `{}`: `{}`".format(
            state.tx.expense_account, beans.format_amount(state.tx.amount),
        )
        update.effective_message.edit_text(text=msg, parse_mode=ParseMode.MARKDOWN)
        save_narration_account(context, state.tx.narration, state.tx.expense_account)
        state.tx.asset_account = "Assets:EUR:Cash"  # TODO
        beans.append_tx(str(state.tx), config.bean_append_file)
    except Exception as e:
        update.effective_message.edit_text(
            quote=True, text="An error occurred, please try again later!"
        )
        update.effective_message.reply_text(
            text="❌ " + update.effective_message.reply_to_message.text
        )
        _log.error(
            f"{type(e)} in _commit_tx: {e}. User: {update.effective_user}. State: {state}."
        )


def _select_account(update: Update, context: CallbackContext):
    try:
        query: CallbackQuery = update.callback_query
        data = query.data.split(":")
        state = get_state(context, data[1])
        if data[2] == "back":
            # Remove last element from path and rebuild data
            state.current_path = ":".join(state.current_path.split(":")[:-1])
        else:
            if state.current_path:
                state.current_path += ":"
            state.current_path += state.accounts[int(data[2])]
            if state.current_path in beans.get_expense_accounts():
                state.tx.expense_account = state.current_path
                save_state(context, state)
                _commit_tx(update, context)
                return
        state.accounts = _get_options(state.current_path)
        markup = _get_btns(state)
        update.effective_message.edit_reply_markup(reply_markup=markup)
    except Exception as e:
        update.effective_message.edit_text(
            quote=True, text="An error occurred, please try again later!"
        )
        update.effective_message.reply_text(
            text="❌ " + update.effective_message.reply_to_message.text
        )
        _log.error(
            f"{type(e)} in _select_account: {e}. User: {update.effective_user}. Query: {query.data}. State: {state}."
        )


def _get_btns(state: ConversationState) -> InlineKeyboardMarkup:
    btns = []

    # Add back button if necessary
    if state.current_path:
        callback_path = f"accounts:{state.id}:back"
        btns.append(InlineKeyboardButton("⬅️ Back", callback_data=callback_path))

    # Build up other buttons
    for i in range(len(state.accounts)):
        # Our callback path is:
        # - account redirects to _select_account
        # - the id of our state
        # - the index of our state
        callback_path = f"accounts:{state.id}:{i}"
        btns.append(
            InlineKeyboardButton(state.accounts[i], callback_data=callback_path)
        )
    return InlineKeyboardMarkup.from_column(btns)


def _get_options(path: str) -> List[str]:
    """Returns all possible expense accounts for the current path"""
    values = beans.get_expense_accounts()
    # In case of None, make empty string
    if not path:
        path = ""

    # Filter only accounts that start with our current path
    values = [v for v in values if v.startswith(path)]
    # Strip prefix if exists
    if path:
        values = [v.split(path + ":")[1] for v in values]
    # Remove suffix
    values = [v.split(":")[0] for v in values]

    return sorted(list(set(values)))