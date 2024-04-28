"""
Test Sitemap parsing.
"""

from __future__ import annotations

import csv
import pathlib
import re
import tempfile
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner, Result

from fetch_sitemap import main as fetch_sitemap

if TYPE_CHECKING:
    from pytest_httpserver import HTTPServer

    from tests.conftest import SitemapContentType


@pytest.fixture()
def _setup_foobar_sitemap(
    httpserver: HTTPServer, sitemap_content: SitemapContentType
) -> None:
    """
    Setup server response for sitemap_foobar.xml which has links to /foo and /bar.
    """
    # This regular sitemap has one link to /foo and /bar
    httpserver.expect_request("/sitemap_foobar.xml").respond_with_data(
        sitemap_content["sitemap_foobar"]
    )

    # Setup link responses
    httpserver.expect_request("/foo").respond_with_data("Foo")
    httpserver.expect_request("/bar").respond_with_data("Bar")


def call_runner(httpserver: HTTPServer, *args: Any) -> Result:
    """
    Call fetch_sitemap with the sitemap_foobar.xml.
    """
    runner_args = [httpserver.url_for("/sitemap_foobar.xml"), *args]

    runner = CliRunner()
    return runner.invoke(fetch_sitemap, runner_args)


# --------------------------------------------------------------------------------------


@pytest.mark.usefixtures("_setup_foobar_sitemap")
def test_sitemap_arguments(httpserver: HTTPServer) -> None:
    """
    Call fetch-sitemap with the sitemap_foobar.xml
    and make sure, both links were indexed.
    """
    result = call_runner(httpserver)
    assert result.exit_code == 0

    called_paths = [log[0].path for log in httpserver.log]
    assert "/foo" in called_paths
    assert "/bar" in called_paths


@pytest.mark.usefixtures("_setup_foobar_sitemap")
def test_limit(httpserver: HTTPServer) -> None:
    """
    Test --limit=1 argument.
    """
    result = call_runner(httpserver, "--limit", "1")
    assert result.exit_code == 0

    called_paths = [log[0].path for log in httpserver.log]

    # Either foo or bar has been called but not both. The actual order is somewhat
    # unknown, because it's called concurrently.
    assert len(called_paths) == 2  # sitemap_foobar.xml and either /foo or /bar
    assert ("/foo" in called_paths) ^ ("/bar" in called_paths)


@pytest.mark.usefixtures("_setup_foobar_sitemap")
@pytest.mark.parametrize(
    ("concurrency_limit", "success"),
    [
        (0, False),  # must be > 0
        (1, True),  # ok
        (100, True),  # ok
        ("foo", False),  # must be int
        ("", False),  # must not be empty
    ],
)
def test_concurrency_limit(
    httpserver: HTTPServer, concurrency_limit: int | str, success: bool
) -> None:
    """
    --concurrency-limit must be a positive integer.
    """
    result = call_runner(httpserver, "--concurrency-limit", concurrency_limit)

    # This parameter test was not successful.
    if not success:
        assert result.exit_code != 0
        return

    assert result.exit_code == 0
    assert len(httpserver.log) == 3  # sitemap_foobar.xml and /foo and /bar


@pytest.mark.usefixtures("_setup_foobar_sitemap")
@pytest.mark.parametrize(
    ("request_timeout", "success"),
    [
        (0, False),  # must be > 0
        (1, True),  # ok
        (100, True),  # ok
        ("foo", False),  # must be int
        ("", False),  # must not be empty
    ],
)
def test_request_timeout(
    httpserver: HTTPServer, request_timeout: int | str, success: bool
) -> None:
    """
    --concurrency-limit must be a positive integer.
    """
    result = call_runner(httpserver, "--request-timeout", request_timeout)

    # This parameter test was not successful.
    if not success:
        assert result.exit_code != 0
        return

    assert result.exit_code == 0
    assert len(httpserver.log) == 3  # sitemap_foobar.xml and /foo and /bar


@pytest.mark.usefixtures("_setup_foobar_sitemap")
def test_random(httpserver: HTTPServer) -> None:
    """
    --random is a flag that appends an integer to all requests.
    """
    result = call_runner(httpserver, "--random")

    # This parameter test was successful.
    assert result.exit_code == 0
    assert len(httpserver.log) == 3  # sitemap_foobar.xml and /foo and /bar

    # /foo and /bar were called with an integer appended. The default length is 15.
    assert int(httpserver.log[1][0].query_string) > pow(10, 14)
    assert int(httpserver.log[2][0].query_string) > pow(10, 14)


@pytest.mark.usefixtures("_setup_foobar_sitemap")
@pytest.mark.parametrize(
    ("random_length", "success"),
    [
        (0, False),  # must be > 0
        (1, True),  # ok
        (10, True),  # ok
        (101, False),  # must be <=100
        ("", False),  # must not be empty
        ("five", False),  # must not be a string
    ],
)
def test_random_length(
    httpserver: HTTPServer, random_length: int | str, success: bool
) -> None:
    """
    --random-length must be a positive integer.
    """
    result = call_runner(httpserver, "--random", "--random-length", random_length)

    # This parameter test was not successful.
    if not success:
        assert result.exit_code != 0
        return

    # This parameter test was successful.
    assert result.exit_code == 0
    assert len(httpserver.log) == 3  # sitemap_foobar.xml and /foo and /bar

    # /foo and /bar were called with a integer appended. The default length is 15.
    assert int(httpserver.log[1][0].query_string) > pow(10, random_length - 1)
    assert int(httpserver.log[2][0].query_string) > pow(10, random_length - 1)


@pytest.mark.usefixtures("_setup_foobar_sitemap")
def test_report_path(httpserver: HTTPServer) -> None:
    """
    Test --report-path argument and the validity of the CSV file.
    """
    # Create a temporary file we can write to
    t = tempfile.NamedTemporaryFile("w")

    result = call_runner(httpserver, "--report-path", t.name)

    # This parameter test was successful.
    assert result.exit_code == 0
    assert len(httpserver.log) == 3  # sitemap_foobar.xml and /foo and /bar

    # Test that the generated CSV is readable
    with pathlib.Path(t.name).open() as csv_file:
        csv_data = list(csv.reader(csv_file))

        # Either /foo or /bar is listed in line 2 and 3. Line 1 is the header.
        assert ("/foo" in csv_data[1][0]) ^ ("/bar" in csv_data[1][0])
        assert ("/foo" in csv_data[2][0]) ^ ("/bar" in csv_data[2][0])


@pytest.mark.usefixtures("_setup_foobar_sitemap")
def test_output_dir(httpserver: HTTPServer) -> None:
    """
    Test --output-dir and that /foo and /bar are written to the directory.
    """
    # Create a temporary file we can write to
    t = tempfile.TemporaryDirectory()

    result = call_runner(httpserver, "--output-dir", t.name)

    # This parameter test was successful.
    assert result.exit_code == 0
    assert len(httpserver.log) == 3  # sitemap_foobar.xml and /foo and /bar

    assert (pathlib.Path(t.name) / "foo.html").is_file()
    assert (pathlib.Path(t.name) / "bar.html").is_file()


@pytest.mark.usefixtures("_setup_foobar_sitemap")
@pytest.mark.parametrize(
    ("threshold", "success"),
    [
        (0, True),  # must be > 0
        (1, True),  # ok
        (1.0, True),  # floats are fine
        (123.4567890, True),  # high-precision floats are fine
        ("", False),  # must not be empty
        ("foo", False),  # must not be a string
    ],
)
def test_slow_threshold(
    httpserver: HTTPServer, threshold: float | str, success: bool
) -> None:
    """
    Test --slow-threshold values.
    """
    result = call_runner(httpserver, "--slow-threshold", threshold)

    # This parameter test was not successful.
    if not success:
        assert result.exit_code != 0
        return

    # This parameter test was successful.
    assert result.exit_code == 0
    assert len(httpserver.log) == 3  # sitemap_foobar.xml and /foo and /bar


@pytest.mark.usefixtures("_setup_foobar_sitemap")
@pytest.mark.parametrize(
    ("slow_num", "success"),
    [
        (0, False),  # must be > 0
        (1, True),  # ok
        ("1", True),  # strings with ints are fine
        (10, True),  # ok
        (10.10, False),  # must not be a float
        ("ALL", True),  # Uppercase ALL if ok
        ("all", False),  # but not lowercase
        ("", False),  # must not be empty
        ("foo", False),  # must not be a string
    ],
)
def test_slow_num(httpserver: HTTPServer, slow_num: float | str, success: bool) -> None:
    """
    Test --slow-num behavior
    """

    result = call_runner(httpserver, "--slow-threshold", 0, "--slow-num", slow_num)

    # This parameter test was not successful.
    if not success:
        assert result.exit_code != 0
        return

    # This parameter test was successful.
    assert result.exit_code == 0
    assert len(httpserver.log) == 3  # sitemap_foobar.xml and /foo and /bar


@pytest.mark.usefixtures("_setup_foobar_sitemap")
def test_slow_num_log(httpserver: HTTPServer) -> None:
    """
    Test --slow-num and that /foo and /bar are displayed twice, once in the log,
    once in the extra 'slow log'.
    """

    result = call_runner(httpserver, "--slow-threshold", 0)

    assert result.exit_code == 0
    assert len(httpserver.log) == 3  # sitemap_foobar.xml and /foo and /bar
    assert len(re.findall(r"/foo", result.output)) == 2
    assert len(re.findall(r"/bar", result.output)) == 2


@pytest.mark.usefixtures("_setup_foobar_sitemap")
def test_user_agent(httpserver: HTTPServer) -> None:
    """
    Test --user-agent is passed to the server.
    """
    result = call_runner(httpserver, "--user-agent", "pytest")

    # This parameter test was successful.
    assert result.exit_code == 0

    assert len(httpserver.log) == 3  # sitemap_foobar.xml and /foo and /bar
    for log in httpserver.log:
        assert log[0].headers["User-Agent"] == "pytest"


@pytest.mark.usefixtures("_setup_foobar_sitemap")
@pytest.mark.parametrize(
    ("credentials", "success"),
    [
        ("test:test", True),  # looks good
        ("test:test:test", True),  # looks good, password would be 'test:test'
        ("test", False),  # Just username
        ("", False),  # must not be empty
    ],
)
def test_basic_auth(httpserver: HTTPServer, credentials: str, success: bool) -> None:
    """
    Tes --slow-num and that /foo and /bar are displayed (twice) if they are treated slow
    """

    result = call_runner(httpserver, "--basic-auth", credentials)

    # This parameter test was not successful.
    if not success:
        assert result.exit_code != 0
        return

    # This parameter test was successful.
    assert result.exit_code == 0
    assert len(httpserver.log) == 3  # sitemap_foobar.xml and /foo and /bar
