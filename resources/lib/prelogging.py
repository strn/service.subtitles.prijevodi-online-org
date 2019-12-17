# -*- coding: utf-8 -*-

import xbmc


class Prelogger(object):

	def dolog(self, message, loglevel):
		xbmc.log(u"[prijevodi-online.org]: {0}".format(message).encode('utf-8'), level=loglevel)

	def info(self, message):
		self.dolog(message, xbmc.LOGINFO)

	def notice(self, message):
		self.dolog(message, xbmc.LOGNOTICE)

	def debug(self, message):
		self.dolog(message, xbmc.LOGDEBUG)

	def error(self, message):
		self.dolog(message, xbmc.LOGERROR)
