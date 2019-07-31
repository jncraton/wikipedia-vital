import urllib.request
import urllib.parse

from html.parser import HTMLParser

vital_article_index = "Wikipedia:Vital_articles"
api_base = "https://en.wikipedia.org/api/rest_v1/page/mobile-html/"

default_head = '<meta charset="utf-8"><style>body{max-width:800px;margin:0 auto;padding:0 1em;}</style><meta name="viewport" content="width=device-width, initial-scale=1">'

def get_mobile_html(page):
  f = urllib.request.urlopen(urllib.request.Request(api_base + page, headers={'User-Agent': 'wikipedia-vital'}))
  
  return f.read().decode('utf-8')

class LinkParser(HTMLParser):
  def __init__(self):
    self.links = set()

    super().__init__()

  def handle_starttag(self, tag, attrs):
    if tag == 'a':
      href = dict(attrs)['href']
      if href.startswith('./') and \
         not 'Wikipedia:' in href and \
         not 'Wikipedia_talk:' in href and \
         not 'Talk:' in href and \
         not 'File:' in href and \
         not 'User:' in href and \
         not 'Template:' in href and \
         not 'Category:' in href:
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

  def get_content(self):
    return ''.join(self.sections)

  def handle_starttag(self, tag, attrs):
    cls = dict(attrs).get('class','')
    role = dict(attrs).get('role','')
    href = dict(attrs).get('href','')

    keep_attrs = ""
    if href and href[2:] in self.valid_links: keep_attrs += ' href="' + href[2:] +'.html"'

    self.is_in_heading = tag in ['h1','h2','h3']

    if tag == 'section':
      self.section_level += 1
      if self.section_level == 1:
        self.sections.append("")
        self.keep_current_section = True

    if tag in ['script','style','figure', 'map', 'figure-inline'] or \
       role == 'note' or \
       'pagelib_collapse_table_container' in cls or \
       'mw-ref' in  cls or \
       'thumb' in cls or \
       'gallery' in cls or \
       'ambox' in cls or \
       'noprint' in cls or \
       'flagicon' in cls:
      self.inactive_until.append('/' + tag)
      return

    if not self.inactive_until:
      if tag in ['span','div', 'section'] or (tag == 'a' and not keep_attrs):
        self.tags_skipped.append(tag)
      elif tag not in ['base','meta','link','br']:
        self.sections[-1] += f"<{tag}{keep_attrs}>"
        if tag == 'head':
          self.sections[-1] += default_head
    elif tag == self.inactive_until[-1]:
      del self.inactive_until[-1]
    elif tag not in ['br', 'img', 'hr', 'wbr', 'meta', 'area','track', 'source']:
      self.inactive_until.append('/' + tag)

  def handle_endtag(self, tag):
    if not self.inactive_until:
      if self.tags_skipped and self.tags_skipped[-1] == tag:
        del self.tags_skipped[-1]
      else:
        self.sections[-1] += f"</{tag}>"
    elif '/' + tag == self.inactive_until[-1]:
      del self.inactive_until[-1]

    if tag == 'section':
      self.section_level -= 1
      if self.section_level == 0:
        if not self.keep_current_section: 
          del self.sections[-1]

  def handle_data(self, data):
    if self.is_in_heading and data.lower() in ['notes','references','bibliography','external links','further reading','see also','gallery']:
      self.keep_current_section = False
  
    if not self.inactive_until:
      self.sections[-1] += data.replace('\n','')

def get_local_html(page,valid_links=[]):
  parser = PageCleaner(valid_links=valid_links)
  parser.feed(get_mobile_html(page))

  print(f"{len(parser.get_content())} bytes for {page}")
  
  return parser.get_content()
    
def save_content(page, valid_links=[]):
  import os.path

  page = urllib.parse.quote(page,safe='')

  filename = f'articles/{page}.html'
  if os.path.isfile(filename):
    print(f'{page} already saved')
  else:
    with open(filename, 'w') as f:
      f.write(get_local_html(page, valid_links=valid_links))

def create_index(pages):
  with open("articles/index.html", 'w') as f:
    f.write(f'<!DOCTYPE html><html><head>{default_head}<title>Wikipedia Vital Articles</title></head><body><header><h1>Wikipedia Vital Articles</h1></header><ul>')

    for page in sorted(pages):
      f.write(f'<li><a href="{page}.html">{page}</a>')

    f.write('</ul></body></html>')

if __name__ == '__main__':
  pages = get_mainspace_links(vital_article_index)

  print(f"Found {len(pages)} pages")

  from time import sleep

  for page in pages:
    print(f"Saving {page}...")
    save_content(page, valid_links=pages)
    sleep(0.1)

  create_index(pages)  
