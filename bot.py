import telegram
import config
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)
from telegram import Update


def connect():
    updater = Updater(config.telegram_api_token, use_context=True)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler("start", start)
    dispatcher.add_handler(start_handler)

    echo_handler = MessageHandler(Filters.text, echo)
    dispatcher.add_handler(echo_handler)
    updater.start_polling()


def echo(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)


def start(update: Update, context: CallbackContext):
    """The command /start registers a new admin with the bot and can only be run once"""
    context.bot.send_message(chat_id=update.effective_chat.id, text="Registering...")
