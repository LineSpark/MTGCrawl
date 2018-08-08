from scripts.ToolBox import Downloader, DiskCache
from datetime import timedelta
from scripts.MTGScraper2 import scrape_language_page, scrape_details_page
import logging
import csv


def known_from_cache():
    """Returns a set of known ids"""
    pass


def MTGCrawler(known=None):
    if not known:
        known = set()
    downloader = Downloader(cache=DiskCache())
    writter = WriteCard()
    language_url = "http://gatherer.wizards.com/Pages/Card/Languages.aspx?multiverseid={}"
    details_url = "http://gatherer.wizards.com/Pages/Card/Details.aspx?multiverseid={}"
    for start_id in range(400000, 500000):
        if start_id not in known:
            language_html = downloader(language_url.format(start_id))
            if language_html:
                english, ids = scrape_language_page(language_html)
                if english not in known:
                    details_html = downloader(details_url.format(english))
                    try:
                        card = scrape_details_page(details_html)
                    except KeyError:
                        card = []
                        logging.error("{}".format(english))
                    writter(card)
                known.update(ids)


class WriteCard:
    def __init__(self, file_name="cards"):
        self.file = "..\data\{}.csv".format(file_name)
        self.header_file = "..\data\{}_headers.txt".format(file_name)
        self.writer = csv.writer(open(self.file, mode="w", encoding="utf-8"))
        self.header, self.header_set = [], set()

    def __call__(self, card):
        card_row = []
        for prop in card:
            if prop[0] not in self.header_set:
                self.header.append(prop[0].rstrip(":"))
                self.header_set.add(prop[0])
                with open(self.header_file, mode="w", encoding="utf-8") as h_write:
                    h_write.write("|".join(self.header))
            card_row.append("|".join(prop[1]))
        self.writer.writerow(card_row)


if __name__ == "__main__":
    logging.basicConfig(filename="..\logs\Crawler.log")
    MTGCrawler()
