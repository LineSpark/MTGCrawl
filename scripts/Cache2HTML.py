from scripts.ToolBox import DiskCache

url = "http://gatherer.wizards.com/Pages/Card/Details.aspx?multiverseid=400008"

dc = DiskCache()

with open("..\static\htmlPage.html", mode="w", encoding="UTF-8") as fwrite:
    fwrite.write(dc[url]["html"])
