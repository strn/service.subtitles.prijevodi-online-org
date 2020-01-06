# -*- coding: utf-8 -*-

# Wrapper class for dealing with archives
# The most important reason for this file:
# xbmcvfs does not support RAR5 format

import os
import platform
import sys
import zipfile
# Addon-specific module
import rarfile

# Custom exception, easy to catch
# all errors occuring in this class
class ArchiveException(Exception):
    pass


class Archive(object):

    UNRAR_DIR = 'unrar'

    def __init__(self, archive_path, resource_path):
        archive_suffix = archive_path.lower().split('.')[-1]
        self.resource_path = resource_path
        if archive_suffix in ('rar', 'zip',):
            self.suffix = archive_suffix
            self.archive_path = archive_path
        else:
            raise ArchiveException("Cannot handle archive '{0}'".format(archive))
        if self.suffix == 'zip':
            self.archive = zipfile.ZipFile(archive_path, 'r')
        else:
            self.archive = rarfile.RarFile(archive_path, 'r', errors='strict')
            # Determine path to "unrar" executable
            self._make_unrar_path()

    # List archive content
    # Return:
    #   list of archive files
    def list(self):
        return self.archive.namelist()

    # Extract files from archive
    def extract(self, member, destination):
        try:
            self.archive.extract(member, destination)
        except:
            e = sys.exc_info()[1]
            raise ArchiveException(e)

    def get_unrar_path(self):
        return rarfile.UNRAR_TOOL

    # Determines which UNRAR to use
    def _make_unrar_path(self):
        los, _, _, _, arch, _ = platform.uname()
        os_lower = los.lower()
        arch_lower = arch.lower()
        unrar_base_dir = os.path.join(self.resource_path, self.UNRAR_DIR)
        if os_lower.startswith('win'):
            path = os.path.join(unrar_base_dir, 'unrarw32.exe')
        elif os_lower.startswith('linux'):
            # Check architecture
            if arch_lower == 'x86_64':
                path = os.path.join(unrar_base_dir, 'unrar-x86_64')
            elif arch_lower.startswith('armv'):
                # Get ARM version
                arm_ver = arch_lower[4]
                if arm_ver == '4':
                    path = os.path.join(unrar_base_dir, 'unrar-armv4')
                else:
                    path = os.path.join(unrar_base_dir, 'unrar-armv5up')
            else:
                raise ArchiveException("UNRAR for Linux on arch '{0}' is not supported - yet".format(arch))
        else:
            raise ArchiveException("UNRAR for OS '{0}' and arch '{1}' is not supported - yet".format(los, arch))
        rarfile.UNRAR_TOOL = path
