import os

from dataclasses import dataclass
from string import Template


@dataclass
class Config:
    bean_append_file: str
    bean_file: str

    @classmethod
    def load(cls):
        """Load the configuration from environment variables."""
        c = cls(
            bean_append_file=os.environ.get("BEAN_APPEND_FILE"),
            bean_file=os.environ.get("BEAN_FILE"),
        )
        return c

    def check(self) -> str:
        """Check if the configuration is in a valid state.
        Returns an error string otherwise.
        """
        tpl = "Configuration error: {} is invalid. (value:{})"

        if self is None:
            return None
        if not self.bean_append_file:
            return tpl.format("BEAN_APPEND_FILE", self.bean_append_file)
        if not self.bean_file:
            return tpl.format("BEAN_FILE", self.bean_file)

        return None
