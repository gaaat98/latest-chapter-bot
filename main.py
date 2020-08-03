#!/usr/bin/env python3
import sys
from fetcher import Fetcher

if __name__ == "__main__":
    if len(sys.argv) > 1:
        title = " ".join(sys.argv[1:], )
    else:
        title = ""
    manga = ["one piece", "black clover", "my hero academia", "tower of god", "attack on titan"]
    t = Fetcher()
    for title in manga:
        print("Seraching MangaWorld for:", title)
        t.fetchManga(title)
    
    t.checkRelease()