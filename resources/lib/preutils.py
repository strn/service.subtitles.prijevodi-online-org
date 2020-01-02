# -*- coding: utf-8 -*-

# Various helper functions

import glob
import os
import re
import sys
import unicodedata
from   urllib import quote_plus
import urlparse
import xbmc

# Fixes unicode problems
def string_unicode(text, encoding='utf-8'):
    try:
        if sys.version_info[0] >= 3:
            text = str(text)
        else:
            text = unicode(text, encoding)
    except:
        pass
    return text

def normalize_string(_string):
    try:
        text = unicodedata.normalize('NFKD', unicode(string_unicode(_string))).encode('ascii', 'ignore')
    except:
        pass
    return text

# Returns list of arguments passed to HTTP GET request
def get_params(param_string):
    return urlparse.parse_qs(param_string)

# Returns string suitable for passing as HTTP GET parameter
def get_quoted_str(param_string):
    return quote_plus(param_string)

def get_cachedir_title(param_string):
    pattern = r'\-{2,}'
    filename = re.sub(pattern, '-', param_string.replace('_','-').replace(' ','-'))
    return filename

# Required for determining flag
def get_language_list(param_string):
    lang_list = param_string.split(",")
    langs_map = {
        "Bosnian"            : ("ba", 32019,),
        "Croatian"           : ("hr", 32016,),
        "English"            : ("en", 32013,),
        "Serbian"            : ("sr", 32015,),
        "Serbian (Cyrillic)" : ("cirilica", 32014,),
        "German"             : ("de", 32017,),
        "Serbo-Croatian"     : ("sh", 32018,)
    }
    ret_map = dict()
    for lang in lang_list:
        if lang in list(langs_map.keys()):
            ret_map[langs_map[lang][0]] = langs_map[lang][1]
    return ret_map

# Returns subtitle candidate name
def get_subtitle_candidate(filepath, lang, ext=''):
    # Get just filename
    filename = filepath.split('/')[-1]
    return ".".join(filename.split('.')[:-1] + [lang, ext])

# Returns possible subtitles for given media and language
def get_possible_subtitles(cachedir, filepath, language):
    candidate = get_subtitle_candidate(filepath, language, '*')
    subtitle_mask = os.path.join(cachedir, candidate)
    return glob.glob(subtitle_mask)

# Determine archive URL for unpacking (vfs)
def get_archive_url(archive_path):
    if archive_path.endswith('rar'):
        return "rar://{0}/".format(get_quoted_str(archive_path))
    elif archive_path.endswith('zip'):
        return "zip://{0}/".format(get_quoted_str(archive_path))
    else:
        return None

# Remove subdirectories from given directory
# that are older than N days
def remove_older_than(toplevel, days):
    pass
