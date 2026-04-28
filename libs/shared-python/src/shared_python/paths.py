import os
from pathlib import Path

def get_workspace_root() -> Path:
    """Find the root of the workspace by looking for nx.json."""
    current = Path(__file__).resolve()
    while current.parent != current:
        if (current / "nx.json").exists():
            return current
        current = current.parent
    # Fallback if somehow not found
    return Path(os.getcwd()).resolve()

WORKSPACE_ROOT = get_workspace_root()
DATA_SOURCE_DIR = WORKSPACE_ROOT / "data_source"

def get_data_path(filename: str) -> Path:
    return DATA_SOURCE_DIR / filename

def get_output_path(app_name: str, filename: str) -> Path:
    out_dir = WORKSPACE_ROOT / "dist" / "apps" / app_name / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / filename

def get_plot_path(app_name: str, filename: str) -> Path:
    plot_dir = WORKSPACE_ROOT / "dist" / "apps" / app_name / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    return plot_dir / filename