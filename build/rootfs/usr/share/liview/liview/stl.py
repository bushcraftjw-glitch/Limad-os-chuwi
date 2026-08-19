from __future__ import annotations

import math
import os
import struct
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import cairo
from PIL import Image

from .documents import BaseDocument, DocumentError


class StlDocument(BaseDocument):
    kind = "3d"

    def __init__(self, path: str):
        super().__init__(path)
        self.source_suffix = Path(self.path).suffix.lower()
        self.format_name = {".stl": "STL", ".obj": "OBJ", ".3mf": "3MF"}.get(self.source_suffix, "3D")
        self.triangles = self._load_model(self.path)
        if not self.triangles:
            raise DocumentError(f"{self.format_name} enthält keine darstellbaren Dreiecke.")
        self.yaw = math.radians(35.0)
        self.pitch = math.radians(-25.0)
        self.model_zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.projection = "perspective"
        self.wireframe = False
        self.show_grid = True
        self._calculate_bounds()

    @property
    def page_count(self) -> int:
        return 1

    @property
    def triangle_count(self) -> int:
        return len(self.triangles)

    @property
    def dimensions(self) -> tuple[float, float, float]:
        return self.size_x, self.size_y, self.size_z

    def page_size(self, index: int) -> tuple[float, float]:
        return 1040.0, 760.0

    def _load_model(self, path: str):
        if self.source_suffix == ".stl":
            return self._load_stl(path)
        if self.source_suffix == ".obj":
            return self._load_obj(path)
        if self.source_suffix == ".3mf":
            return self._load_3mf(path)
        raise DocumentError("Nicht unterstütztes 3D-Format.")

    def _load_stl(self, path: str):
        data = Path(path).read_bytes()
        if len(data) < 15:
            raise DocumentError("STL-Datei ist zu klein oder beschädigt.")
        if len(data) >= 84:
            count = struct.unpack_from("<I", data, 80)[0]
            expected = 84 + count * 50
            if count > 0 and expected <= len(data):
                return self._load_binary_stl(data, count)
        return self._load_ascii_stl(data)

    def _load_binary_stl(self, data: bytes, count: int):
        triangles = []
        offset = 84
        for _ in range(count):
            if offset + 50 > len(data):
                break
            values = struct.unpack_from("<12fH", data, offset)
            triangles.append((
                (float(values[3]), float(values[4]), float(values[5])),
                (float(values[6]), float(values[7]), float(values[8])),
                (float(values[9]), float(values[10]), float(values[11])),
            ))
            offset += 50
        return triangles

    def _load_ascii_stl(self, data: bytes):
        text = data.decode("utf-8", errors="replace")
        vertices = []
        triangles = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line.lower().startswith("vertex "):
                continue
            parts = line.split()
            if len(parts) != 4:
                continue
            try:
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
            except ValueError:
                continue
            if len(vertices) == 3:
                triangles.append(tuple(vertices))
                vertices = []
        return triangles

    def _load_obj(self, path: str):
        vertices: list[tuple[float, float, float]] = []
        triangles = []
        try:
            lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception as exc:
            raise DocumentError(f"OBJ konnte nicht gelesen werden: {exc}") from exc
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if parts[0] == "v" and len(parts) >= 4:
                try:
                    vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
                except ValueError:
                    continue
            elif parts[0] == "f" and len(parts) >= 4:
                face = []
                for token in parts[1:]:
                    index_text = token.split("/", 1)[0]
                    if not index_text:
                        face = []
                        break
                    try:
                        index = int(index_text)
                    except ValueError:
                        face = []
                        break
                    resolved = index - 1 if index > 0 else len(vertices) + index
                    if resolved < 0 or resolved >= len(vertices):
                        face = []
                        break
                    face.append(vertices[resolved])
                if len(face) >= 3:
                    anchor = face[0]
                    for index in range(1, len(face) - 1):
                        triangles.append((anchor, face[index], face[index + 1]))
        return triangles

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    @staticmethod
    def _identity_matrix():
        return (
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        )

    def _parse_3mf_transform(self, text: str | None):
        if not text:
            return self._identity_matrix()
        try:
            values = [float(value) for value in text.split()]
        except ValueError as exc:
            raise DocumentError("3MF enthält eine ungültige Transformation.") from exc
        if len(values) != 12:
            raise DocumentError("3MF-Transformation muss 12 Werte enthalten.")
        return (
            (values[0], values[1], values[2], 0.0),
            (values[3], values[4], values[5], 0.0),
            (values[6], values[7], values[8], 0.0),
            (values[9], values[10], values[11], 1.0),
        )

    @staticmethod
    def _matrix_multiply(a, b):
        return tuple(
            tuple(sum(a[row][k] * b[k][column] for k in range(4)) for column in range(4))
            for row in range(4)
        )

    @staticmethod
    def _transform_point(point, matrix):
        x, y, z = point
        vector = (x, y, z, 1.0)
        result = tuple(sum(vector[row] * matrix[row][column] for row in range(4)) for column in range(4))
        return float(result[0]), float(result[1]), float(result[2])

    def _load_3mf(self, path: str):
        try:
            with zipfile.ZipFile(path, "r") as archive:
                model_names = [name for name in archive.namelist() if name.lower().endswith(".model")]
                if not model_names:
                    raise DocumentError("3MF enthält keinen 3D-Modellteil.")
                preferred = next((name for name in model_names if name.lower() == "3d/3dmodel.model"), model_names[0])
                data = archive.read(preferred)
        except DocumentError:
            raise
        except (zipfile.BadZipFile, KeyError, OSError) as exc:
            raise DocumentError(f"3MF konnte nicht geöffnet werden: {exc}") from exc

        try:
            root = ET.fromstring(data)
        except ET.ParseError as exc:
            raise DocumentError(f"3MF-Modell-XML ist beschädigt: {exc}") from exc

        unit_factors = {
            "micron": 0.001,
            "millimeter": 1.0,
            "centimeter": 10.0,
            "inch": 25.4,
            "foot": 304.8,
            "meter": 1000.0,
        }
        unit_name = root.attrib.get("unit", "millimeter")
        unit_factor = unit_factors.get(unit_name)
        if unit_factor is None:
            raise DocumentError(f"3MF-Maßeinheit '{unit_name}' wird nicht unterstützt.")

        objects = {}
        resources = next((child for child in root if self._local_name(child.tag) == "resources"), None)
        build = next((child for child in root if self._local_name(child.tag) == "build"), None)
        if resources is None:
            raise DocumentError("3MF enthält keine Ressourcen.")
        for element in resources:
            if self._local_name(element.tag) == "object" and "id" in element.attrib:
                objects[element.attrib["id"]] = element

        def resolve_object(object_id: str, inherited, stack: tuple[str, ...]):
            if object_id in stack:
                raise DocumentError("3MF enthält eine zyklische Komponentenreferenz.")
            element = objects.get(object_id)
            if element is None:
                raise DocumentError(f"3MF verweist auf unbekanntes Objekt {object_id}.")
            next_stack = stack + (object_id,)
            output = []
            mesh = next((child for child in element if self._local_name(child.tag) == "mesh"), None)
            if mesh is not None:
                vertices_element = next((child for child in mesh if self._local_name(child.tag) == "vertices"), None)
                triangles_element = next((child for child in mesh if self._local_name(child.tag) == "triangles"), None)
                if vertices_element is not None and triangles_element is not None:
                    vertices = []
                    for vertex in vertices_element:
                        if self._local_name(vertex.tag) != "vertex":
                            continue
                        try:
                            vertices.append((float(vertex.attrib["x"]), float(vertex.attrib["y"]), float(vertex.attrib["z"])))
                        except (KeyError, ValueError) as exc:
                            raise DocumentError("3MF enthält einen ungültigen Vertex.") from exc
                    for triangle in triangles_element:
                        if self._local_name(triangle.tag) != "triangle":
                            continue
                        try:
                            indices = (int(triangle.attrib["v1"]), int(triangle.attrib["v2"]), int(triangle.attrib["v3"]))
                            raw = tuple(vertices[index] for index in indices)
                        except (KeyError, ValueError, IndexError) as exc:
                            raise DocumentError("3MF enthält ein ungültiges Dreieck.") from exc
                        transformed = tuple(self._transform_point(point, inherited) for point in raw)
                        output.append(transformed)
            components = next((child for child in element if self._local_name(child.tag) == "components"), None)
            if components is not None:
                for component in components:
                    if self._local_name(component.tag) != "component":
                        continue
                    referenced = component.attrib.get("objectid")
                    if not referenced:
                        raise DocumentError("3MF-Komponente ohne Objekt-ID.")
                    local_transform = self._parse_3mf_transform(component.attrib.get("transform"))
                    combined = self._matrix_multiply(local_transform, inherited)
                    output.extend(resolve_object(referenced, combined, next_stack))
            return output

        triangles = []
        identity = self._identity_matrix()
        if build is not None:
            for item in build:
                if self._local_name(item.tag) != "item":
                    continue
                object_id = item.attrib.get("objectid")
                if not object_id:
                    continue
                transform = self._parse_3mf_transform(item.attrib.get("transform"))
                triangles.extend(resolve_object(object_id, transform, ()))
        if not triangles:
            for object_id in objects:
                triangles.extend(resolve_object(object_id, identity, ()))
        if unit_factor != 1.0:
            triangles = [
                tuple((x * unit_factor, y * unit_factor, z * unit_factor) for x, y, z in triangle)
                for triangle in triangles
            ]
        return triangles

    def _calculate_bounds(self) -> None:
        xs, ys, zs = [], [], []
        for triangle in self.triangles:
            for x, y, z in triangle:
                xs.append(x)
                ys.append(y)
                zs.append(z)
        self.min_x, self.max_x = min(xs), max(xs)
        self.min_y, self.max_y = min(ys), max(ys)
        self.min_z, self.max_z = min(zs), max(zs)
        self.center = (
            (self.min_x + self.max_x) / 2.0,
            (self.min_y + self.max_y) / 2.0,
            (self.min_z + self.max_z) / 2.0,
        )
        self.size_x = self.max_x - self.min_x
        self.size_y = self.max_y - self.min_y
        self.size_z = self.max_z - self.min_z
        self.max_dimension = max(self.size_x, self.size_y, self.size_z, 1e-9)

    def reset_view(self) -> None:
        self.yaw = math.radians(35.0)
        self.pitch = math.radians(-25.0)
        self.fit_view()

    def fit_view(self) -> None:
        self.model_zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0

    def set_orbit(self, yaw: float, pitch: float) -> None:
        self.yaw = yaw
        self.pitch = max(math.radians(-89.0), min(math.radians(89.0), pitch))

    def set_view(self, name: str) -> None:
        views = {
            "iso": (35.0, -25.0),
            "front": (0.0, 0.0),
            "back": (180.0, 0.0),
            "left": (-90.0, 0.0),
            "right": (90.0, 0.0),
            "top": (0.0, -89.0),
            "bottom": (0.0, 89.0),
        }
        if name not in views:
            raise DocumentError("Unbekannte 3D-Ansicht.")
        yaw, pitch = views[name]
        self.yaw = math.radians(yaw)
        self.pitch = math.radians(pitch)
        self.fit_view()

    def zoom_model(self, factor: float) -> None:
        self.model_zoom = max(0.15, min(12.0, self.model_zoom * factor))

    def pan_model(self, x: float, y: float) -> None:
        self.pan_x = max(-1600.0, min(1600.0, x))
        self.pan_y = max(-1200.0, min(1200.0, y))

    def toggle_projection(self) -> None:
        self.projection = "orthographic" if self.projection == "perspective" else "perspective"

    def toggle_wireframe(self) -> None:
        self.wireframe = not self.wireframe

    def toggle_grid(self) -> None:
        self.show_grid = not self.show_grid

    def rotate(self, page_index: int, degrees: int) -> None:
        self.yaw += math.radians(float(degrees))

    def _rotate_point(self, point):
        x = point[0] - self.center[0]
        y = point[1] - self.center[1]
        z = point[2] - self.center[2]
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        x1 = cy * x + sy * z
        z1 = -sy * x + cy * z
        y2 = cp * y - sp * z1
        z2 = sp * y + cp * z1
        return x1, y2, z2

    @staticmethod
    def _normal(a, b, c):
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        return nx / length, ny / length, nz / length

    def _project(self, point, cx: float, cy: float, view_scale: float):
        x, y, z = point
        factor = 1.0
        if self.projection == "perspective":
            camera_distance = self.max_dimension * 4.5
            denominator = max(self.max_dimension * 1.25, camera_distance - z)
            factor = camera_distance / denominator
        return cx + x * view_scale * factor, cy - y * view_scale * factor

    def _draw_background(self, cr: cairo.Context, width: float, height: float) -> None:
        gradient = cairo.LinearGradient(0.0, 0.0, 0.0, height)
        gradient.add_color_stop_rgb(0.0, 0.105, 0.115, 0.135)
        gradient.add_color_stop_rgb(1.0, 0.055, 0.060, 0.073)
        cr.set_source(gradient)
        cr.rectangle(0.0, 0.0, width, height)
        cr.fill()

    def _draw_grid(self, cr: cairo.Context, cx: float, cy: float, view_scale: float) -> None:
        if not self.show_grid:
            return
        extent = self.max_dimension * 1.35
        floor_y = self.min_y - self.center[1] - self.max_dimension * 0.04
        steps = 12
        spacing = extent * 2.0 / steps
        cr.save()
        cr.set_line_width(0.75)
        for index in range(steps + 1):
            value = -extent + index * spacing
            alpha = 0.18 if index != steps // 2 else 0.36
            cr.set_source_rgba(0.72, 0.76, 0.82, alpha)
            p1 = self._project(self._rotate_point((self.center[0] - extent, self.center[1] + floor_y, self.center[2] + value)), cx, cy, view_scale)
            p2 = self._project(self._rotate_point((self.center[0] + extent, self.center[1] + floor_y, self.center[2] + value)), cx, cy, view_scale)
            cr.move_to(*p1)
            cr.line_to(*p2)
            cr.stroke()
            p3 = self._project(self._rotate_point((self.center[0] + value, self.center[1] + floor_y, self.center[2] - extent)), cx, cy, view_scale)
            p4 = self._project(self._rotate_point((self.center[0] + value, self.center[1] + floor_y, self.center[2] + extent)), cx, cy, view_scale)
            cr.move_to(*p3)
            cr.line_to(*p4)
            cr.stroke()
        cr.restore()

    def render_page(self, index: int, cr: cairo.Context, scale: float) -> None:
        width, height = self.page_size(0)
        cr.save()
        cr.scale(scale, scale)
        self._draw_background(cr, width, height)
        view_scale = (min(width, height) * 0.64 / self.max_dimension) * self.model_zoom
        cx = width / 2.0 + self.pan_x
        cy = height / 2.0 + self.pan_y - 12.0
        self._draw_grid(cr, cx, cy, view_scale)
        rendered = []
        max_faces = 120000
        step = max(1, len(self.triangles) // max_faces)
        key_light = (0.32, -0.48, 0.82)
        fill_light = (-0.62, 0.22, 0.58)
        for triangle in self.triangles[::step]:
            rotated = [self._rotate_point(point) for point in triangle]
            normal = self._normal(rotated[0], rotated[1], rotated[2])
            key = max(0.0, normal[0] * key_light[0] + normal[1] * key_light[1] + normal[2] * key_light[2])
            fill = max(0.0, normal[0] * fill_light[0] + normal[1] * fill_light[1] + normal[2] * fill_light[2])
            intensity = min(1.0, 0.22 + key * 0.62 + fill * 0.20)
            points = [self._project(point, cx, cy, view_scale) for point in rotated]
            depth = (rotated[0][2] + rotated[1][2] + rotated[2][2]) / 3.0
            rendered.append((depth, intensity, points))
        rendered.sort(key=lambda item: item[0])
        for _, intensity, points in rendered:
            cr.move_to(*points[0])
            cr.line_to(*points[1])
            cr.line_to(*points[2])
            cr.close_path()
            if self.wireframe:
                cr.set_source_rgba(0.84, 0.89, 0.96, 0.86)
                cr.set_line_width(0.85)
                cr.stroke()
                continue
            base = 0.42 + intensity * 0.44
            cr.set_source_rgb(base * 0.86, base * 0.92, base)
            cr.fill_preserve()
            cr.set_source_rgba(0.04, 0.05, 0.065, 0.34)
            cr.set_line_width(0.45)
            cr.stroke()
        cr.restore()

    def save(self) -> None:
        self.dirty = False

    def save_as(self, target: str) -> None:
        target = os.path.abspath(target)
        if Path(target).suffix.lower() != self.source_suffix:
            raise DocumentError(f"{self.format_name} muss als {self.source_suffix} gespeichert werden.")
        Path(target).write_bytes(Path(self.path).read_bytes())
        self.path = target
        self.dirty = False

    def _render_surface(self, width: int = 1920, height: int = 1440) -> cairo.ImageSurface:
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        cr = cairo.Context(surface)
        logical_width, logical_height = self.page_size(0)
        factor = min(width / logical_width, height / logical_height)
        cr.translate((width - logical_width * factor) / 2.0, (height - logical_height * factor) / 2.0)
        self.render_page(0, cr, factor)
        surface.flush()
        return surface

    def export(self, target: str, page_index: int) -> None:
        target_path = Path(target)
        suffix = target_path.suffix.lower()
        surface = self._render_surface()
        if suffix == ".png":
            surface.write_to_png(str(target_path))
            return
        if suffix in {".jpg", ".jpeg"}:
            temp = target_path.with_suffix(target_path.suffix + ".tmp.png")
            try:
                surface.write_to_png(str(temp))
                with Image.open(temp) as image:
                    image.convert("RGB").save(target_path, format="JPEG", quality=95)
            finally:
                temp.unlink(missing_ok=True)
            return
        raise DocumentError("3D-Vorschau kann als PNG oder JPEG exportiert werden.")

    def print_page(self, page_index: int, cr: cairo.Context, width: float, height: float) -> None:
        logical_width, logical_height = self.page_size(0)
        factor = min(width / logical_width, height / logical_height)
        cr.save()
        cr.translate((width - logical_width * factor) / 2.0, (height - logical_height * factor) / 2.0)
        self.render_page(0, cr, factor)
        cr.restore()
