# AI Agent Guide

Use this repository when you need fresh documentation context before coding,
reviewing, or planning.

## Agent Workflow

1. Identify the canonical docs URL for the library, API, or framework.
2. Scrape only the relevant scope with `--base-url` and a small `--max-pages`.
3. Read `context.md` first for a broad pass.
4. Read individual files in `pages/` when you need source-level detail.
5. Cite or mention the source URL from the Markdown front matter when giving an answer.

## Recommended Commands

```bash
ai-docs-scraper https://example.com/docs --base-url https://example.com/docs --max-pages 30
```

```bash
ai-docs-scraper https://example.com/llms.txt --mode llms --max-pages 50
```

```bash
ai-docs-scraper --urls-file examples/targets.txt --out scraped-docs/custom
```

## Context Engineering Tips

- Keep the crawl narrow. A small, relevant context beats a huge noisy one.
- Prefer `llms.txt` when available because it is curated for model consumption.
- Prefer `sitemap.xml` for official docs with stable page lists.
- Use `--urls-file` for high-signal pages like quickstarts, API references, auth, webhooks, limits, and examples.
- Re-scrape docs before important implementation work if the package or API changes frequently.
- Do not commit scraped output by default; treat it as generated context.

## Safety Rules

- Only scrape documentation you are allowed to access.
- Respect docs site rate limits and terms.
- Use `--delay` for larger crawls.
- Avoid scraping private dashboards, authenticated pages, or URLs containing tokens.
