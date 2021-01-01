import os
import pymongo

from hashlib import sha1
from time import time

UPDATE_VALIDITY_SECONDS = 3600

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class MangaDB(metaclass=Singleton):
    def __init__(self):
        self.connectToDb()

    def connectToDb(self):
        dburl = os.getenv('MONGODB_URI')
        dbname = os.getenv('MONGODB_DBNAME')
        self.mangas = pymongo.MongoClient(dburl, retryWrites=False)[dbname].mangas

    def insertManga(self, title, url, latestn, latesturl):
        manga_id = self.mangaHash(title, url)
        m = {}
        m["_id"] = manga_id
        m["title"] = title
        m["url"] = url
        m["latestn"] = latestn
        m["latesturl"] = latesturl
        m["updatetime"] = int(time())
        self.mangas.insert_one(m)

    def updateManga(self, title, url, latestn, latesturl):
        manga_id = self.mangaHash(title, url)
        q = {"_id": manga_id}
        if self.mangas.count_documents(q) != 0:
            m = {}
            m["latestn"] = latestn
            m["latesturl"] = latesturl
            m["updatetime"] = int(time())
            self.mangas.update_one(q, {"$set": m})
        else:
            self.insertManga(title, url, latestn, latesturl)

    def mangaHash(self, title, url):
        s = title + url
        h = sha1(s.encode())
        return h.hexdigest()

    def getUpdatedData(self, title, url):
        manga_id = self.mangaHash(title, url)
        q = {"_id": manga_id}
        attr = {"updatetime":1, "latestn": 1, "latesturl":1}
        res = self.mangas.find_one(q, attr)
        if res == None:
            data = []
        elif res["updatetime"] >= int(time()) - UPDATE_VALIDITY_SECONDS:
            data = [ [title, res["latestn"], res["latesturl"]] ]
        else:
            data = []

        return data


