import json

from cadforge.models.registry import get_model


def recipe(model_id, parameters):
    model = get_model(model_id)
    return {
        "schema_version": 1,
        "model": model.id,
        "generator_version": model.version,
        "units": "mm",
        "parameters": model.normalize(parameters),
    }


def parse_recipe(raw):
    try:
        obj = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
    except (ValueError, UnicodeError):
        raise ValueError("Recipe is not valid UTF-8 JSON.") from None
    if not isinstance(obj, dict) or obj.get("schema_version") != 1:
        raise ValueError("Unsupported recipe schema. CADForge supports version 1.")
    model = get_model(obj.get("model"))
    if obj.get("generator_version") != model.version or obj.get("units") != "mm":
        raise ValueError(
            "Unsupported generator version or units; this release requires current generators and mm."
        )
    if not isinstance(obj.get("parameters"), dict) or set(obj["parameters"]) != set(model.defaults()):
        raise ValueError("Recipe must contain every model parameter exactly once.")
    return recipe(model.id, obj["parameters"])
