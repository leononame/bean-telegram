import subprocess
from os import path

from webdav3.client import Client


class Sync(object):
    """Sync is the class that syncs our beancount structure with some server. This is
    used as an abstract base class does not synchronize anything.

    Attributes:
        path (:obj:`str`):  The local directory path to synchronize.
    """

    def __init__(self, path: str):
        self.os_path = path

    def pull(self):
        """Download updated directory from server."""
        return

    def push(self, fname: str, msg=""):
        """Upload a file to the server. If the directory or file does not exist
        on the remote server, crete it.

        Args:
            fname (:obj:`str`): File to upload.
            msg (:obj:`str`, optional): A message. When using git, this will be used as commit message."""
        return


class DavSync(Sync):
    """DavSync synchronizes the changes with a webdav server.

    Attributes:
        path (:obj:`str`): The local directory path to synchronize.
        dav_path (:obj:`str`): The remote directory path which corresponds to the local one.
        dav_root (:obj:`str`): The path to access the dav server. Nextcloud, e.g., uses /remote.php/webdav/
        username (:obj:`str`): Webdav username.
        password (:obj:`str`): Webdav password.
        hostname (:obj:`str`): Webdav server host, e.g. https://cloud.example.com/
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
        """Download updated directory from server."""
        self.client.download_sync(self.dav_path, self.os_path)

    def push(self, fname, msg=""):
        """Upload a file to the server. If the directory or file does not exist
        on the remote server, create it.

        Args:
            fname (:obj:`str`): File to upload.
            msg (:obj:`str`, optional): Not used with DavSync.
        """
        self.client.upload_file(
            path.join(self.dav_path, fname), path.join(self.os_path, fname)
        )


class GitSync(Sync):
    """GitSync synchronizes the changes with a git server."""

    def __init__(
        self,
        path: str,
    ):
        super().__init__(path)
        self.path = path

    def pull(self):
        """Download updated directory from server."""
        subprocess.run(["git", "reset", "--hard"], cwd=self.os_path, check=True)
        subprocess.run(["git", "clean", "-fd"], cwd=self.os_path, check=True)
        subprocess.run(["git", "pull"], cwd=self.os_path, check=True)

    def push(self, fname, msg=""):
        """Upload a file to the server. If the directory or file does not exist
        on the remote server, create it.

        Args:
            fname (:obj:`str`): File to upload.
            msg (:obj:`str`, optional): Not used with DavSync.
        """
        if msg == "":
            msg = "bot"
        print("comitting")
        subprocess.run(
            ["git", "commit", "--author", "beanbot <beanbot@lho.io>", "-am", msg],
            cwd=self.os_path,
            check=True,
        )
        print("committed")
        subprocess.run(["git", "push"], cwd=self.os_path, check=True)
