from time import sleep
import os.path
import re

import urllib.request
import urllib.parse

from html.parser import HTMLParser

level4 = True

vital_article_index = "Wikipedia:Vital_articles"
vital_article_indices = [
    "Wikipedia:Vital_articles/Level/4/People",
    "Wikipedia:Vital_articles/Level/4/History",
    "Wikipedia:Vital_articles/Level/4/Geography",
    "Wikipedia:Vital_articles/Level/4/Arts",
    "Wikipedia:Vital_articles/Level/4/Philosophy_and_religion",
    "Wikipedia:Vital_articles/Level/4/Everyday_life",
    "Wikipedia:Vital_articles/Level/4/Society_and_social_sciences",
    "Wikipedia:Vital_articles/Level/4/Biology_and_health_sciences",
    "Wikipedia:Vital_articles/Level/4/Physical_sciences",
    "Wikipedia:Vital_articles/Level/4/Technology",
    "Wikipedia:Vital_articles/Level/4/Mathematics",
]

api_base = "https://en.wikipedia.org/api/rest_v1/page/mobile-html/"
headers = {"User-Agent": "wikipedia-vital-10k"}

default_head = (
    '<meta charset="utf-8">'
    "<style>body{max-width:800px;margin:0 auto;padding:0 1em;}</style>"
    '<meta name="viewport" content="width=device-width, initial-scale=1">'
)

ignored_namespaces = [
    "Wikipedia:",
    "Wikipedia_talk:",
    "Talk:",
    "File:",
    "User:",
    "Template:",
    "Category:",
]

ignored_tags = ["script", "style", "figure", "map", "figure-inline", "annotation"]

ignored_classes = [
    "pagelib_collapse_table_container",
    "mw-ref",
    "thumb",
    "gallery",
    "ambox",
    "noprint",
    "flagicon",
]

ignored_roles = ["note"]

ignored_sections = [
    "notes",
    "references",
    "bibliography",
    "external links",
    "further reading",
    "see also",
    "gallery",
    "footnotes",
    "sources",
]


def is_tag_ignored(tag, cls="", role=""):
    """ Returns True if a tag should be ignored

    >>> is_tag_ignored("script")
    True

    >>> is_tag_ignored("p")
    False

    >>> is_tag_ignored("div", "alignright ambox important")
    True

    >>> is_tag_ignored("div", "noborder")
    False

    >>> is_tag_ignored("div", "", "note")
    True
    """

    return (
        tag in ignored_tags
        or role in ignored_roles
        or any(c in cls for c in ignored_classes)
    )


def is_mainspace(url):
    """ Returns True if URL points to a mainspace page

    >>> is_mainspace("./Physics")
    True

    >>> is_mainspace("./Wikipedia:NPV")
    False

    >>> is_mainspace("Physics")
    False
    """

    if not url.startswith("./"):
        return False

    return not any([ns in url for ns in ignored_namespaces])


def get_mobile_html(page):
    page = urllib.parse.quote(page, safe='')

    f = urllib.request.urlopen(urllib.request.Request(api_base + page, headers=headers))

    return f.read().decode("utf-8")


class LinkParser(HTMLParser):
    def __init__(self):
        self.links = set()

        super().__init__()

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs)["href"]
            if is_mainspace(href):
                self.links.add(href[2:])


def get_mainspace_links(page):
    parser = LinkParser()
    parser.feed(get_mobile_html(page))

    return parser.links


class PageCleaner(HTMLParser):
    def __init__(self, valid_links=[]):
        self.sections = ["<!DOCTYPE html>"]
        self.inactive_until = []
        self.valid_links = set(valid_links)
        self.keep_current_section = True
        self.is_in_heading = False
        self.section_level = 0
        self.tags_skipped = []

        super().__init__()

    def is_valid_page(self, url):
        return url and url[2:] in self.valid_links

    def get_content(self):
        content = "".join(self.sections)
        content = re.sub(">\s+<", "><", content, flags=re.M)
        return content

    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get("href", "")

        keep_attrs = ""

        if self.is_valid_page(href):
            keep_attrs += ' href="' + href[2:] + '.html"'

        self.is_in_heading = tag in ["h1", "h2", "h3"]

        if tag == "section":
            self.section_level += 1
            if self.section_level == 1:
                self.sections.append("")
                self.keep_current_section = True

        cls = dict(attrs).get("class", "")
        role = dict(attrs).get("role", "")

        if is_tag_ignored(tag, cls, role):
            self.inactive_until.append("/" + tag)
            return

        if not self.inactive_until:
            if tag in ["span", "div", "section"] or (tag == "a" and not keep_attrs):
                self.tags_skipped.append(tag)
            elif tag not in ["base", "meta", "link", "br"]:
                self.sections[-1] += f"<{tag}{keep_attrs}>"
                if tag == "head":
                    self.sections[-1] += default_head
        elif tag == self.inactive_until[-1]:
            del self.inactive_until[-1]
        elif tag not in ["br", "img", "hr", "wbr", "meta", "area", "track", "source"]:
            self.inactive_until.append("/" + tag)

    def handle_endtag(self, tag):
        if not self.inactive_until:
            if self.tags_skipped and self.tags_skipped[-1] == tag:
                del self.tags_skipped[-1]
            else:
                self.sections[-1] += f"</{tag}>"
        elif "/" + tag == self.inactive_until[-1]:
            del self.inactive_until[-1]

        if tag == "section":
            self.section_level -= 1
            if self.section_level == 0:
                if not self.keep_current_section:
                    del self.sections[-1]

    def handle_data(self, data):
        if self.is_in_heading and data.lower() in ignored_sections:
            self.keep_current_section = False

        if not self.inactive_until:
            self.sections[-1] += data.replace("\n", "")


def get_local_html(page, valid_links=[]):
    parser = PageCleaner(valid_links=valid_links)
    parser.feed(get_mobile_html(page))

    return parser.get_content()


def save_content(page, valid_links=[]):
    filename = f"articles/{page.replace('/','%2F')}.html"
    if os.path.isfile(filename):
        print(f"{page} already saved")
    else:
        with open(filename, "w") as f:
            f.write(get_local_html(page, valid_links=valid_links))


def create_index(valid_links):
    with open("articles/index.html", "w") as f:
        html = get_local_html(vital_article_index, valid_links=valid_links)
        html = re.sub("<(table|tbody|thead|td|tr|th)\/*>", "", html, flags=re.I)
        html = re.sub("<p.*?\/p>", "", html, flags=re.I | re.DOTALL | re.M)
        html = re.sub(
            "<\/header>.*?<h2>People",
            "</header><h2>People",
            html,
            flags=re.I | re.DOTALL | re.M,
        )
        html = re.sub(
            "<h1>View Counts.*?<\/body>", "</body>", html, flags=re.I | re.DOTALL | re.M
        )
        f.write(html)

if __name__ == "__main__":
    print("Collecting level 3 page titles and generating index...")
    pages = get_mainspace_links(vital_article_index)
    create_index(pages)

    if level4:
        print("Collecting level 4 page titles")
        for idx in vital_article_indices:
            pages = pages.union(get_mainspace_links(idx))
            print(f"Added pages from {idx} (new total: {len(pages)})")

    print(f"Total pages without duplicates: {len(pages)}")

    from multiprocessing import Pool

    def f(page):
        i, page = page
        print(f"Saving {page} ({i}/{len(pages)})...")
        save_content(page, valid_links=pages)

    with Pool(8) as p:
        p.map(f, enumerate(pages))
