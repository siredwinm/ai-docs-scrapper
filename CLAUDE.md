# CLAUDE.md

Guidance for Claude Code when working *on* this repository (developing the
scraper itself). If you're using the scraper's *output* to build something
else, read [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md) instead.

## What this is

A single-file CLI (`src/ai_docs_scraper/cli.py`) that turns documentation
sites into Markdown for AI agent context. No API key, no external services —
`requests` + `BeautifulSoup` + `markdownify` + `defusedxml`.

## Commands

```bash
pip install -e .              # install in editable mode
pip install pytest
pytest tests/ -v               # run the test suite (all logic is covered here)
ai-docs-scraper <url> --out /tmp/scrape-test --allow-private-hosts  # manual smoke test
```

There is no linter/formatter configured. Match the existing style (no
type-annotation-only helper modules, no classes beyond the three dataclasses
and `ScrapeError`).

## Architecture

Everything lives in `cli.py`, roughly top to bottom:

1. **URL safety** — `require_safe_url` / `host_resolves_to_private_network` /
   `safe_url_error`. Two call sites: `validate_safe_url_or_raise_system_exit`
   (CLI-argument validation, fails the whole run) and
   `validate_safe_url_or_raise_scrape_error` (used inside `fetch`, so a
   single bad URL during discovery is skipped instead of killing the run).
2. **`fetch()`** — manual redirect loop (`allow_redirects=False`, each hop
   re-validated), streamed size limits (`read_limited_body`), `Content-Type`
   checks (`is_expected_content_type`), and encoding fallback
   (`decode_body`, `encoding_from_content_type`). Returns a `FetchResult`.
3. **Discovery** — `discover_llms` / `discover_sitemap` / `discover_crawl`
   each return a `list[str]` of in-scope URLs for their mode.
4. **Scraping** — `scrape_html` cleans a page and converts it to Markdown;
   `scrape_page` wraps it with a `fetch()` call.
5. **Output** — `write_outputs` writes `pages/*.md`, `index.md`
   (`render_index_markdown`), `index.json`, and `context.md`.

## Non-negotiable invariants

This tool's entire value proposition is "safe to point at arbitrary docs
URLs." When touching `fetch()` or anything upstream of it, preserve:

- **No SSRF**: every URL — including each redirect hop — goes through
  `require_safe_url`/`validate_safe_url_or_raise_*` before a request is made.
- **No unbounded downloads**: responses are streamed and capped
  (`MAX_PAGE_BYTES` / `MAX_XML_BYTES` / `MAX_TEXT_BYTES`), never loaded via
  `.text`/`.content` directly.
- **No crash-on-weird-server**: anything a hostile or misconfigured server
  can trigger (bad charset, wrong content-type, infinite redirects, oversized
  body) must raise `ScrapeError` or `requests.RequestException` — those are
  the only exception types the discovery/write loops catch. A different
  exception type escaping `fetch()` takes down the whole CLI run. (This bit
  us twice already — see `decode_body`'s `LookupError` fallback and the
  `apparent_encoding`-after-stream-close fix in git history.)
- **`context.md`/`pages/*.md` must keep `UNTRUSTED_DOCS_NOTICE`** — scraped
  content is adversarial input to whatever agent reads it next.

## Testing conventions

`tests/test_cli.py` uses hand-rolled `FakeResponse`/`FakeSession` fakes
(see top of the file) instead of mocking `requests` — reuse that pattern for
new `fetch()`-level tests. Pure functions (`slug_for_url`, `is_in_scope`,
`extract_markdown_links`, `render_index_markdown`, etc.) get direct unit
tests with no fakes needed. When you fix a bug that a real HTTP server would
trigger but a unit test wouldn't catch (encoding edge cases, redirect
handling), prefer reproducing it against a real `http.server` instance first
to confirm, then add the fast fake-based regression test.

## Docs to keep in sync

- `README.md` — options table must match `build_parser()`; output tree must
  match what `write_outputs` actually writes.
- `SECURITY.md` / `PROMPT_INJECTION.md` — update if the safety mechanisms
  they describe change.
- `AI_AGENT_GUIDE.md` / `skills/ai-docs-scraper/SKILL.md` — describe the
  *output* workflow for agents consuming scraped docs, not the CLI's
  internals.
