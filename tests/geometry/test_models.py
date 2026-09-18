import math
import pytest
from build123d import import_step
from cadforge.models.registry import MODELS, generate, get_model
from cadforge.services.exports import export_shape
from cadforge.services.recipes import recipe, parse_recipe


@pytest.mark.parametrize("model", MODELS.values(), ids=lambda m: m.id)
def test_default_geometry_and_step_roundtrip(model, tmp_path):
    p = model.normalize(model.defaults())
    shape = generate(model.id, p)
    assert shape.is_valid
    assert len(shape.solids()) == {"car": 6, "enclosure": 2}.get(model.id, 1)
    files = export_shape(shape, recipe(model.id, p), tmp_path)
    loaded = import_step(tmp_path / files["step"])
    assert loaded.is_valid
    assert loaded.volume == pytest.approx(shape.volume, rel=1e-6)
    assert list(loaded.bounding_box().size) == pytest.approx(list(shape.bounding_box().size), abs=1e-5)
    assert (tmp_path / "preview.glb").read_bytes()[:4] == b"glTF"


@pytest.mark.parametrize("model_id,preset", [(m.id, p) for m in MODELS.values() for p in m.presets.values()])
def test_presets(model_id, preset):
    shape = generate(model_id, get_model(model_id).defaults() | preset)
    assert shape.is_valid


def test_reference_volumes():
    assert generate("block", {}).volume == pytest.approx(60 * 40 * 20)
    expected = 100 * 70 * 5 - 6 * math.pi * 3**2 * 5
    assert generate("plate", {}).volume == pytest.approx(expected)
    assert list(generate("block", {}).bounding_box().size) == pytest.approx([60, 40, 20])


@pytest.mark.parametrize(
    "model,params",
    [
        ("block", {"length": 0}),
        ("block", {"width": float("nan")}),
        ("block", {"height": True}),
        ("block", {"extra": 2}),
        ("airfoil", {"code": "abc"}),
        ("airfoil", {"code": "2012"}),
        ("airfoil", {"code": "2400"}),
        ("airfoil", {"code": "0112"}),
        ("airfoil", {"span": 0}),
        ("plate", {"diameter": 22}),
        ("plate", {"columns": 10}),
        ("plate", {"rows": 2.5}),
        ("bracket", {"thickness": 30}),
        ("bracket", {"diameter": 100}),
        ("enclosure", {"wall": 30}),
        ("car", {"wheel_radius": 30}),
    ],
)
def test_invalid_parameters(model, params):
    with pytest.raises(ValueError):
        get_model(model).normalize(params)


def test_profile_exports(tmp_path):
    design = recipe("airfoil", {"mode": "profile", "span": 0})
    shape = generate("airfoil", design["parameters"])
    assert len(shape.solids()) == 0
    assert shape.bounding_box().size.Z == pytest.approx(0)
    files = export_shape(shape, design, tmp_path)
    assert set(files) == {"svg", "dxf", "json"}
    assert "<svg" in (tmp_path / files["svg"]).read_text()


@pytest.mark.parametrize(
    "patch", [{"schema_version": 2}, {"generator_version": "99"}, {"units": "in"}, {"parameters": []}]
)
def test_recipe_compatibility(patch):
    with pytest.raises(ValueError):
        parse_recipe(recipe("block", {}) | patch)
