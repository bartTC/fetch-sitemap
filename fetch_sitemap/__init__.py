import argparse
import asyncio
import importlib.metadata
from pathlib import Path

from .fetch import PageFetcher

__version__ = importlib.metadata.version("fetch-sitemap")
__author__ = "Martin Mahner"


def main():
    parser = argparse.ArgumentParser(
        prog="fetch-sitemap",
        description="Fetch a given sitemap and retrieve all URLs in it.",
    )
    parser.add_argument("sitemap_url", help="URL of the sitemap to fetch")
    parser.add_argument(
        "--basic-auth",
        type=str,
        required=False,
        help="Basic auth information. Use: 'username:password'.",
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        required=False,
        default=None,
        help="Maximum number of URLs to fetch from the given sitemap.xml. Default: All",
    )
    parser.add_argument(
        "-c",
        "--concurrency-limit",
        type=int,
        required=False,
        default=10,
        help="Max number of concurrent requests. Default: 10",
    )
    parser.add_argument(
        "-t",
        "--request-timeout",
        type=int,
        required=False,
        default=30,
        help="Timeout for fetching a URL in seconds. Default: 30",
    )
    parser.add_argument(
        "--random",
        action="store_true",
        default=False,
        help="Append a random string like ?12334232343 to each URL to bypass frontend cache. Default: False",  # noqa
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        required=False,
        default=None,
        help="Store results in a CSV file. Example: ./report.csv",
    )
    args = parser.parse_args()

    try:
        f = PageFetcher(options=args)
        asyncio.run(f.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
