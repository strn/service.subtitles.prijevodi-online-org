# -*- coding: utf-8 -*-

# Various helper functions

import unicodedata
import urlparse

def normalize_string(_string):
    return unicodedata.normalize('NFKD', unicode(_string, 'utf-8')).encode('ascii', 'ignore')

def get_params(param_string):
	return urlparse.parse_qs(param_string)
