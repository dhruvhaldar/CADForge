"""Private subprocess entry point. Accepts only registered models, never user code."""

import json
import sys
import time
from pathlib import Path


def main():
    started = time.perf_counter()
    output = Path(sys.argv[2])
    try:
        from cadforge.models.registry import generate
        from cadforge.services.exports import export_shape
        from cadforge.services.recipes import parse_recipe

        recipe = parse_recipe(Path(sys.argv[1]).read_text(encoding="utf-8"))
        shape = generate(recipe["model"], recipe["parameters"])
        valid = shape.is_valid
        if not valid:
            raise ValueError("The kernel produced invalid geometry. Try less extreme parameters.")
        dimensions = list(shape.bounding_box().size)
        solids = len(shape.solids())
        files = export_shape(shape, recipe, output)
        result = {
            "recipe": recipe,
            "center": list(shape.bounding_box().center()),
            "dimensions": dimensions,
            "volume": shape.volume if solids else None,
            "solids": solids,
            "valid": valid,
            "duration": time.perf_counter() - started,
            "files": files,
        }
        (output / "result.json").write_text(json.dumps(result), encoding="utf-8")
    except Exception as exc:
        (output / "error.txt").write_text(f"{type(exc).__name__}: {exc}", encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
