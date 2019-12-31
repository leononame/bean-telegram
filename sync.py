import subprocess
from os import path

from webdav3.client import Client

import config


class Sync(object):
    """Sync is the class that syncs our beancount structure with some server. This is 
    used as an abstract base class and should be overwritten.
    """

    def __init__(self, path: str):
        self.os_path = path

    def pull(self):
        return

    def push(self, fname: str):
        return


class GitSync(Sync):
    """GitSync synchronizes the changes with a git server.
    """

    def __init__(self, path: str):
        super().__init__(path)

    def pull(self):
        # We expect git to be installed and pull to pull wherever you want to pull from
        subprocess.run(
            ["git", "pull"], cwd=self.os_path, check=True, capture_output=True
        )

    def push(self, fname, msg=""):
        subprocess.run(
            ["git", "add", fname], cwd=self.os_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", msg if msg else "Automatic commit"],
            cwd=self.os_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push"], cwd=self.os_path, check=True, capture_output=True
        )
        pass


class DavSync(Sync):
    """DavSync synchronizes the changes with a webdav server.
    """

    def __init__(
        self,
        path: str,
        dav_path: str,
        dav_root: str,
        username: str,
        password: str,
        hostname: str,
    ):
        super().__init__(path)
        self.dav_path = dav_path
        self.username = username
        self.password = password
        self.hostname = hostname
        options = {
            "webdav_hostname": hostname,
            "webdav_login": username,
            "webdav_password": password,
            "root": dav_root,
        }
        self.client = Client(options)
        self.pull()

    def pull(self):
        self.client.download_sync(self.dav_path, self.os_path)

    def push(self, fname, msg=""):
        self.client.upload_file(
            path.join(self.dav_path, fname), path.join(self.os_path, fname)
        )
