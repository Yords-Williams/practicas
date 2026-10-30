import os
import shutil
import sys
from pathlib import Path


APP_DATA_DIR = Path(
    os.environ.get(
        "LOCALAPPDATA",
        Path.home() / "AppData" / "Local",
    )
) / "Alertas Tempranas Videovigilancia"


def user_data_path(filename):
    """Return a stable writable path, migrating legacy files when present."""
    target = APP_DATA_DIR / filename
    if target.exists():
        return str(target)

    candidates = []
    if not getattr(sys, "frozen", False):
        candidates.append(Path.cwd() / filename)
        candidates.append(Path(__file__).resolve().parent / filename)
    else:
        candidates.append(Path(sys.executable).resolve().parent / filename)
        candidates.append(Path.cwd() / filename)

    for source in candidates:
        if source.is_file() and source.resolve() != target.resolve():
            APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            break

    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return str(target)
