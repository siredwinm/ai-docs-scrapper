# AI Docs Scraper

A tiny CLI that turns documentation websites into Markdown context for AI
agents.

The goal is simple: make context engineering easier. When an AI agent needs
fresh docs for a framework, SDK, API, or tool, scrape the official docs into
local Markdown and give the agent the context it needs.

No API key is required.

## Why

AI agents are better when they can read the same docs you would read. This
tool helps you collect current documentation into files that are easy to pass
into Codex, Claude Code, Cursor, Gemini, OpenCode, or any other coding agent.

It tries the simple routes first:

- `/llms.txt`
- `sitemap.xml`
- a bounded same-site crawl
- a plain list of URLs

This is useful when you want an agent to:

- implement against the latest docs
- compare old assumptions with current behavior
- build a small project-specific knowledge pack
- avoid guessing from stale model memory

## Install

```bash
git clone https://github.com/siredwinm/ai-docs-scrapper.git
cd ai-docs-scrapper
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

Scrape a docs site:

```bash
ai-docs-scraper https://docs.example.com --out scraped-docs/example
```

Keep the crawl inside a docs path:

```bash
ai-docs-scraper https://example.com/docs --base-url https://example.com/docs --max-pages 40
```

Use a URL list:

```bash
ai-docs-scraper --urls-file examples/targets.txt --out scraped-docs/custom
```

Prefer `llms.txt` only:

```bash
ai-docs-scraper https://example.com/llms.txt --mode llms
```

Limit large docs sites:

```bash
ai-docs-scraper https://developers.cloudflare.com/workers/ \
  --base-url https://developers.cloudflare.com/workers/ \
  --max-pages 25 \
  --delay 0.5
```

## Output

The output folder contains:

- `pages/*.md` for each scraped page
- `context.md` as one bundled Markdown context file
- `index.json` with source URLs and output paths

Each Markdown page includes source metadata:

```markdown
---
title: "Example"
source: "https://example.com/docs"
scraped_at: "2026-06-16T00:00:00+00:00"
---
```

## For AI Agents

See [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md) for a compact workflow agents can
follow before coding with fresh documentation.

Quick version:

1. Scrape a narrow docs scope.
2. Read `context.md`.
3. Open individual `pages/*.md` files when details matter.
4. Prefer official docs URLs and cite the source URL when answering.

## Tips

- Start with `--max-pages 20` before crawling a large site.
- Use `--base-url` to keep the crawl inside the docs area.
- Use `--urls-file` when you already know the important pages.
- Do not commit generated `scraped-docs/` output unless your project needs it.
- Re-run the scraper when dependencies or APIs change.

## Should this use Exa?

Not as the default path.

Exa is useful when you do not know what URLs to scrape yet. For an open-source
tool people can clone and run immediately, deterministic sources are better:
`llms.txt`, sitemap, direct URLs, and bounded crawling.

An Exa integration can be added later as an optional discovery provider:

```bash
ai-docs-scraper discover "OpenAI API docs embeddings" --provider exa
```

That keeps the core free, local, and predictable.

## Security

Read [SECURITY.md](SECURITY.md). Short version: scrape public documentation,
avoid authenticated/private pages, and never include tokens in URLs.

## License

MIT
