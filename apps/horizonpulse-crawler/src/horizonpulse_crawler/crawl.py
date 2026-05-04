import asyncio
import json
import hashlib
import re
from datetime import datetime
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, DomainFilter, ContentTypeFilter

from horizonpulse_crawler.config import CONFIG

def url_to_filename(url: str) -> str:
    parsed = urlparse(url)
    path_and_query = f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path
    # Use [^\w\-] to preserve Unicode characters (like Persian) while sanitizing
    sanitized = re.sub(r'[^\w\-]', '_', path_and_query).strip('_')
    sanitized = sanitized[:50] or "index"
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{sanitized}_{url_hash}"

def save_result(result):
    try:
        fname = url_to_filename(result.url)
        
        pages_dir = CONFIG["OUTPUT_DIR"] / "pages"
        html_dir = CONFIG["OUTPUT_DIR"] / "html"

        # Save Markdown
        md_path = pages_dir / f"{fname}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# {result.url}\n\n")
            if hasattr(result, 'markdown') and result.markdown:
                md_content = getattr(result.markdown, 'fit_markdown', None) or getattr(result.markdown, 'raw_markdown', None) or ""
                f.write(md_content)

        # Save HTML
        html_path = html_dir / f"{fname}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(result.html or "")
            
        return True, None
    except Exception as e:
        return False, str(e)

async def main():
    print(f"Starting crawl of {CONFIG['BASE_URL']}")
    CONFIG["OUTPUT_DIR"].mkdir(parents=True, exist_ok=True)
    
    # Setup directories early to avoid concurrent mkdir race conditions
    (CONFIG["OUTPUT_DIR"] / "pages").mkdir(parents=True, exist_ok=True)
    (CONFIG["OUTPUT_DIR"] / "html").mkdir(parents=True, exist_ok=True)

    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        verbose=False,
        accept_downloads=False,
        extra_args=["--lang=fa,en", "--disable-blink-features=AutomationControlled"]
    )

    filter_chain = FilterChain([
        DomainFilter(allowed_domains=["horizonpulse.ir", "www.horizonpulse.ir"]),
        ContentTypeFilter(allowed_types=["text/html"])
    ])

    deep_crawl = BFSDeepCrawlStrategy(
        max_depth=CONFIG["MAX_DEPTH"],
        max_pages=CONFIG["MAX_PAGES"],
        include_external=False,
        filter_chain=filter_chain
    )

    run_config = CrawlerRunConfig(
        deep_crawl_strategy=deep_crawl,
        cache_mode=CacheMode.BYPASS,
        wait_for=f"js:() => new Promise(r => setTimeout(r, {CONFIG['WAIT_FOR_MS']}))",
        stream=True,
        verbose=True,
        page_timeout=30000,
        word_count_threshold=10,
        exclude_social_media_links=True,
        excluded_tags=["script", "style", "nav", "footer"]
    )

    crawled_urls = []
    failed_urls = []

    async with AsyncWebCrawler(config=browser_config) as crawler:
        async for result in crawler.arun(CONFIG["BASE_URL"], config=run_config):
            depth = result.metadata.get("depth", 0)
            if result.success:
                # Offload blocking I/O to a thread
                success, error_msg = await asyncio.to_thread(save_result, result)
                if success:
                    crawled_urls.append(result.url)
                    print(f"  ✓  [depth={depth}] {result.url}")
                else:
                    failed_urls.append(result.url)
                    print(f"  ✗  [depth={depth}] {result.url} — Save Error: {error_msg}")
            else:
                failed_urls.append(result.url)
                print(f"  ✗  [depth={depth}] {result.url} — {result.error_message}")

    summary = {
        "crawled_at": datetime.now().isoformat(),
        "base_url": CONFIG["BASE_URL"],
        "total_success": len(crawled_urls),
        "total_failed": len(failed_urls),
        "crawled_urls": crawled_urls,
        "failed_urls": failed_urls,
    }

    summary_path = CONFIG["OUTPUT_DIR"] / "crawl_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Done! Saved {len(crawled_urls)} pages.")

if __name__ == "__main__":
    asyncio.run(main())
