from build123d import Box, Compound, Cylinder, Pos


def generate(p):
    length, w, h, r, t = p["length"], p["width"], p["height"], p["wheel_radius"], p["wheel_width"]
    body = Pos(0, 0, r + h / 2) * Box(length, w, h)
    cabin = Pos(-length / 12, 0, r + 1.4 * h) * Box(length * 0.45, w * 0.85, h * 0.8)
    body.label, cabin.label = "Body", "Cabin"
    pieces = [body, cabin]
    for x in (-length / 3, length / 3):
        for y in (-(w + t) / 2, (w + t) / 2):
            wheel = Pos(x, y, r) * Cylinder(r, t, rotation=(90, 0, 0))
            wheel.label = "Wheel"
            pieces.append(wheel)
    return Compound(children=pieces)
