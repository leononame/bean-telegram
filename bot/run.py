from os.path import join

from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    PicklePersistence,
    Updater,
)

import config

from .handlers import (
    _handle_account_callback,
    _handle_add_user,
    _handle_auth,
    _handle_check_config,
    _handle_confirm_callback,
    _handle_error,
    _handle_get_users,
    _handle_help,
    _handle_message,
    _handle_set_user_accounts,
    _handle_set_user_file,
    _handle_start,
    _handle_withdraw,
)


def run():
    # Define groups under which the handlers run. Auth group will first authorize users,
    # then default group will run with lower priority. Config group will configure user's
    # data
    AUTH_GROUP = 0
    CONFIG_GROUP = 1
    DEFAULT_GROUP = 5

    # Register persistence for user_data and chat_data, get bot
    p = PicklePersistence(join(config.db_dir, "telegram.pickle"))
    updater = Updater(config.telegram_api_token, use_context=True, persistence=p)
    dispatcher = updater.dispatcher

    # Handle all errors
    dispatcher.add_error_handler(_handle_error)

    # First, the auth group is run.
    # /start registers a new user as admin if none exist, otherwise gets discarded
    dispatcher.add_handler(CommandHandler("start", _handle_start), group=AUTH_GROUP)
    # This handler checks that the user is whitelisted, otherwise stops all other handlers from running
    dispatcher.add_handler(MessageHandler(Filters.all, _handle_auth), group=AUTH_GROUP)

    # Add users or update their configuration
    dispatcher.add_handler(CommandHandler("add", _handle_add_user), CONFIG_GROUP)
    dispatcher.add_handler(CommandHandler("file", _handle_set_user_file), CONFIG_GROUP)
    dispatcher.add_handler(
        CommandHandler("account", _handle_set_user_accounts), CONFIG_GROUP
    )
    dispatcher.add_handler(CommandHandler("users", _handle_get_users), CONFIG_GROUP)
    # Check if the configuration is valid, otherwise stop all other handlers from running
    dispatcher.add_handler(
        MessageHandler(Filters.all, _handle_check_config), group=CONFIG_GROUP
    )

    # Run the default group last
    dispatcher.add_handler(CommandHandler("help", _handle_help), DEFAULT_GROUP)
    dispatcher.add_handler(CommandHandler("withdraw", _handle_withdraw), DEFAULT_GROUP)
    dispatcher.add_handler(MessageHandler(Filters.text, _handle_message), DEFAULT_GROUP)

    # Handle callbacks (when a user presses a button, the response is logged as callback)
    dispatcher.add_handler(
        CallbackQueryHandler(_handle_confirm_callback, pattern=r"^confirm"),
        DEFAULT_GROUP,
    )
    dispatcher.add_handler(
        CallbackQueryHandler(_handle_account_callback, pattern=r"^account"),
        DEFAULT_GROUP,
    )

    # Run
    updater.start_polling()
    updater.idle()
