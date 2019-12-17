# -*- coding: utf-8 -*-

from   HTMLParser import HTMLParser
import os
import sys
import re
import requests


# Custom exception, easy to catch
# all errors occuring in this class
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
            if  attrs[0][0] == 'class' and attrs[0][1] == 'open' \
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
                self.show[ self.season ] = dict()
        elif self.tag == 'li':
            match = self.reg_episode_num.search(data)
            if match:
                self.episode = "{0}".format(match.group(1).zfill(2))
                self.show[ self.season ][ self.episode ] = []
        elif self.tag == 'a':
            self.show[ self.season ][ self.episode ].append(data)
            self.show[ self.season ][ self.episode ].append(self.rel)

    def get_tv_show(self):
        return self.show


# Class handling HTTP traffic to the server
class Prevodi(object):

    # Data division :-)
    PREVODI_SITE_NAME = "www.prijevodi-online.org"
    PREVODI_HOME_URL  = "https://{0}".format(PREVODI_SITE_NAME)
    PREVODI_LOGIN_URL = "{0}/smf/index.php?action=login2".format(PREVODI_HOME_URL)
    REGEX_SEARCH_URL  = r"po_search\.url\s*=\s*'(\S+)'"
    REGEX_SEARCH_KEY  = r"po_search\.key\s*=\s*'(\S+)'"
    REGEX_TV_SHOWS    = r'href="(\/serije\/\S+)"\S+<\/b>(.+)<\/a>'
    REGEX_EPISODE     = r'href="(\/preuzmi\-prijevod\/\S+)".+?>(.+)<\/a>'
    REGEX_ATTACHMENT  = r'attachment; filename="(.+)"'
    REGEX_LOGIN_ERROR = r'<p class="error">(.+)</p>'
    SEARCH_URL_KEY    = 'search_url'
    SEARCH_KEY_KEY    = 'search_key'
    SEARCH_FIELD_USER = 'user'
    SEARCH_FIELD_PASS = 'passwrd'
    SEARCH_FIELD_CLEN = 'cookielength'
    HEADER_CONT_DESC  = 'Content-Description'
    HEADER_TRANS_ENC  = 'Content-Transfer-Encoding'
    HEADER_CONT_DISP  = 'Content-Disposition'
    USER_AGENT        = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.79 Safari/537.36'
    HEADERS = {
        'Host'             : PREVODI_SITE_NAME,
        'Origin'           : PREVODI_HOME_URL,
        'Referer'          : "{0}/".format(PREVODI_HOME_URL),
        'X-Requested-With' : 'XMLHttpRequest',
        'sec-fetch-mode'   : 'cors',
        'sec-fetch-site'   : 'same-origin',
        'User-agent'       : USER_AGENT,
    }

    def __init__(self, username, password):
        self.username   = username
        self.password   = password
        self.sess       = requests.Session()
        self.search_url = None
        self.search_key = None
        self.season     = None
        self.episode    = None
        self.shows      = dict()
        self.tv_show    = None
        self.seasons    = dict()
        self.sparser    = SeasonParser()

    # Parses HTML page looking for search URL and key
    # Return:
    #   Dictionary with search URL and key
    def _get_site_search_params(self):
        r = self.sess.get(self.PREVODI_HOME_URL)
    	regurl = re.compile(self.REGEX_SEARCH_URL)
    	regkey = re.compile(self.REGEX_SEARCH_KEY)
    	url = key = None
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

    # Parses HTML page for subtitles links
    # Return:
    #   Dictionary with episode and links to subtitles
    def _get_subtitle_links(self, html_page):
    	regurl = re.compile(self.REGEX_EPISODE)
    	result = dict()
    	for episode, url in re.findall(regurl, html_page):
    		result[episode] = url
    	return result

    # Checks headers, returning appropriate file name
    def _get_archive_name(self, adict):
    	keys = list(adict.keys())
    	filename = re.compile(self.REGEX_ATTACHMENT)
    	if  self.HEADER_CONT_DESC in keys and adict[self.HEADER_CONT_DESC] == 'File Transfer' \
    	and self.HEADER_TRANS_ENC in keys and adict[self.HEADER_TRANS_ENC] == 'binary' \
    	and self.HEADER_CONT_DISP in keys:
    		match = filename.search(adict[self.HEADER_CONT_DISP])
    		if match:
                # Condense multiple occurences of dash into one
    			pattern = '\-{2,}'
    			res = re.sub(pattern, '-', match.group(1).replace('_','-').replace(' ','-'))
    			return res
    		else:
    			return None
    	else:
    		return None

    def login(self):
        r = self.sess.post(
            url = self.PREVODI_LOGIN_URL,
            data = {
                self.SEARCH_FIELD_USER : self.username,
                self.SEARCH_FIELD_PASS : self.password,
                self.SEARCH_FIELD_CLEN : '-1'},
            headers = self.HEADERS)
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
            url = "{0}/{1}".format(self.PREVODI_HOME_URL, self.search_url),
            data = {'search' : search_term, 'key' : self.search_key},
            headers = self.HEADERS)
        r.raise_for_status()
        self.shows = self._get_result_links(r.text)

    # We come here with exact title
    def get_tv_show(self, title):
        if title not in list(self.shows.keys()):
            raise PrevodException("Exact show title '{0}' could not be found".format(title))
        self.tv_show = title
        r = self.sess.get(
            url = "{0}{1}".format(self.PREVODI_HOME_URL, self.shows[title]),
            headers = self.HEADERS)
        r.raise_for_status()
        # Get all valid subtitle links
        self.sparser.feed(r.text.replace("\n","").replace("\r",""))
        self.seasons = self.sparser.get_tv_show()

    # Get links for subtitles for season and episode
    def get_subtitles(self, season, episode):
        # Format season and episode approrpriately
        try:
            subtitle = self.seasons[season][episode][1]
        except KeyError:
            raise PrevodException("Invalid parameters for TV show '{0}': season {1}, episode {2}".format(
                self.tv_show, season, episode))
        r = self.sess.post(
            url = "{0}{1}/".format(self.PREVODI_HOME_URL, subtitle),
            data = {'key' : self.search_key},
            headers = self.HEADERS)
        r.raise_for_status()
        self.season  = season
        self.episode = episode
        self.archives = self._get_subtitle_links(r.text)

    # Get subtitle archive itself
    def get_subtitle_archive(self, archive_link):
        if not archive_link:
            raise PrevodException("Link for downloading archive was not provided!")
        r = self.sess.get(
            url = "{0}{1}".format(self.PREVODI_HOME_URL, archive_link),
            allow_redirects = True,
            headers = self.HEADERS)
        r.raise_for_status()
        # Check if this is indeed archive
        archive_name = self._get_archive_name(r.headers)
        if archive_name:
            self.archive = archive_name
            with open(archive_name, 'wb') as f:
                f.write(r.content)
                f.close()
        else:
            raise PrevodException("Archive name verification failed!")
