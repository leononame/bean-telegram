from telegram.ext import (
    PicklePersistence,
    Updater,
    MessageHandler,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
)
import config
from .handlers import _err_handler, _create_tx, _select_account


def run():
    # Persistence
    p = PicklePersistence(config.db_dir + "/bot.data")

    # Get bot updater and dispatcher
    updater = Updater(config.telegram_api_token, use_context=True, persistence=p)
    dispatcher = updater.dispatcher

    # Register error handler
    dispatcher.add_error_handler(_err_handler)

    # Answer to regular messages
    dispatcher.add_handler(MessageHandler(Filters.text, _create_tx))

    # Handle callbacks (i.e. the button responses)
    # select the expense account
    account_handler = CallbackQueryHandler(_select_account, pattern=r"^accounts")
    dispatcher.add_handler(account_handler)

    # Start bot
    updater.start_polling()
    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
