import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from cadforge.services.cache import Cache, cache_key
from cadforge.services.recipes import recipe


class GenerationService:
    """One subprocess at a time, bounded admission, cancellable queued/running tasks."""

    def __init__(self, settings):
        self.settings = settings
        self.cache = Cache(settings.cache)
        self.slots = asyncio.Semaphore(1)
        self.pending = 0
        self.tasks = set()
        self.pins = {}

    async def generate(self, model_id, parameters, status=lambda value: None):
        design = recipe(model_id, parameters)
        key = cache_key(design)
        if self.pending >= self.settings.queue_limit:
            raise ValueError("Generation queue is full. Wait for a running job or cancel one.")
        self.pending += 1
        task = asyncio.current_task()
        self.tasks.add(task)
        temp, process = None, None
        started = time.perf_counter()
        try:
            status("Queued")
            async with self.slots:
                cached = self.cache.read(key)
                if cached:
                    return dict(cached, key=key, cache_hit=True, elapsed=time.perf_counter() - started)
                status("Generating")
                temp = Path(tempfile.mkdtemp(prefix="job-", dir=self.settings.cache))
                request = temp / "request.json"
                request.write_text(json.dumps(design), encoding="utf-8")
                with (temp / "worker.log").open("wb") as log:
                    process = subprocess.Popen(
                        [sys.executable, "-m", "cadforge.services.worker", str(request), str(temp)],
                        stdout=log,
                        stderr=log,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )
                    deadline = time.monotonic() + self.settings.timeout
                    while process.poll() is None:
                        if time.monotonic() > deadline:
                            raise TimeoutError(
                                f"Generation exceeded {self.settings.timeout:g} seconds; try simpler parameters."
                            )
                        await asyncio.sleep(0.1)
                if process.returncode:
                    error = temp / "error.txt"
                    raise ValueError(
                        error.read_text(encoding="utf-8")
                        if error.exists()
                        else "CAD worker failed. See the worker log."
                    )
                result = json.loads((temp / "result.json").read_text(encoding="utf-8"))
                destination = self.settings.cache / key
                if destination.exists():
                    shutil.rmtree(destination)
                temp.rename(destination)
                temp = None
                self.cache.prune(self.settings.cache_limit, set(self.pins.values()) | {key})
                return dict(result, key=key, cache_hit=False, elapsed=time.perf_counter() - started)
        finally:
            if process and process.poll() is None:
                process.kill()
                await asyncio.to_thread(process.wait)
            if temp:
                shutil.rmtree(temp, ignore_errors=True)
            self.pending -= 1
            self.tasks.discard(task)

    async def close(self):
        tasks = list(self.tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
