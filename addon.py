# -*- coding: utf-8 -*-

import os
import shutil
import sys

import xbmc
import xbmcaddon
import xbmcplugin
import xbmcvfs

__addon__      = xbmcaddon.Addon()
__cwd__        = xbmc.translatePath( __addon__.getAddonInfo('path') ).decode("utf-8")
__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")
__temp__       = xbmc.translatePath( os.path.join( __profile__, 'temp', '') ).decode("utf-8")
get_local_str  = __addon__.getLocalizedString

sys.path.append (__resource__)

# Import own modules
from prevodi    import PrevodException, Prevodi
from prelogging import Prelogger
from preutils   import get_params, normalize_string

# Action handler
class ActionHandler(object):

    SETTINGS_USERNAME = 'prevodi-username'
    SETTINGS_PASSWORD = 'prevodi-password'

    def __init__(self, raw_params):
        self.log  = Prelogger()
        self.username = __addon__.getSetting(self.SETTINGS_USERNAME)
        self.password = __addon__.getSetting(self.SETTINGS_PASSWORD)
        self.script_name = __addon__.getAddonInfo('name')
        self.params = get_params(sys.argv[2])
        self.action = self.params['?action'][0]
        self.prev = Prevodi(self.username, self.password)
        self.resume = raw_params[2][7:].lower() == 'true'
        self.handle = int(raw_params[1])
        if xbmcvfs.exists(__temp__):
            shutil.rmtree(__temp__)
        xbmcvfs.mkdirs(__temp__)
        self.ACTION_MAP = {
            'search'       : self.search,
            'manualsearch' : self.manual_search,
            'download'     : self.download
        }
        self.log.debug("Action handler initialized")
        self.log.debug("Invoked with: {0}".format(raw_params[2]))
        self.log.notice("Parameters: {0}, resume: {1}, handle: {2}".format(
            self.params, self.resume, self.handle))

    def show_notification(self, message):
        xbmc.executebuiltin(u'Notification({0}, {1})'.format(self.script_name, message).encode("utf-8"))

    def params_are_valid(self):
        if not self.username or not self.password:
            self.show_notification(get_local_str(32005))
            __addon__.openSettings()
            return False
        if self.action not in ('search', 'manualsearch', 'download'):
            self.show_notification(get_local_str(2103))
            return False
        # Check if username and password are valid
        try:
            self.prev.login()
        except PrevodException:
            self.show_notification(get_local_str(32012))
            __addon__.openSettings()
            return False
        return True

    def do(self):
        if not self.params_are_valid():
            return
        # Dispatch the action
        self.ACTION_MAP[self.action]()

    def search(self):
        self.log.notice("Searching for subtitles")

    def manual_search(self):
        search_term = self.params['searchstring'][0]
        self.log.notice("Searching subtitles with term '{0}'".format(search_term))

    def download(self):
        self.log.notice("Downloading subtitles")

    def get_current_show(self):
        pass
        # xbmc.Player() must be instantiated outside of class
        # due to garbage collection error

# end class ActionHandler

handler = ActionHandler(sys.argv)
handler.do()

xbmcplugin.endOfDirectory(handler.handle)
