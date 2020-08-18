from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler)
from telegram import (Bot, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup)

import logging
import os
from datetime import time
from pymongo import MongoClient
from requests import post

from fetcher import Fetcher

def instantiateFetcher(update, context):
    if "fetcher" not in context.user_data.keys():
        user_id = update.message.from_user.id
        chat_id = update.message.chat.id
        if user_id in FETCHERS.keys():
            context.user_data["fetcher"] = FETCHERS[user_id]
        else:
            context.user_data["fetcher"] = Fetcher(user_id, chat_id)
        logger.info(f'Fetcher for user {user_id} has been instantiated successfully!')

def sendTitleMessage(update, context, data):
    chat_id = update.message.chat_id
    for m in data:
        try:
            context.bot.sendMessage(chat_id=chat_id, text=f'*=== {m[0]} ===*\n'
                                        f'Ultimo capitolo: *{m[1]}*\n'
                                        f'*LINK:* {m[2]}', parse_mode="MARKDOWN")
        except:
            context.bot.sendMessage(chat_id=chat_id, text=f'<b>=== {m[0]} ===</b>\n'
                                    f'Ultimo capitolo: <b>{m[1]}</b>\n'
                                    f'<b>LINK:</b> {m[2]}', parse_mode="HTML")

def sendUpdateMessage(context, data):
    chat_id = context.job.context["chat_id"]
    bot =  context.job.context["bot"]

    message = "<b>HO TROVATO I SEGUENTI NUOVI CAPITOLI:</b>\n\n"
    for m in data:
        message += f'<b>=== {m[0]} ===</b>\nUltimo capitolo: <b>{m[1]}</b>\n<b>LINK:</b> {m[2]}\n\n'
    message += "/notify per disabilitare le notifiche."

    bot.sendMessage(chat_id=chat_id, text=message, parse_mode="HTML", disable_web_page_preview=True)

def start(update, context):
    """Send a message when the command /start is issued."""
    user = update.message.from_user
    instantiateFetcher(update, context)
    reply_keyboard = [['/add manga'], ['/check for latest chapters'], ['/list and manage manga'], ['/notify to enable or disable notifications'], ['/help']]
    keyboard = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    update.message.reply_text(f'Benvenuto {user.first_name}!\n'
                               'Cosa vuoi fare?',
                               reply_markup=keyboard)

def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_markdown(  'Comandi:\n'
                                '/start    ---  guided procedure, use if notification service stops working\n'
                                '/add      ---  to add manga\n'
                                '/check  ---  check for updates of all mangas\n'
                                '/list        ---  list and manage mangas\n'
                                '/notify   ---  enable/disable new chapters notifications\n'
                                '/help     ---  show this message\n')

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
        query.edit_message_text(text="Operazione annullata.")
        return ConversationHandler.END
    else:
        if query.data != "$$check_user_data$$":
            context.user_data["title"] = query.data
        keyboard = [[InlineKeyboardButton("Ultimo capitolo", callback_data="latest")], [InlineKeyboardButton("Rimuovi", callback_data="remove")]]
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
    user_id = update.message.from_user.id
    filtered = update.message.text
    logger.info(f"Filtered command while in conversation with user {user_id}: '{filtered}'.")
    return

def notify(update, context):
    instantiateFetcher(update, context)
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    fetcher = context.user_data["fetcher"]
    bot = context.bot
    job_queue = context.job_queue

    if fetcher.notificationStatus():
        fetcher.setNotificationStatus(False)
        removeNotifier(job_queue, user_id)
        bot.sendMessage(chat_id=chat_id, text="Notifiche disabilitate!")
    else:
        fetcher.setNotificationStatus(True)
        instantiateNotifier(job_queue, fetcher, bot, user_id, chat_id)
        bot.sendMessage(chat_id=chat_id, text="Notifiche abilitate!")

def instantiateNotifier(job_queue, fetcher, bot, userid, chatid):
    # runs every six hours starting at midnight
    context = {"fetcher": fetcher, "chat_id": chatid, "bot": bot}
    job_queue.run_repeating(periodicCheck, interval=2000, first=0, name="PeriodicUpdateNotifier"+str(userid), context=context)
    logger.info(f'Notifier for user {userid} has been instantiated succesfully!')

def removeNotifier(job_queue, userid):
    job =  job_queue.get_jobs_by_name("PeriodicUpdateNotifier"+str(userid))[0]
    job.schedule_removal()

def periodicCheck(context):
    fetcher = context.job.context["fetcher"]
    updates = fetcher.checkRelease(updatesOnly=True)
    chat_id = context.job.context["chat_id"]
    logger.info(f"Periodic check for chat_id {chat_id}")
    if updates != []:
        sendUpdateMessage(context, updates)

def startupRoutine(updater):
    # instantiating notifiers
    mongo_url = os.getenv('MONGODB_URI')
    db = MongoClient(mongo_url, retryWrites=False)
    collection = db['***REMOVED***'].statuses
    users = collection.find({},{"_id": 1, "notifications": 1, "chat_id": 1})

    for u in users:
        user_id = u["_id"]
        chat_id = u["chat_id"]
        FETCHERS[user_id] = Fetcher(user_id, chat_id)
        if u["notifications"] == True:
            instantiateNotifier(updater.job_queue, FETCHERS[user_id], updater.bot, user_id, chat_id)
    db.close()

    # instantiating auto-pinger
    instantiatePinger(updater)

def instantiatePinger(updater):
    target = updater.bot.get_webhook_info()["url"]
    context = {"url": target}
    updater.job_queue.run_repeating(ping, interval=900, first=0, name="KeepUpPinger", context=context)
    logger.info(f'KeepUp pinger has been instantiated succesfully!')

def ping(context):
    url = context.job.context["url"]
    headers = {"content-type": "application/json", 'User-Agent': None, 'accept': None}
    data = {
        "update_id": 0, 
        "message": {
                "message_id": 0,
                "date": 0,
                "text": "ping"
        }
    }
    try:
        r = post(url, json=data, headers=headers )
        logger.info(f"Pinged Heroku app to keep up service. STATUS CODE: {r.status_code}")
    except:
        logger.info(f"Failed to ping Heroku. Will try again later.")
    


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
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
    dp.add_handler(CommandHandler("notify", notify, pass_job_queue=True), 0)
    dp.add_handler(CommandHandler("help", help), 0)
    
    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_webhook(listen="0.0.0.0", port=int(PORT), url_path=TOKEN)
    updater.bot.setWebhook('***REMOVED***' + TOKEN)
    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    
    startupRoutine(updater)
    updater.idle()

if __name__ == '__main__':
    # Enable logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)

    PORT = int(os.environ.get('PORT', 5000))
    TOKEN = '***REMOVED***'

    TITLES, SELECTANDFETCH = range(2)
    LISTOPTIONS, EXECUTEOPTION = range(2)

    FETCHERS = {}

    main()
