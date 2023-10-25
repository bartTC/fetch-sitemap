from __future__ import annotations

import asyncio
import csv
import dataclasses
import os
import pathlib
import re
import sys
import time
from decimal import Decimal
from http import HTTPStatus
from random import randint
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Awaitable, Iterable

from aiohttp import BasicAuth, ClientResponse, ClientSession, ClientTimeout
from rich.console import Console
from rich.text import Text

if TYPE_CHECKING:
    import argparse

LOG_ITEMS = re.compile(r"<loc>(.*?)</loc>")

# Defines what a 'slow' response time is
SLOW_THRESHOLD = int(os.getenv("SLOW_THRESHOLD", "5"))

# How many 'slow' responses to show
SLOW_NUM = int(os.getenv("SLOW_NUM", "10"))

# How long should the --random hash be?
RANDOM_LENGTH = int(os.getenv("RANDOM_LENGTH", "15"))


@dataclasses.dataclass
class Response:
    url: str
    status: int
    response_time: Decimal

    @property
    def is_error(self) -> bool:
        return self.status >= HTTPStatus.BAD_REQUEST

    def info(self) -> str:
        if self.is_error:
            status = f"[bold red]{self.status}[/bold red]"
        else:
            status = f"[bold green]{self.status}[/bold green]"

        if self.status == HTTPStatus.REQUEST_TIMEOUT:
            response_time = "[bold magenta]Timeout[/bold magenta]"
        elif self.response_time > SLOW_THRESHOLD:
            response_time = f"[bold red]{self.response_time:.3f}s[/bold red]"
        else:
            response_time = f"[bold green]{self.response_time:.3f}s[/bold green]"

        return f"{status} {self.url} {response_time}"


@dataclasses.dataclass
class Report:
    sitemap_url: str
    limit: int | None
    concurrency_limit: int
    total_time: Decimal = Decimal(0)
    responses: list[Response] | None = None

    def get_slow_responses(self) -> Iterable[Response]:
        return sorted(self.responses, key=lambda r: r.response_time, reverse=True)

    def get_failed_responses(self) -> Iterable[Response]:
        return filter(lambda r: isinstance(r, Exception) or r.is_error, self.responses)


async def gather_with_concurrency(
    n: int,
    *coroutines: Awaitable,
    **kwargs: Any,
) -> tuple[Any]:
    semaphore = asyncio.Semaphore(n)

    async def sem_coro(coro: Awaitable) -> Awaitable:
        async with semaphore:
            return await coro

    return await asyncio.gather(*(sem_coro(c) for c in coroutines), **kwargs)


class PageFetcher:
    console: Console
    options: argparse.Namespace
    timeout: ClientTimeout
    report: Report
    auth: BasicAuth | None
    output_dir: pathlib.Path

    def __init__(self, options: argparse.Namespace) -> None:
        self.options = options
        self.timeout = ClientTimeout(options.request_timeout)

        self.auth = None
        if options.basic_auth:
            login, password = str(options.basic_auth).split(":", 1)
            self.auth = BasicAuth(login, password=password, encoding="latin1")

        self.report = Report(
            sitemap_url=options.sitemap_url,
            concurrency_limit=options.concurrency_limit,
            limit=options.limit,
        )

    async def run(self) -> None:
        """
        Fetch the given sitemap, extract all URLs and then call each URL  individually.
        """
        self.console = Console()
        sitemap_urls = await self.get_sitemap_urls()

        if self.report.limit:
            sitemap_urls = sitemap_urls[: self.report.limit]

        start = time.time()
        async with ClientSession(auth=self.auth, timeout=self.timeout) as session:
            self.report.responses = await gather_with_concurrency(
                self.options.concurrency_limit,
                *[self.fetch(session, url) for url in sitemap_urls],
                return_exceptions=False,
            )

        end = time.time()
        self.report.total_time = Decimal(end - start)
        self.show_statistics_report()

        if self.options.report_path:
            with pathlib.Path(self.options.report_path).open(
                "w",
                newline="",
            ) as csvfile:
                w = csv.writer(
                    csvfile,
                    delimiter=",",
                    quotechar='"',
                    quoting=csv.QUOTE_MINIMAL,
                )
                for r in self.report.responses:
                    w.writerow(dataclasses.astuple(r))

    async def get_sitemap_urls(self) -> re.findall:
        """
        Get the main sitemap.xml file and extract all location url's of it.
        """
        async with (
            ClientSession(auth=self.auth, timeout=self.timeout) as session,
            session.get(self.options.sitemap_url) as response,
        ):
            content = await response.content.read()
            if response.status == HTTPStatus.UNAUTHORIZED:
                sys.stderr.write(
                    "❌ Unable to fetch sitemap.xml file. Authorization error.\n\n",
                )
                sys.stderr.write(content.decode("utf-8"))
                sys.exit(1)

            elif response.status >= HTTPStatus.MULTIPLE_CHOICES:
                sys.stderr.write(
                    f"❌ Unable to fetch sitemap.xml file. "
                    f"Error: {response.status}\n\n",
                )
                sys.stderr.write(content.decode("utf-8"))
                sys.exit(1)

            return LOG_ITEMS.findall(content.decode("utf-8"))

    async def fetch(self, session: ClientSession, url: str) -> Response | None:
        """
        Fetch the given URL concurrently.
        """
        # Append a random integer to each URL to bypass frontend cache.
        if self.options.random:
            rand = randint(  # noqa: S311
                pow(10, RANDOM_LENGTH),
                pow(10, RANDOM_LENGTH + 1),
            )
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{rand}"

        response: ClientResponse | None
        start = time.time()
        try:
            async with session.get(url) as response:
                response_time = Decimal(time.time() - start)
                content = await response.text()
                r = Response(
                    url=url,
                    status=response.status,
                    response_time=response_time,
                )
        except TimeoutError:
            response = None
            r = Response(url=url, status=408, response_time=Decimal(-1))

        # Store the content of each Sitemap document in a local file
        if self.options.output and response:
            if response.url.path in ["/", ""]:
                path = "index"
            else:
                path = response.url.path.lstrip("/").rstrip("/")

            outfile = (self.options.output / f"{path}.html").absolute()
            outfile.parent.mkdir(parents=True, exist_ok=True)
            with pathlib.Path(outfile).open("w") as f:
                f.write(content)

        self.console.print(r.info())
        return r

    def show_statistics_report(self) -> None:
        text = Text(
            dedent(
                f"""
                Sitemap ........: {self.report.sitemap_url}
                Limit ..........: {self.report.limit or "No limit"}
                Concurrent Limit: {self.report.concurrency_limit}
                Total Time .....: {self.report.total_time:.2f}s
                URLs fetched ...: {len(self.report.responses)}
                """,
            ),
        )
        self.console.print(text)

        failed_responses = list(self.report.get_failed_responses())
        if len(failed_responses) > 0:
            text = Text("❌ Failed Responses:\n", style="bold")
            self.console.print(text)
            for r in failed_responses:
                self.console.print(r.info())
            sys.stderr.write("\n")

        slow_responses = self.report.get_slow_responses()[:SLOW_NUM]
        if slow_responses:
            text = Text(f"🐢 Top {SLOW_NUM} Slow Responses:\n", style="bold")
            self.console.print(text)
            for r in slow_responses:
                self.console.print(r.info())
