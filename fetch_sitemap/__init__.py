from __future__ import annotations

import asyncio
import pathlib
from dataclasses import dataclass
from importlib import metadata
from typing import Any

import rich_click as click

__version__ = metadata.version("fetch-sitemap")
__author__ = "Martin Mahner"

click.rich_click.USE_RICH_MARKUP = True


@dataclass
class Options:
    basic_auth: str | None
    concurrency_limit: int
    limit: int | None
    output_dir: pathlib.Path | None
    random: bool
    random_length: int
    recursive: bool
    report_path: pathlib.Path | None
    request_timeout: int
    sitemap_url: str
    slow_num: int
    slow_threshold: float
    user_agent: str


@click.command(
    name="fetch-sitemap", context_settings={"show_default": True}, no_args_is_help=True
)
@click.argument("sitemap_url", type=str)
@click.option(
    "-a",
    "--basic-auth",
    type=str,
    required=False,
    help="Basic auth information. Format: 'username:password'",
)
@click.option(
    "-l",
    "--limit",
    type=int,
    default=None,
    help="Maximum number of URLs to fetch from the given sitemap.xml.",
)
@click.option(
    "--recursive/--no-recursive",
    type=bool,
    default=True,
    help="Recursively fetch all sitemap documents from the given sitemap.xml. ",
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
    "-r",
    "--random",
    is_flag=True,
    help=(
        "Append a random string like ?12334232343 to each URL to bypass frontend cache."
    ),
)
@click.option(
    "--random-length",
    type=int,
    default=15,
    envvar="RANDOM_LENGTH",
    help="Length of the --random hash.",
)
@click.option(
    "-p",
    "--report-path",
    type=click.Path(file_okay=True, dir_okay=False, path_type=pathlib.Path),
    required=False,
    help="Store results in a CSV file. [dim]Example: ./report.csv[/]",
)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=pathlib.Path),
    required=False,
    help=(
        "Store all fetched sitemap documents in this folder. "
        "[dim]Example: /tmp/my.domain.com/[/]"
    ),
)
@click.option(
    "--slow-threshold",
    type=float,
    required=False,
    default=5.0,
    envvar="SLOW_THRESHOLD",
    help="Responses slower than this (in seconds) are considered 'slow'.",
)
@click.option(
    "--slow-num",
    type=int,
    required=False,
    default=10,
    envvar="SLOW_NUM",
    help="How many 'slow' responses to show.",
)
@click.option(
    "--user-agent",
    type=str,
    required=False,
    default=f"Mozilla/5.0 (compatible; fetch-sitemap/{__version__})",
    help='User-Agent string set in the HTTP header. Pass "" to disable.',
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
