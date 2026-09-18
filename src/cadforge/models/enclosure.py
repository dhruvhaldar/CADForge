from build123d import Box, Compound, Pos


def generate(p):
    length, w, h, t = p["length"], p["width"], p["height"], p["wall"]
    body = Box(length, w, h) - Pos(0, 0, t) * Box(length - 2 * t, w - 2 * t, h)
    body.label = "Box"
    lid = Pos(length + 10, 0, -(h - t) / 2) * Box(length, w, t)
    lid.label = "Lid"
    return Compound(children=[body, lid])
