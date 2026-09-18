from build123d import Box


def generate(p):
    return Box(p["length"], p["width"], p["height"])
