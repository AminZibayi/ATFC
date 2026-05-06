import os
from pathlib import Path


def get_workspace_root() -> Path:
    """Find the workspace root by looking for nx.json or .git."""
    current = Path(__file__).resolve().parent
    while current.parent != current:
        if (current / "nx.json").exists() or (current / ".git").exists():
            return current
        current = current.parent
    return Path(os.getcwd()).resolve()


WORKSPACE_ROOT = get_workspace_root()
DATA_DIR = WORKSPACE_ROOT / "data"


def get_raw_data_path(filename: str) -> Path:
    return DATA_DIR / "raw" / filename


def get_intermediate_data_path(app_name: str, filename: str) -> Path:
    out_dir = DATA_DIR / "intermediate" / app_name
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / filename


def get_output_path(app_name: str, filename: str) -> Path:
    out_dir = DATA_DIR / "outputs" / app_name
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / filename


def get_plot_path(app_name: str, filename: str) -> Path:
    plot_dir = DATA_DIR / "outputs" / app_name / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    return plot_dir / filename


def get_data_path(filename: str) -> Path:
    return get_raw_data_path(filename)
