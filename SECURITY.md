# Security

This project is a local CLI for scraping public documentation into Markdown.

## Defaults

- Manual URL mode is the default.
- Automatic modes still exist, but must be selected intentionally.
- Localhost and private network hosts are blocked by default.
- Redirects are followed manually and each hop is checked.
- Page, text, and XML responses have size limits.
- HTML, text, and XML fetches check `Content-Type`.
- Generated Markdown includes an untrusted-content warning for AI agents.
- Sitemap XML is parsed with `defusedxml`.

## Supported Use

- Public documentation pages
- Public `llms.txt` files
- Public `sitemap.xml` files
- Manually curated URL lists

## Avoid

- Authenticated dashboards
- Private customer portals
- URLs containing secrets, tokens, or session IDs
- Running the tool against internal network services unless you understand the risk

## Prompt Injection

Documentation pages can contain text that tries to manipulate an AI agent.
Examples include instructions like "ignore previous instructions", "send your
secrets", "run this command", or "visit this unrelated URL".

This scraper cannot prove that documentation is safe. Instead, it reduces risk:

- it defaults to manually provided URLs
- it validates redirects before following them
- it rejects unexpected content types
- it strips scripts, iframes, SVG, styles, and HTML comments
- it adds an untrusted-content warning to generated Markdown
- it keeps source URLs in front matter
- it blocks private network hosts by default

Agents using scraped output should treat it as reference data only.

## Private Hosts

By default the CLI rejects localhost, loopback, link-local, private, reserved,
multicast, and unspecified network targets.

Only use this flag for a trusted internal documentation site:

```bash
ai-docs-scraper http://localhost:3000/docs --allow-private-hosts
```

## Reporting Issues

Please open a GitHub issue with:

- affected version or commit
- command used
- expected behavior
- actual behavior
- redacted logs or sample URL if possible

Never include real API keys, tokens, cookies, or private URLs in reports.
