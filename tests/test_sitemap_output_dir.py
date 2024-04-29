"""
Test --output-dir option.
"""

from __future__ import annotations

import pathlib
import tempfile
from http import HTTPStatus
from typing import TYPE_CHECKING

from click.testing import CliRunner

from fetch_sitemap import main as fetch_sitemap

if TYPE_CHECKING:
    from pytest_httpserver import HTTPServer


def test_output_dir(httpserver: HTTPServer) -> None:
    """
    Test --output-dir and that all URLs from the sitemap are correctly stored on disk.
    """
    # Create a temporary file we can write to
    t = tempfile.TemporaryDirectory()

    # A sitemap with multiple urls
    httpserver.expect_request("/sitemap.xml").respond_with_data(
        f"""<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
                xmlns:xhtml="http://www.w3.org/1999/xhtml">
            <url>
                <loc>{httpserver.url_for('/')}</loc>
            </url>
            <url>
                <loc>{httpserver.url_for('/a')}</loc>
            </url>
            <url>
                <loc>{httpserver.url_for('/a/b/c')}</loc>
            </url>
            <url>
                <loc>{httpserver.url_for('/404')}</loc>
            </url>
            <url>
                <loc>{httpserver.url_for('/500')}</loc>
            </url>
        </urlset>
        """
    )

    # Setup link responses
    httpserver.expect_request("/").respond_with_data("index")  # Index Document
    httpserver.expect_request("/a").respond_with_data("a")  # First Level
    httpserver.expect_request("/a/b/c").respond_with_data("c")  # Three levels
    httpserver.expect_request("/404").respond_with_data(
        "Not Found", status=HTTPStatus.NOT_FOUND
    )
    httpserver.expect_request("/500").respond_with_data(
        "Server Error", status=HTTPStatus.INTERNAL_SERVER_ERROR
    )

    runner_args = [httpserver.url_for("/sitemap.xml"), "--output-dir", t.name]

    runner = CliRunner()
    result = runner.invoke(fetch_sitemap, runner_args)
    # This parameter test was successful.
    assert result.exit_code == 0
    assert len(httpserver.log) == 6  # sitemap.xml and five urls in it

    # Regular 200 Responses are stored on disk.
    # Directories for slahes are automatically created.
    assert (pathlib.Path(t.name) / "index.html").is_file()
    assert (pathlib.Path(t.name) / "a.html").is_file()
    assert (pathlib.Path(t.name) / "a" / "b" / "c.html").is_file()

    # Error responses are also stored on disk
    assert (pathlib.Path(t.name) / "404.html").is_file()
    assert (pathlib.Path(t.name) / "500.html").is_file()
