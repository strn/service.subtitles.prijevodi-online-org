# -*- coding: utf-8 -*-

# System modules
import json
import os
import re
import shutil
import sys

# Kodi modules
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

__addon__      = xbmcaddon.Addon()
__dialog__     = xbmcgui.Dialog()
__progress__   = xbmcgui.DialogProgress()
__player__     = xbmc.Player()
__addonname__  = __addon__.getAddonInfo('name')
__addonid__    = __addon__.getAddonInfo('id')
get_local_str  = __addon__.getLocalizedString

if sys.version_info[0] >= 3:
    __cwd__      = xbmc.translatePath(__addon__.getAddonInfo('path'))
    __profile__  = xbmc.translatePath(__addon__.getAddonInfo('profile'))
    __resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib'))
    __resdata__  = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'data'))
    __cache__    = xbmc.translatePath(os.path.join(__profile__, 'cache'))
    __unrar__    = xbmc.translatePath(os.path.join(__profile__, 'unrar'))
    __temp__     = xbmc.translatePath(os.path.join(__profile__, 'temp'))
else:
    __cwd__      = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
    __profile__  = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
    __resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')).decode("utf-8")
    __resdata__  = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'data')).decode("utf-8")
    __cache__    = xbmc.translatePath(os.path.join(__profile__, 'cache')).decode("utf-8")
    __unrar__    = xbmc.translatePath(os.path.join(__profile__, 'unrar')).decode("utf-8")
    __temp__     = xbmc.translatePath(os.path.join(__profile__, 'temp')).decode("utf-8")

sys.path.append (__resource__)

# Addon modules
from   prevodi    import PrevodException, Prevodi
from   prelogging import Prelogger
import prearchive as     pa
import preutils   as     pu


# Action handler
class ActionHandler(object):

    SETTINGS_USERNAME = 'prevodi-username'
    SETTINGS_PASSWORD = 'prevodi-password'

    def __init__(self, raw_params):
        self.log         = Prelogger()
        self.username    = __addon__.getSetting(self.SETTINGS_USERNAME)
        self.password    = __addon__.getSetting(self.SETTINGS_PASSWORD)
        self.script_name = __addonname__
        self.params      = pu.get_params(sys.argv[2])
        self.action      = self.params['?action'][0]
        self.prev        = Prevodi(self.username, self.password)
        self.resume      = raw_params[2][7:].lower() == 'true'
        self.handle      = int(raw_params[1])
        if xbmcvfs.exists(__temp__):
            shutil.rmtree(__temp__)
        for dir in __cache__, __unrar__, __temp__ :
            if not xbmcvfs.exists(dir):
                xbmcvfs.mkdirs(dir)
        self.ACTION_MAP = {
            'search'       : self.search,
            'manualsearch' : self.manual_search,
            'download'     : self.download
        }
        self.log.debug("Action handler invoked with: {0}".format(raw_params[2]))
        self.log.debug("Parameters: {0}, resume: {1}, handle: {2}".format(
            self.params, self.resume, self.handle))
        # Remove old directories
        dirs = pu.remove_older_than(__cache__, 3)
        self.log.debug("Removed {0} items older than 3 days".format(dirs))

    def show_notification(self, message):
        xbmc.executebuiltin(u'Notification({0}, {1})'.format(self.script_name, message).encode("utf-8"))

    # Minimal parameter check
    def params_are_valid(self):
        if not self.username or not self.password:
            ok = __dialog__.ok(self.script_name, get_local_str(32005))
            __addon__.openSettings()
            return False
        if self.action not in ('search', 'manualsearch', 'download'):
            self.show_notification(get_local_str(2103))
            return False
        # Check if username and password are valid
        try:
            self.prev.login()
        except PrevodException:
            ok = __dialog__.ok(self.script_name, get_local_str(32012))
            __addon__.openSettings()
            return False
        return True

    # Simply dispatch the action
    def do(self):
        if not self.params_are_valid():
            return
        self.ACTION_MAP[self.action]()

    # Search when invoking plugin while playing a show
    # or when a TV show is selected through the GUI
    def search(self):
        self.log.debug("Searching for subtitles ...")
        curr_show = self.get_current_show()
        # Check if cached directory exists
        if os.path.exists(curr_show['cachedir']):
            # Load JSON file with subtitle data
            json_file_path = os.path.join(curr_show['cachedir'], 'subtitles.json')
            with open(json_file_path, 'r') as f:
                subtitle_archives = json.load(f)
            self.log.debug("Loaded data from '{0}'".format(json_file_path))
        else:
            # Search in prijevodi
            self.prev.search(curr_show['tvshow_title'])
            try:
                self.prev.get_tv_show(curr_show['tvshow_title'])
            except PrevodException as e:
                self.log.error(e)
                return
            # At this moment
            if len(self.prev.seasons.keys()) > 0:
                self.prev.get_subtitles(curr_show['season'], curr_show['episode'])
                if self.prev.archives:
                    # Make subdirectory for potential subtitles
                    os.makedirs(curr_show['cachedir'])
                    # Save this episode's subtitle data
                    json_file_path = os.path.join(curr_show['cachedir'], 'subtitles.json')
                    with open(json_file_path, 'wb') as f:
                        json.dump(self.prev.archives, f)
                    subtitle_archives = self.prev.archives
                    self.log.debug("Saved data to '{0}'".format(json_file_path))
                else:
                    return
            else:
                return
        langs_map = pu.get_language_list(self.params['languages'][0])
        self.log.debug("Languages map: {0}".format(langs_map))
        # Construct regex to catch all languages we are interested in
        regex_lang = r'\s+({0})'.format('|'.join(langs_map.keys()).replace('ba','bs'))
        regex_lang_match = re.compile(regex_lang, re.IGNORECASE)

        for url, data in subtitle_archives.items():
            # Check if subtitle is in list of languages
            match = regex_lang_match.search(data[0])
            if not match:
                continue
            subt_name = data[0]
            subt_suitable = data[1]
            supp_country = match.group(1).lower()
            if supp_country.find('irilic') > -1:
                supp_country = 'sr'

            subt_lang = xbmc.convertLanguage(supp_country, xbmc.ISO_639_1)
            self.log.debug("Subtitle: url='{0}', subt_name='{1}', subt_suitable='{2}', lang={3}".format(
                url, subt_name, subt_suitable, subt_lang))

            # Setting thumbnail image makes country flag
            list_item = xbmcgui.ListItem(
                label  = get_local_str(langs_map[supp_country]),
                label2 = "[B]{0}[/B]".format(subt_name))
            list_item.setArt({'thumb': subt_lang})

            plugin_url = "plugin://{0}/?action=download&url={1}&suitable={2}&cachedir={3}&lang={4}&filepath={5}".format(
                __addonid__,
                pu.get_quoted_str(url),
                pu.get_quoted_str(subt_suitable),
                pu.get_quoted_str(curr_show['cachedir']),
                subt_lang,
                pu.get_quoted_str(curr_show['file_original_path']))

            xbmcplugin.addDirectoryItem(
                handle   = self.handle,
                url      = plugin_url,
                listitem = list_item,
                isFolder = False)

    # Search with manually entered search phrase
    def manual_search(self):
        search_term = self.params['searchstring'][0]
        self.log.notice("Searching subtitles with term '{0}'".format(search_term))

    # Downloading subtitles that were selected during "search"
    # or "manualsearch" invocation
    def download(self):
        ret = __dialog__.yesno(
            get_local_str(32021),
            self.params['suitable'][0],
            yeslabel=get_local_str(32022))
        if not ret:
            self.log.debug("Subtitle download cancelled")
            return
        # Check if subtitles are already downloaded in cache directory
        possible_subtitles = pu.get_possible_subtitles(
            self.params['cachedir'][0],
            self.params['filepath'][0],
            self.params['lang'][0])
        if len(possible_subtitles) == 0:
            self.log.debug("Downloading subtitles for '{0}'".format(self.params['filepath'][0]))
            arch_name, arch_content = self.prev.get_subtitle_archive(self.params['url'][0])
            archive_path = os.path.join(self.params['cachedir'][0], arch_name)
            # Write to file because of unified archive interface
            with open(archive_path, 'wb') as f:
                f.write(arch_content)
                f.close()
            self.log.debug("Subtitle archive saved as '{0}'".format(archive_path))

            archive = pa.Archive(archive_path, __resdata__)
            archive.unrar_dir = __unrar__
            archive.temp_dir = __temp__
            archive.dialog = __progress__
            archive.str_get_unrar = get_local_str(32023)
            opersys, architecture = archive.get_platform_info()
            self.log.debug("Platform ID: '{0}_{1}'".format(opersys, architecture))
            archive.check_unrar_exe()
            files = archive.list()
            if len(files) == 0:
                # Empty archive
                self.log.error("No files in archive '{0}'".format(archive_path))
                return
            else:
                self.log.debug("Archive: files={0}".format(files))
            archive_source = files[0]
            archive_dest = self.params['cachedir'][0]
            self.log.debug("Unpacking '{0}' to '{1}' using '{2}'".format(
                archive_source, archive_dest, archive.get_dearch_path()))
            archive.extract(archive_source, archive_dest)
            archive.remove()

            # Rename subtitle accordingly
            archive_dest = os.path.join(archive_dest, files[0])
            final_subtitle = pu.get_subtitle_candidate(
                self.params['filepath'][0],
                self.params['lang'][0],
                archive_dest.rpartition('.')[2])
            final_subtitle = os.path.join(self.params['cachedir'][0], final_subtitle)
            os.rename(archive_dest, final_subtitle)
            self.log.debug("Renamed subtitle file '{0}' to '{1}'".format(archive_dest, final_subtitle))
            self.add_subtitle_dir_item(final_subtitle, self.params['lang'][0])
        else:
            self.log.debug("Using cached subtitles: {0}".format(possible_subtitles))
            # TODO: Handle case of more than one available subtitle
            self.add_subtitle_dir_item(possible_subtitles[0], self.params['lang'][0])

    # Adds directory item with subtitle file
    def add_subtitle_dir_item(self, subtitle_path, lang):
        # Copy subtitle to __temp__
        shutil.copy2(subtitle_path, __temp__)
        returned_path = os.path.join(__temp__, os.path.basename(subtitle_path))
        self.log.debug("Returned subtitle: '{0}', lang: '{1}'".format(returned_path, lang))
        list_item = xbmcgui.ListItem(label=lang)
        xbmcplugin.addDirectoryItem(
            handle   = self.handle,
            url      = returned_path,
            listitem = list_item,
            isFolder = False)

    def take_title_from_focused_item(self):
        lbl_year         = str(xbmc.getInfoLabel("ListItem.Year"))
        lbl_orig_title   = xbmc.getInfoLabel("ListItem.OriginalTitle")
        lbl_tvshow_title = xbmc.getInfoLabel("ListItem.TVShowTitle")
        lbl_season       = str(xbmc.getInfoLabel("ListItem.Season"))
        lbl_episode      = str(xbmc.getInfoLabel("ListItem.Episode"))
        lbl_type         = xbmc.getInfoLabel("ListItem.DBTYPE") # movie/tvshow/season/episode
        lbl_title        = xbmc.getInfoLabel("ListItem.Title")
        lbl_filepath     = xbmc.getInfoLabel("ListItem.FileNameAndPath")

        is_movie = lbl_type == 'movie' or xbmc.getCondVisibility("Container.Content(movies)")
        is_episode = lbl_type == 'episode' or xbmc.getCondVisibility("Container.Content(episodes)")

        title = 'SearchFor...'
        if is_movie and lbl_year:
            if lbl_title:
                title = lbl_title
            else:
                title = lbl_original_title
        elif is_episode and lbl_season and lbl_episode:
            if lbl_tvshow_title:
                title = lbl_tvshow_title
            else:
                title = lbl_title
        ret = {
            "year"           : lbl_year,
            "season"         : lbl_season.zfill(2),
            "episode"        : lbl_episode.zfill(2),
            "title"          : title,
            "tvshow_title"   : lbl_tvshow_title,
            "lbl_type"       : lbl_type,
            "lbl_orig_title" : lbl_orig_title,
            "is_movie"       : is_movie,
            "is_episode"     : is_episode,
            "filepath"       : lbl_filepath
        }
        self.log.debug("Focused item ({0}): {1}".format(lbl_type, str(ret)))
        return ret

    # Collect TV show data from either currently playing file
    # or one selected through GUI
    def get_current_show(self):
        # xbmc.Player() must be instantiated outside of class
        # due to garbage collection error
        item              = dict()
        item['temp']      = False
        item['mansearch'] = False

        if __player__.isPlaying():
            item['year']               = xbmc.getInfoLabel("VideoPlayer.Year")                          # Year
            item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season")).zfill(2)          # Season
            item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode")).zfill(2)         # Episode
            item['tvshow_title']       = unicode(xbmc.getInfoLabel("VideoPlayer.TVShowTitle"), 'utf-8') # Show
            item['title']              = unicode(xbmc.getInfoLabel("VideoPlayer.Title"), 'utf-8')       # try to get original title
            item['file_original_path'] = __player__.getPlayingFile().decode('utf-8')                    # Full path of a playing file
            self.log.debug("Got info from currently playing file")
        else:
            itemdata                   = self.take_title_from_focused_item()
            item['year']               = itemdata['year']
            item['season']             = itemdata['season']
            item['episode']            = itemdata['episode']
            item['title']              = itemdata['title']
            item['tvshow_title']       = itemdata['tvshow_title']
            item['file_original_path'] = itemdata['filepath']

        item['cachedir'] = os.path.join(__cache__, pu.get_cachedir_title(item['tvshow_title']),
            "{0}x{1}".format(item['season'], item['episode']))
        self.log.debug("Current show: {0}".format(item))
        return item

# end class ActionHandler

handler = ActionHandler(sys.argv)
handler.do()

xbmcplugin.endOfDirectory(handler.handle)
