# -*- coding: utf-8 -*-

# Wrapper class for dealing with archives
# The most important reason for this file:
# xbmcvfs in Kodi 18 does not support RAR5 format

import gzip
import json
import os
import platform
import shutil
import stat
import sys
import zipfile

import requests

# Addon-specific module
import rarfile


# Custom exception, easy to catch
# all errors occurring in this class
class ArchiveException(Exception):
    pass


class Archive(object):

    # Params:
    #  archive_path: Path to archive with subtitle
    #  res_data: Data to addon's resource data directory
    #  unrar_dir: Path to directory with UnRAR executable
    def __init__(self, archive_path, res_data):
        archive_suffix = archive_path.lower().split('.')[-1]
        self.resource_data = res_data
        self.unrar_dir = None
        self.temp_dir = None
        self.dialog = None
        self.str_get_unrar = None
        if archive_suffix in ('rar', 'zip',):
            self.suffix = archive_suffix
            self.archive_path = archive_path
        else:
            raise ArchiveException("Cannot handle archive '{0}'".format(archive_path))
        if self.suffix == 'zip':
            self.archive = zipfile.ZipFile(archive_path, 'r')
        else:
            self.archive = rarfile.RarFile(archive_path, 'r', errors='strict')
            # Load UnRAR executable map
            json_cfg = os.path.join(self.resource_data, "unrar.json")
            with open(json_cfg, 'r') as f:
                self.unrar = json.load(f)
                f.close()

    # List archive content
    # Return:
    #   list of archive files
    def list(self):
        return self.archive.namelist()

    # Extract files from archive
    def extract(self, member, destination):
        try:
            self.archive.extract(member, destination)
            self.archive.close()
        except:
            e = sys.exc_info()[1]
            raise ArchiveException(e)

    def get_dearchive_path(self):
        if self.suffix == 'zip':
            return 'zipfile module'
        else:
            return rarfile.UNRAR_TOOL

    # Assists with debugging and
    # new platform introduction
    @staticmethod
    def get_platform_info():
        los, _, _, _, arch, _ = platform.uname()
        os_lower = los.lower()
        arch_lower = arch.lower()
        return os_lower, arch_lower,

    # Get unrar executable for specific OS and architecture
    # Addons cannot ship precompiled binaries
    def check_unrar_exe(self):
       if self.suffix != 'rar':
            return "Archive not RAR"
        los, arch = self.get_platform_info()
        if los == 'windows':
            pass
        elif los == 'linux':
            if arch.startswith('armv'):
                # Get ARM version
                arm_ver = arch[4]
                if arm_ver == '4':
                    arch = 'armv4'
                else:
                    arch = 'armv5up'
            elif arch == 'x86_64':
                pass
            else:
                raise ArchiveException("UNRAR for Linux on arch '{0}' is not supported - yet".format(arch))
        else:
            raise ArchiveException("UNRAR for OS '{0}' and arch '{1}' is not supported - yet".format(los, arch))
        unrar_key = "{0}_{1}".format(los, arch)
        unrar_exe_path = os.path.join(self.unrar_dir, self.unrar["exe"][unrar_key]["destination"])
        if not os.path.exists(unrar_exe_path):
            unrar_exe_path = self._fetch_unrar_exe(unrar_key)
            fetched = True
        else:
            fetched = False
        rarfile.UNRAR_TOOL = unrar_exe_path
        if fetched:
            return "Fetched UnRAR executable from '{0}' to '{1}'".format(
                self.unrar["exe"][unrar_key]["source"], unrar_exe_path)
        else:
            return "Using existing UnRAR executable '{0}'".format(unrar_exe_path)

    def remove(self):
        os.remove(self.archive_path)

    # Fetches UnRAR executable from RarLAB site
    def _fetch_unrar_exe(self, unrar_key):
        if not self.dialog:
            raise ArchiveException("Progress dialog is not initialized!")
        if not self.str_get_unrar:
            raise ArchiveException("Progress dialog string is not initialized!")
        unrar_url = "{0}{1}".format(self.unrar["home"], self.unrar["exe"][unrar_key]["source"])
        self.dialog.create(self.str_get_unrar, unrar_url)
        self.dialog.update(50)
        sess = requests.Session()
        r = sess.get(
            url=unrar_url,
            allow_redirects=True)
        r.raise_for_status()
        self.dialog.update(75)
        unrar_source = os.path.join(self.temp_dir, self.unrar["exe"][unrar_key]["source"])
        with open(unrar_source, 'wb') as f:
            f.write(r.content)
            f.close()
        r.close()
        self.dialog.update(100)
        self.dialog.close()
        compressed = self.unrar["exe"][unrar_key]["compressed"]
        if compressed != "":
            unrar_source = self.extract_unrar_exe(unrar_source, compressed)
        unrar_dest = os.path.join(self.unrar_dir, self.unrar["exe"][unrar_key]["destination"])
        os.rename(unrar_source, unrar_dest)
        # Make executable really executable
        os.chmod(unrar_dest, stat.S_IRWXU)
        return unrar_dest

    # Extracts UnRAR executable if compressed
    @staticmethod
    def extract_unrar_exe(unrar_source, compressed):
        if compressed == "gz":
            unrar_exe = unrar_source.replace('.gz', '')
            with gzip.open(unrar_source, 'rb') as f_in, open(unrar_exe, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
                f_in.close()
                f_out.close()
        os.remove(unrar_source)
        return unrar_exe
