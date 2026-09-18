import argparse

from nicegui import app, ui

from cadforge.services.generation import GenerationService
from cadforge.services.projects import Projects
from cadforge.settings import Settings
from cadforge.ui.workspace import Workspace


def main():
    parser = argparse.ArgumentParser(description="CADForge local parametric CAD workbench")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    settings = Settings.load()
    service = GenerationService(settings)
    projects = Projects(settings.data)

    @ui.page("/")
    def workspace():
        Workspace(service, projects)

    app.on_shutdown(service.close)
    ui.run(host="127.0.0.1", port=args.port, title="CADForge", reload=False, show=not args.no_browser)
