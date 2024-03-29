from requests import get
from bs4 import BeautifulSoup
from user import User
from MangaDB import MangaDB

class Fetcher():
    def __init__(self, userID, chatID):
        self.searchUrl = "https://www.mangaworld.in/archive?keyword={}&sort=most_read"
        self.master = User(userID, chatID)
        self.mangaDB = MangaDB()

    def fetchManga(self, title=""):
        title.replace(" ", "+")
        resp = get(self.searchUrl.format(title)).text
        soup = BeautifulSoup(resp, "html.parser")
        #if soup.find_all("div", {"class":"not-found-content"}):
        if "Nessun risultato trovato" in resp:
            results = {}
        else:
            post_titles = soup.find_all("div", {"class":"entry"})
            results = {}
            for p in post_titles:
                t = p.find('a')
                title = t['title'].replace("-", "—")
                results[title] = t['href']

        return results

    def selectMangaAddAndFetch(self, title, url):
        self.master.presentManga(title, url)
        data = self.fetchLatestChapter(title)
        #self.master.updateLatest(*data[0])
        self.master.updateLatest(data[0][0], data[0][1])
        return data

    def fetchLatestChapter(self, title):
        url = self.master.getUrlFromName(title)

        data = self.mangaDB.getUpdatedData(title, url)
        if data != []:
            return data

        resp = get(url).text
        soup = BeautifulSoup(resp, "html.parser")
        chapters = soup.find_all("div", {"class":"chapter"})
        # indagare perchè qui lancia index out of range
        last_chapter = chapters[0].find("a")

        try:
            text = last_chapter.find("span", {"class":"d-inline-block"}).text
            lastn = int(text.split(" ")[1])
        except:
            try:
                text = last_chapter.find("span", {"class":"d-inline-block"}).text
                lastn = float(text.split(" ")[1])
            except:
                lastn = 0
        lasturl = last_chapter["href"]

        self.mangaDB.updateManga(title, url, lastn, lasturl)
        return [[title, lastn, lasturl]]

    def checkRelease(self, updatesOnly=False):
        mangas = self.master.getTitles()
        res = []
        if updatesOnly:
            for title in mangas:
                _, latestn, latesturl = self.fetchLatestChapter(title)[0]
                if self.master.getLatest(title) < latestn:
                    self.master.updateLatest(title, latestn)
                    res.append((title, latestn, latesturl))
        else:
            for title in mangas:
                _, latestn, latesturl = self.fetchLatestChapter(title)[0]
                if self.master.getLatest(title) < latestn:
                    self.master.updateLatest(title, latestn)
                res.append((title, latestn, latesturl))
        
        return res

    def listMangaTitles(self):
        return self.master.getTitles()

    def isPresent(self, title):
        return self.master.isPresent(title)
    
    def removeFromList(self, title):
        self.master.removeManga(title)
    
    def getNotificationStatus(self):
        return self.master.notificationStatus()
    
    def setNotificationStatus(self, notifications):
        if notifications:
            self.master.enableNotifications()
        else:
            self.master.disableNotifications()
    
    def setUserLanguage(self, lang):
        if lang in ["it", "en"]:
            self.master.setLanguage(lang)
        else:
            self.master.setLanguage("en")

    def getUserLanguage(self):
       return self.master.getLanguage()

    def setUsername(self, username):
        self.master.setUsername(username)

    def getUsername(self):
        return self.master.getUsername()

