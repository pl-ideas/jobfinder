"""Job source adapters."""

from jobfinder.sources.remotive import RemotiveSource
from jobfinder.sources.web_boards import (
    BuiltInSource,
    DiceSource,
    IndeedSource,
    LinkedInJobsSource,
    WellfoundSource,
)

__all__ = [
    "BuiltInSource",
    "DiceSource",
    "IndeedSource",
    "LinkedInJobsSource",
    "RemotiveSource",
    "WellfoundSource",
]
