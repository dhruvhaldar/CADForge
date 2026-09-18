import asyncio
import json
from pathlib import Path
import sys
import time
import psutil
from cadforge.services.generation import GenerationService
from cadforge.settings import Settings


async def main():
    root = Path(sys.argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    service = GenerationService(Settings(root / "data", root / "cache"))
    process = psutil.Process()
    measurements = []
    for label, model, parameters in [
        ("cold_block", "block", {}),
        ("cached_block", "block", {}),
        ("cold_airfoil", "airfoil", {}),
    ]:
        peak = 0
        started = time.perf_counter()
        task = asyncio.create_task(service.generate(model, parameters))
        while not task.done():
            children = process.children(recursive=True)
            for child in children:
                try:
                    peak = max(peak, child.memory_info().rss)
                except psutil.NoSuchProcess:
                    pass
            await asyncio.sleep(0.05)
        result = await task
        measurements.append(
            {
                "case": label,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "cache_hit": result["cache_hit"],
                "peak_worker_rss_mib": round(peak / 1024**2, 1),
                "preview_bytes": (service.settings.cache / result["key"] / "preview.glb").stat().st_size,
            }
        )
    before = process.memory_info().rss
    for index in range(10):
        await service.generate("block", {"length": 60 + index})
    after = process.memory_info().rss
    report = {
        "measurements": measurements,
        "ten_updates_parent_rss_change_mib": round((after - before) / 1024**2, 2),
        "children_remaining": len(process.children()),
        "notes": "Single Windows run; includes Python/OpenCascade subprocess startup. Warm filesystem and installed dependencies. RSS is sampled, not a leak proof.",
    }
    print(json.dumps(report, indent=2))
    Path(sys.argv[2]).write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
