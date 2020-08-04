import os
import redis
import json

class User():
    def __init__(self, username="test"):
        redis_url = "redis://redis-13589.c78.eu-west-1-2.ec2.cloud.redislabs.com:13589"
        #redis_url = "redis://localhost:6379"
        self.redis = redis.from_url(redis_url)
        self.username = username
        self.redisGetStatus()
    
    def redisGetStatus(self):
        data = self.redis.get(self.username)
        if data == None:
            self.status = {}
        else:
            self.status = json.loads(data)
    
    def redisSetStatus(self):
        data = json.dumps(self.status)
        self.redis.set(self.username, data)
    
    # todo improve data structures ---> maybe add "manga" class
    def addManga(self, title, url, latest_chapter, latest_url):
        if title not in self.status.keys():
            self.status[title] = {}
            self.status[title]["url"] = url
            self.status[title]["latestn"] = latest_chapter
            self.status[title]["latesturl"] = latest_url
            self.redisSetStatus()
        

    def getLatest(self, title):
        return self.status[title]["latestn"]
    
    def updateLatest(self, title, n, url):
        self.status[title]["latestn"] = n
        self.status[title]["latesturl"] = url
        self.redisSetStatus()
    
    def getTitlesAndUrls(self):
        ret = {}
        for title in self.status.keys():
            ret[title] = self.status[title]["url"]
        return ret

    def getTitles(self):
        return list(self.status.keys())

    def getUrlFromName(self, title):
        return self.status[title]["url"]