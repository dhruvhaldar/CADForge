import json
import shutil
import uuid
from contextlib import closing
from pathlib import Path

from cadforge.services.recipes import parse_recipe
from cadforge.storage.database import connect


class Projects:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.artifacts = self.root / "revisions"
        self.artifacts.mkdir(exist_ok=True)
        self.database = self.root / "cadforge.sqlite3"
        with closing(connect(self.database)):
            pass

    @staticmethod
    def name(value):
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= 120:
            raise ValueError("Names must contain 1–120 characters.")
        return value.strip()

    def create(self, name):
        identifier = uuid.uuid4().hex
        with closing(connect(self.database)) as db, db:
            db.execute("INSERT INTO projects(id,name) VALUES (?,?)", (identifier, self.name(name)))
        return identifier

    def list(self):
        with closing(connect(self.database)) as db:
            return [
                dict(row) for row in db.execute("SELECT * FROM projects ORDER BY created DESC, rowid DESC")
            ]

    def revisions(self, project):
        with closing(connect(self.database)) as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM revisions WHERE project_id=? ORDER BY created DESC, rowid DESC", (project,)
                )
            ]

    def save(self, project, label, result, source):
        label = self.name(label)
        design = parse_recipe(result["recipe"])
        identifier = uuid.uuid4().hex
        target = self.artifacts / identifier
        staging = self.artifacts / f".{identifier}"
        try:
            shutil.copytree(source, staging)
            staging.rename(target)
            with closing(connect(self.database)) as db, db:
                db.execute(
                    "INSERT INTO revisions(id,project_id,label,recipe,artifact) VALUES (?,?,?,?,?)",
                    (identifier, project, label, json.dumps(design), identifier),
                )
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            shutil.rmtree(target, ignore_errors=True)
            raise
        return identifier

    def restore(self, revision_id):
        with closing(connect(self.database)) as db:
            row = db.execute("SELECT * FROM revisions WHERE id=?", (revision_id,)).fetchone()
        if row is None:
            raise ValueError("Revision does not exist.")
        design = parse_recipe(row["recipe"])
        path = self.artifacts / row["artifact"]
        result = json.loads((path / "result.json").read_text(encoding="utf-8"))
        if result["recipe"] != design:
            raise ValueError("Revision artifacts do not match the saved recipe.")
        return result, path

    def duplicate(self, project, name):
        revisions = self.revisions(project)
        new = self.create(name)
        if revisions:
            result, source = self.restore(revisions[0]["id"])
            self.save(new, "Duplicated design", result, source)
        return new
