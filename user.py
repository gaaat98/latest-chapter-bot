import os
import pymongo
import json

class User():
    def __init__(self, userID="test"):
        """
        redis_pw = "g3xk3MDUHkmNMqan7O9wG5b2WfRZX2AI"
        redis_host = "redis-13589.c78.eu-west-1-2.ec2.cloud.redislabs.com"
        redis_port = 13589
        #redis_url = "redis://localhost:6379"
        #self.redis = redis.from_url(redis_url)
        self.redis = redis.Redis(host=redis_host, port=redis_port, password=redis_pw)
        """
        self.connectToDb()
        self.userID = userID
        self.getStatusFromDb()
    
    def connectToDb(self):
        mongo_url = os.getenv('MONGODB_URI')
        self.db = pymongo.MongoClient(mongo_url, retryWrites=False)['***REMOVED***'].statuses

    def getStatusFromDb(self):
        data = self.db.find_one({"_id":self.userID})
        if data == None:
            self.status = {}
        else:
            self.status = data
    
    def setStatusToDb(self):
        data = {}
        data["_id"] = self.userID
        data["status"] = self.status
        self.db.insert_one(data)
    
    # todo improve data structures ---> maybe add "manga" class
    def addManga(self, title, url, latest_chapter, latest_url):
        if title not in self.status.keys():
            self.status[title] = {}
            self.status[title]["url"] = url
            self.status[title]["latestn"] = latest_chapter
            self.status[title]["latesturl"] = latest_url
            self.setStatusToDb()
        

    def getLatest(self, title):
        return self.status[title]["latestn"]
    
    def updateLatest(self, title, n, url):
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