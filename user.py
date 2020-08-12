import os
import pymongo
import json

class User():
    def __init__(self, userID="test"):
        self.connectToDb()
        self.userID = userID
        self.getStatusFromDb()
    
    def connectToDb(self):
        mongo_url = os.getenv('MONGODB_URI')
        #mongo_url = "***REMOVED***"
        self.db = pymongo.MongoClient(mongo_url, retryWrites=False)['***REMOVED***'].statuses

    def getStatusFromDb(self):
        data = self.db.find_one({"_id":self.userID})
        if data == None:
            self.status = {}
        else:
            self.status = data["status"]
    
    def setStatusToDb(self):
        data = {}
        data["_id"] = self.userID
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