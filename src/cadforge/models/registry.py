from cadforge.models.parameters import Model
from cadforge.models.parameters import Parameter as P

MODELS = {
    m.id: m
    for m in (
        Model(
            "block",
            "Parametric block",
            "A solid reference part with exact dimensions.",
            (P("length", "Length", 60), P("width", "Width", 40), P("height", "Height", 20)),
            {"Cube": {"length": 40, "width": 40, "height": 40}},
        ),
        Model(
            "airfoil",
            "NACA airfoil",
            "Closed four-digit NACA profile, or a straight extruded wing.",
            (
                P("code", "NACA code", "2412", unit=""),
                P("chord", "Chord", 100),
                P("span", "Span", 150, minimum=0),
                P("mode", "Geometry", "solid", choices=("solid", "profile"), unit=""),
            ),
            {"Symmetric 0012": {"code": "0012"}, "2D profile": {"mode": "profile", "span": 0}},
        ),
        Model(
            "car",
            "Simple car",
            "Educational assembly: body, cabin and four independent wheels.",
            (
                P("length", "Body length", 100),
                P("width", "Body width", 40),
                P("height", "Body height", 16),
                P("wheel_radius", "Wheel radius", 10),
                P("wheel_width", "Wheel width", 6),
            ),
            {"Long body": {"length": 140}},
        ),
        Model(
            "bracket",
            "Mounting bracket",
            "L-shaped solid with one mounting hole in each leg.",
            (
                P("base", "Base leg", 60),
                P("height", "Upright leg", 50),
                P("width", "Width", 30),
                P("thickness", "Thickness", 5),
                P("diameter", "Hole diameter", 6),
            ),
            {"Heavy duty": {"thickness": 8, "diameter": 10}},
        ),
        Model(
            "plate",
            "Hole-pattern plate",
            "A rectangular plate with a centered grid of through holes.",
            (
                P("length", "Length", 100),
                P("width", "Width", 70),
                P("thickness", "Thickness", 5),
                P("columns", "Columns", 3, 1, 12, "", integer=True),
                P("rows", "Rows", 2, 1, 12, "", integer=True),
                P("diameter", "Hole diameter", 6),
                P("spacing", "Hole spacing", 20),
            ),
            {"Four holes": {"columns": 2, "rows": 2, "spacing": 40}},
        ),
        Model(
            "enclosure",
            "Enclosure",
            "Open box and a separate flat lid shown beside it.",
            (
                P("length", "Length", 100),
                P("width", "Width", 70),
                P("height", "Height", 40),
                P("wall", "Wall / lid thickness", 3),
            ),
            {"Compact": {"length": 60, "width": 40, "height": 25, "wall": 2}},
        ),
    )
}


def get_model(model_id):
    try:
        return MODELS[model_id]
    except (KeyError, TypeError):
        raise ValueError(f"Unknown model: {model_id!r}.") from None


def generate(model_id, parameters):
    from importlib import import_module

    model = get_model(model_id)
    return import_module(f"cadforge.models.{model_id}").generate(model.normalize(parameters))
