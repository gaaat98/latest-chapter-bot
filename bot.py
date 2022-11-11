from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler)
from telegram import (ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup)

import logging
import os

from json import load
from pymongo import MongoClient
from requests import post

from fetcher import Fetcher

############################### helper methods ################################
def sendTitleMessage(update, context, data):
    """Helper method to send multiple single messages after user request for updates. 
    Data is a list of tuples containing (manga_title, latest_chapter_number, link_to_latest_chapter)."""

    chat_id = update.message.chat_id
    lang = context.user_data["fetcher"].getUserLanguage()
    for manga in data:
        text = LOCALE[lang]["mangaMessage_html"].format(*manga)
        context.bot.sendMessage(chat_id=chat_id, text=text, parse_mode="HTML")

def sendUpdateMessage(context, data):
    """Helper method to send single message after updates are automatically found. 
    Data is a list of tuples containing (manga_title, latest_chapter_number, link_to_latest_chapter)."""

    chat_id = context.job.context["chat_id"]
    bot =  context.job.context["bot"]
    lang = context.job.context["fetcher"].getUserLanguage()

    text = LOCALE[lang]["updateHeader_html"]
    for manga in data:
        text += LOCALE[lang]["mangaMessage_html"].format(*manga)
        text += "\n\n"
    text += LOCALE[lang]["updateFooter"]

    bot.sendMessage(chat_id=chat_id, text=text, parse_mode="HTML", disable_web_page_preview=True)

def emptyListMessage(update, context):
    """Sends message stating that user's list is empty"""

    lang = context.user_data["fetcher"].getUserLanguage()

    text = LOCALE[lang]["emptyListMessage_MarkdownV2"]
    update.message.reply_markdown_v2(text)

def generateTitleKeyboard(context, options):
    """Generates inline keyboard with manga titles"""

    lang = context.user_data["fetcher"].getUserLanguage()
    keyboard = []

    if isinstance(options, list):
        elements = options
    else:
        elements = options.keys()
        context.user_data["title_list"] = options


    for t in elements:
        if len(t) > 64:
            text = t[0:32]+"..."
            data = "$$check_user_data$$" + text
            context.user_data[data] = t
        else:
            text = t
            data = t
        keyboard.append( [InlineKeyboardButton(text, callback_data=data)] )
    keyboard.append([InlineKeyboardButton(LOCALE[lang]["cancel"], callback_data="cancel_operation")])
    return keyboard

def fetchLatest(fetcher, title, url=None):
    """Fetches latest chapter of given manga. url must be 
    None if the given manga is already in the list"""

    if url == None:
        data = fetcher.fetchLatestChapter(title)
    else:
        data = fetcher.selectMangaAddAndFetch(title, url)

    return data
###############################################################################

############################### single handlers ###############################
def start(update, context):
    """Sends welcome message when the command /start is issued."""

    instantiateFetcher(update, context)

    user_first_name = update.message.chat.first_name
    lang = context.user_data["fetcher"].getUserLanguage()
    notification_status = LOCALE[lang]["ON"] if context.user_data["fetcher"].getNotificationStatus() else LOCALE[lang]["OFF"]

    keyboard = ReplyKeyboardMarkup(LOCALE[lang]["startKeyboard"], one_time_keyboard=True)
    text = LOCALE[lang]["startMessage_MarkdownV2"].format(user_first_name, notification_status)

    update.message.reply_markdown_v2(text=text, reply_markup=keyboard)

def help(update, context):
    """Sends detailed help message when the command /help is issued."""

    instantiateFetcher(update, context)

    lang = context.user_data["fetcher"].getUserLanguage()
    text = LOCALE[lang]["helpMessage_Markdown"]
    update.message.reply_markdown(text)

def check(update, context):
    """Sends lastes chapters when the command /check is issued."""

    instantiateFetcher(update, context)

    data = context.user_data["fetcher"].checkRelease()
    if data == []:
        emptyListMessage(update, context)
    else:
        sendTitleMessage(update, context, data)

def notify(update, context):
    """Enables or disables notifications alternately when 
    the command /notify is issued."""

    instantiateFetcher(update, context)

    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    fetcher = context.user_data["fetcher"]
    lang = fetcher.getUserLanguage()
    bot = context.bot
    job_queue = context.job_queue

    if fetcher.getNotificationStatus():
        fetcher.setNotificationStatus(False)
        removeNotifier(job_queue, user_id)
        text = LOCALE[lang]["notificationsDisabled"]
        bot.sendMessage(chat_id=chat_id, text=text)
    else:
        fetcher.setNotificationStatus(True)
        instantiateNotifier(job_queue, fetcher, bot, user_id, chat_id)
        text = LOCALE[lang]["notificationsEnabled"]
        bot.sendMessage(chat_id=chat_id, text=text)

def error(update, context):
    """Log Errors caused by Updates."""

    logger.warning('Update "%s" caused error "%s"', update, context.error)
###############################################################################

###################### /list conversation handler states ######################
def listAllTitles(update, context):
    """Lists all manga in user's list"""

    instantiateFetcher(update, context)

    titles = context.user_data["fetcher"].listMangaTitles()
    if titles == []:
        emptyListMessage(update, context)
        return ConversationHandler.END
    else:
        lang = context.user_data["fetcher"].getUserLanguage()
        keyboard = InlineKeyboardMarkup( generateTitleKeyboard(context, titles) )
        text = LOCALE[lang]["mangaSelectionHeader_MarkdownV2"]
        update.message.reply_markdown_v2(text, reply_markup=keyboard)
    return LISTOPTIONS

def listTitleOptions(update, context):
    """Lists all options available for a manga in user's list"""

    query = update.callback_query
    query.answer()
    lang = context.user_data["fetcher"].getUserLanguage()

    if query.data == "cancel_operation":
        text = LOCALE[lang]["cancelOperation"]
        query.edit_message_text(text=text)
        return ConversationHandler.END
    else:
        if "$$check_user_data$$" not in query.data:
            context.user_data["title"] = query.data
        else:
            context.user_data["title"] = context.user_data[query.data]
            for key in list( context.user_data.keys() ):
                if "$$check_user_data$$" in key:
                    del context.user_data[key]
        keyboard = [
                [InlineKeyboardButton(LOCALE[lang]["latestChapter"], callback_data="latest")], 
                [InlineKeyboardButton(LOCALE[lang]["remove"], callback_data="remove")],
                [InlineKeyboardButton(LOCALE[lang]["cancel"], callback_data="cancel_operation")]
            ]
        keyboard = InlineKeyboardMarkup(keyboard)
        text = LOCALE[lang]["optionSelectionHeader_MarkdownV2"].format(context.user_data["title"])
        query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="MarkdownV2")

        return EXECUTEOPTION

def executeOption(update, context):
    """Executes chosen option"""

    query = update.callback_query
    query.answer()
    lang = context.user_data["fetcher"].getUserLanguage()

    if query.data == "cancel_operation":
        text = LOCALE[lang]["cancelOperation"]
        query.edit_message_text(text=text)
        return ConversationHandler.END

    elif query.data == "remove":
        title = context.user_data["title"]
        context.user_data["fetcher"].removeFromList(title)

        text = LOCALE[lang]["titleRemoved_MarkdownV2"].format(title)
        query.edit_message_text(text=text, parse_mode="MarkdownV2")

    elif query.data == "latest":
        title = context.user_data["title"]
        data = fetchLatest(context.user_data["fetcher"], title)
        sendTitleMessage(query, context, data)

        text = LOCALE[lang]["singleLatestHeader_MarkdownV2"]
        query.edit_message_text(text=text, parse_mode="MarkdownV2")
        #query.message.delete()

    try:
        del context.user_data["title"]
    except:
        logger.warning('Unable to delete item in user_data: {}'.format(context.user_data))

    
    return ConversationHandler.END
###############################################################################

####################### /add conversation handler states #######################
def add(update, context):
    """Begins the procedure (through different conversation states) of title addition when the command /help is issued."""
    instantiateFetcher(update, context)
    lang = context.user_data["fetcher"].getUserLanguage()

    text = LOCALE[lang]["addMangaHeader_MarkdownV2"]
    message_id = update.message.reply_markdown_v2(text)["message_id"]
    context.chat_data["target_message_id"] = message_id #stored for clean-up in case of "/cancel"
    return TITLES

def getTitles(update, context):
    """Searches for corrispondences to user input and lists results"""

    title = update.message.text
    results = context.user_data["fetcher"].fetchManga(title)
    lang = context.user_data["fetcher"].getUserLanguage()

    if results == {}:
        text = LOCALE[lang]["notFound_MarkdownV2"].format(title)
        update.message.reply_markdown_v2(text)
        del context.chat_data["target_message_id"]
        return ConversationHandler.END
    else:
        keyboard = InlineKeyboardMarkup( generateTitleKeyboard(context, results) )
        text = LOCALE[lang]["foundResultsHeader_MarkdownV2"].format(title)
        update.message.reply_markdown_v2(text, reply_markup=keyboard)
        return SELECTANDFETCH

def selectSearchResult(update, context):
    """Searches for latest chapter of the selected manga and adds it to user's list"""

    query = update.callback_query
    query.answer()
    lang = context.user_data["fetcher"].getUserLanguage()

    if query.data == "cancel_operation":
        text = LOCALE[lang]["cancelOperation"]
        query.edit_message_text(text=text)
    else:
        if "$$check_user_data$$" not in query.data:
            title = query.data
        else:
            title = context.user_data[query.data]
            for key in list( context.user_data.keys() ):
                if "$$check_user_data$$" in key:
                    del context.user_data[key]

        text = LOCALE[lang]["searching"]
        query.edit_message_text(text=text)

        url = context.user_data["title_list"][title]
        data = fetchLatest(context.user_data["fetcher"], title, url=url)
        sendTitleMessage(query, context, data)

        text = LOCALE[lang]["singleLatestHeader_MarkdownV2"] + "\n"
        text += LOCALE[lang]["successfullyAdded_MarkdownV2"].format(title)
        query.edit_message_text(text=text, parse_mode="MarkdownV2")

    try:
        del context.chat_data["target_message_id"]
        del context.user_data["title_list"]
    except:
        logger.warning('Unable to delete item in user_data: {} or chat_data: {}'.format(context.user_data, context.chat_data))


    return ConversationHandler.END

def fallback(update, context):
    """Handles /cancel command and filters other commands during /add conversation"""

    user_id = update.message.from_user.id
    current_id = update.message.message_id
    chat_id = update.message.chat.id
    filtered = update.message.text
    lang = context.user_data["fetcher"].getUserLanguage()

    if filtered == "/cancel":
        edit_id = context.chat_data["target_message_id"]
        for i in range(current_id, edit_id, -1):
            context.bot.deleteMessage(chat_id=chat_id, message_id=i)

        text = LOCALE[lang]["cancelOperation"]
        context.bot.editMessageText(chat_id=chat_id, message_id=edit_id, text=text)
        del context.chat_data["target_message_id"]
        return ConversationHandler.END

    text = LOCALE[lang]["commandsDisabled"]
    update.message.reply_text(text)
    logger.info(f"Filtered command while in conversation with user {user_id}: '{filtered}'.")
    return
###############################################################################

############################### "instantiators" ###############################
def instantiateFetcher(update, context):
    """Creates per-user fetcher objects and stores into current user's context.user_data["fetcher"]"""

    if "fetcher" not in context.user_data.keys():
        user_id = update.message.from_user.id
        chat_id = update.message.chat.id

        if user_id in FETCHERS.keys():
            context.user_data["fetcher"] = FETCHERS[user_id]
        else:
            context.user_data["fetcher"] = Fetcher(user_id, chat_id)

        logger.info(f'Fetcher for user {user_id} has been instantiated successfully!')
    try:
        lang = update.message.from_user.language_code[0:2]
        context.user_data["fetcher"].setUserLanguage(lang)
    except:
        logger.warning('Failed to retreive user language! The update was "%s".', update)

    try:
        username = update.message.from_user.first_name
        context.user_data["fetcher"].setUsername(username)
    except:
        logger.warning('Failed to retreive user first name! The update was "%s".', update)

def instantiatePinger(updater):
    """Creates single job to periodically ping Heroku's dyno 
    to keep it from idling"""

    target = updater.bot.get_webhook_info()["url"]
    context = {"url": target}
    updater.job_queue.run_repeating(periodicPing, interval=900, first=0, name="KeepUpPinger", context=context)
    logger.info(f'KeepUp pinger has been instantiated succesfully!')

def instantiateNotifier(job_queue, fetcher, bot, userid, chatid):
    """Creates per-user job to periodically (every hour) check for the release
    of new chapters of manga in user's list"""

    context = {"fetcher": fetcher, "chat_id": chatid, "bot": bot}
    job_queue.run_repeating(periodicCheck, interval=3600, first=0, name="PeriodicUpdateNotifier"+str(userid), context=context)
    logger.info(f'Notifier for user {userid} has been instantiated succesfully!')

def removeNotifier(job_queue, userid):
    """Removes per-user jobs instantiated with instantiateNotifier"""

    job =  job_queue.get_jobs_by_name("PeriodicUpdateNotifier"+str(userid))[0]
    job.schedule_removal()
    logger.info(f'Notifier for user {userid} has been removed succesfully!')
###############################################################################

############################## periodic routines ##############################
def periodicCheck(context):
    """Routine to periodically check for the release
    of new chapters of manga in user's list"""

    fetcher = context.job.context["fetcher"]
    updates = fetcher.checkRelease(updatesOnly=True)
    chat_id = context.job.context["chat_id"]
    logger.info(f"Periodic check for chat_id {chat_id}")
    if updates != []:
        logger.info(f"Sending {len(updates)} update(s) to {chat_id}")
        sendUpdateMessage(context, updates)

def periodicPing(context):
    """Routine to periodically ping Heroku's dyno with an 
    empty telegram message to keep it from idling"""

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
###############################################################################

def startupRoutine(updater):
    """Fetches known users from database and instantiates 
    their fetchers and notifiers if notifications are enabled
    """

    # fetching users
    mongo_url = os.getenv('MONGODB_URI')
    mongo_dbname = os.getenv('MONGODB_DBNAME')
    db = MongoClient(mongo_url, retryWrites=False)
    collection = db[mongo_dbname].statuses
    users = collection.find({},{"_id": 1, "notifications": 1, "chat_id": 1})

    #instantiating fetchers and notifiers
    for u in users:
        user_id = u["_id"]
        chat_id = u["chat_id"]
        FETCHERS[user_id] = Fetcher(user_id, chat_id)
        if u["notifications"] == True:
            instantiateNotifier(updater.job_queue, FETCHERS[user_id], updater.bot, user_id, chat_id)
    db.close()

    # instantiating auto-pinger
    instantiatePinger(updater)

def main():
    """Starts the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # ConversationHandler per la ricerca e aggiunta del manga
    addManga_handler = ConversationHandler(
        entry_points=[CommandHandler('add', add)],
        states={
            TITLES: [MessageHandler(Filters.text & ~Filters.command, getTitles)],
            SELECTANDFETCH:  [CallbackQueryHandler(selectSearchResult)]
        },
        fallbacks=[MessageHandler(Filters.command, fallback)],
    )

    # ConversationHandler per la gestione della lista di manga
    list_handler = ConversationHandler(
        entry_points=[CommandHandler('list', listAllTitles)],
        states={
            LISTOPTIONS:   [CallbackQueryHandler(listTitleOptions)],
            EXECUTEOPTION:  [CallbackQueryHandler(executeOption)],
        },
        fallbacks=[],
    )

    # add all conversations
    dp.add_handler(addManga_handler, 0)
    dp.add_handler(list_handler, 0)

    # add all command handlers
    dp.add_handler(CommandHandler("start", start), 0)
    dp.add_handler(CommandHandler("check", check), 0)
    dp.add_handler(CommandHandler("notify", notify, pass_job_queue=True), 0)
    dp.add_handler(CommandHandler("help", help), 0)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    if CERT_PATH != None and CERT_KEY_PATH != None:
        updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN, cert=CERT_PATH, key=CERT_KEY_PATH)
        logger.info('Webhook started WITH certificate!')
    else:
        updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)
        logger.info('Webhook started WITHOUT certificate!')

    updater.bot.setWebhook("https://" + WEBHOOK_URL + ":" + str(PORT) + "/" + TOKEN)

    startupRoutine(updater)
    updater.idle()

if __name__ == '__main__':
    # Enable logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        with open("lang.json", "r") as lang_dict:
            LOCALE = load(lang_dict)
        logger.info('Localization file has been loaded successfully!')
    except:
        logger.info('Failed to load localization file. Exiting.')
        exit(-1)

    # sensible data
    WEBHOOK_URL = os.getenv('WEBHOOK_URL')
    PORT = int(os.getenv('PORT'))
    TOKEN = os.getenv('TELEGRAM_TOKEN')

    # cert path
    CERT_PATH = os.getenv('CERT_PATH')
    CERT_KEY_PATH = os.getenv('CERT_KEY_PATH')

    # conversation constants, not needed, but help understand code
    TITLES, SELECTANDFETCH = LISTOPTIONS, EXECUTEOPTION = range(2)

    FETCHERS = {}

    main()
