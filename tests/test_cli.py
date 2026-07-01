from __future__ import annotations

import unittest

import requests

from ai_docs_scraper.cli import (
    MAX_PAGE_BYTES,
    PageResult,
    ScrapeError,
    default_base_url,
    discover_crawl,
    extract_markdown_links,
    fetch,
    host_resolves_to_private_network,
    is_expected_content_type,
    is_in_scope,
    render_index_markdown,
    slug_for_url,
)


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        url: str,
        body: bytes = b"",
        headers: dict[str, str] | None = None,
        raises_http_error: bool = False,
    ) -> None:
        self.status_code = status_code
        self.url = url
        self.headers = headers or {}
        self.encoding: str | None = "utf-8"
        self.closed = False
        self._body = body
        self._raises_http_error = raises_http_error

    @property
    def apparent_encoding(self) -> str:
        if self.closed:
            raise RuntimeError("The content for this response was already consumed")
        return "utf-8"

    def iter_content(self, chunk_size: int = 65536):
        for index in range(0, len(self._body), chunk_size):
            yield self._body[index : index + chunk_size]

    def raise_for_status(self) -> None:
        if self._raises_http_error:
            raise requests.HTTPError(f"HTTP {self.status_code}")
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def close(self) -> None:
        self.closed = True


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def get(self, url: str, **kwargs):
        self.calls.append(url)
        return self.responses.pop(0)


class CliSecurityTests(unittest.TestCase):
    def test_redirect_to_private_host_is_blocked(self) -> None:
        session = FakeSession(
            [
                FakeResponse(
                    302,
                    "https://docs.example.com/start",
                    headers={"Location": "http://127.0.0.1:3000/private"},
                )
            ]
        )

        with self.assertRaises(ScrapeError):
            fetch(session, "https://docs.example.com/start", 1, False, MAX_PAGE_BYTES, "html")

    def test_redirect_to_non_http_url_is_scrape_error(self) -> None:
        session = FakeSession(
            [
                FakeResponse(
                    302,
                    "https://docs.example.com/start",
                    headers={"Location": "file:///etc/passwd"},
                )
            ]
        )

        with self.assertRaises(ScrapeError):
            fetch(session, "https://docs.example.com/start", 1, False, MAX_PAGE_BYTES, "html")

    def test_fetch_does_not_use_apparent_encoding_after_stream_is_consumed(self) -> None:
        response = FakeResponse(
            200,
            "https://docs.example.com/no-charset",
            body="<html><h1>Hello</h1></html>".encode("utf-8"),
            headers={"Content-Type": "text/html"},
        )
        response.encoding = None
        session = FakeSession([response])

        result = fetch(session, "https://docs.example.com/no-charset", 1, False, MAX_PAGE_BYTES, "html")

        self.assertIn("Hello", result.text)

    def test_fetch_falls_back_to_utf8_on_unknown_charset(self) -> None:
        response = FakeResponse(
            200,
            "https://docs.example.com/legacy",
            body="<html><h1>Hello</h1></html>".encode("utf-8"),
            headers={"Content-Type": "text/html; charset=x-unknown-legacy"},
        )
        response.encoding = None
        session = FakeSession([response])

        result = fetch(session, "https://docs.example.com/legacy", 1, False, MAX_PAGE_BYTES, "html")

        self.assertIn("Hello", result.text)

    def test_http_error_closes_response(self) -> None:
        response = FakeResponse(
            404,
            "https://docs.example.com/missing",
            headers={"Content-Type": "text/html"},
            raises_http_error=True,
        )
        session = FakeSession([response])

        with self.assertRaises(requests.HTTPError):
            fetch(session, "https://docs.example.com/missing", 1, False, MAX_PAGE_BYTES, "html")
        self.assertTrue(response.closed)

    def test_response_size_limit_is_enforced(self) -> None:
        session = FakeSession(
            [
                FakeResponse(
                    200,
                    "https://docs.example.com/huge",
                    body=b"x" * 11,
                    headers={"Content-Type": "text/html"},
                )
            ]
        )

        with self.assertRaises(ScrapeError):
            fetch(session, "https://docs.example.com/huge", 1, False, 10, "html")

    def test_content_type_filter_rejects_binary(self) -> None:
        session = FakeSession(
            [
                FakeResponse(
                    200,
                    "https://docs.example.com/file.zip",
                    body=b"PK",
                    headers={"Content-Type": "application/zip"},
                )
            ]
        )

        with self.assertRaises(ScrapeError):
            fetch(session, "https://docs.example.com/file.zip", 1, False, MAX_PAGE_BYTES, "html")

    def test_private_hosts_are_detected(self) -> None:
        self.assertTrue(host_resolves_to_private_network("localhost"))
        self.assertTrue(host_resolves_to_private_network("127.0.0.1"))

    def test_crawl_does_not_return_failed_pages(self) -> None:
        session = FakeSession(
            [
                FakeResponse(
                    200,
                    "https://docs.example.com/good",
                    body=b"<html><a href='/bad'>Bad</a></html>",
                    headers={"Content-Type": "text/html"},
                ),
                FakeResponse(
                    500,
                    "https://docs.example.com/bad",
                    headers={"Content-Type": "text/html"},
                    raises_http_error=True,
                ),
            ]
        )

        urls = discover_crawl(
            session,
            "https://docs.example.com/good",
            "https://docs.example.com",
            1,
            10,
            False,
            {},
        )

        self.assertEqual(urls, ["https://docs.example.com/good"])


class CliParsingTests(unittest.TestCase):
    def test_default_base_url_for_llms_txt(self) -> None:
        self.assertEqual(default_base_url("https://example.com/llms.txt"), "https://example.com")
        self.assertEqual(default_base_url("https://example.com/docs/llms.txt"), "https://example.com/docs")
        self.assertEqual(default_base_url("https://example.com/foollms.txt"), "https://example.com/foollms.txt")

    def test_markdown_links_with_titles(self) -> None:
        text = '[API](https://example.com/api "API docs") and [Guide](<guide page.html>)'
        self.assertEqual(
            extract_markdown_links(text, "https://example.com/docs/"),
            ["https://example.com/api", "https://example.com/docs/guide page.html"],
        )

    def test_scope_prefix_is_path_aware(self) -> None:
        self.assertTrue(is_in_scope("https://example.com/docs/a", "https://example.com/docs"))
        self.assertFalse(is_in_scope("https://example.com/docs-v2/a", "https://example.com/docs"))

    def test_slug_has_markdown_extension(self) -> None:
        self.assertTrue(slug_for_url("https://example.com/docs/a?b=c").endswith(".md"))

    def test_content_type_helpers(self) -> None:
        self.assertTrue(is_expected_content_type("text/html; charset=utf-8", "html"))
        self.assertTrue(is_expected_content_type("application/sitemap+xml", "xml"))
        self.assertFalse(is_expected_content_type("application/pdf", "html"))

    def test_render_index_markdown_lists_pages_with_frontmatter(self) -> None:
        results = [
            PageResult(url="https://example.com/a", title="A", path="pages/a.md"),
            PageResult(url="https://example.com/b", title="B", path="pages/b.md"),
        ]
        rendered = render_index_markdown(results, "2026-07-01T00:00:00+00:00")
        self.assertTrue(rendered.startswith("---\ntype: index\n"))
        self.assertIn("page_count: 2", rendered)
        self.assertIn("[A](pages/a.md) — https://example.com/a", rendered)
        self.assertIn("[B](pages/b.md) — https://example.com/b", rendered)

    def test_render_index_markdown_handles_no_pages(self) -> None:
        rendered = render_index_markdown([], "2026-07-01T00:00:00+00:00")
        self.assertIn("page_count: 0", rendered)

    def test_render_index_markdown_escapes_brackets_in_title(self) -> None:
        results = [PageResult(url="https://example.com/a", title="list[str] Reference", path="pages/a.md")]
        rendered = render_index_markdown(results, "2026-07-01T00:00:00+00:00")
        self.assertIn("[list\\[str\\] Reference](pages/a.md)", rendered)


if __name__ == "__main__":
    unittest.main()
