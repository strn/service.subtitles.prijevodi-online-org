# -*- coding: utf-8 -*-

try:
    from HTMLParser import HTMLParser
except ModuleNotFoundError:
    from html.parser import HTMLParser
import re

import requests


# Custom exception, easy to catch
# all errors occurring in this class
class PrevodException(Exception):
    pass


# Custom season parser due to complex
# HTML page
class SeasonParser(HTMLParser):
    # Start of season data
    REGEX_SEASON = r'Sezona\s+(\d+)'
    # Episode number
    REGEX_EPISODE_NUM = r'(\d+)'

    def __init__(self):
        HTMLParser.__init__(self)
        self.tag = None
        self.show = dict()
        self.reg_season_num = re.compile(self.REGEX_SEASON)
        self.reg_episode_num = re.compile(self.REGEX_EPISODE_NUM)
        self.rel = None
        self.season = None
        self.episode = None

    # HTML tags we are interested in, with specific attributes
    def handle_starttag(self, tag, attrs):
        if tag == 'h3':
            self.tag = tag
        elif tag == 'li' and len(attrs) > 0:
            if attrs[0][0] == 'class' and attrs[0][1] == 'broj':
                self.tag = tag
            else:
                self.tag = None
        elif tag == 'a' and len(attrs) >= 2:
            if attrs[0][0] == 'class' and attrs[0][1] == 'open' \
                    and attrs[1][0] == 'rel':
                self.tag = tag
                self.rel = attrs[1][1]
            else:
                self.tag = None

    def handle_data(self, data):
        if self.tag == 'h3':
            # Get season number
            match = self.reg_season_num.search(data)
            if match:
                self.season = "{0}".format(match.group(1).zfill(2))
                self.show[self.season] = dict()
        elif self.tag == 'li':
            match = self.reg_episode_num.search(data)
            if match:
                self.episode = "{0}".format(match.group(1).zfill(2))
                self.show[self.season][self.episode] = []
        elif self.tag == 'a':
            self.show[self.season][self.episode].append(data)
            self.show[self.season][self.episode].append(self.rel)

    def get_tv_show(self):
        return self.show


# Custom subtitle parser due to complex HTML page
class PrijevodParser(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.tag = self.description = None
        self.archives = dict()
        self.url = None

    def handle_starttag(self, tag, attrs):
        if tag == 'a' and len(attrs) > 0:
            if attrs[0][0] == 'href' and attrs[1][0] == 'rel':
                self.tag = tag
                self.url = attrs[0][1]
            else:
                self.tag = self.url = None
        elif tag == 'td' and len(attrs) > 0:
            if ("class", "opis",) in attrs:
                self.tag = tag
            else:
                self.tag = None

    def handle_data(self, data):
        if self.tag == 'a' and self.url:
            # Get description
            self.description = data.strip()
        elif self.tag == 'td':
            self.archives[self.url] = (self.description, data,)
        self.tag = None

    def get_archives(self):
        return self.archives


# Class handling HTTP traffic to the server
class Prevodi(object):
    # Data division :-)
    PREVODI_SITE_NAME = "www.prijevodi-online.org"
    PREVODI_HOME_URL = "https://{0}".format(PREVODI_SITE_NAME)
    PREVODI_LOGIN_URL = "{0}/smf/index.php?action=login2".format(PREVODI_HOME_URL)
    REGEX_SEARCH_URL = r"po_search\.url\s*=\s*'(\S+)'"
    REGEX_SEARCH_KEY = r"po_search\.key\s*=\s*'(\S+)'"
    REGEX_TV_SHOWS = r'href="(\/serije\/\S+)"\S+<\/b>(.+)<\/a>'
    # Only if HTML page does not have line breaks
    REGEX_EPISODE = r'href="(\/preuzmi\-prijevod\/\S+)".+?>(.+?)<\/a>(.+?)opis">(.+?)<\/td>'
    REGEX_ATTACHMENT = r'attachment; filename="(.+)"'
    REGEX_LOGIN_ERROR = r'<p class="error">(.+)</p>'
    SEARCH_URL_KEY = 'search_url'
    SEARCH_KEY_KEY = 'search_key'
    SEARCH_FIELD_USER = 'user'
    SEARCH_FIELD_PASS = 'passwrd'
    SEARCH_FIELD_CLEN = 'cookielength'
    HEADER_CONT_DESC = 'Content-Description'
    HEADER_TRANS_ENC = 'Content-Transfer-Encoding'
    HEADER_CONT_DISP = 'Content-Disposition'
    USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.79 Safari/537.36'
    HEADERS = {
        'Host': PREVODI_SITE_NAME,
        'Origin': PREVODI_HOME_URL,
        'Referer': "{0}/".format(PREVODI_HOME_URL),
        'X-Requested-With': 'XMLHttpRequest',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'User-agent': USER_AGENT,
    }

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.sess = requests.Session()
        self.search_url = None
        self.search_key = None
        self.season = None
        self.episode = None
        self.tv_show = None
        self.shows = dict()
        self.seasons = dict()
        self.seasparser = SeasonParser()
        self.subtparser = PrijevodParser()
        self.show_id = None
        self.archive = None
        self.archives = None

    # Parses HTML page looking for search URL and key
    # Return:
    #   Dictionary with search URL and key
    def _get_site_search_params(self):
        r = self.sess.get(self.PREVODI_HOME_URL)
        regurl = re.compile(self.REGEX_SEARCH_URL)
        regkey = re.compile(self.REGEX_SEARCH_KEY)
        match = regurl.search(r.text)
        if match:
            url = match.group(1)
        else:
            raise PrevodException("Search URL was not found!")
        match = regkey.search(r.text)
        if match:
            key = match.group(1)
        else:
            raise PrevodException("Search key was not found!")
        self.search_url = url
        self.search_key = key

    # Parses HTMl page for search results
    # Return:
    #   Dictionary with name and web page with subtitles
    def _get_result_links(self, html_page):
        regurl = re.compile(self.REGEX_TV_SHOWS)
        result = dict()
        for url, title in re.findall(regurl, html_page):
            result[title] = url
        return result

    # Checks headers, returning appropriate file name
    def _get_archive_name(self, adict):
        keys = list(adict.keys())
        filename = re.compile(self.REGEX_ATTACHMENT)
        if self.HEADER_CONT_DESC in keys and adict[self.HEADER_CONT_DESC] == 'File Transfer' \
                and self.HEADER_TRANS_ENC in keys and adict[self.HEADER_TRANS_ENC] == 'binary' \
                and self.HEADER_CONT_DISP in keys:
            match = filename.search(adict[self.HEADER_CONT_DISP])
            if match:
                # Condense multiple occurrences of dash into one
                pattern = '\-{2,}'
                return re.sub(pattern, '-', match.group(1).replace('_', '-').replace(' ', '-'))
            else:
                return None
        else:
            return None

    def login(self):
        r = self.sess.post(
            url=self.PREVODI_LOGIN_URL,
            data={
                self.SEARCH_FIELD_USER: self.username,
                self.SEARCH_FIELD_PASS: self.password,
                self.SEARCH_FIELD_CLEN: '-1'},
            headers=self.HEADERS)
        r.raise_for_status()
        # In spite of OK status, check if error occured
        regex = re.compile(self.REGEX_LOGIN_ERROR)
        match = regex.search(r.text)
        if match:
            raise PrevodException(match.group(1))

    # Search by given keyword
    def search(self, search_term):
        if not self.search_url or not self.search_key:
            self._get_site_search_params()
        r = self.sess.post(
            url="{0}/{1}".format(self.PREVODI_HOME_URL, self.search_url),
            data={'search': search_term, 'key': self.search_key},
            headers=self.HEADERS)
        r.raise_for_status()
        self.shows = self._get_result_links(r.text)

    # We come here with exact title
    def get_tv_show(self, title):
        shows_lower = dict(self.shows)
        title_lower = title.lower()
        for key, value in shows_lower.items():
            shows_lower[key.lower()] = value
        if title_lower not in list(shows_lower.keys()):
            raise PrevodException(u"Exact show title '{0}' could not be found".format(title))
        self.tv_show = title
        # Create ID for caching purposes
        self.show_id = '-'.join(shows_lower[title_lower].split('/')[-2:])
        r = self.sess.get(
            url="{0}{1}".format(self.PREVODI_HOME_URL, shows_lower[title_lower]),
            headers=self.HEADERS)
        r.raise_for_status()
        # Get all valid subtitle links
        self.seasparser.feed(r.text.replace("\n", "").replace("\r", ""))
        self.seasons = self.seasparser.get_tv_show()

    # Get links for subtitles for season and episode
    def get_subtitles(self, season, episode):
        # Format season and episode appropriately
        try:
            subtitle = self.seasons[season][episode][1]
        except KeyError:
            raise PrevodException(u"Invalid parameters for TV show '{0}': season {1}, episode {2}".format(
                self.tv_show, season, episode))
        r = self.sess.post(
            url="{0}{1}/".format(self.PREVODI_HOME_URL, subtitle),
            data={'key': self.search_key},
            headers=self.HEADERS)
        r.raise_for_status()
        self.season = season
        self.episode = episode
        self.subtparser.feed(r.text)
        self.archives = self.subtparser.get_archives()

    # Get subtitle archive itself
    def get_subtitle_archive(self, archive_link):
        if not archive_link:
            raise PrevodException("Link for downloading archive was not provided!")
        r = self.sess.get(
            url="{0}{1}".format(self.PREVODI_HOME_URL, archive_link),
            allow_redirects=True,
            headers=self.HEADERS)
        r.raise_for_status()
        # Check if this is indeed archive
        archive_name = self._get_archive_name(r.headers)
        if archive_name:
            self.archive = archive_name
            return archive_name, r.content,
        else:
            raise PrevodException("Archive '{0}' is not a subtitle archive!".format(archive_link))
