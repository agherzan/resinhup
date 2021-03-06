#!/usr/bin/env python

#
# ** License **
#
# Home: http://resin.io
#
# Author: Andrei Gherzan <andrei@resin.io>
#

import requests
import os
import tarfile
import logging
import shutil
from modules.util import *

log = logging.getLogger(__name__)

class tarFetcher:

    def __init__ (self, conffile):
        self.remote = getConfigurationItem(conffile, 'fetcher', 'remote')
        self.workspace = getConfigurationItem(conffile, 'fetcher', 'workspace')
        self.remotefile = self.remote + "/" + getConfigurationItem(conffile, 'fetcher', 'updatefilename')
        self.workspacefile = os.path.join(self.workspace, "update.tar")
        self.workspaceunpack = os.path.join(self.workspace, "update")
        self.bootfilesdir = os.path.join(self.workspace, "update/resin-boot")
        self.update_file_fingerprints = getConfigurationItem(conffile, 'fetcher', 'update_file_fingerprints').split()

    def cleanworkspace(self, remove_workdir=False):
        if os.path.isdir(self.workspace):
            shutil.rmtree(self.workspace)
        if not remove_workdir:
            os.makedirs(self.workspace)

    def cleanunpack(self, remove_unpackdir=False):
        if os.path.isdir(self.workspaceunpack):
            shutil.rmtree(self.workspaceunpack)
        if not remove_unpackdir:
            os.makedirs(self.workspaceunpack)

    def download(self):
        self.cleanworkspace()

        try:
            log.info("Download started... this can take a couple of minutes...")
            r = requests.get(self.remotefile, stream=True)
        except:
            log.error("Can't download update file.")
            return False

        if r.status_code != 200:
            log.error("HTTP status code: " + str(r.status_code))
            return False

        with open(self.workspacefile, 'wb') as fd:
            for chunk in r.iter_content(1000000):
                fd.write(chunk)

        return True

    def testUpdate(self):
        if not os.path.exists(self.workspacefile):
            log.error("No such file: " + self.workspacefile)
            return False
        if not tarfile.is_tarfile(self.workspacefile):
            log.error(self.workspacefile + " doesn't seem to be a tar archive.")
            return False

        update = tarfile.open(self.workspacefile)
        namelist = update.getnames()
        for entry in self.update_file_fingerprints:
            if not entry in namelist:
                update.close()
                log.warning("Check update file failed: " + entry)
                return False
        update.close()

        return True

    def unpack(self, downloadFirst=False):
        if downloadFirst:
            self.download()

        self.cleanunpack()

        if not self.testUpdate():
            log.error(self.workspacefile + " not an update file.")
            return False

        log.info("Unpack started... this can take a couple of seconds...")

        update = tarfile.open(self.workspacefile)
        update.extractall(self.workspaceunpack)

        # Save the rootfs filename of easy access
        rootfsfiles = os.listdir(self.workspace + "/update/resin-root")
        self.rootfsarchive = self.workspace + "/update/resin-root/" + os.listdir(self.workspace + "/update/resin-root")[0]

        log.debug("Unpacked " + self.workspacefile + " in " + self.workspaceunpack)
        return True

    def unpackRootfs(self, location):
        log.info("Unpack rootfs started... this can take a couple of seconds or even minutes...")
        update = tarfile.open(self.rootfsarchive)
        update.extractall(location)
        log.debug("Unpacked rootfs " + self.rootfsarchive + " in " + location)
        return True

    def getBootFiles(self):
        bootfiles = []
        if not os.path.isdir(self.bootfilesdir):
            log.warn(self.bootfilesdir + " does not exist.")
        for root, dirs, files in os.walk(self.bootfilesdir):
            for name in files:
                bootfiles.append(os.path.relpath(os.path.join(root, name), self.bootfilesdir))
        return bootfiles
