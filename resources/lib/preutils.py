# -*- coding: utf-8 -*-

# Various helper functions

import glob
import os
import re
import sys
import time
import unicodedata
import urlparse
from urllib import quote_plus


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


def get_cache_dir_title(param_string):
    pattern = r'\-{2,}'
    filename = re.sub(pattern, '-', param_string.replace('_', '-').replace(' ', '-'))
    return filename


# Required for determining flag
def get_language_list(param_string):
    lang_list = param_string.split(",")
    langs_map = {
        "Bosnian": ("bs", 32019,),
        "Croatian": ("hr", 32016,),
        "English": ("en", 32013,),
        "Serbian": ("sr", 32015,),
        "Serbian (Cyrillic)": ("cirilica", 32014,),
        "German": ("de", 32017,),
        "Serbo-Croatian": ("sh", 32018,)
    }
    ret_map = dict()
    for lang in lang_list:
        if lang in list(langs_map.keys()):
            ret_map[langs_map[lang][0]] = langs_map[lang][1]
    return ret_map


# Returns subtitle candidate name
def get_subtitle_candidate(file_path, lang, ext=''):
    # Get just filename
    filename = file_path.split('/')[-1]
    return ".".join(filename.split('.')[:-1] + [lang, ext])


# Returns possible subtitles for given media and language
def get_possible_subtitles(cache_dir, file_path, language):
    candidate = get_subtitle_candidate(file_path, language, '*')
    subtitle_mask = os.path.join(cache_dir, candidate)
    return glob.glob(subtitle_mask)


# Remove subdirectories from given directory
# that are older than N days
def remove_older_than(top_level, days):
    def remove(path):
        if os.path.isdir(path):
            try:
                os.rmdir(path)
            except OSError:
                raise Exception("Unable to remove folder '{0}'".format(path))
        else:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                raise Exception("Unable to remove file '{0}'".format(path))

    time_in_secs = time.time() - (days * 24 * 60 * 60)
    items = list()
    for root, dirs, files in os.walk(top_level, topdown=False):
        for file_ in files:
            full_path = os.path.join(root, file_)
            stat = os.stat(full_path)
            if stat.st_mtime <= time_in_secs:
                remove(full_path)
                items.append(full_path)
        if not os.listdir(root):
            remove(root)
            items.append(root)
    return items
