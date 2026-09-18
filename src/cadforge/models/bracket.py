from build123d import Align, Box, Cylinder, Pos


def generate(p):
    t, b, h, w = p["thickness"], p["base"], p["height"], p["width"]
    align = (Align.MIN, Align.CENTER, Align.MIN)
    part = Box(b, w, t, align=align) + Box(t, w, h, align=align)
    part -= Pos((b + t) / 2, 0, t / 2) * Cylinder(p["diameter"] / 2, 2 * t)
    part -= Pos(t / 2, 0, (h + t) / 2) * Cylinder(p["diameter"] / 2, 2 * t, rotation=(0, 90, 0))
    return part
