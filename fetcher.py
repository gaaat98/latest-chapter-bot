import requests
import re
import difflib
from user import User

class Fetcher():
    def __init__(self, username):
        self.searchUrl = "https://mangaworld.tv/?s={}&post_type=wp-manga&m_orderby=trending"
        self.master = User(username)

    def fetchManga(self, title=""):
        title.replace(" ", "+")
        resp = requests.get(self.searchUrl.format(title)).content.decode()
        if "Nessun Manga trovato" in resp:
            results = {}
        else:
            temp = re.findall(r"<h4>.*</h4>", resp)
            results = {}
            for r in temp:
                name = re.findall(r'">.+</a', r)[0][2:-3]
                results[name] = re.findall(r'".*"', r)[0].strip('"')
            final = difflib.get_close_matches(title, results.keys())
            if final != []:
                for k in list(results.keys()):
                    if k not in final:
                        results.pop(k)

        return results

    def selectMangaAddAndFetch(self, title, url):
        self.master.presentManga(title, url)
        data = self.fetchLatestChapter(title)
        self.master.updateLatest(*data[0])
        return data

    def fetchLatestChapter(self, title):
        url = self.master.getUrlFromName(title)
        resp = requests.get(url)
        temp = resp.content.decode()
        temp = temp.replace("\n", "\r")
        temp = temp.replace("   ", " ")
        temp = re.findall(r'<li class="wp-manga-chapter\s?">.{0,310}</a>', temp)
        temp = [' '.join(t.split()) for t in temp]

        try:
            lastn = int(re.findall(r" \d{1,5}", temp[0])[0])
        except:
            lastn = 0
        lasturl = re.findall(r'https://.*"', temp[0])[0][0:-1]

        return [[title, lastn, lasturl]]

    def checkRelease(self, updatesOnly=False):
        mangas = self.master.getTitlesAndUrls()
        res = []
        if updatesOnly:
            for title in mangas.keys():
                _, latestn, latesturl = self.fetchLatestChapter(title)[0]
                if self.master.getLatest(title) < latestn:
                    self.master.updateLatest(title, latestn, latesturl)
                    res.append((title, latestn, latesturl))
        else:
            for title in mangas.keys():
                _, latestn, latesturl = self.fetchLatestChapter(title)[0]
                if self.master.getLatest(title) < latestn:
                    self.master.updateLatest(title, latestn, latesturl)
                res.append((title, latestn, latesturl))
        
        return res

    def listMangaTitles(self):
        return self.master.getTitles()

    def isPresent(self, title):
        return self.master.isPresent(title)
    
    def removeFromList(self, title):
        self.master.removeManga(title)
    
    def notificationStatus(self):
        return self.master.notificationStatus()
    
    def setNotificationStatus(self, notifications):
        if notifications:
            self.master.enableNotifications()
        else:
            self.master.disableNotifications()

