import asyncio
from dataclasses import replace
import pytest
from cadforge.services.generation import GenerationService
from cadforge.services.projects import Projects
from cadforge.services.recipes import parse_recipe
from cadforge.settings import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(tmp_path / "data", tmp_path / "cache", timeout=60)


async def test_worker_cache_persistence_and_reopen(settings):
    service = GenerationService(settings)
    states = []
    result = await service.generate("block", {}, states.append)
    assert states == ["Queued", "Generating"]
    assert result["valid"] and result["volume"] == pytest.approx(48000)
    cached = await service.generate("block", {})
    assert cached["cache_hit"]
    projects = Projects(settings.data)
    project = projects.create("Reference project")
    revision = projects.save(project, "First solid", result, settings.cache / result["key"])
    service.cache.prune(0)
    assert not (settings.cache / result["key"]).exists()
    reopened = Projects(settings.data)
    restored, source = reopened.restore(revision)
    assert restored["recipe"] == result["recipe"]
    assert (source / "model.step").stat().st_size > 1000
    assert parse_recipe((source / "model.json").read_text()) == result["recipe"]
    duplicate = reopened.duplicate(project, "Copy")
    assert len(reopened.revisions(duplicate)) == 1
    regenerated = await service.generate(restored["recipe"]["model"], restored["recipe"]["parameters"])
    assert regenerated["volume"] == pytest.approx(result["volume"])


async def test_identical_requests_use_single_generation(settings):
    service = GenerationService(settings)
    a, b = await asyncio.gather(service.generate("block", {}), service.generate("block", {}))
    assert a["key"] == b["key"]
    assert sum([a["cache_hit"], b["cache_hit"]]) == 1


async def test_timeout_cancel_and_queue_recovery(settings):
    service = GenerationService(replace(settings, timeout=0.001, queue_limit=1))
    with pytest.raises(TimeoutError):
        await service.generate("block", {})
    assert service.pending == 0
    assert not list(settings.cache.glob("job-*"))
    service.settings = replace(settings, timeout=60, queue_limit=1)
    task = asyncio.create_task(service.generate("airfoil", {}))
    await asyncio.sleep(0.02)
    with pytest.raises(ValueError, match="queue is full"):
        await service.generate("block", {})
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert service.pending == 0
    assert not list(settings.cache.glob("job-*"))
    assert (await service.generate("block", {}))["valid"]


async def test_invalid_request_never_queued(settings):
    service = GenerationService(settings)
    with pytest.raises(ValueError):
        await service.generate("block", {"length": -2})
    assert service.pending == 0


def test_data_cache_must_not_overlap(tmp_path, monkeypatch):
    monkeypatch.setenv("CADFORGE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CADFORGE_CACHE_DIR", str(tmp_path / "cache"))
    with pytest.raises(ValueError, match="separate"):
        Settings.load()


def test_default_windows_layout_is_non_nested(tmp_path, monkeypatch):
    import cadforge.settings as config

    monkeypatch.delenv("CADFORGE_DATA_DIR", raising=False)
    monkeypatch.delenv("CADFORGE_CACHE_DIR", raising=False)
    monkeypatch.setattr(config, "user_data_path", lambda app, **kw: tmp_path / app)
    monkeypatch.setattr(config, "user_cache_path", lambda app, **kw: tmp_path / app / "Cache")
    settings = Settings.load()
    assert settings.data not in settings.cache.parents
    assert settings.data.is_dir() and settings.cache.is_dir()
