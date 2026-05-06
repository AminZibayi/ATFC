from shared_python.paths import get_workspace_root

WORKSPACE_ROOT = get_workspace_root()

CONFIG = {
    "BASE_URL": "https://www.horizonpulse.ir",
    "MAX_DEPTH": 5,
    "MAX_PAGES": 200,
    "WAIT_FOR_MS": 2000,
    "HTML_DIR": WORKSPACE_ROOT / "data" / "raw" / "horizonpulse_crawler" / "html",
    "PAGES_DIR": WORKSPACE_ROOT / "data" / "intermediate" / "horizonpulse_crawler" / "pages",
    "SUMMARY_PATH": WORKSPACE_ROOT / "data" / "outputs" / "horizonpulse_crawler" / "crawl_summary.json",
}
