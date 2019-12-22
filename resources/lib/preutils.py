# -*- coding: utf-8 -*-

# Various helper functions

import glob
import re
import sys
import unicodedata
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

def get_params(param_string):
    return urlparse.parse_qs(param_string)

def get_cachedir_title(param_string):
    pattern = '\-{2,}'
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

# Remove subdirectories from given directory
# that are older than N days
def remove_older_than(toplevel, days):
    pass
