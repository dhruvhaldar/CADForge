import hashlib
import json
import shutil
import time
from importlib.metadata import version
from pathlib import Path

EXPORT_SETTINGS = {
    "preview_deflection": 0.2,
    "stl_deflection": 0.05,
    "angular_deflection": 0.1,
    "pipeline": 2,
}


def cache_key(recipe):
    content = {
        "recipe": recipe,
        "build123d": version("build123d"),
        "ocp": version("cadquery-ocp-novtk"),
        "settings": EXPORT_SETTINGS,
    }
    return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Cache:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def read(self, key):
        path = self.root / key
        try:
            result = json.loads((path / "result.json").read_text(encoding="utf-8"))
            files = [*result["files"].values(), "preview.json", "preview.glb"]
            if all(
                Path(name).name == name and (path / name).is_file() and (path / name).stat().st_size
                for name in files
            ):
                (path / "result.json").touch()
                return result
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return None

    def prune(self, limit, protected=()):
        entries = []
        for path in self.root.iterdir():
            if path.is_dir() and len(path.name) == 64 and all(c in "0123456789abcdef" for c in path.name):
                size = sum(f.stat().st_size for f in path.iterdir() if f.is_file())
                marker = path / "result.json"
                entries.append((marker.stat().st_mtime if marker.exists() else 0, size, path))
        total = sum(e[1] for e in entries)
        for stamp, size, path in sorted(entries):
            if path.name not in protected and (total > limit or time.time() - stamp > 30 * 86400):
                shutil.rmtree(path)
                total -= size
        return total
