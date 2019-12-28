import subprocess
import config


class Sync(object):
    """Sync is the class that syncs our beancount structure with some server. This is 
    used as an abstract base class and should be overwritten.
    """

    def __init__(self, path: str):
        self.os_path = path

    def pull(self):
        raise NotImplementedError("Not implemented")

    def push(self, fname: str):
        raise NotImplementedError("Not implemented")


class GitSync(Sync):
    """GitSync synchronizes the changes with a git server.
    """

    # TODO No output of git
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
