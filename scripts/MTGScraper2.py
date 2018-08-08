from lxml.html import fromstring, tostring
import re

def manaRow(root):
    mana = []
    for child in root:
        mana.append(child.get("alt"))
    return mana


def textRow(root):
    text = []
    for element in root.cssselect(".cardtextbox"):
        st = tostring(element)
        result = re.sub(r"<div[^>]*?>([\s\S]*?)</div>", r"\1", st.decode("utf-8"))
        result = re.sub(r"<img.+?(?=alt=\")[^\"]*\"([^\"]*)\"[^>]*>", r"\1", result)
        result = re.sub(r"<i>([^<]*)</i>", r"", result)
        # print(result)
        text.append(result)
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


def get_card_id(tree):
    return tree.xpath("//*[@id='aspnetForm']")[0].get("action").split("=")[-1]


def scrape_details_page(html=""):
    function_lookup = {"manaRow_v": manaRow,
                       "textRow_v": textRow,
                       "flavorRow_v": flavorRow,
                       "setRow_v": setRow,
                       "rarityRow_v": rarityRow,
                       "otherSetsRow_v": otherSetsRow,
                       "artistRow_v": artistRow,
                       "ptRow_l": ptRow}

    tree = fromstring(html.encode())
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
            if type(value) == str:
                value = [value]
            card.append((label, value))

        return card


def scrape_language_page(html=""):
    """returns a tuple of (English_Id, {All_Id})"""
    tree = fromstring(html.encode())
    english_id = None
    id_set = set()
    if tree.xpath("//*[@id='ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_languageList_noOtherLanguagesParent']"):
        # print("No translations")
        english_id = get_card_id(tree)
        id_set.add(english_id)
    else:
        # Multiple translations found.
        for translation in tree.cssselect("tr.cardItem"):
            language_id = translation.cssselect("a")[0].get("href").split("=")[-1]
            language = translation.xpath("td[2]")[0].text
            id_set.add(language_id)
            if language.strip() == "English":
                english_id = language_id
        if not english_id:
            english_id = get_card_id(tree)
            id_set.add(english_id)

    return english_id, id_set


if __name__ == "__main__":
    from scripts.ToolBox import Downloader, DiskCache

    downloader = Downloader(cache=DiskCache())
    # url = "http://gatherer.wizards.com/Pages/Card/Languages.aspx?multiverseid={}"
    url = "http://gatherer.wizards.com/Pages/Card/Details.aspx?multiverseid={}"
    # print(scrape_language_page(downloader(url.format(400004))))
    scrape_details_page(downloader(url.format(445969)))
    # 398422
