from __future__ import annotations

import asyncio
import pathlib
from importlib import metadata
from typing import Any, Literal

import rich_click as click

from .datastructures import Options
from .fetch import PageFetcher

__version__ = metadata.version("fetch-sitemap")
__author__ = "Martin Mahner"

click.rich_click.USE_RICH_MARKUP = True


def validate_basic_auth(
    ctx: click.Context,  # noqa: ARG001: Unused argument
    param: click.ParamType,  # noqa: ARG001: Unused argument
    value: str | None,
) -> None:
    """
    Make sure, the basic auth information is either None or in the format string:string.
    """
    if value is None or len(value.split(":", 1)) == 2:  # noqa: PLR2004
        return

    msg = "Format must be '<username>:<password>'"
    raise click.BadParameter(msg)


class IntOrAll(click.ParamType):
    """
    A custom Click parameter type that accepts an integer
    or the specific string 'ALL'.
    """

    name = 'INTEGER or "ALL"'

    def convert(
        self,
        value: Any,
        param: click.ParamType,  # noqa: ARG002: Unused argument
        ctx: click.Context,  # noqa: ARG002: Unused argument
    ) -> int | Literal["ALL"]:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        if value == "ALL":
            return -1

        self.fail(f"{value} is not a positive integer or 'ALL'")  # noqa: RET503


@click.command(
    name="fetch-sitemap",
    context_settings={"show_default": True},
    no_args_is_help=True,
)
@click.argument("sitemap_url", type=str)
@click.option(
    "-a",
    "--basic-auth",
    type=str,
    required=False,
    envvar="BASIC_AUTH",
    help="Basic auth information. Format: 'username:password'",
    callback=validate_basic_auth,
)
@click.option(
    "-l",
    "--limit",
    type=int,
    default=None,
    envvar="LIMIT",
    help="Maximum number of URLs to fetch from the given sitemap.xml.",
)
@click.option(
    "--recursive/--no-recursive",
    type=bool,
    default=True,
    envvar="RECURSIVE",
    help="Recursively fetch all sitemap documents from the given sitemap.xml. ",
)
@click.option(
    "-c",
    "--concurrency-limit",
    type=int,
    default=5,
    envvar="CONCURRENCY_LIMIT",
    help="Max number of concurrent requests.",
)
@click.option(
    "-t",
    "--request-timeout",
    type=int,
    default=30,
    envvar="REQUEST_TIMEOUT",
    help="Timeout for fetching a URL in seconds.",
)
@click.option(
    "-r",
    "--random",
    is_flag=True,
    envvar="RANDOM_URL",
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
    envvar="REPORT_PATH",
    help="Store results in a CSV file. [dim]Example: ./report.csv[/]",
)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=pathlib.Path),
    required=False,
    envvar="OUTPUT_DIR",
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
    # param type is int or "ALL"
    "--slow-num",
    type=IntOrAll(),
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
    envvar="USER_AGENT",
    help="User-Agent string set in the HTTP header.",
)
@click.version_option(
    __version__,
    "--version",
    prog_name="fetch-version",
)
def main(**kwargs: Any) -> None:
    """
    Fetch a given sitemap and retrieve all URLs in it.
    """

    options = Options(**kwargs)

    try:
        f = PageFetcher(options=options)
        asyncio.run(f.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
