import json
import struct

from build123d import ExportDXF, ExportSVG, export_gltf, export_step, export_stl

from cadforge.models.registry import get_model
from cadforge.services.cache import EXPORT_SETTINGS


def export_shape(shape, recipe, directory):
    formats = get_model(recipe["model"]).formats(recipe["parameters"])
    files = {}
    for fmt in formats:
        path = directory / f"model.{fmt}"
        if fmt == "step":
            export_step(shape, path)
        elif fmt == "stl":
            export_stl(shape, path, tolerance=EXPORT_SETTINGS["stl_deflection"])
        elif fmt == "glb":
            export_gltf(shape, path, binary=True, linear_deflection=EXPORT_SETTINGS["preview_deflection"])
        elif fmt in ("svg", "dxf"):
            exporter = ExportSVG() if fmt == "svg" else ExportDXF()
            exporter.add_shape(shape)
            exporter.write(path)
        else:
            path.write_text(json.dumps(recipe, indent=2), encoding="utf-8")
        if fmt == "glb":
            matte_materials(path)
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError(f"{fmt.upper()} export did not produce a file.")
        files[fmt] = path.name
    export_gltf(
        shape, directory / "preview.glb", binary=True, linear_deflection=EXPORT_SETTINGS["preview_deflection"]
    )
    matte_materials(directory / "preview.glb")
    vertices, triangles = shape.tessellate(
        EXPORT_SETTINGS["preview_deflection"], EXPORT_SETTINGS["angular_deflection"]
    )
    preview = {"vertices": [list(v) for v in vertices], "triangles": [list(t) for t in triangles]}
    (directory / "preview.json").write_text(json.dumps(preview), encoding="utf-8")
    return files


def matte_materials(path):
    """Use non-metallic preview materials: glTF defaults to metal without an environment map."""
    data = path.read_bytes()
    length = struct.unpack_from("<I", data, 12)[0]
    document = json.loads(data[20 : 20 + length])
    materials = document.setdefault("materials", [])
    default = len(materials)
    materials.append({"pbrMetallicRoughness": {"baseColorFactor": [0.49, 0.71, 0.87, 1]}})
    for material in materials:
        pbr = material.setdefault("pbrMetallicRoughness", {})
        pbr["metallicFactor"] = 0
        pbr["roughnessFactor"] = 0.7
    for mesh in document.get("meshes", []):
        for primitive in mesh["primitives"]:
            primitive.setdefault("material", default)
    encoded = json.dumps(document, separators=(",", ":")).encode()
    encoded += b" " * (-len(encoded) % 4)
    remaining = data[20 + length :]
    header = struct.pack("<4sII", b"glTF", 2, 20 + len(encoded) + len(remaining))
    path.write_bytes(header + struct.pack("<I4s", len(encoded), b"JSON") + encoded + remaining)
