import urllib.request
import urllib.parse

from html.parser import HTMLParser

vital_article_index = "Wikipedia:Vital_articles"
api_base = "https://en.wikipedia.org/api/rest_v1/page/mobile-html/"

def get_mobile_html(page):
  f = urllib.request.urlopen(api_base + page)
  
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
         not 'Category:' in href:
        self.links.add(href[2:])

def get_mainspace_links(page):
  parser = LinkParser()
  parser.feed(get_mobile_html(page))
  
  return parser.links

class PageCleaner(HTMLParser):
  def __init__(self, valid_links=[]):
    self.content = "<!DOCTYPE html>"
    self.inactive_until = []
    self.valid_links = set(valid_links)

    super().__init__()

  def handle_starttag(self, tag, attrs):
    cls = dict(attrs).get('class','')
    role = dict(attrs).get('role','')
    href = dict(attrs).get('href','')
    
    if tag in ['script','style','figure'] or \
       role == 'note' or \
       'pagelib_collapse_table_container' in cls or \
       'mw-ref' in  cls or \
       'thumb' in cls:
      self.inactive_until.append('/' + tag)
      print(self.inactive_until)
      return
  
    if not self.inactive_until:
      if tag not in ['base','meta','link']:
        keep_attrs = ""
        if cls: keep_attrs += ' class="' + cls +'"'
        if href and href[2:] in self.valid_links: keep_attrs += ' href="' + href[2:] +'"'
        
        self.content += f"<{tag}{keep_attrs}>"
    elif tag == self.inactive_until[-1]:
      del self.inactive_until[-1]
    elif tag not in ['br', 'img', 'hr', 'wbr', 'meta']:
      self.inactive_until.append('/' + tag)

  def handle_endtag(self, tag):
    if not self.inactive_until:
      self.content += f"</{tag}>"
    elif '/' + tag == self.inactive_until[-1]:
      del self.inactive_until[-1]
    
  def handle_data(self, data):
    if not self.inactive_until:
      self.content += data

def get_local_html(page,valid_links=[]):
  parser = PageCleaner(valid_links=valid_links)
  parser.feed(get_mobile_html(page))

  print(f"{len(parser.content)} bytes for {page}")
  
  return parser.content
    
def save_content(page, valid_links=[]):
  with open(f'articles/{page}', 'w') as f:
    f.write(get_local_html(page, valid_links=valid_links))

if __name__ == '__main__':
  pages = get_mainspace_links(vital_article_index)

  print(f"Found {len(pages)} pages")

  save_content('Tokyo',valid_links=pages)
