import math
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Parameter:
    name: str
    label: str
    default: Any
    minimum: float = 0.1
    maximum: float = 1000
    unit: str = "mm"
    choices: tuple[str, ...] = ()
    integer: bool = False

    def normalize(self, value):
        if self.choices:
            if value not in self.choices:
                raise ValueError(f"{self.label}: choose {', '.join(self.choices)}.")
            return value
        if isinstance(self.default, str):
            if not isinstance(value, str):
                raise ValueError(f"{self.label} must be text.")
            return value.strip()
        if isinstance(value, bool):
            raise ValueError(f"{self.label} must be a number.")
        try:
            number = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"{self.label} must be a number.") from None
        if not math.isfinite(number) or not self.minimum <= number <= self.maximum:
            raise ValueError(
                f"{self.label} must be between {self.minimum:g} and {self.maximum:g} {self.unit}."
            )
        if self.integer and not number.is_integer():
            raise ValueError(f"{self.label} must be a whole number.")
        return int(number) if self.integer else number


@dataclass(frozen=True)
class Model:
    id: str
    title: str
    description: str
    parameters: tuple[Parameter, ...]
    presets: dict = field(default_factory=dict)
    version: str = "1"

    def defaults(self):
        return {p.name: p.default for p in self.parameters}

    def normalize(self, values):
        if not isinstance(values, dict):
            raise ValueError("Parameters must be an object.")
        unknown = set(values) - set(self.defaults())
        if unknown:
            raise ValueError(f"Unknown parameters: {', '.join(sorted(unknown))}.")
        p = {s.name: s.normalize(values.get(s.name, s.default)) for s in self.parameters}
        if self.id == "airfoil":
            code = p["code"]
            if len(code) != 4 or not code.isascii() or not code.isdigit():
                raise ValueError("NACA code must contain exactly four digits, e.g. 2412.")
            if int(code[2:]) == 0 or (code[0] != "0" and code[1] == "0"):
                raise ValueError(
                    "NACA thickness must be positive; cambered profiles need a nonzero camber position."
                )
            if code[0] == "0" and code[1] != "0":
                raise ValueError("Symmetric NACA profiles must start with 00.")
            if p["mode"] == "solid" and p["span"] <= 0:
                raise ValueError("Solid airfoils need a positive span. Choose profile for 2D geometry.")
        if self.id == "plate":
            if p["spacing"] <= p["diameter"]:
                raise ValueError("Hole spacing must exceed hole diameter.")
            if (p["columns"] - 1) * p["spacing"] + p["diameter"] >= p["length"] or (p["rows"] - 1) * p[
                "spacing"
            ] + p["diameter"] >= p["width"]:
                raise ValueError("Hole pattern must fit inside the plate with material around every hole.")
        if self.id == "bracket":
            if 2 * p["thickness"] >= min(p["base"], p["height"]):
                raise ValueError("Thickness must be less than half of each leg.")
            if p["diameter"] >= min(p["width"], p["base"] - p["thickness"], p["height"] - p["thickness"]):
                raise ValueError("Mounting holes must fit within both legs.")
        if self.id == "enclosure" and 2 * p["wall"] >= min(p["length"], p["width"], p["height"]):
            raise ValueError("Wall thickness must be less than half of every enclosure dimension.")
        if self.id == "car":
            if 4 * p["wheel_radius"] >= p["length"]:
                raise ValueError("Body length must exceed four wheel radii so the wheels stay separate.")
        return p

    def formats(self, parameters):
        return (
            ("svg", "dxf", "json") if parameters.get("mode") == "profile" else ("step", "stl", "glb", "json")
        )
