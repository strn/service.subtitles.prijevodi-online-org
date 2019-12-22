# -*- coding: utf-8 -*-

from   sys import version_info
import xbmc


class Prelogger(object):

    def dolog(self, txt, loglevel):
        if version_info[0] >= 3:
            message = '[prijevodi-online.org]: {0}'.format(txt.encode('utf-8'))
        else:
            if isinstance (txt, str):
                txt = txt.decode("utf-8")
            message = (u'[prijevodi-online.org]: {0}'.format(txt)).encode("utf-8")
        xbmc.log(msg=message, level=loglevel)

    def info(self, message):
        self.dolog(message, xbmc.LOGINFO)

    def notice(self, message):
        self.dolog(message, xbmc.LOGNOTICE)

    def debug(self, message):
        self.dolog(message, xbmc.LOGDEBUG)

    def error(self, message):
        self.dolog(message, xbmc.LOGERROR)
