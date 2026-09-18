import math

from build123d import Face, Wire, extrude


def generate(p):
    code = p["code"]
    m, location, thickness = int(code[0]) / 100, int(code[1]) / 10, int(code[2:]) / 100
    upper, lower = [], []
    for i in range(101):
        x = (1 - math.cos(math.pi * i / 100)) / 2
        yt = (
            5
            * thickness
            * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x * x + 0.2843 * x**3 - 0.1036 * x**4)
        )
        if not m:
            yc, slope = 0, 0
        elif x < location:
            yc = m / location**2 * (2 * location * x - x * x)
            slope = 2 * m / location**2 * (location - x)
        else:
            yc = m / (1 - location) ** 2 * (1 - 2 * location + 2 * location * x - x * x)
            slope = 2 * m / (1 - location) ** 2 * (location - x)
        angle = math.atan(slope)
        upper.append(((x - yt * math.sin(angle)) * p["chord"], (yc + yt * math.cos(angle)) * p["chord"], 0))
        lower.append(((x + yt * math.sin(angle)) * p["chord"], (yc - yt * math.cos(angle)) * p["chord"], 0))
    # Cosine-spaced polygon; trailing edge is explicitly closed, without a fictitious thickness.
    profile = Face(Wire.make_polygon(upper + lower[-2:0:-1], close=True))
    return profile if p["mode"] == "profile" else extrude(profile, amount=p["span"])
