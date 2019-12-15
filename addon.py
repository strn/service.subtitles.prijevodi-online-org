# -*- coding: utf-8 -*-

import os
import sys
import re
"""
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
"""
import requests
#import simplecache
#import time
#import unicodedata
#import StringIO
#import codecs
#from datetime import datetime, timedelta
#from urlparse import parse_qs
#from urllib import quote_plus
#from zipfile import ZipFile


# Data division :-)
PREVODI_URL      = "www.prijevodi-online.org"
REGEX_SEARCH_URL = r"po_search\.url\s*=\s*'(\S+)'"
REGEX_SEARCH_KEY = r"po_search\.key\s*=\s*'(\S+)'"
REGEX_TV_SHOWS   = r'href="(\/serije\/\S+)"\S+<\/b>(.+)<\/a>'

# Returns search parameters:
# site's search URL and search key
def get_search_params(a_text):
	regurl = re.compile(REGEX_SEARCH_URL)
	regkey = re.compile(REGEX_SEARCH_KEY)
	url = ''
	key = ''
	match = regurl.search(a_text)
	if match:
		url = match.group(1)
	match = regkey.search(a_text)
	if match:
		key = match.group(1)
	return {'search_url' : url, 'search_key' : key}


# Returns result's dictionary in format:
# Name : Web page with subtitles
def get_result_links(a_text):
	regurl = re.compile(REGEX_TV_SHOWS)
	result = dict()
	for url, title in re.findall(regurl, a_text):
		result[title] = url
	return result

# Returns links to subtitle episodes
def get_episode_links(a_text):
	regurl = re.compile(r'broj">(\d+).+?rel="(\/prijevod\/get\/\d+)"')
	result = dict()
	for episode, url in re.findall(regurl, a_text.replace("\n","").replace("\r","")):
		result[episode] = url
	return result


# Returns links to subtitles
def get_subtitle_links(a_text):
	regurl = re.compile('href="(\/preuzmi\-prijevod\/\S+)".+?>(.+)<\/a>')
	result = dict()
	for episode, url in re.findall(regurl, a_text):
		result[episode] = url
	return result

# Checks headers, returning appropriate file name
def get_archive_name(adict):
	keys = adict.keys()
	filename = re.compile(r'attachment; filename="(.+)"')
	if  'Content-Description' in keys and adict['Content-Description'] == 'File Transfer' \
	and 'Content-Transfer-Encoding' in keys and adict['Content-Transfer-Encoding'] == 'binary' \
	and 'Content-Disposition' in keys:
		match = filename.search(adict['Content-Disposition'])
		if match:
            # Condense multiple occurences of dash into one
			pattern = '\-{2,}'
			res = re.sub(pattern, '-', match.group(1).replace('_','-').replace(' ','-'))
			return res
		else:
			return None
	else:
		return None


def attempt_login(url, uname, passw, search_term):
    session = requests.Session()
    r = session.post(url, data={
        'user': uname,
        'passwrd': passw,
        'cookielength': '-1'
    })
    # Get main page for search URL and key
    r = session.get("https://{0}/".format(PREVODI_URL))
    #print(r.status_code)
    search_params = get_search_params(r.text)
    # Prepare headers for search request
    headers = {
    	'Host'    : PREVODI_URL,
    	'Origin'  : "https://{0}".format(PREVODI_URL),
    	'Referer' : "https://{0}/".format(PREVODI_URL),
    	'X-Requested-With': 'XMLHttpRequest',
    	'sec-fetch-mode' : 'cors',
		'sec-fetch-site' : 'same-origin',
		'User-agent' : 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.79 Safari/537.36',
    }
    r = session.post(
    	"https://{0}/{1}".format(PREVODI_URL, search_params["search_url"]),
    	data = {'search': search_term, 'key' : search_params["search_key"]})
    print(r.status_code)
    if r.text == '':
    	print("INFO: Nothing found")
    	return
    # Find links to all results
    results = get_result_links(r.text)
    print(results)
    # Suppose we select a result
    series = list(results.items())[0]
    print("Selected series:",series)
    r = session.get("https://{0}/{1}".format(PREVODI_URL, series[1]))
    # Get all valid subtitle links
    episodes = get_episode_links(r.text)
    print("Episodes:",episodes)
    # Get titles for selected episode
    subtitles = list(episodes.items())[0]
    print(subtitles)
    r = session.post(
    	"https://{0}{1}/".format(PREVODI_URL, subtitles[1]),
    	data = {'key' : search_params["search_key"]})
    archives = get_subtitle_links(r.text)
    print(archives)
    # Suppose we selected last result
    archive = list(archives.items())[-1]
    print(archive)
    # Get the archive itself
    r = session.get("https://{0}/{1}".format(PREVODI_URL, archive[0]), allow_redirects=True)
    # Check if this is indeed file transfer
    archive_name = get_archive_name(r.headers)
    if archive_name:
    	print(archive_name)
    	with open(archive_name, 'wb') as f:
    		f.write(r.content)
    		f.close()
    else:
    	print("This is not an archive")

def main():
    attempt_login(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])

if __name__ == '__main__':
    main()
