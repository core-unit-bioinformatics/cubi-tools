
import dataclasses as dcl
import typing

import cubitools.commons.sanitizers as sanitizers


@dcl.dataclass(frozen=True)
class GitConfigPreset:
    name: str
    remotes: list[str]
    remote_handles: list[str]
    local_user: str

    @classmethod
    def get_user_queries(cls):
        opening = (
            "Please provide the following information "
            "to configure a new git preset:"
        )
        questions = [
            (
                "Name of the git preset (allowed: a-z and '-'):",
                sanitizers.LiteralSanitizer("^[a-z\\-]+$"),
                "name"
            ),
            (
                "Comma-separated list of git remote names:",
                sanitizers.CommaListSanitizer("^[a-z]$"),
                "remotes"
            ),
            (
                "Comma-separated list of git handles for remotes:",
                sanitizers.CommaListSanitizer("^[a-zA-Z0-9\\-]$"),
                "remote_handles"
            ),
            (
                "Git handle of local user:",
                sanitizers.LiteralSanitizer("^[a-zA-Z0-9\\-]$"),
                "local_user"
            )
        ]
        return opening, questions


@dcl.dataclass(frozen=True)
class GitConfigRemote:
    name: str
    server: str
    priority: int = 0 | 1

    def __post_init__(self):
        if self.priority not in [0,1]:
            err_msg = (
                f"Invalid priority value: {self.priority} "
                "- Priority must be 0 or 1."
            )
            raise ValueError(err_msg)


@dcl.dataclass(frozen=True)
class GitConfigAccountOrg:
    handle: str
    remotes: list[str]
    category: typing.Literal["org"] = "org"


@dcl.dataclass(frozen=True)
class GitConfigAccountUser:
    handle: str
    name: str
    email: str
    remotes: list[str]
    category: typing.Literal["user"] = "user"
