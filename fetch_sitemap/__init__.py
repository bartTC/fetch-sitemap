import argparse
import asyncio
from importlib import metadata
from pathlib import Path

from .fetch import PageFetcher

__version__ = metadata.version("fetch-sitemap")
__author__ = "Martin Mahner"


def main() -> None:
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
        default=5,
        help="Max number of concurrent requests. Default: 5",
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
        help=(
            "Append a random string like ?12334232343 to each URL to bypass frontend "
            "cache. Default: False"
        ),
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        required=False,
        default=None,
        help="Store results in a CSV file. Example: ./report.csv",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        dest="output",
        type=Path,
        required=False,
        help="Store all fetched sitemap documents in this folder.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s v{__version__}",
    )
    args = parser.parse_args()

    try:
        f = PageFetcher(options=args)
        asyncio.run(f.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
