from scripts.ToolBox import Downloader, DiskCache
from lxml.html import fromstring

def manaRow(root):
    mana = []
    for child in root:
        mana.append(child.get("alt"))
    return mana


def textRow(root):
    text = []
    for element in root.cssselect(".cardtextbox"):
        s = []
        for child in element:
            if child.tag == "img":
                s.append(child.get("alt"))
        s.append(element.xpath("text()")[0].strip())
        text.append(" ".join(s))
    return text


def flavorRow(root):
    text = []
    for element in root.cssselect(".flavortextbox"):
        text.append(element.text.strip())
    return text


def setRow(root):
    for element in root.cssselect("a"):
        if element.text:
            return element.text.strip()
    return None


def rarityRow(root):
    return root.cssselect("span")[0].text.strip()


def otherSetsRow(root):
    sets = []
    for img in root.cssselect("img"):
        sets.append(img.get("title"))
    return sets


def artistRow(root):
    return root.cssselect("a")[0].text.strip()


def ptRow(root):
    return root.cssselect("b")[0].text.strip()


function_lookup = {"manaRow_v": manaRow,
                   "textRow_v": textRow,
                   "flavorRow_v": flavorRow,
                   "setRow_v": setRow,
                   "rarityRow_v": rarityRow,
                   "otherSetsRow_v": otherSetsRow,
                   "artistRow_v": artistRow,
                   "ptRow_l": ptRow}

card = {}
D = Downloader(cache=DiskCache())
for multiverse_id in range(400000, 500000):
    url = "http://gatherer.wizards.com/Pages/Card/Details.aspx?multiverseid={}".format(multiverse_id)
    tree = fromstring(D(url).encode())
    for container in tree.cssselect(".cardComponentContainer"):
        card = []
        for a in container.cssselect("div [id*='ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_'].row"):
            id_elements = a.get("id").split("_")

            label = a.cssselect(".label")[0]
            if len(label) > 0:
                label = function_lookup[id_elements[-1] + '_l'](label)
            else:
                label = label.text.strip()

            value = a.cssselect(".value")[0]
            if len(value) > 0:
                value = function_lookup[id_elements[-1] + '_v'](value)
            else:
                value = value.text.strip()

            print(label, value)
