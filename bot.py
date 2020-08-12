"""
Simple Bot to reply to Telegram messages taken from the python-telegram-bot examples.
Deployed using heroku.
Author: liuhh02 https://medium.com/@liuhh02
"""

import logging
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler, CallbackQueryHandler)
from telegram import (Bot, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup)
import os

from fetcher import Fetcher

PORT = int(os.environ.get('PORT', 5000))

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
TOKEN = '1390945914:AAFlBPy0JbmtRzXg7ob2T3TRKoDaiVgpwpI'

TITLES, SELECTANDFETCH = range(2)
LISTOPTIONS, EXECUTEOPTION = range(2)

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def instantiateFetcher(update, context):
    if "fetcher" not in context.user_data.keys():
        user = update.message.from_user
        context.user_data["fetcher"] = Fetcher(user.id)

def sendTitleMessage(update, context, data):
    for m in data:
        try:
            update.message.reply_markdown(f'*=== {m[0]} ===*\n'
                                        f'Ultimo capitolo: *{m[1]}*\n'
                                        f'*LINK:* {m[2]}')
        except:
            update.message.reply_html(f'<b>=== {m[0]} ===</b>\n'
                                    f'Ultimo capitolo: <b>{m[1]}</b>\n'
                                    f'<b>LINK:</b> {m[2]}')

def start(update, context):
    """Send a message when the command /start is issued."""
    user = update.message.from_user
    instantiateFetcher(update, context)
    reply_keyboard = [['/add manga'], ['/check for updates'], ['/list and manage manga']]
    keyboard = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    update.message.reply_text(f'Benvenuto {user.first_name}!\n'
                               'Cosa vuoi fare?',
                               reply_markup=keyboard)

def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_markdown(  'Comandi:\n'
                                '/start    --- guided procedure\n'
                                '/add      --- to add manga\n'
                                '/check  --- check for updates of all manga\n'
                                '/list        --- list mangas --> /remove  /latest chapter')

def checkAll(update, context):
    instantiateFetcher(update, context)
    res = context.user_data["fetcher"].checkRelease()
    if res == []:
        emptyListMessage(update, context)
    else:
        sendTitleMessage(update, context, res)

def listAllTitles(update, context):
    instantiateFetcher(update, context)
    titles = context.user_data["fetcher"].listMangaTitles()
    if titles == []:
        emptyListMessage(update, context)
        return ConversationHandler.END
    else:
        keyboard = generateTitleKeyboard(context, titles)
        update.message.reply_markdown(  '*Seleziona un manga dalla lista:*\n',
                                    reply_markup=InlineKeyboardMarkup(keyboard))
    return LISTOPTIONS

def listTitleOptions(update, context):
    query = update.callback_query
    query.answer()
    if query.data == "cancel_operation":
        query.edit_message_text(text="Operazione annullata")
        return ConversationHandler.END
    else:
        if query.data != "$$check_user_data$$":
            context.user_data["title"] = query.data
        keyboard = [[InlineKeyboardButton("Rimuovi", callback_data="remove")], [InlineKeyboardButton("Ultimo capitolo", callback_data="latest")]]
        keyboard.append([InlineKeyboardButton("Annulla", callback_data="cancel_operation")])
        query.edit_message_text(text="*Seleziona un'opzione:*\n",
                                reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MARKDOWN")
        return EXECUTEOPTION

def executeOption(update, context):
    query = update.callback_query
    query.answer()
    if query.data == "cancel_operation":
        query.edit_message_text(text="Operazione annullata.")
        return ConversationHandler.END
    elif query.data == "remove":
        context.user_data["fetcher"].removeFromList(context.user_data["title"])
    elif query.data == "latest":
        fetchLatest(query, context)
    query.edit_message_text(text="Operazione completata!")
    try:
        del context.user_data["title"]
        del context.user_data["title_list"]
    except:
        pass
    
    return ConversationHandler.END

def emptyListMessage(update, context):
    message = "No titles found in your list!\nStart adding with /add"
    update.message.reply_markdown(message)

def add(update, context):
    instantiateFetcher(update, context)
    update.message.reply_text(f'Inserisci il titolo da ricercare')
    return TITLES

def getTitles(update, context):
    title = update.message.text
    options = context.user_data["fetcher"].fetchManga(title)
    if options == {}:
        update.message.reply_text("Not found :(")
        return ConversationHandler.END
    else:
        keyboard = generateTitleKeyboard(context, options)
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_markdown('*Ho trovato i seguenti manga:*\n',
                               reply_markup=reply_markup)
        return SELECTANDFETCH

def generateTitleKeyboard(context, options):
    context.user_data["title_list"] = options
    keyboard = []
    if isinstance(options, list):
        elements = options
    else:
        elements = options.keys()

    for t in elements:
        if len(t) > 64:
            data = "$$check_user_data$$"
            text = t[0:32]+"..."
            context.user_data["title"] = t
        else:
            text = t
            data = t
        keyboard.append( [InlineKeyboardButton(text, callback_data=data)] )
    keyboard.append([InlineKeyboardButton("Annulla", callback_data="cancel_operation")])
    return keyboard

def selectSearchResult(update, context):
    query = update.callback_query
    query.answer()
    if query.data == "cancel_operation":
        query.edit_message_text(text="Operazione annullata.")
    else:
        if query.data != "$$check_user_data$$":
            context.user_data["title"] = query.data
        context.user_data["url"] = context.user_data["title_list"][context.user_data["title"]]
        query.edit_message_text(text="Searching...")
        fetchLatest(query, context)
        query.edit_message_text(text="Trovato!")
    
    try:
        del context.user_data["title"]
        del context.user_data["url"]
        del context.user_data["title_list"]
    except:
        pass

    return ConversationHandler.END

def fetchLatest(update, context):
    title = context.user_data["title"]
    try:
        url = context.user_data["url"]
        data = context.user_data["fetcher"].selectMangaAddAndFetch(title, url)
    except:
        data = context.user_data["fetcher"].fetchLatestChapter(title)
    
    sendTitleMessage(update, context, data)

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def fallback(update, context):
    print("Filtrato comando")
    return

def notify(update, context):
    instantiateFetcher(update, context)
    if "chat_id" not in context.user_data.keys():
        context.user_data["chat_id"] = update.message.chat.id

    if context.user_data["fetcher"].notificationStatus():
        context.user_data["fetcher"].setNotificationStatus(False)
        context.bot.sendMessage(chat_id=context.user_data["chat_id"], text="Notifiche disabilitate!")
        del context.user_data["chat_id"]
    else:
        context.user_data["fetcher"].setNotificationStatus(True)
        context.bot.sendMessage(chat_id=context.user_data["chat_id"], text="Notifiche abilitate!")
    
    print(context.user_data)



def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # ConversationHandler per la ricerca e aggiunta del mango
    addManga_handler = ConversationHandler(
        entry_points=[CommandHandler('add', add)],
        states={
            TITLES: [MessageHandler(Filters.text & ~Filters.command, getTitles)],
            SELECTANDFETCH:  [CallbackQueryHandler(selectSearchResult)]
        },
        fallbacks=[MessageHandler(Filters.command, fallback)],
    )

    list_handler = ConversationHandler(
        entry_points=[CommandHandler('list', listAllTitles)],
        states={
            LISTOPTIONS:   [CallbackQueryHandler(listTitleOptions)],
            EXECUTEOPTION:  [CallbackQueryHandler(executeOption)],
        },
        fallbacks=[MessageHandler(Filters.command, fallback)],
    )

    dp.add_handler(addManga_handler, 0)
    dp.add_handler(list_handler, 0)
    

    dp.add_handler(CommandHandler("start", start), 0)
    dp.add_handler(CommandHandler("check", checkAll), 0)
    dp.add_handler(CommandHandler("notify", notify), 0)
    dp.add_handler(CommandHandler("help", help), 0)
    

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_webhook(listen="0.0.0.0",
                          port=int(PORT),
                          url_path=TOKEN)
    #updater.bot.setWebhook('https://02034edd4179.ngrok.io/' + TOKEN)
    updater.bot.setWebhook('***REMOVED***' + TOKEN)
    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()