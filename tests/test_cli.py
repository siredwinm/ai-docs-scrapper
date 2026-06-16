from __future__ import annotations

import unittest

from ai_docs_scraper.cli import (
    MAX_PAGE_BYTES,
    ScrapeError,
    default_base_url,
    extract_markdown_links,
    fetch,
    host_resolves_to_private_network,
    is_expected_content_type,
    is_in_scope,
    slug_for_url,
)


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        url: str,
        body: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.url = url
        self.headers = headers or {}
        self.encoding: str | None = "utf-8"
        self.closed = False
        self._body = body

    @property
    def apparent_encoding(self) -> str:
        if self.closed:
            raise RuntimeError("The content for this response was already consumed")
        return "utf-8"

    def iter_content(self, chunk_size: int = 65536):
        for index in range(0, len(self._body), chunk_size):
            yield self._body[index : index + chunk_size]

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

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


if __name__ == "__main__":
    unittest.main()
