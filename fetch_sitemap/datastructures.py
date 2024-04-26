from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from http import HTTPStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from fetch_sitemap import Options


@dataclass
class Options:
    """
    Program argument options for fetch_sitemap.
    """

    basic_auth: str | None
    concurrency_limit: int
    limit: int | None
    output_dir: Path | None
    random: bool
    random_length: int
    recursive: bool
    report_path: Path | None
    request_timeout: int
    sitemap_url: str
    slow_num: int  # -1 indicates 'all'
    slow_threshold: float
    user_agent: str


@dataclass(frozen=True)
class Response:
    """
    Response from a single URL.
    """

    url: str
    status: int
    response_time: Decimal  # -1 indicates a Timeout

    @property
    def is_error(self) -> bool:
        return self.status >= HTTPStatus.BAD_REQUEST

    def info(self, slow_threshold: float) -> str:
        if self.is_error:
            status = f"[bold red]{self.status}[/bold red]"
        else:
            status = f"[bold green]{self.status}[/bold green]"

        if self.status == HTTPStatus.REQUEST_TIMEOUT:
            response_time = "[bold magenta]Timeout[/bold magenta]"
        elif self.response_time > slow_threshold:
            response_time = f"[bold red]{self.response_time:.3f}s[/bold red]"
        else:
            response_time = f"[bold green]{self.response_time:.3f}s[/bold green]"

        return f"{status} {self.url} {response_time}"


@dataclass(init=True)
class Report:
    """
    Report of the sitemap fetch.
    """

    sitemap_url: str
    limit: int | None
    concurrency_limit: int
    total_time: Decimal = field(default=Decimal(0))
    responses: list[Response | Exception | None] = field(default_factory=list)

    def get_slow_responses(self, threshold: float) -> list[Response]:
        """Get the slowest responses."""
        slow = filter(lambda r: r.response_time > Decimal(threshold), self.responses)
        return sorted(slow, key=lambda r: r.response_time, reverse=True)

    def get_failed_responses(self) -> list[Response]:
        """Get the failed responses."""
        return list(
            filter(lambda r: isinstance(r, Exception) or r.is_error, self.responses)
        )
