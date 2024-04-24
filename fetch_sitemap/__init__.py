from __future__ import annotations

import asyncio
from dataclasses import dataclass
from importlib import metadata
from typing import Any

import rich_click as click

__version__ = metadata.version("fetch-sitemap")
__author__ = "Martin Mahner"


@dataclass
class Options:
    sitemap_url: str
    basic_auth: str | None
    limit: int | None
    output_dir: str | None
    random: bool
    report_path: str | None
    concurrency_limit: int = 5
    request_timeout: int = 30


@click.command(
    name="fetch-sitemap", context_settings={"show_default": True}, no_args_is_help=True
)
@click.argument("sitemap_url", type=str)
@click.option(
    "--basic-auth",
    type=str,
    required=False,
    help="Basic auth information. Use: 'username:password'.",
)
@click.option(
    "-l",
    "--limit",
    type=int,
    default=None,
    help="Maximum number of URLs to fetch from the given sitemap.xml.",
)
@click.option(
    "-c",
    "--concurrency-limit",
    type=int,
    default=5,
    help="Max number of concurrent requests.",
)
@click.option(
    "-t",
    "--request-timeout",
    type=int,
    default=30,
    help="Timeout for fetching a URL in seconds.",
)
@click.option(
    "--random",
    is_flag=True,
    help=(
        "Append a random string like ?12334232343 to each URL to bypass frontend cache."
    ),
)
@click.option(
    "--report-path",
    type=click.Path(),
    required=False,
    help="Store results in a CSV file (example: ./report.csv).",
)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(),
    required=False,
    help="Store all fetched sitemap documents in this folder.",
)
@click.version_option(__version__, "-v", "--version")
def main(**kwargs: Any) -> None:
    """
    Fetch a given sitemap and retrieve all URLs in it.
    """

    options = Options(**kwargs)

    try:
        from .fetch import PageFetcher

        f = PageFetcher(options=options)
        asyncio.run(f.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
