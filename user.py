import os
import pymongo

class User():
    def __init__(self, userID, chatID):
        self.connectToDb()
        self.userID = userID
        self.chatID = chatID
        self.getStatusFromDb()
    
    def connectToDb(self):
        mongo_url = os.getenv('MONGODB_URI')
        mongo_dbname = os.getenv('MONGODB_DBNAME')
        self.db = pymongo.MongoClient(mongo_url, retryWrites=False)[mongo_dbname].statuses

    def getStatusFromDb(self):
        data = self.db.find_one({"_id":self.userID})
        if data == None:
            self.status = {}
            self.notifications = False
            self.language = "en"
            self.username = None
        else:
            self.username = data["username"]
            self.language = data["language"]
            self.status = data["status"]
            self.notifications = data["notifications"]

    def setStatusToDb(self):
        data = {}
        data["_id"] = self.userID
        data["chat_id"] = self.chatID
        data["username"] = self.username
        data["language"] = self.language
        data["notifications"] = self.notifications
        data["status"] = self.status
        self.db.delete_one({"_id":self.userID})
        self.db.insert_one(data)

    def presentManga(self, title, url):
        if not self.isPresent(title):
            self.status[title] = {}
            self.status[title]["url"] = url
            self.setStatusToDb()

    def removeManga(self, title):
        if self.isPresent(title):
            del self.status[title]
            self.setStatusToDb() 

    def getLatest(self, title):
        return self.status[title]["latestn"]
    
    def updateLatest(self, title, n, url):
        if self.isPresent(title):
            self.status[title]["latestn"] = n
            self.status[title]["latesturl"] = url
            self.setStatusToDb()

    def getTitlesAndUrls(self):
        ret = {}
        for title in self.status.keys():
            ret[title] = self.status[title]["url"]
        return ret

    def getTitles(self):
        return list(self.status.keys())

    def getUrlFromName(self, title):
        return self.status[title]["url"]
    
    def isPresent(self, title):
        return title in self.status.keys()
    
    def notificationStatus(self):
        return self.notifications
    
    def enableNotifications(self):
        self.notifications = True
        self.setStatusToDb()
    
    def disableNotifications(self):
        self.notifications = False
        self.setStatusToDb()

    def setLanguage(self, lang):
        self.language = lang
        self.setStatusToDb()

    def getLanguage(self):
        return self.language

    def setUsername(self, username):
        self.username = username
        self.setStatusToDb()

    def getUsername(self):
        return self.username