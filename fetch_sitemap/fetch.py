#!/usr/bin/env python

"""
usage: fetch-sitemap [-h] [--basic-auth BASIC_AUTH] [-l LIMIT] [-c CONCURRENCY_LIMIT] [-t REQUEST_TIMEOUT] [--report-path REPORT_PATH] sitemap_url

Fetch a given sitemap and retrieve all URLs in it.

positional arguments:
  sitemap_url           URL of the sitemap to fetch

options:
  -h, --help            show this help message and exit
  --basic-auth BASIC_AUTH
                        Basic auth information. Use: 'username:password'.
  -l LIMIT, --limit LIMIT
                        Max number of URLs to fetch from the given sitemap.xml. Default: All
  -c CONCURRENCY_LIMIT, --concurrency-limit CONCURRENCY_LIMIT
                        Max number of concurrent requests. Default: 10
  -t REQUEST_TIMEOUT, --request-timeout REQUEST_TIMEOUT
                        Timeout for fetching a URL. Default: 30
  --random              Append a random string like ?12334232343 to each URL to bypass frontend cache. Default: False
  --report-path REPORT_PATH
                        Store results in a CSV file. Example: ./report.csv
""" # noqa

from __future__ import annotations

import argparse
import asyncio
import csv
import dataclasses
import os
import re
import sys
import time
from decimal import Decimal
from random import randint
from textwrap import dedent
from typing import Iterable

try:
    from aiohttp import BasicAuth, ClientSession, ClientTimeout
    from rich.console import Console
    from rich.text import Text
except (ImportError, ModuleNotFoundError):
    sys.stderr.write("Some dependencies are missing. Run: pip install aiohttp rich")
    sys.exit(1)

LOG_ITEMS = re.compile(r"<loc>(.*?)</loc>")

# Defines what a 'slow' response time is
SLOW_THRESHOLD = int(os.getenv("SLOW_THRESHOLD", 5))

# How many 'slow' responses to show
SLOW_NUM = int(os.getenv("SLOW_NUM", 10))

# How long should the --random hash be?
RANDOM_LENGTH = int(os.getenv("RANDOM_LENGTH", 15))


@dataclasses.dataclass
class Response:
    url: str
    status: int
    response_time: Decimal

    @property
    def is_error(self):
        return self.status >= 400

    def info(self) -> str:
        if self.is_error:
            status = f"[bold red]{self.status}[/bold red]"
        else:
            status = f"[bold green]{self.status}[/bold green]"

        if self.status == 408:
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


async def gather_with_concurrency(n, *coroutines, **kwargs):
    semaphore = asyncio.Semaphore(n)

    async def sem_coro(coro):
        async with semaphore:
            return await coro

    return await asyncio.gather(*(sem_coro(c) for c in coroutines), **kwargs)


class PageFetcher:
    console: Console
    options: argparse.Namespace
    timeout: ClientTimeout
    report: Report
    auth: BasicAuth | None

    def __init__(self, options: argparse.Namespace):
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
                return_exceptions=True,
            )

        end = time.time()
        self.report.total_time = Decimal(end - start)
        self.show_statistics_report()

        if self.options.report_path:
            with open(self.options.report_path, "w", newline="") as csvfile:
                w = csv.writer(
                    csvfile, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
                )
                for r in self.report.responses:
                    w.writerow(dataclasses.astuple(r))

    async def get_sitemap_urls(self) -> re.findall:
        """
        Get the main sitemap.xml file and extract all location url's of it.
        """
        async with ClientSession(auth=self.auth, timeout=self.timeout) as session:
            async with session.get(self.options.sitemap_url) as response:
                content = await response.content.read()
                if response.status == 401:
                    sys.stderr.write(
                        "❌ Unable to fetch sitemap.xml file. Authorization error.\n\n"
                    )
                    sys.stderr.write(content.decode("utf-8"))
                    sys.exit(1)

                elif response.status >= 300:
                    sys.stderr.write(
                        f"❌ Unable to fetch sitemap.xml file. "
                        f"Error: {response.status}\n\n"
                    )
                    sys.stderr.write(content.decode("utf-8"))
                    sys.exit(1)

                sitemap_links = LOG_ITEMS.findall(content.decode("utf-8"))
                return sitemap_links

    async def fetch(self, session: ClientSession, url: str) -> Response:
        """
        Fetch the given URL concurrently.
        """
        # Appennd a random integer to each URL to bypass frontend cache.
        if self.options.random:
            rand = randint(pow(10, RANDOM_LENGTH), pow(10, RANDOM_LENGTH + 1))
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{rand}"

        start = time.time()
        try:
            async with session.get(url) as response:
                response_time = Decimal(time.time() - start)
                r = Response(
                    url=url, status=response.status, response_time=response_time
                )
                self.console.print(r.info())
                return r
        except TimeoutError:
            r = Response(url=url, status=408, response_time=Decimal(-1))
            self.console.print(r.info())
            return r

    def show_statistics_report(self):
        text = Text(
            dedent(
                f"""
                Sitemap ........: {self.report.sitemap_url}
                Limit ..........: {self.report.limit or "No limit"}
                Concurrent Limit: {self.report.concurrency_limit}
                Total Time .....: {self.report.total_time:.2f}s
                URLs fetched ...: {len(self.report.responses)}
                """
            )
        )
        self.console.print(text)

        failed_responses = list(self.report.get_failed_responses())
        if len(failed_responses) > 0:
            text = Text("❌ Failed Responses:\n", style="bold")
            self.console.print(text)
            for r in failed_responses:
                self.console.print(r.info())

        slow_responses = self.report.get_slow_responses()[:SLOW_NUM]
        if slow_responses:
            text = Text(f"🐢 Top {SLOW_NUM} Slow Responses:\n", style="bold")
            self.console.print(text)
            for r in slow_responses:
                self.console.print(r.info())
