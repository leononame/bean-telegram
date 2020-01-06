from datetime import date
from logging import getLogger
from typing import List

from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    Update,
)
from telegram.ext import CallbackContext, DispatcherHandlerStop

import beans
import config

from .storage import (
    ConversationState,
    delete_state,
    get_narration_account,
    get_shelve,
    get_state,
    save_narration_account,
    save_state,
)

_log = getLogger("bot")


def _handle_error(update: Update, context: CallbackContext):
    """This handler gets called on any unhandled exception and just logs it."""
    _log.exception(f"error caught in error handler: {context.error}: {context.error}.")


def _handle_start(update: Update, context: CallbackContext):
    with get_shelve() as data:  # If user is not in our users class, stop the handler
        u = str(update.effective_user.id)
        if len(data) == 0:
            data[u] = {
                "admin": True,
                "name": update.effective_user["first_name"],
            }
            update.effective_message.reply_text(
                "You have been added as bot admin. You can add new users and set their configuration. Please use /help for more information about the commands."
            )

    _handle_auth(update, context)
    _handle_help(update, context)
    pass


def _handle_auth(update: Update, context: CallbackContext):
    """Check if user is whitelisted to use this bot.
    
    Raises:
        DispatcherHandlerStop: The user is not authorized to use the bot, end the handler chain.
    """
    with get_shelve() as data:
        u = str(update.effective_user.id)
        if not data.get(u):
            update.effective_message.reply_text(
                "You are not authorized to use this bot."
            )
            raise DispatcherHandlerStop()
        # Save user data for later use in our context
        if context.user_data.get("opts") != data[u]:
            context.user_data["opts"] = dict(data[u]).copy()


def _handle_help(update: Update, context: CallbackContext):
    """Send a general help message to the user."""
    # Check if the user is an admin, send an extra help message if so
    if context.user_data["opts"]["admin"]:
        # pylint: disable=anomalous-backslash-in-string
        update.effective_message.reply_markdown(
            text="""You are the admin. If you want to add users, use the following command:
    `/add :ID :NAME`
where `:ID` is the user ID and `:NAME` a simple name. You can find out the user ID by forwarding a user's message to @userinfobot.

Each user needs two settings: a file and a target account. The file will be the beancount file in which the transaction will be logged. The target account is the user's asset account which will be used.
    `/file :ID :FILE`
    `/account` :ID :ACCOUNT :WITHDRAWAL\_ACCOUNT
`:FILE` is a relative path from the beancount base folder. E.g., the path `cash/john.bean` would use a file named `john.bean` in the subfolder `cash`. The path supports the directives `%Y` for the current year and `%M` for the current month. If you want to set your own file, just use the command with your own ID. You HAVE to list a file for each user.
`:ACCOUNT` is the asset account from which data will be retrieved, e.g. something like Assets:Cash.
`:WITHDRAWAL_ACCOUNT` is the asset account from which money withdrawals will be taken, like Assets:Current
`:ID` is the id of the user.

You can inspect all users with /users.
            """
        )
    update.effective_message.reply_markdown(
        text="""Use me to create a transaction. The most basic format is:
    `1.5 Coffee`

However, you can specify tags which will be added to the transaction:
    `1.5 Coffee with my friends #madrid #vacation2019`

I will prompt you for the expense account to be used, but I'll also remember expense accounts, so if you write 
    `3 Coffee`
    `2.5 Cofee`
on the second transaction, I will ask you if you want to use the same account as last time you typed "Coffee". To skip the question and use the account directly, use:
    `2.5 Coffee!`

If you know the expense account, you can tell me directly:
    `2.5 Supermarket [Shopping:Groceries]`

To withdraw money, type:
    `/withdraw 200`

Type /help anytime if you want to read this message again.
"""
    )


def _handle_add_user(update: Update, context: CallbackContext):
    """Let the admin add a new user."""
    if len(context.args) != 2:
        update.effective_message.reply_text("Usage: /add id name")
        return

    id = str(context.args[0])
    name = str(context.args[1])
    with get_shelve() as data:
        u = data[str(update.effective_user.id)]
        if not u or not u["admin"]:
            update.effective_message.reply_text(
                "You are not authorized to add new users."
            )

        if data.get(id):
            update.effective_message.reply_text("User with id already exists")
            return
        data[id] = {"name": name, "admin": False}
        update.effective_message.reply_text(
            f"User with ID {id} has been added as {name}!"
        )


def _handle_set_user_accounts(update: Update, context: CallbackContext):
    """Let the admin set the accounts for the user."""
    if len(context.args) != 3:
        update.effective_message.reply_text(
            "Usage: /account id account withdrawal_account"
        )
    id = str(context.args[0])
    acct = str(context.args[1])
    wacct = str(context.args[2])

    with get_shelve() as data:
        u = data[str(update.effective_user.id)]
        if not u or not u["admin"]:
            update.effective_message.reply_text(
                "You are not authorized to set userdata."
            )

        if not data.get(id):
            update.effective_message.reply_text(f"User with id {id} does not exist.")
            return
        data[id]["account"] = acct
        data[id]["withdrawal_account"] = wacct
        update.effective_message.reply_text(
            f"Account for user {id} set to {acct} and withdrawal account set to {wacct}."
        )


def _handle_set_user_file(update: Update, context: CallbackContext):
    """Let the admin set the user's file."""
    if len(context.args) != 2:
        update.effective_message.reply_text("Usage: /file id file")
    id = str(context.args[0])
    file = str(context.args[1])

    with get_shelve() as data:
        u = data[str(update.effective_user.id)]
        if not u or not u["admin"]:
            update.effective_message.reply_text(
                "You are not authorized to set userdata."
            )

        if not data.get(id):
            update.effective_message.reply_text(f"User with id {id} does not exist.")
            return
        data[id]["file"] = file
        update.effective_message.reply_text(f"Set file for user {id} to {file}.")


def _handle_get_users(update: Update, context: CallbackContext):
    """Let the admin get a list of users."""
    with get_shelve() as data:
        u = data[str(update.effective_user.id)]
        if not u or not u["admin"]:
            update.effective_message.reply_text("You are not authorized to see users.")
        for id, user in data.items():
            name = user.get("name")
            file = user.get("file")
            acct = user.get("account")
            wacct = user.get("withdrawal_account")
            msg = f"""*{name}*
`{id}`
`    file: ``{file}`
` account: ``{acct}`
`withdraw: ``{wacct}`
`   admin: ``{user["admin"]}`
"""
            update.effective_message.reply_markdown(msg)


def _handle_check_config(update: Update, context: CallbackContext):
    """Check if user's config is valid.
    
    Raises:
        DispatcherHandlerStop: The user's configuration is invalid, don't run any more handlers.
    """
    if not context.user_data["opts"].get("file"):
        update.effective_message.reply_text(
            "No file is specified. Please ask the admin to specify a file for you."
        )
        raise DispatcherHandlerStop()
    else:
        f: str = context.user_data["opts"]["file"]
        f = f.replace("%Y", f"{date.today():%Y}").replace("%M", f"{date.today():%m}")
        context.user_data["opts"]["file"] = f
    if not context.user_data["opts"].get("account"):
        update.effective_message.reply_text(
            "No account is specified. Please ask the admin to specify an account for you."
        )
        raise DispatcherHandlerStop()
    if not context.user_data["opts"].get("withdrawal_account"):
        update.effective_message.reply_text(
            "No withdrawal account is specified. Please ask the admin to specify an account for you."
        )
        raise DispatcherHandlerStop()


def _handle_withdraw(update: Update, context: CallbackContext):
    """Handle the command /withdraw amount. Withdraws amount from the user's
    ``withdrawal_account`` to the user's ``account``."""
    if len(context.args) != 1:
        update.effective_message.reply_text("Usage: /withdraw amount")
        return
    amount = beans.parse_amount(str(context.args[0]))
    if amount <= 0:
        update.effective_message.reply_text(
            "Amount invalid, must be positive.", quote=True
        )
        return
    tx = beans.Transaction(
        narration="Withdrawal",
        credit_account=context.user_data["opts"]["withdrawal_account"],
        debit_account=context.user_data["opts"]["account"],
        amount=amount,
    )
    try:
        balances = _commit_tx(context, tx)
        update.effective_message.reply_markdown(
            quote=True,
            text=_format_success(
                beans.format_amount(tx.amount),
                "Withdrawal",
                balances["debit"],
                balances["credit"],
            ),
        )
    except Exception:
        # TODO check various exception types and message, send better user message
        _log.exception(
            f"Can't withdraw money. Original message: '{update.effective_message.text}''"
        )
        update.effective_message.reply_markdown(
            text=f"❌ Error on withdrawing money", quote=True
        )


def _handle_message(update: Update, context: CallbackContext):
    """Handle an incoming text message, no command. This will try to parse a transaction
    and complete it.
    """
    try:
        tx = beans.parse_tx(update.message.text)
    except ValueError as e:
        _log.debug(
            f"ValueError in message parsing: {str(e)}. Original message: '{update.message.text}'.",
            exc_info=True,
        )
        update.effective_message.reply_text(text="I don't understand this.", quote=True)
        update.effective_message.reply_markdown(
            text=f"❌ `{update.effective_message.text}`"
        )
        return

    try:
        # If the user did specify an account
        if tx.debit_account:
            # If the account exists, just commit the transaction directly
            if tx.debit_account in beans.get_expense_accounts():
                save_narration_account(context, tx.narration, tx.debit_account)
                balances = _commit_tx(context, tx)
                update.effective_message.reply_markdown(
                    text=_format_success(
                        beans.format_amount(tx.amount),
                        tx.debit_account,
                        balances["credit"],
                    ),
                    quote=True,
                )
                return
            # Otherwise, return an error
            update.effective_message.reply_text(
                quote=True, text="The account you specified doesn't exist."
            )
            update.effective_message.reply_markdown(text=f"❌ `{update.message.text}`")
            return

        # The user did not specify an account, we'll have to prompt for one
        state = ConversationState(
            update.effective_message.message_id,
            accounts=_get_options_for_path(""),
            current_path="",
            tx=tx,
        )
    except beans.Error as e:
        _log.exception("Can't load beancount data in _handle_message: " + e.message)
        update.effective_message.reply_text(
            quote=True,
            text="❌ An internal error with the accounting program occurred. Please contact the administrator.",
        )
        return
    # If the user used this exact narration previously
    if acct := get_narration_account(context, tx.narration):
        state.tx.debit_account = acct
        # The bang means to not ask
        if update.message.text.endswith("!"):
            balances = _commit_tx(context, state.tx)
            update.effective_message.reply_markdown(
                text=_format_success(
                    beans.format_amount(state.tx.amount),
                    state.tx.debit_account,
                    balances["credit"],
                ),
                quote=True,
            )
            return
        save_state(context, state)
        # Ask user if they want to use that account
        update.message.reply_markdown(
            text=f"Use account `{acct}`?",
            quote=True,
            reply_markup=InlineKeyboardMarkup.from_row(
                [
                    InlineKeyboardButton(
                        "No", callback_data=f"accounts:{state.id}:back"
                    ),
                    InlineKeyboardButton("Yes", callback_data=f"confirm:{state.id}"),
                ]
            ),
        )
        return
    save_state(context, state)
    update.message.reply_markdown(
        text="Please choose an account", quote=True, reply_markup=(_get_btns(state))
    )


def _handle_account_callback(update: Update, context: CallbackContext):
    """Handle callbacks starting with "account". These callbacks mean
    the user selected an expense account option. This handler parses the
    account and either confirms it or asks for more accounts."""
    try:
        query: CallbackQuery = update.callback_query
        data = query.data.split(":")
        state = get_state(context, data[1])
        if not state:
            _log.error(
                f"State with id {data[1]} not found in _handle_account_callback."
            )
            raise ValueError(f"State with id {data[1]} not found.")
        if data[2] == "back":
            # Remove last element from path
            state.current_path = ":".join(state.current_path.split(":")[:-1])
        else:
            if state.current_path:
                state.current_path += ":"
            # data[2] contains the index the user chose
            state.current_path += state.accounts[int(data[2])]
            if state.current_path in beans.get_expense_accounts():
                state.tx.debit_account = state.current_path
                # Remove the state, we don't need it anymore
                delete_state(context, data[2])
                save_narration_account(
                    context, state.tx.narration, state.tx.debit_account
                )
                balances = _commit_tx(context, state.tx)
                update.effective_message.edit_text(
                    text=_format_success(
                        beans.format_amount(state.tx.amount),
                        state.tx.debit_account,
                        balances["credit"],
                    ),
                    quote=True,
                    parse_mode=ParseMode.MARKDOWN,
                )
                return

        state.accounts = _get_options_for_path(state.current_path)
        update.effective_message.edit_reply_markup(reply_markup=_get_btns(state))
    except Exception as e:
        _log.exception(f"Exception caught in _handle_account_callback: {e}")
        update.effective_message.edit_text(
            quote=True, text="An error occurred, please try again later!"
        )
        update.effective_message.reply_markup(
            text=f"❌ `{update.effective_message.reply_to_message.text}`"
        )


def _handle_confirm_callback(update: Update, context: CallbackContext):
    """Handle callbacks starting with "confirm". These callbacks mean
    the user confirmed an expense account option. This handler parses the
    account and either confirms it or asks for more accounts."""
    try:
        query: CallbackQuery = update.callback_query
        data = query.data.split(":")
        state = get_state(context, data[1])
        if not state:
            _log.error(
                f"State with id {data[1]} not found in _handle_account_callback."
            )
            raise ValueError(f"State with id {data[1]} not found.")
        delete_state(context, data[1])
        balances = _commit_tx(context, state.tx)
        update.effective_message.edit_text(
            text=_format_success(
                beans.format_amount(state.tx.amount),
                state.tx.debit_account,
                balances["credit"],
            ),
            quote=True,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        _log.exception(
            f"{type(e)} in _commit_tx: {e}. User: {update.effective_user}. State: {state}."
        )
        update.effective_message.edit_text(
            quote=True, text="An error occurred, please try again later!"
        )
        update.effective_message.reply_markdown(
            text=f"❌ `{update.effective_message.reply_to_message.text}`"
        )


def _commit_tx(
    context: CallbackContext, tx: beans.Transaction, push_message=""
) -> dict:
    """Save the transaction and sync. This raises any exception that might be thrown.
    
    Args:
        context: CallbackContext used.
        tx (:class: beans.Transaction): The transaction to commit.
        push_message (:obj: str [optional]): The message to be thrown.
    
    Returns:
        Both account balances as dictionary.
    """
    config.synchronizer.pull()
    # If the credit account is not defined, set it to the user's account
    if not tx.credit_account:
        tx.credit_account = context.user_data["opts"]["account"]

    balances = beans.append_tx(tx, context.user_data["opts"]["file"])
    config.synchronizer.push(context.user_data["opts"]["file"], msg=push_message)
    save_narration_account(context, tx.narration, tx.debit_account)
    return balances


def _format_success(amount: str, account: str, cash: str, bank: str = "") -> str:
    """Get a success message for a successful operation.

    Args:
        amount (:obj: str): The amount of the operation.
        account (:obj: str): The account used in the operation or the operation name.
        cash (:obj: str): The amount of cash you have left.
        bank (:obj: str [optional]): How much money is left in your bank accoutn (skipped if empty).

    Returns:
        The message formatted as string.
    """
    msg = f"""`✅ {account}`: `{amount}`
Balance: {cash}
"""
    if bank:
        msg += f"Bank: {bank}\n"
    return msg


def _get_options_for_path(path: str) -> List[str]:
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


def _get_btns(state: ConversationState) -> InlineKeyboardMarkup:
    """Get an InlineKeyboardMarkup, i.e. buttons, with a list of
    valid expense account options considering the current state.
    
    Returns:
        InlineKeyboardMarkup: All option's presented to the user.
    """
    btns = []

    # Add back button if necessary
    if state.current_path:
        callback_path = f"accounts:{state.id}:back"
        btns.append(InlineKeyboardButton("⬅️ Back", callback_data=callback_path))

    # Build up other buttons
    for i in range(len(state.accounts)):
        # Our callback path is:
        # - account redirects to the handler for account selection
        # - the id of our state
        # - the index of our state
        callback_path = f"accounts:{state.id}:{i}"
        btns.append(
            InlineKeyboardButton(state.accounts[i], callback_data=callback_path)
        )
    return InlineKeyboardMarkup.from_column(btns)
