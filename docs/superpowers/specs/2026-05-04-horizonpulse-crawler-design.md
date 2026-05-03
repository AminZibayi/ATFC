# Horizonpulse Crawler — Design Spec

## Overview

An Nx Python application that crawls and mirrors `https://www.horizonpulse.ir/` using Crawl4AI v0.8.x. The crawler launches a headless Chromium browser, waits for Next.js hydration, and outputs clean Markdown and raw HTML per page.

## Technology

- **Crawl4AI** — async Playwright-based crawler with JS rendering
- **Nx + uv** — monorepo task orchestration and Python package management
- **shared-python** — workspace root path utilities

## Project Structure

```
apps/horizonpulse-crawler/
├── pyproject.toml
├── project.json
└── src/
    └── horizonpulse_crawler/
        ├── __init__.py
        ├── config.py      # BASE_URL, MAX_DEPTH, MAX_PAGES, WAIT_FOR_MS, OUTPUT_DIR
        ├── crawl.py       # Main crawling orchestration
        └── summarize.py   # Summary JSON generation
```

## Configuration (`config.py`)

| Constant | Value | Purpose |
|----------|-------|---------|
| `BASE_URL` | `"https://www.horizonpulse.ir"` | Start URL |
| `MAX_DEPTH` | `5` | Link-hop depth limit |
| `MAX_PAGES` | `200` | Hard cap on pages |
| `WAIT_FOR_MS` | `2000` | Extra wait after page load for JS rendering |

Output directory: `{workspaceRoot}/data/horizonpulse/`

## Dependencies

```toml
dependencies = [
    "crawl4ai",
    "shared-python",
]
```

## Nx Targets

### `crawl`
Runs the full BFS deep crawl of horizonpulse.ir, streaming results as pages complete. Saves Markdown to `data/horizonpulse/pages/` and HTML to `data/horizonpulse/html/`.

### `summarize`
Reads the crawled pages and generates `data/horizonpulse/crawl_summary.json` with metadata.

## Data Flow

1. `crawl` target invokes `crawl4ai.AsyncWebCrawler`
2. `BFSDeepCrawlStrategy` explores pages breadth-first
3. `FilterChain` restricts to `horizonpulse.ir` domain and `text/html` content type
4. Each result saves `.md` and `.html` files named from URL path
5. On completion, writes `crawl_summary.json` with success/failed URL lists

## Error Handling

- Failed URLs tracked separately and reported in summary
- Empty pages (word count < 10) are skipped
- Page timeout: 30 seconds per page