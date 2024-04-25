from __future__ import annotations

import asyncio
import csv
import dataclasses
import pathlib
import re
import sys
import time
import xml.parsers.expat
from decimal import Decimal
from http import HTTPStatus
from random import randint
from textwrap import dedent
from typing import TYPE_CHECKING

from aiohttp import BasicAuth, ClientResponse, ClientSession, ClientTimeout
from defusedxml import minidom
from rich.console import Console
from rich.text import Text

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fetch_sitemap import Options

LOG_ITEMS = re.compile(r"<loc>(.*?)</loc>")


@dataclasses.dataclass
class Response:
    url: str
    status: int
    response_time: Decimal

    @property
    def is_error(self) -> bool:
        return self.status >= HTTPStatus.BAD_REQUEST

    def info(self, options: Options) -> str:
        if self.is_error:
            status = f"[bold red]{self.status}[/bold red]"
        else:
            status = f"[bold green]{self.status}[/bold green]"

        if self.status == HTTPStatus.REQUEST_TIMEOUT:
            response_time = "[bold magenta]Timeout[/bold magenta]"
        elif self.response_time > options.slow_threshold:
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


class PageFetcher:
    console: Console
    options: Options
    timeout: ClientTimeout
    report: Report
    auth: BasicAuth | None
    output_dir: pathlib.Path
    semaphore: asyncio.Semaphore
    headers: dict[str, str]
    sitemap_counter: int = 0

    def __init__(self, options: Options) -> None:
        self.options = options
        self.timeout = ClientTimeout(options.request_timeout)
        self.semaphore = asyncio.Semaphore(options.concurrency_limit)

        if options.user_agent:
            self.headers = {"User-Agent": options.user_agent}

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
        Fetch the given sitemap, extract all URLs and then call each URL individually.
        """
        self.console = Console()

        async with ClientSession(
            auth=self.auth, timeout=self.timeout, headers=self.headers
        ) as session:
            sitemap_urls = list(
                set(await self.get_sitemap_urls(session, self.options.sitemap_url))
            )

            self.console.print(
                f"\n💪 Found {len(sitemap_urls)} documents across "
                f"{self.sitemap_counter} Sitemap files.\n"
            )

            if self.report.limit:
                sitemap_urls = sitemap_urls[: self.report.limit]

            start = time.time()
            self.report.responses = await asyncio.gather(
                *[self.fetch(session, url) for url in sitemap_urls]
            )

            end = time.time()
            self.report.total_time = Decimal(end - start)
            self.show_statistics_report()

            if self.options.report_path:
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

    async def get_sitemap_urls(
        self, session: ClientSession, sitemap_url: str
    ) -> Iterable[str]:
        """
        Get the main sitemap.xml file and extract all location url's of it.
        """
        urls = []

        self.console.print(f"🔬 Parsing {sitemap_url}")

        async with session.get(sitemap_url) as response:
            content = await response.content.read()

            if response.status == HTTPStatus.UNAUTHORIZED:
                sys.stderr.write(
                    f"❌  Unable to fetch {sitemap_url}. " f"Authorization error.\n",
                )
                return []

            if response.status >= HTTPStatus.MULTIPLE_CHOICES:
                sys.stderr.write(
                    f"❌  Unable to fetch {sitemap_url}. Error: {response.status}\n",
                )
                return []

            # Parse XML
            try:
                document = minidom.parseString(content)
            except xml.parsers.expat.ExpatError as e:
                sys.stderr.write(f"❌ Unable to parse {sitemap_url}: {e}\n")
                return []

            # If this sitemap.xml contains links to other sitemap.xml,
            # recursively fetch them.
            if self.options.recursive and (
                sitemaps := document.getElementsByTagName("sitemap")
            ):
                for locs in (s.getElementsByTagName("loc") for s in sitemaps):
                    for loc in locs:
                        sitemap_url = loc.firstChild.nodeValue
                        sub_urls = await self.get_sitemap_urls(session, sitemap_url)
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
            if response and self.options.output_dir:
                if response.url.path in ["/", ""]:
                    path = "index"
                else:
                    path = response.url.path.lstrip("/").rstrip("/")

                outdir = self.options.output_dir.expanduser().absolute()
                outfile = outdir / f"{path}.html"
                outfile.parent.mkdir(parents=True, exist_ok=True)
                with pathlib.Path(outfile).open("w") as f:  # noqa: ASYNC101
                    f.write(content)

            self.console.print(r.info(self.options))
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
            self.console.print(
                "❌ Failed Responses:\n",
                style="bold underline",
                highlight=False,
            )
            for r in failed_responses:
                self.console.print(r.info(self.options))
            sys.stderr.write("\n")

        slow_responses = self.report.get_slow_responses()[: self.options.slow_num]
        if slow_responses:
            self.console.print(
                f"🐢 Top {self.options.slow_num} Slow Responses:\n",
                style="bold underline",
                highlight=False,
            )
            for r in slow_responses:
                self.console.print(r.info(self.options))

        if self.options.report_path or self.options.output_dir:
            self.console.print("")

        if self.options.report_path:
            self.console.print(
                f" 📊 Results are written to "
                f"[magenta underline]{self.options.report_path}[/]"
            )

        if self.options.output_dir:
            self.console.print(
                f" 💾 Documents are stored in "
                f"[magenta underline]{self.options.output_dir}[/]"
            )
