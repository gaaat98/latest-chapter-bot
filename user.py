import json

class User():
    def __init__(self):
        self.status = {}
    
    # todo improve data structures ---> maybe add "manga" class
    def addManga(self, title, url, latest_chapter, latest_url):
        self.status[title] = {}
        self.status[title]["url"] = url
        self.status[title]["latestn"] = latest_chapter
        self.status[title]["latesturl"] = latest_url

    def getLatest(self, title):
        return self.status[title]["latestn"]
    
    def updateLatest(self, title, n, url):
        self.status[title]["latestn"] = n
        self.status[title]["latesturl"] = url
    
    def getTitlesAndUrls(self):
        ret = {}
        for title in self.status.keys():
            ret[title] = self.status[title]["url"]
        return ret

    def getUrlFromName(self, title):
        return self.status[title]["url"]