import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_cache_path, user_data_path


@dataclass(frozen=True)
class Settings:
    data: Path
    cache: Path
    timeout: float = 120
    queue_limit: int = 4
    cache_limit: int = 512 * 1024 * 1024

    @classmethod
    def load(cls):
        data = Path(os.environ.get("CADFORGE_DATA_DIR", user_data_path("CADForge", appauthor=False)))
        cache = Path(os.environ.get("CADFORGE_CACHE_DIR", user_cache_path("CADForgeCache", appauthor=False)))
        data, cache = data.resolve(), cache.resolve()
        if data == cache or data in cache.parents or cache in data.parents:
            raise ValueError("Data and cache directories must be separate, non-nested locations.")
        data.mkdir(parents=True, exist_ok=True)
        cache.mkdir(parents=True, exist_ok=True)
        return cls(data, cache)
