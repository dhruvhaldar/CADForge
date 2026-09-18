from build123d import Box, Cylinder, Pos


def generate(p):
    part = Box(p["length"], p["width"], p["thickness"])
    for column in range(p["columns"]):
        for row in range(p["rows"]):
            x = (column - (p["columns"] - 1) / 2) * p["spacing"]
            y = (row - (p["rows"] - 1) / 2) * p["spacing"]
            part -= Pos(x, y, 0) * Cylinder(p["diameter"] / 2, p["thickness"] * 2)
    return part
