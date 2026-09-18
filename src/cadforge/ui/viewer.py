import math

from nicegui import app, ui


class Viewer:
    def __init__(self):
        self.center = [0, 0, 0]
        self.extent = 80
        self.model = None
        self.preview = None
        self.fit_on_update = False
        with ui.row().classes("items-center gap-2"):
            ui.button("Fit", icon="fit_screen", on_click=self.fit).props("flat dense")
            for label in ("Top", "Front", "Right"):
                ui.button(label, on_click=lambda _, view=label: self.fit(view)).props("flat dense")
            ui.switch(
                "Fit on update", value=False, on_change=lambda e: setattr(self, "fit_on_update", e.value)
            ).props("dense")
        with ui.scene(width=900, height=540, grid=(1000, 100), background_color="#e8edf2", fps=60).classes(
            "w-full rounded-lg"
        ) as self.scene:
            self.scene.axes_helper(20)
            self.scene.spot_light(intensity=2, decay=0).move(150, -200, 300)
        ui.label("Drag to orbit · right-drag to pan · scroll to zoom").classes("text-xs text-slate-500")

    async def show(self, result, directory, is_current=lambda: True):
        """Load a replacement before retiring the visible mesh; preserve the user's camera."""
        await self.scene.initialized()
        cx, cy, cz = result["center"]
        floor_offset = result["dimensions"][2] / 2 + 0.05
        model_id = result["recipe"]["model"]
        url = f"/preview/{directory.name}.glb"
        app.add_media_file(local_file=directory / "preview.glb", url_path=url)
        with self.scene:
            candidate = self.scene.gltf(url).visible(False)
            candidate.scale(1000).rotate(math.pi / 2, 0, 0).move(-cx, -cy, -cz + floor_offset)
            candidate.material("#7db6de", side="both")
        try:
            # NiceGUI's native visibility method awaits its GLTF object's ready promise.
            # Awaiting this call also flushes the queued object creation/transforms now,
            # rather than declaring the result ready while the browser is still loading it.
            await self.scene.run_method("visible", candidate.id, False, timeout=30)
            if not is_current():
                candidate.delete()
                return False
            # Refresh the drawing surface before committing; cancellation must still
            # leave the previous mesh and its inspection/export metadata together.
            await self.scene.run_method("resize", timeout=10)
            candidate.visible(True)
            await self.scene.run_method("visible", candidate.id, True, timeout=30)
            if not is_current():
                candidate.delete()
                return False
            previous = self.preview
            self.preview = candidate
            changed = self.model != model_id
            self.model = model_id
            self.center = [0, 0, floor_offset]
            self.extent = max(result["dimensions"])
            if previous:
                previous.delete()
            if changed or self.fit_on_update:
                self.fit()
            self.scene.update()
            return True
        except BaseException:
            if self.preview is not candidate and candidate.id in self.scene.objects:
                candidate.delete()
            raise

    def fit(self, view="Iso"):
        x, y, z = self.center
        distance = max(self.extent * 1.9, 2)
        dx, dy, dz = {"Top": (0, -0.001, 1), "Front": (0, -1, 0.001), "Right": (1, 0, 0.001)}.get(
            view, (1, -1, 0.8)
        )
        self.scene.move_camera(
            x=x + dx * distance,
            y=y + dy * distance,
            z=z + dz * distance,
            look_at_x=x,
            look_at_y=y,
            look_at_z=z,
            duration=0.2,
        )
