"""Run against a local test instance: CADFORGE_TEST_URL=http://127.0.0.1:8765."""

import json
import os
import re
import uuid
import pytest
from playwright.sync_api import sync_playwright, expect

pytestmark = [
    pytest.mark.browser,
    pytest.mark.skipif(not os.getenv("CADFORGE_TEST_URL"), reason="Set CADFORGE_TEST_URL for browser tests"),
]


@pytest.fixture
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=os.getenv("CADFORGE_BROWSER_CHANNEL", "chrome"), headless=True)
        page = browser.new_page(viewport={"width": 1500, "height": 1000}, accept_downloads=True)
        page.errors = []
        page.on("pageerror", lambda error: page.errors.append(str(error)))
        page.goto(os.environ["CADFORGE_TEST_URL"])
        expect(page.get_by_role("button", name="Generate", exact=True)).to_be_visible()
        yield page
        assert not page.errors
        browser.close()


def generate(page):
    page.get_by_role("button", name="Generate", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Ready", timeout=60000)


def choose_model(page, name):
    page.get_by_label("Model", exact=True).click()
    page.get_by_role("option", name=name, exact=True).click()


def test_generate_download_save_restore_and_reopen(page, tmp_path):
    with page.expect_response(lambda r: "/preview/" in r.url and r.status == 200, timeout=60000):
        generate(page)
    expect(page.get_by_text("1 solids · Valid geometry", exact=True)).to_be_visible()
    expect(page.locator("canvas")).to_be_visible()
    with page.expect_download() as download:
        page.get_by_role("button", name="STEP", exact=True).click()
    destination = tmp_path / "block.step"
    download.value.save_as(destination)
    assert "ISO-10303-21" in destination.read_text()
    name = "Browser project " + uuid.uuid4().hex[:8]
    page.get_by_label("Project name", exact=True).fill(name)
    page.get_by_role("button", name="Create project", exact=True).click()
    page.get_by_role("button", name="Save revision", exact=True).click()
    expect(page.get_by_text("Revision saved", exact=True)).to_be_visible()
    page.get_by_label("Length (mm)", exact=True).fill("90")
    expect(page.get_by_role("status")).to_contain_text("Outdated")
    page.get_by_role("button", name="Restore revision", exact=True).click()
    expect(page.get_by_label("Length (mm)", exact=True)).to_have_value("60")
    page.reload()
    page.get_by_label("Saved project", exact=True).click()
    page.get_by_role("option", name=name, exact=True).click()
    page.get_by_role("button", name="Restore revision", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("saved revision restored")
    expect(page.get_by_role("button", name="STEP", exact=True)).to_be_visible()
    for name in ("Top", "Front", "Right", "Fit"):
        page.get_by_role("button", name=name, exact=True).click()
    shot = os.getenv("CADFORGE_SCREENSHOT")
    if shot:
        page.screenshot(path=shot, full_page=True)


def test_model_switch_profile_recipe_and_invalid_inputs(page, tmp_path):
    choose_model(page, "NACA airfoil")
    page.get_by_label("NACA code", exact=True).fill("bad")
    page.get_by_role("button", name="Generate", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text("exactly four digits")
    page.get_by_label("NACA code", exact=True).fill("0012")
    page.get_by_label("Geometry", exact=True).click()
    page.get_by_role("option", name="profile", exact=True).click()
    page.get_by_label("Span (mm)", exact=True).fill("0")
    generate(page)
    expect(page.get_by_role("button", name="SVG", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="STEP", exact=True)).to_have_count(0)
    with page.expect_download() as download:
        page.get_by_role("button", name="JSON", exact=True).click()
    path = tmp_path / "recipe.json"
    download.value.save_as(path)
    assert json.loads(path.read_text())["parameters"]["mode"] == "profile"
    choose_model(page, "Parametric block")
    page.get_by_text("Recipes & cache", exact=True).click()
    page.locator("input[type=file]").set_input_files(path)
    expect(page.get_by_role("status")).to_contain_text("Recipe imported")
    expect(page.get_by_label("NACA code", exact=True)).to_have_value("0012")


@pytest.mark.parametrize("name", ["Simple car", "Mounting bracket", "Hole-pattern plate", "Enclosure"])
def test_other_models_generate(page, name):
    choose_model(page, name)
    generate(page)
    expect(page.get_by_text("Last successful result: " + name, exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="STEP", exact=True)).to_be_visible()


def test_pending_edits_do_not_publish_stale_result(page):
    generate(page)
    choose_model(page, "NACA airfoil")
    page.get_by_label("Chord (mm)", exact=True).fill(str(137 + int(uuid.uuid4().hex[:6], 16) / 100000))
    page.get_by_role("button", name="Generate", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text(re.compile("Queued|Generating"))
    page.get_by_label("Chord (mm)", exact=True).fill("138")
    expect(page.get_by_role("status")).to_contain_text("parameters changed during generation", timeout=60000)
    expect(page.get_by_text("Last successful result: Parametric block", exact=True)).to_be_visible()


def test_automatic_updates_and_cancel(page):
    page.get_by_role("switch", name="Automatic updates", exact=True).click()
    expect(page.get_by_role("switch", name="Automatic updates", exact=True)).to_have_attribute(
        "aria-checked", "true"
    )
    page.get_by_label("Length (mm)", exact=True).fill("75")
    expect(page.get_by_role("status")).to_contain_text("Ready", timeout=60000)
    expect(page.get_by_text("75.00 × 40.00 × 20.00 mm", exact=True)).to_be_visible()
    page.get_by_role("switch", name="Automatic updates", exact=True).click()
    expect(page.get_by_role("switch", name="Automatic updates", exact=True)).to_have_attribute(
        "aria-checked", "false"
    )
    choose_model(page, "NACA airfoil")
    page.get_by_label("Chord (mm)", exact=True).fill(str(180 + int(uuid.uuid4().hex[:2], 16)))
    page.get_by_role("button", name="Generate", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text(re.compile("Queued|Generating"))
    page.get_by_role("button", name="Cancel", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Cancelled")
    expect(page.get_by_text("Last successful result: Parametric block", exact=True)).to_be_visible()


def test_small_screen_controls(page):
    page.set_viewport_size({"width": 480, "height": 900})
    expect(page.get_by_role("button", name="Generate", exact=True)).to_be_visible()
    assert page.locator("body").bounding_box()["width"] <= 480


def test_geometry_refreshes_without_viewport_interaction(page):
    generate(page)
    page.wait_for_function(
        '!getElement(document.querySelector(".nicegui-scene").id.slice(1)).camera_tween?.isPlaying()'
    )
    canvas = page.locator("canvas")
    before = canvas.screenshot()
    frame = page.evaluate(
        'getElement(document.querySelector(".nicegui-scene").id.slice(1)).renderer.info.render.frame'
    )
    camera = page.evaluate('getElement(document.querySelector(".nicegui-scene").id.slice(1)).get_camera()')
    page.get_by_label("Height (mm)", exact=True).fill("85")
    generate(page)
    # The renderer advances without a mouse, camera, Fit, or resize action.
    page.wait_for_function(
        '(frame) => getElement(document.querySelector(".nicegui-scene").id.slice(1)).renderer.info.render.frame > frame',
        arg=frame,
    )
    assert canvas.screenshot() != before
    expect(page.get_by_text("60.00 × 40.00 × 85.00 mm", exact=True)).to_be_visible()
    updated_camera = page.evaluate(
        'getElement(document.querySelector(".nicegui-scene").id.slice(1)).get_camera()'
    )
    assert updated_camera["position"] == pytest.approx(camera["position"], abs=0.01)
    assert updated_camera["quaternion"] == pytest.approx(camera["quaternion"], abs=0.01)


def test_preview_waits_for_mesh_download(page):
    generate(page)
    intercepted = []

    def delayed_mesh(route):
        response = route.fetch()
        expect(page.get_by_role("status")).to_have_text("Loading preview")
        expect(page.get_by_text("60.00 × 40.00 × 20.00 mm", exact=True)).to_be_visible()
        intercepted.append(True)
        route.fulfill(response=response)

    page.route("**/preview/*.glb", delayed_mesh)
    page.get_by_label("Length (mm)", exact=True).fill("92")
    generate(page)
    assert intercepted
    expect(page.get_by_text("92.00 × 40.00 × 20.00 mm", exact=True)).to_be_visible()


def test_edit_during_preview_load_keeps_previous_result(page):
    generate(page)

    def change_while_loading(route):
        response = route.fetch()
        expect(page.get_by_role("status")).to_have_text("Loading preview")
        page.get_by_label("Length (mm)", exact=True).fill("94")
        expect(page.get_by_role("status")).to_contain_text("Outdated")
        route.fulfill(response=response)

    page.route("**/preview/*.glb", change_while_loading)
    page.get_by_label("Length (mm)", exact=True).fill("93")
    page.get_by_role("button", name="Generate", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text(
        "parameters changed during preview loading", timeout=60000
    )
    expect(page.get_by_text("60.00 × 40.00 × 20.00 mm", exact=True)).to_be_visible()
