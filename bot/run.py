from telegram.ext import (
    PicklePersistence,
    Updater,
    MessageHandler,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    Handler,
)
import config
from os import path
from .handlers import (
    _err_handler,
    _create_tx,
    _select_account,
    _commit_tx,
    _auth_handler,
    _start_handler,
    _add_user_handler,
    _set_user_file_handler,
    _set_user_account_handler,
    _help_handler,
    _list_users_handler,
    _check_config_handler,
)


def run():
    # Define groups under which the handlers run. Auth group will first authorize users,
    # then default group will run with lower priority. Config group will configure user's
    # data
    AUTH_GROUP = 0
    CONFIG_GROUP = 1
    DEFAULT_GROUP = 5

    # Persistence
    p = PicklePersistence(path.join(config.db_dir, "telegram.pickle"))

    # Get bot updater and dispatcher
    updater = Updater(config.telegram_api_token, use_context=True, persistence=p)
    dispatcher = updater.dispatcher

    # Register error handler
    dispatcher.add_error_handler(_err_handler)

    # _start_handler registers you as admin if you exist. _auth_handler checks if you are allowed to use the bot
    dispatcher.add_handler(CommandHandler("start", _start_handler), group=AUTH_GROUP)
    dispatcher.add_handler(MessageHandler(Filters.all, _auth_handler), group=AUTH_GROUP)

    # Add, remove users and set their beancount file
    dispatcher.add_handler(CommandHandler("add", _add_user_handler), CONFIG_GROUP)
    dispatcher.add_handler(CommandHandler("file", _set_user_file_handler), CONFIG_GROUP)
    dispatcher.add_handler(
        CommandHandler("account", _set_user_account_handler), CONFIG_GROUP
    )
    dispatcher.add_handler(CommandHandler("users", _list_users_handler), CONFIG_GROUP)
    dispatcher.add_handler(
        MessageHandler(Filters.all, _check_config_handler), group=CONFIG_GROUP
    )

    # Help
    dispatcher.add_handler(CommandHandler("help", _help_handler), DEFAULT_GROUP)

    # Answer to regular messages
    dispatcher.add_handler(
        MessageHandler(Filters.text, _create_tx), group=DEFAULT_GROUP
    )

    # Handle callbacks (i.e. the button responses)
    dispatcher.add_handler(
        CallbackQueryHandler(_select_account, pattern=r"^accounts"), group=DEFAULT_GROUP
    )
    dispatcher.add_handler(
        CallbackQueryHandler(_commit_tx, pattern=r"^confirm"), group=DEFAULT_GROUP
    )

    # Start bot
    updater.start_polling()
    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
