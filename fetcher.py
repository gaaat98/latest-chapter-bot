import requests
import re
import difflib
from user import User

class Fetcher():
    def __init__(self):
        self.searchUrl = "https://mangaworld.tv/?s={}&post_type=wp-manga&m_orderby=trending"
        self.master = User()

    def fetchManga(self, title=""):
        title.replace(" ", "+")
        resp = requests.get(self.searchUrl.format(title)).content.decode()
        if "Nessun Manga trovato" in resp:
            print("No results")
        else:
            temp = re.findall(r"<h4>.*</h4>", resp)
            results = {}
            for r in temp:
                name = re.findall(r'">.+</a', r)[0][2:-3]
                results[name] = re.findall(r'".*"', r)[0].strip('"')
            final = difflib.get_close_matches(title, results.keys())
            print("Closest matches:", final)
            if final != []:
                for k in list(results.keys()):
                    if k not in final:
                        results.pop(k)
            if results == {}: return
            self.selectManga(results)

    def selectManga(self, l):
        temp = {}
        for i, v in enumerate(l.items()):
            temp[i] = (v[0],v[1])
            print(i, "-", v[0])
        c = int(input())
        target = temp[c][1]
        latest_chapter, latest_url = self.fetchLatestChapter(target)
        self.master.addManga(temp[c][0], temp[c][1], latest_chapter, latest_url)

    def fetchLatestChapter(self, url):
        resp = requests.get(url)
        temp = resp.content.decode()
        temp = temp.replace("\n", "\r")
        temp = re.findall(r'<li class="wp-manga-chapter\s?">.{0,310}</a>', temp)
        temp = [' '.join(t.split()) for t in temp]
        
        lastn = int(re.findall(r" \d{1,5}", temp[3])[0])
        lasturl = re.findall(r'https://.*"', temp[3])[0][0:-1]
        print("Last chapter is", int(lastn))
        print("Link:", lasturl)

        return lastn, lasturl

    def checkRelease(self):
        mangas = self.master.getTitlesAndUrls()
        for title, url in mangas.items():
            print(f"Checking {title}:")
            latestn, latesturl = self.fetchLatestChapter(url)
            if self.master.getLatest(title) < latestn:
                print("New chapter for", title)
                self.master.updateLatest(title, latestn, latesturl)
