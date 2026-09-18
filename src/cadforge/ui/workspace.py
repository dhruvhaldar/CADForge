import asyncio

from nicegui import ui

from cadforge.models.registry import MODELS, get_model
from cadforge.services.recipes import parse_recipe
from cadforge.ui.viewer import Viewer


class Workspace:
    def __init__(self, service, projects):
        self.service, self.projects = service, projects
        self.model_id = "block"
        self.controls = {}
        self.result = self.directory = None
        self.task = self.debounce = None
        self.revision = 0
        self.project_id = None
        self.automatic = False
        ui.colors(primary="#28658a", secondary="#456a76", accent="#a45f24")
        with ui.header().classes("bg-slate-900 items-center px-6"):
            ui.icon("view_in_ar", size="30px")
            ui.label("CADForge").classes("text-xl font-semibold tracking-wide")
            ui.label("PARAMETRIC CAD IN PYTHON").classes("text-xs text-slate-300 ml-4")
            ui.space()
            ui.label("LOCAL WORKSPACE · mm").classes("text-xs")
        with ui.column().classes("w-full p-4 gap-4"):
            with ui.row().classes("w-full items-center"):
                ui.label("Design workbench").classes("text-2xl font-semibold text-slate-800")
                ui.space()
                self.status = (
                    ui.label("Choose parameters, then Generate").props("role=status").classes("text-sm")
                )
            with ui.row().classes("w-full items-start gap-4 flex-wrap lg:flex-nowrap"):
                with ui.card().classes("w-full lg:w-64 shrink-0"):
                    with ui.expansion("Model & parameters", icon="tune", value=True).classes("w-full"):
                        self.selector = ui.select(
                            {k: m.title for k, m in MODELS.items()},
                            value="block",
                            label="Model",
                            on_change=self.change_model,
                        ).classes("w-full")
                        self.description = ui.label().classes("text-sm text-slate-500")
                        self.parameter_panel = ui.column().classes("w-full")
                        self.error = ui.label().classes("text-red-700 text-sm").props("role=alert")
                        ui.button("Generate", icon="play_arrow", on_click=self.generate).classes("w-full")
                        with ui.row():
                            ui.button("Cancel", on_click=self.cancel).props("flat dense")
                            ui.button("Reset", on_click=self.reset).props("flat dense")
                        ui.switch(
                            "Automatic updates", on_change=lambda e: setattr(self, "automatic", e.value)
                        )
                        ui.label("Ctrl+Enter to generate").classes("text-xs text-slate-500")
                with ui.card().classes("flex-1 min-w-0 w-full"):
                    self.viewer = Viewer()
                    self.preview_caption = ui.label("No geometry generated yet").classes(
                        "text-sm text-slate-600"
                    )
                with ui.card().classes("w-full lg:w-72 shrink-0"):
                    with ui.expansion("Inspection & exports", icon="straighten", value=True).classes(
                        "w-full"
                    ):
                        self.inspection = ui.column().classes("w-full")
                        self.downloads = ui.row().classes("gap-2")
                    with ui.expansion("Projects & revisions", icon="folder_open", value=True).classes(
                        "w-full"
                    ):
                        self.project_selector = ui.select(
                            {}, label="Saved project", on_change=self.select_project
                        ).classes("w-full")
                        self.project_name = ui.input("Project name", value="Untitled design").classes(
                            "w-full"
                        )
                        with ui.row():
                            ui.button("Create project", on_click=self.create_project).props("outline dense")
                            ui.button("Duplicate", on_click=self.duplicate).props("flat dense")
                        self.revision_name = ui.input("Revision name", value="Checkpoint").classes("w-full")
                        ui.button("Save revision", icon="save", on_click=self.save).classes("w-full")
                        self.revision_selector = ui.select({}, label="Revision").classes("w-full")
                        ui.button("Restore revision", on_click=self.restore).props("outline dense")
                    with ui.expansion("Recipes & cache", icon="settings").classes("w-full"):
                        ui.upload(
                            label="Import JSON recipe",
                            auto_upload=True,
                            on_upload=self.import_recipe,
                            max_file_size=65536,
                        ).props("accept=.json").classes("w-full")
                        ui.button("Clear unused cache", on_click=self.clear_cache).props("flat dense")
            ui.label(
                "STEP stores geometry. JSON recipes preserve the parameters needed to regenerate it."
            ).classes("text-xs text-slate-500")
        ui.keyboard(on_key=self.keyboard)
        ui.context.client.on_delete(self.cleanup)
        self.render_parameters()
        self.refresh_projects()

    def values(self):
        return {key: control.value for key, control in self.controls.items()}

    def render_parameters(self, values=None):
        model = get_model(self.model_id)
        values = values or model.defaults()
        self.parameter_panel.clear()
        self.controls.clear()
        self.description.set_text(model.description)
        with self.parameter_panel:
            ui.select(
                list(model.presets), label="Preset", on_change=lambda e: self.apply_preset(e.value)
            ).classes("w-full")
            for p in model.parameters:
                label = f"{p.label} ({p.unit})" if p.unit else p.label
                if p.choices:
                    control = ui.select(
                        list(p.choices), label=label, value=values[p.name], on_change=self.edited
                    )
                elif isinstance(p.default, str):
                    control = ui.input(label, value=values[p.name], on_change=self.edited)
                else:
                    control = ui.number(
                        label,
                        value=values[p.name],
                        min=p.minimum,
                        max=p.maximum,
                        step=1 if p.integer else 0.5,
                        on_change=self.edited,
                        validation={
                            f"Use {p.minimum:g}–{p.maximum:g}": lambda v, spec=p: (
                                v is not None and spec.minimum <= v <= spec.maximum
                            )
                        },
                    )
                self.controls[p.name] = control.classes("w-full").props("outlined dense")

    def edited(self, _=None):
        self.revision += 1
        self.status.set_text("Outdated — generate to update" if self.result else "Parameters changed")
        if self.debounce:
            self.debounce.cancel()
        if self.automatic:
            self.debounce = asyncio.create_task(self.delayed_generate())

    async def delayed_generate(self):
        await asyncio.sleep(0.7)
        await self.generate()

    def change_model(self, e):
        self.model_id = e.value
        self.render_parameters()
        self.edited()

    def apply_preset(self, preset):
        if preset:
            model = get_model(self.model_id)
            self.render_parameters(model.defaults() | model.presets[preset])
            self.edited()

    def reset(self):
        self.render_parameters()
        self.edited()

    async def generate(self):
        current = asyncio.current_task()
        if self.task and self.task is not current:
            self.task.cancel()
        self.task = current
        serial = self.revision
        self.error.set_text("")
        try:
            result = await self.service.generate(self.model_id, self.values(), self.status.set_text)
            if serial != self.revision:
                self.status.set_text("Outdated — parameters changed during generation")
                return
            self.status.set_text("Loading preview")
            if not await self.show(
                result, self.service.settings.cache / result["key"], lambda: serial == self.revision
            ):
                self.status.set_text("Outdated — parameters changed during preview loading")
                return
            self.status.set_text("Ready — cache hit" if result["cache_hit"] else "Ready")
        except asyncio.CancelledError:
            if self.task is current:
                self.status.set_text("Cancelled")
        except (ValueError, TimeoutError, OSError) as exc:
            self.error.set_text(str(exc))
            self.status.set_text("Failed — previous successful result retained")
        finally:
            if self.task is current:
                self.task = None

    async def show(self, result, directory, is_current=lambda: True):
        loading_pin = (id(self), "loading")
        self.service.pins[loading_pin] = directory.name
        try:
            if not await self.viewer.show(result, directory, is_current):
                return False
            self.service.pins[id(self)] = directory.name
        finally:
            self.service.pins.pop(loading_pin, None)
        self.result, self.directory = result, directory
        self.preview_caption.set_text(f"Last successful result: {get_model(result['recipe']['model']).title}")
        self.inspection.clear()
        with self.inspection:
            ui.label(" × ".join(f"{v:.2f}" for v in result["dimensions"]) + " mm").classes("font-semibold")
            ui.label(f"{result['solids']} solids · Valid geometry")
            if result["volume"] is not None:
                ui.label(f"Volume: {result['volume']:,.2f} mm³")
            ui.label(f"Generation: {result['duration']:.2f} s")
        self.downloads.clear()
        with self.downloads:
            for fmt, name in result["files"].items():
                ui.button(fmt.upper(), on_click=lambda _, p=directory / name: ui.download(p)).props(
                    "outline dense"
                )

        return True

    def cancel(self, *_):
        if self.debounce:
            self.debounce.cancel()
        if self.task:
            self.task.cancel()

    def keyboard(self, e):
        if e.action.keydown and e.modifiers.ctrl and e.key == "Enter":
            asyncio.create_task(self.generate())

    def refresh_projects(self):
        self.project_selector.set_options(
            {p["id"]: p["name"] for p in self.projects.list()}, value=self.project_id
        )
        self.refresh_revisions()

    def select_project(self, e):
        self.project_id = e.value
        self.refresh_revisions()

    def refresh_revisions(self):
        rows = self.projects.revisions(self.project_id) if self.project_id else []
        self.revision_selector.set_options(
            {r["id"]: f"{r['label']} · {r['created']}" for r in rows}, value=rows[0]["id"] if rows else None
        )

    def create_project(self):
        try:
            self.project_id = self.projects.create(self.project_name.value)
            self.refresh_projects()
            ui.notify("Project created")
        except ValueError as exc:
            ui.notify(str(exc), type="negative")

    def duplicate(self):
        if not self.project_id:
            ui.notify("Select a project first", type="warning")
            return
        try:
            self.project_id = self.projects.duplicate(self.project_id, self.project_name.value + " copy")
            self.refresh_projects()
            ui.notify("Project duplicated from its latest saved revision")
        except (ValueError, OSError) as exc:
            ui.notify(str(exc), type="negative")

    def save(self):
        try:
            if not self.project_id or not self.result:
                raise ValueError("Create or select a project and generate a result first.")
            if (
                self.result["recipe"]["model"] != self.model_id
                or get_model(self.model_id).normalize(self.values()) != self.result["recipe"]["parameters"]
            ):
                raise ValueError(
                    "Parameters have changed. Generate successfully before saving this revision."
                )
            self.projects.save(self.project_id, self.revision_name.value, self.result, self.directory)
            self.refresh_revisions()
            ui.notify("Revision saved")
        except (ValueError, OSError) as exc:
            ui.notify(str(exc), type="negative")

    def load_recipe(self, recipe):
        self.cancel()
        self.selector.set_value(recipe["model"])
        self.model_id = recipe["model"]
        self.render_parameters(recipe["parameters"])
        self.edited()

    async def restore(self):
        if not self.revision_selector.value:
            return
        try:
            result, directory = self.projects.restore(self.revision_selector.value)
            self.load_recipe(result["recipe"])
            self.task = asyncio.current_task()
            serial = self.revision
            self.status.set_text("Loading preview")
            if not await self.show(result, directory, lambda: serial == self.revision):
                self.status.set_text("Outdated — parameters changed during preview loading")
                return
            self.status.set_text("Ready — saved revision restored")
        except asyncio.CancelledError:
            pass
        except (ValueError, OSError, TimeoutError) as exc:
            ui.notify(str(exc), type="negative")
        finally:
            if self.task is asyncio.current_task():
                self.task = None

    async def import_recipe(self, e):
        try:
            design = parse_recipe(await e.file.read())
            self.load_recipe(design)
            self.status.set_text("Recipe imported — Generate to inspect")
        except ValueError as exc:
            ui.notify(str(exc), type="negative")

    def clear_cache(self):
        self.service.cache.prune(0, set(self.service.pins.values()))
        ui.notify("Unused cache cleared; saved revisions and active results retained")

    def cleanup(self, *_):
        self.cancel()
        self.service.pins.pop(id(self), None)
