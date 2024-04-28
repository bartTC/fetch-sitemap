from typing import TypedDict

import pytest
from pytest_httpserver import HTTPServer


class SitemapContentType(TypedDict):
    sitemap_index: str
    sitemap_foobar: str
    sitemap_baz: str


@pytest.fixture()
def sitemap_content(httpserver: HTTPServer) -> SitemapContentType:
    """
    Return content for sitemap test files.
    """

    # Index Sitemap that links to /sitemap_1.xml and sitemap_b.xml
    sitemap_index = f"""<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.google.com/schemas/sitemap/0.84">
        <sitemap>
            <loc>{httpserver.url_for('/sitemap_foobar.xml')}</loc>
        </sitemap>
        <sitemap>
            <loc>{httpserver.url_for('/sitemap_baz.xml')}</loc>
        </sitemap>
    </sitemapindex>
    """

    # Sitemap A that links to /foo
    sitemap_foobar = f"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
            xmlns:xhtml="http://www.w3.org/1999/xhtml">
        <url>
            <loc>{httpserver.url_for('/foo')}</loc>
        </url>
        <url>
            <loc>{httpserver.url_for('/bar')}</loc>
        </url>
    </urlset>
    """

    # Sitemap B that links to /bar
    sitemap_baz = f"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
            xmlns:xhtml="http://www.w3.org/1999/xhtml">
        <url>
            <loc>{httpserver.url_for('/baz')}</loc>
        </url>
    </urlset>
    """

    return {
        "sitemap_index": sitemap_index,
        "sitemap_foobar": sitemap_foobar,
        "sitemap_baz": sitemap_baz,
    }
