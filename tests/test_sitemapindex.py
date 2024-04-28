"""
Test "Index Sitemaps" parsing.
"""

from click.testing import CliRunner
from pytest_httpserver import HTTPServer

from fetch_sitemap import main as fetch_sitemap
from tests.conftest import SitemapContentType


def test_indexsitemap(
    httpserver: HTTPServer, sitemap_content: SitemapContentType
) -> None:
    """
    This tests loads the sitemap_index.xml which itself has two sitemaps,
    sitemap_foo.xml and sitemap_bar.xml.

    The sitemap_foo.xml has one link to /foo, and the sitemap_bar.xml
    has one link to /bar. So eventually are two URLs fetched.
    """
    # Setup server response
    #
    # This base sitemap returns a link to sitemap_foo.xml and sitemap_bar.xml
    httpserver.expect_request("/sitemap.xml").respond_with_data(
        sitemap_content["sitemap_index"]
    )
    # This regular sitemap has one link to /foo and /bar
    httpserver.expect_request("/sitemap_foobar.xml").respond_with_data(
        sitemap_content["sitemap_foobar"]
    )
    # This regular sitemap has one link to /baz
    httpserver.expect_request("/sitemap_baz.xml").respond_with_data(
        sitemap_content["sitemap_baz"]
    )

    # Setup link responses
    httpserver.expect_request("/foo").respond_with_data("Foo")
    httpserver.expect_request("/bar").respond_with_data("Bar")
    httpserver.expect_request("/baz").respond_with_data("Bar")

    runner = CliRunner()
    result = runner.invoke(fetch_sitemap, httpserver.url_for("/sitemap.xml"))

    # The fetch_sitemap command did not fail
    assert result.exit_code == 0

    # Check, that all paths were called by the fetch_sitemap command
    called_paths = [log[0].path for log in httpserver.log]
    assert "/sitemap.xml" in called_paths
    assert "/sitemap_foobar.xml" in called_paths
    assert "/sitemap_baz.xml" in called_paths
    assert "/foo" in called_paths
    assert "/bar" in called_paths

    # /foo and /bar were called by the fetch_sitemap command
    # and they are listed in the output. The output looks like this:
    #
    # 200 http://localhost:63808/foo 0.005s
    # 200 http://localhost:63808/bar 0.006s
    # 200 http://localhost:63808/baz 0.006s
    assert "/foo" in result.output
    assert "/bar" in result.output
    assert "/baz" in result.output


def test_indexsitemap_norecursive(
    httpserver: HTTPServer, sitemap_content: SitemapContentType
) -> None:
    """
    Calling fetch-sitemap with --no-recursive does not
    fetch any of the linked sub sitemaps.
    """
    httpserver.expect_request("/sitemap.xml").respond_with_data(
        sitemap_content["sitemap_index"]
    )

    runner = CliRunner()
    result = runner.invoke(
        fetch_sitemap, [httpserver.url_for("/sitemap.xml"), "--no-recursive"]
    )

    # The fetch_sitemap command fail since it wasn't able to collect any links
    assert result.exit_code == 1

    # Only the sitemap.xml was called by the fetch_sitemap command
    assert len(httpserver.log) == 1
