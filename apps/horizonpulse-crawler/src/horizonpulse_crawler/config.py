from shared_python.paths import get_workspace_root

WORKSPACE_ROOT = get_workspace_root()

CONFIG = {
    "BASE_URL": "https://www.horizonpulse.ir",
    "MAX_DEPTH": 5,
    "MAX_PAGES": 200,
    "WAIT_FOR_MS": 2000,
    "OUTPUT_DIR": WORKSPACE_ROOT / "data" / "horizonpulse",
}
