from __future__ import annotations

import asyncio
import csv
import dataclasses
import sys
import time
import xml.parsers.expat
from decimal import Decimal
from http import HTTPStatus
from random import randint
from textwrap import dedent
from typing import TYPE_CHECKING

import aiofiles
from aiohttp import BasicAuth, ClientSession, ClientTimeout
from aiohttp.client_exceptions import (
    ClientConnectorError,
    ServerConnectionError,
    ServerTimeoutError,
)
from defusedxml import minidom
from rich.console import Console
from rich.text import Text

from .datastructures import Options, Report, Response

if TYPE_CHECKING:
    from collections.abc import Iterable

    from aiohttp import ClientResponse


class PageFetcher:
    console: Console
    headers: dict[str, str]
    options: Options
    report: Report
    semaphore: asyncio.Semaphore
    timeout: ClientTimeout

    auth: BasicAuth | None = None
    sitemap_counter: int = 0

    def __init__(self, options: Options) -> None:
        self.options = options
        self.timeout = ClientTimeout(options.request_timeout)
        self.semaphore = asyncio.Semaphore(options.concurrency_limit)

        # Default headers for all requests
        self.headers = {"User-Agent": options.user_agent}

        if options.basic_auth:
            login, password = options.basic_auth.split(":", 1)
            self.auth = BasicAuth(login, password=password, encoding="latin1")

        # Initialize the report
        self.report = Report(
            sitemap_url=options.sitemap_url,
            concurrency_limit=options.concurrency_limit,
            limit=options.limit,
        )

    async def run(self) -> None:
        """
        Fetch the given sitemap, extract all URLs and then call each URL individually.
        """
        self.console = Console()

        async with ClientSession(
            auth=self.auth,
            timeout=self.timeout,
            headers=self.headers,
        ) as session:
            sitemap_urls = list(
                set(await self.get_sitemap_urls(session, self.options.sitemap_url))
            )

            if len(sitemap_urls) == 0:
                self.error("No URLs to fetch found.", exit_now=True)
            else:
                self.console.print(
                    f"\n💪 Found {len(sitemap_urls)} documents across "
                    f"{self.sitemap_counter} Sitemap files.\n"
                )

            # Only fetch a subset of urls if options.report.limit is set.
            # Can be useful for quick tests.
            sitemap_urls = sitemap_urls[slice(0, self.report.limit)]

            with self.console.status(
                "[bold green]Fetching documents...", spinner="dots2"
            ):
                start = time.time()
                self.report.responses = await asyncio.gather(
                    *[self.fetch(session, url) for url in sitemap_urls]
                )
                end = time.time()

        self.report.total_time = Decimal(end - start)
        self.write_report()
        self.show_report()

    async def get_sitemap_urls(  # noqa: C901 PLR0912 too complex
        self, session: ClientSession, sitemap_url: str
    ) -> Iterable[str]:
        """
        Get the main sitemap.xml file and extract all location url's of it.
        """
        urls = []

        self.console.print(f"🔬 Parsing {sitemap_url}")

        try:
            async with session.get(sitemap_url) as response:
                content = await response.content.read()

        # Connection issues on the server side (timeout, broken response)
        except (ServerTimeoutError, ServerConnectionError):
            self.error(f"Unable to fetch {sitemap_url}. Server Timeout.")
            return []

        # Connection issues on the client side (invalid URL)
        except ClientConnectorError:
            self.error(f"Unable to fetch {sitemap_url}. Connect call failed.")
            return []

        # Connection OK, but not authorized.
        if response.status == HTTPStatus.UNAUTHORIZED:
            self.error(
                f"Unable to fetch {sitemap_url}. "
                f"Authorization Error: {response.status}"
            )
            return []

        # Any other error response
        if response.status >= HTTPStatus.BAD_REQUEST:
            self.error(f"Unable to fetch {sitemap_url}. Error: {response.status}")
            return []

        # Parse XML
        try:
            document = minidom.parseString(content)
        except xml.parsers.expat.ExpatError as e:
            self.error(f"Unable to parse {sitemap_url}: {e}\n")
            return []

        # If this sitemap.xml contains links to other sitemap.xml,
        # recursively fetch them.
        if self.options.recursive and (
            other_sitemaps := document.getElementsByTagName("sitemap")
        ):
            for locs in (s.getElementsByTagName("loc") for s in other_sitemaps):
                for loc in locs:
                    other_sitemap_url = loc.firstChild.nodeValue
                    sub_urls = await self.get_sitemap_urls(session, other_sitemap_url)
                    urls += sub_urls

        if sitemap_urls := document.getElementsByTagName("url"):
            for locs in (s.getElementsByTagName("loc") for s in sitemap_urls):
                for loc in locs:
                    urls.append(loc.firstChild.nodeValue)

        self.sitemap_counter += 1

        return urls

    async def fetch(self, session: ClientSession, url: str) -> Response | None:
        """
        Fetch the given URL concurrently.
        """
        # Semaphor Boundary so we don't fetch all at once
        async with self.semaphore:
            # Append a random integer to each URL to bypass frontend cache.
            if self.options.random:
                rand = randint(  # noqa: S311
                    pow(10, self.options.random_length),
                    pow(10, self.options.random_length + 1),
                )
                sep = "&" if "?" in url else "?"
                url = f"{url}{sep}{rand}"

            client_response: ClientResponse | None
            start = time.time()

            try:
                async with session.get(url) as client_response:
                    response_time = Decimal(time.time() - start)
                    response = Response(
                        url=url,
                        status=client_response.status,
                        response_time=response_time,
                    )

                    # Store the content of each document in a local file
                    if client_response and self.options.output_dir:
                        content = await client_response.text()
                        await self.store_response(client_response, content)

            except TimeoutError:
                response = Response(url=url, status=408, response_time=Decimal(-1))

            self.console.print(
                response.info(slow_threshold=self.options.slow_threshold)
            )
            return response

    async def store_response(self, response: ClientResponse, content: str) -> None:
        """
        Store the response body of each URL in a file.
        This is similar to a webcrawler.

        :param response:  The client response object by aiohttp
        :param content: The text content of the current URL.
        :return: None
        """
        if response.url.path in ["/", ""]:
            path = "index"
        else:
            path = response.url.path.lstrip("/").rstrip("/")

        outdir = self.options.output_dir.expanduser().absolute()
        outfile = outdir / f"{path}.html"
        outfile.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(outfile, mode="w") as f:
            await f.write(content)

    def write_report(self) -> None:
        """
        Write the report to a CSV file.
        """
        if not self.options.report_path:
            return

        outfile = self.options.report_path.expanduser().absolute()
        outfile.parent.mkdir(parents=True, exist_ok=True)
        with outfile.open(
            "w",
            newline="",
        ) as csvfile:
            w = csv.writer(
                csvfile,
                delimiter=",",
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL,
            )
            w.writerow(["URL", "Status", "Response Time"])
            for r in self.report.responses:
                w.writerow(dataclasses.astuple(r))

    def show_report(self) -> None:
        """
        Display the report.
        """
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

        if failed_responses := self.report.get_failed_responses():
            self.console.print(
                ":cross_mark: Failed Responses:\n",
                style="bold underline",
                highlight=False,
                emoji=True,
            )
            for r in failed_responses:
                self.console.print(r.info(slow_threshold=self.options.slow_threshold))
            self.console.print("")

        # Only show a subset of slow responses if --slow-num is set
        # options.slow_num = -1 indicates "ALL"
        if self.options.slow_num == -1 or self.options.slow_num > 0:
            slow_responses = self.report.get_slow_responses(self.options.slow_threshold)
            slow_responses = slow_responses[: self.options.slow_num]

            if slow_responses:
                top = (
                    ""
                    if self.options.slow_num == -1
                    else f"Top {self.options.slow_num} "
                )
                self.console.print(
                    f":turtle: {top}Slow Responses:\n",
                    style="bold underline",
                    highlight=False,
                    emoji=True,
                )

                for r in slow_responses:
                    self.console.print(
                        r.info(slow_threshold=self.options.slow_threshold)
                    )
                self.console.print("")

        if self.options.report_path:
            self.console.print(
                f":bar_chart: Results are written to "
                f"[magenta underline]{self.options.report_path}[/]",
                emoji=True,
            )

        if self.options.output_dir:
            self.console.print(
                f":floppy_disk: Documents are stored in "
                f"[magenta underline]{self.options.output_dir}[/]",
                emoji=True,
            )

    def error(self, msg: str, exit_now: bool = False) -> None:
        """
        Display an error message and optionally exit the program.

        :param msg: The error message to display.
        :param exit_now: Whether to exit the program after displaying the error message.
                         Default is False.
        :return: None
        """
        sys.stderr.write(f"❌ {msg}\n")
        if exit_now:
            sys.exit(1)
