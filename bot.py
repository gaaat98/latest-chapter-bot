"""
Simple Bot to reply to Telegram messages taken from the python-telegram-bot examples.
Deployed using heroku.
Author: liuhh02 https://medium.com/@liuhh02
"""

import logging
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler)
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
import os

from fetcher import Fetcher

PORT = int(os.environ.get('PORT', 5000))

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
TOKEN = '1390945914:AAFlBPy0JbmtRzXg7ob2T3TRKoDaiVgpwpI'

TITLES, FETCH = range(2)

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def instantiateFetcher(update, context):
    if "fetcher" not in context.user_data.keys():
        user = update.message.from_user
        context.user_data["fetcher"] = Fetcher(user.id)

def sendTitleMessage(update, context, title, lastn, lasturl):
    try:
        update.message.reply_markdown(f'*=== {title} ===*\n'
                                      f'Ultimo capitolo: *{lastn}*\n'
                                      f'*LINK:* {lasturl}')
    except:
        update.message.reply_html(f'<b>=== {title} ===</b>\n'
                                  f'Ultimo capitolo: <b>{lastn}</b>\n'
                                  f'<b>LINK:</b> {lasturl}')

def start(update, context):
    """Send a message when the command /start is issued."""
    user = update.message.from_user
    instantiateFetcher(update, context)
    reply_keyboard = [['/add manga'], ['/check for updates']]
    update.message.reply_text(f'Benvenuto {user.first_name}!\n'
                               'Cosa vuoi fare?',
                               reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Prima cosa modificata fra')

def add(update, context):
    instantiateFetcher(update, context)
    update.message.reply_text(f'Inserisci il titolo da ricercare')
    return TITLES

def checkAll(update, context):
    instantiateFetcher(update, context)
    res = context.user_data["fetcher"].checkRelease()
    if res == []:
        emptyListMessage(update, context)
    else:
        for t in res:
            sendTitleMessage(update, context, *t)

def listAll(update, context):
    instantiateFetcher(update, context)
    titles = context.user_data["fetcher"].listMangaTitles()
    if titles == []:
        emptyListMessage(update, context)
    else:
        message = ""
        for t in titles:
            message += f"+ *{t}*\n"
        update.message.reply_markdown(message)
def emptyListMessage(update, context):
    message = "No titles found in your list!\nStart adding with /add"
    update.message.reply_markdown(message)

def getTitles(update, context):
    title = update.message.text
    options = context.user_data["fetcher"].fetchManga(title)
    if options == {}:
        update.message.reply_text("Not found :(")
        return ConversationHandler.END
    else:
        context.user_data["title_list"] = options
        reply_keyboard = [[k] for k in options.keys()]
        reply_keyboard.append(["/cancel"])
        update.message.reply_text(f'Seleziona il titolo dalla lista\n',
                               reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return FETCH

def fetchLatest(update, context):
    title = update.message.text
    lastn, lasturl = context.user_data["fetcher"].selectMangaAddAndFetch(context.user_data["title_list"], title)
    del context.user_data["title_list"]
    sendTitleMessage(update, context, title, lastn, lasturl)
    return ConversationHandler.END

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def cancel(update, context):
    user = update.message.from_user
    logger.info("User %s canceled the action.", user.first_name)
    update.message.reply_text('Operazione annullata')

    return ConversationHandler.END

def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add', add)],

        states={
            TITLES: [MessageHandler(Filters.text & ~Filters.command, getTitles)],
            FETCH: [MessageHandler(Filters.text & ~Filters.command, fetchLatest)],
        },

        fallbacks=[CommandHandler("cancel", cancel)]
    )
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("check", checkAll))
    dp.add_handler(CommandHandler("list", listAll))
    dp.add_handler(conv_handler)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_webhook(listen="0.0.0.0",
                          port=int(PORT),
                          url_path=TOKEN)
    #updater.bot.setWebhook('https://7190e44115ad.ngrok.io/' + TOKEN)
    updater.bot.setWebhook('***REMOVED***' + TOKEN)
    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()