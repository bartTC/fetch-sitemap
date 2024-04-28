"""
Test the various error responses of a URL a server could return.
For sitemaps itself, and the urls contained within a sitemap.
"""

from __future__ import annotations

from http import HTTPStatus
from time import sleep
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner, Result

from fetch_sitemap import main as fetch_sitemap

if TYPE_CHECKING:
    from pytest_httpserver import HTTPServer

    from tests.conftest import SitemapContentType


@pytest.fixture()
def _setup_baz_sitemap(
    httpserver: HTTPServer, sitemap_content: SitemapContentType
) -> None:
    """
    Setup server response for sitemap_baz.xml which has links to /baz.
    """
    # This regular sitemap has one link to /foo and /bar
    httpserver.expect_request("/sitemap_baz.xml").respond_with_data(
        sitemap_content["sitemap_baz"]
    )


def call_runner(httpserver: HTTPServer, *args: Any) -> Result:
    """
    Call fetch_sitemap with the sitemap_baz.xml.
    """
    runner_args = [httpserver.url_for("/sitemap_baz.xml"), *args]

    runner = CliRunner()
    return runner.invoke(fetch_sitemap, runner_args)


# Broken URL response tests ------------------------------------------------------------


@pytest.mark.usefixtures("_setup_baz_sitemap")
@pytest.mark.parametrize(
    "status",
    [
        HTTPStatus.BAD_GATEWAY,
        HTTPStatus.BAD_REQUEST,
        HTTPStatus.FORBIDDEN,
        HTTPStatus.IM_A_TEAPOT,
        HTTPStatus.NOT_FOUND,
        HTTPStatus.UNAUTHORIZED,
    ],
)
def test_error_response(httpserver: HTTPServer, status: HTTPStatus) -> None:
    """
    Any error response of a URL of a Sitemap will never break the tool.
    """
    httpserver.expect_request("/baz").respond_with_data("", status=status)

    result = call_runner(httpserver)
    assert result.exit_code == 0
    assert str(status) in result.output


@pytest.mark.usefixtures("_setup_baz_sitemap")
def test_timeout_response(httpserver: HTTPServer) -> None:
    """
    A timeout of an URL will not break the tool.
    """

    httpserver.expect_request("/baz").respond_with_handler(lambda request: sleep(2))

    result = call_runner(httpserver, "--request-timeout", "1")
    assert result.exit_code == 0
    assert str(HTTPStatus.REQUEST_TIMEOUT) in result.output


# Broken Sitemap tests -----------------------------------------------------------------


@pytest.mark.parametrize(
    "status",
    [
        HTTPStatus.BAD_GATEWAY,
        HTTPStatus.BAD_REQUEST,
        HTTPStatus.FORBIDDEN,
        HTTPStatus.IM_A_TEAPOT,
        HTTPStatus.NOT_FOUND,
        HTTPStatus.UNAUTHORIZED,
    ],
)
def test_sitemap_error_response(httpserver: HTTPServer, status: HTTPStatus) -> None:
    """
    The sitemap returns an Error code.
    """
    httpserver.expect_request("/sitemap_baz.xml").respond_with_data("", status=status)

    result = call_runner(httpserver)
    assert result.exit_code == 1
    assert str(status) in result.output


def test_unparsable_sitemap_xml(httpserver: HTTPServer) -> None:
    """
    A broken sitemap.xml will not break the tool. It will be noted that the XML is
    invalid and no urls were able to be fetched.
    """
    httpserver.expect_request("/sitemap_baz.xml").respond_with_data(
        "<?xml version='1.0' encoding='UTF-8'?>"
    )

    result = call_runner(httpserver)
    assert result.exit_code == 1
    assert "Unable to parse" in result.output


def test_notexisting_sitemap_xml() -> None:
    """
    Call a sitemap URL that doesn't exist will return a Connection Error.
    """
    # Call a random port to trigger connection error
    # https://pytest-httpserver.readthedocs.io/en/latest/howto.html#emulating-connection-refused-error
    runner = CliRunner()
    result = runner.invoke(fetch_sitemap, "http://localhost:12345/sitemap_baz.xml")

    assert result.exit_code == 1
    assert "Connect call failed." in result.output


@pytest.mark.parametrize(
    "sitemap_url",
    [
        "foo",  # not a URL
        "file:///tmp/foo",  # not a URL
        "/sitemap.xml",  # must be a fully qualified URL
    ],
)
def test_sitemap_must_be_url(sitemap_url: str) -> None:
    """Calling with an invalid sitemap URL doesn't just crash"""
    runner = CliRunner()
    result = runner.invoke(fetch_sitemap, sitemap_url)
    assert result.exit_code != 0
    assert "Invalid value for 'SITEMAP_URL'" in result.output
