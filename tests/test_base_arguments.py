"""
Test arguments which don't require an actual sitemap file.
"""

from click.testing import CliRunner

from fetch_sitemap import main as fetch_sitemap


def test_no_arguments() -> None:
    """Calling the tool with no arguments does not error and displays the help text."""
    runner = CliRunner()
    result = runner.invoke(fetch_sitemap)
    assert result.exit_code == 0
    assert "Usage: fetch-sitemap [OPTIONS] SITEMAP_URL" in result.output


def test_help_argument() -> None:
    """Calling the tool with --help"""
    runner = CliRunner()
    result = runner.invoke(fetch_sitemap, "--help")
    assert result.exit_code == 0
    assert "Usage: fetch-sitemap [OPTIONS] SITEMAP_URL" in result.output


def test_version_argument() -> None:
    """Calling the tool with --version"""
    runner = CliRunner()
    result = runner.invoke(fetch_sitemap, "--version")
    assert result.exit_code == 0
    assert "fetch-sitemap, version" in result.output
    assert "Usage: fetch-sitemap [OPTIONS] SITEMAP_URL" not in result.output
