from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cairo
import gi

gi.require_version("Gio", "2.0")
gi.require_version("Poppler", "0.18")
from gi.repository import Gio, Poppler
from PIL import Image, ImageDraw, ImageFont, ImageOps
import pikepdf


@dataclass(frozen=True)
class SearchHit:
    page_index: int
    rect: tuple[float, float, float, float]


@dataclass(frozen=True)
class FormFieldInfo:
    name: str
    kind: str
    value: str | bool
    options: tuple[str, ...] = ()
    editable: bool = True


class DocumentError(RuntimeError):
    pass


class PdfPasswordRequired(DocumentError):
    pass


class BaseDocument:
    kind = "base"

    def __init__(self, path: str):
        self.path = os.path.abspath(path)
        self.dirty = False
        self._thumbnail_cache: dict[tuple[int, int, int], cairo.ImageSurface] = {}

    @property
    def title(self) -> str:
        return os.path.basename(self.path)

    @property
    def page_count(self) -> int:
        raise NotImplementedError

    def page_size(self, index: int) -> tuple[float, float]:
        raise NotImplementedError

    def render_page(self, index: int, cr: cairo.Context, scale: float) -> None:
        raise NotImplementedError

    def render_thumbnail(self, index: int, max_width: int = 132, max_height: int = 176) -> cairo.ImageSurface:
        key = (index, max_width, max_height)
        cached = self._thumbnail_cache.get(key)
        if cached is not None:
            return cached
        width, height = self.page_size(index)
        factor = min(max_width / width, max_height / height)
        pixel_width = max(1, int(round(width * factor)))
        pixel_height = max(1, int(round(height * factor)))
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, pixel_width, pixel_height)
        cr = cairo.Context(surface)
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.paint()
        self.render_page(index, cr, factor)
        surface.flush()
        self._thumbnail_cache[key] = surface
        return surface

    def clear_thumbnail_cache(self) -> None:
        self._thumbnail_cache.clear()

    def save(self) -> None:
        raise NotImplementedError

    def save_as(self, target: str) -> None:
        raise NotImplementedError

    def export(self, target: str, page_index: int) -> None:
        raise NotImplementedError

    def close(self) -> None:
        return None


class PdfDocument(BaseDocument):
    kind = "pdf"

    def __init__(self, path: str, password: str = ""):
        super().__init__(path)
        self._tmp = tempfile.TemporaryDirectory(prefix="liview-")
        self._work_path = os.path.join(self._tmp.name, "document.pdf")
        self._poppler = None
        self._history_counter = 0
        self._undo_paths: list[str] = []
        self._redo_paths: list[str] = []
        self.source_encrypted = False
        self._source_password = password
        try:
            with pikepdf.Pdf.open(self.path, password=password) as source:
                self.source_encrypted = bool(source.is_encrypted)
                if self.source_encrypted:
                    source.save(self._work_path)
                else:
                    shutil.copy2(self.path, self._work_path)
        except pikepdf.PasswordError as exc:
            self._tmp.cleanup()
            raise PdfPasswordRequired("Für dieses PDF ist ein Passwort erforderlich.") from exc
        except Exception as exc:
            self._tmp.cleanup()
            raise DocumentError(f"PDF konnte nicht geöffnet werden: {exc}") from exc
        self._reload()

    @property
    def page_count(self) -> int:
        return self._poppler.get_n_pages()

    def _reload(self) -> None:
        self.clear_thumbnail_cache()
        uri = Path(self._work_path).resolve().as_uri()
        try:
            self._poppler = Poppler.Document.new_from_file(uri, None)
        except Exception as exc:
            raise DocumentError(f"PDF konnte nicht geöffnet werden: {exc}") from exc

    def _page(self, index: int):
        page = self._poppler.get_page(index)
        if page is None:
            raise DocumentError(f"PDF-Seite {index + 1} existiert nicht.")
        return page

    def page_size(self, index: int) -> tuple[float, float]:
        return tuple(float(value) for value in self._page(index).get_size())

    def render_page(self, index: int, cr: cairo.Context, scale: float) -> None:
        cr.save()
        cr.scale(scale, scale)
        self._page(index).render(cr)
        cr.restore()

    def search(self, query: str) -> list[SearchHit]:
        query = query.strip()
        if not query:
            return []
        hits: list[SearchHit] = []
        for page_index in range(self.page_count):
            page = self._page(page_index)
            try:
                rectangles = page.find_text(query)
            except Exception:
                rectangles = []
            for rect in rectangles or []:
                hits.append(SearchHit(page_index, (rect.x1, rect.y1, rect.x2, rect.y2)))
        return hits

    def selected_text(self, page_index: int, rect: tuple[float, float, float, float]) -> str:
        x1, y1, x2, y2 = rect
        width, height = self.page_size(page_index)
        x_low = max(0.0, min(width, min(x1, x2)))
        x_high = max(0.0, min(width, max(x1, x2)))
        y_top = max(0.0, min(height, min(y1, y2)))
        y_bottom = max(0.0, min(height, max(y1, y2)))
        poppler_rect = Poppler.Rectangle()
        poppler_rect.x1 = x_low
        poppler_rect.x2 = x_high
        poppler_rect.y1 = height - y_bottom
        poppler_rect.y2 = height - y_top
        text = self._page(page_index).get_selected_text(Poppler.SelectionStyle.GLYPH, poppler_rect)
        return text or ""

    def _snapshot(self, stack: list[str]) -> str:
        self._history_counter += 1
        path = os.path.join(self._tmp.name, f"history-{self._history_counter}.pdf")
        shutil.copy2(self._work_path, path)
        stack.append(path)
        while len(stack) > 20:
            old_path = stack.pop(0)
            if os.path.exists(old_path):
                os.unlink(old_path)
        return path

    def _clear_history(self, stack: list[str]) -> None:
        for path in stack:
            if os.path.exists(path):
                os.unlink(path)
        stack.clear()

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_paths)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_paths)

    def undo(self) -> None:
        if not self._undo_paths:
            return
        self._snapshot(self._redo_paths)
        previous = self._undo_paths.pop()
        shutil.copy2(previous, self._work_path)
        if os.path.exists(previous):
            os.unlink(previous)
        self.dirty = True
        self._reload()

    def redo(self) -> None:
        if not self._redo_paths:
            return
        self._snapshot(self._undo_paths)
        next_path = self._redo_paths.pop()
        shutil.copy2(next_path, self._work_path)
        if os.path.exists(next_path):
            os.unlink(next_path)
        self.dirty = True
        self._reload()

    def _edit(self, callback) -> None:
        next_path = os.path.join(self._tmp.name, "next.pdf")
        if os.path.exists(next_path):
            os.unlink(next_path)
        snapshot = self._snapshot(self._undo_paths)
        self._clear_history(self._redo_paths)
        try:
            with pikepdf.Pdf.open(self._work_path) as pdf:
                callback(pdf)
                pdf.save(next_path)
            os.replace(next_path, self._work_path)
            self.dirty = True
            self._reload()
        except Exception as exc:
            if os.path.exists(next_path):
                os.unlink(next_path)
            if self._undo_paths and self._undo_paths[-1] == snapshot:
                self._undo_paths.pop()
            if os.path.exists(snapshot):
                os.unlink(snapshot)
            raise DocumentError(str(exc)) from exc

    def rotate(self, page_index: int, degrees: int) -> None:
        def apply(pdf: pikepdf.Pdf) -> None:
            pdf.pages[page_index].rotate(degrees, relative=True)
        self._edit(apply)

    def delete_page(self, page_index: int) -> None:
        if self.page_count <= 1:
            raise DocumentError("Die letzte PDF-Seite kann nicht gelöscht werden.")
        def apply(pdf: pikepdf.Pdf) -> None:
            del pdf.pages[page_index]
        self._edit(apply)

    def duplicate_page(self, page_index: int) -> None:
        def apply(pdf: pikepdf.Pdf) -> None:
            pdf.pages.insert(page_index + 1, pdf.pages[page_index])
        self._edit(apply)

    def move_page(self, page_index: int, new_index: int) -> int:
        if page_index == new_index:
            return page_index
        new_index = max(0, min(self.page_count - 1, new_index))
        def apply(pdf: pikepdf.Pdf) -> None:
            moved = pdf.pages[page_index]
            del pdf.pages[page_index]
            pdf.pages.insert(new_index, moved)
        self._edit(apply)
        return new_index

    def append_pdf(self, source_path: str) -> None:
        source_path = os.path.abspath(source_path)
        def apply(pdf: pikepdf.Pdf) -> None:
            with pikepdf.Pdf.open(source_path) as source:
                pdf.pages.extend(source.pages)
        self._edit(apply)

    def crop(self, page_index: int, display_rect: tuple[float, float, float, float]) -> None:
        x1, y1, x2, y2 = display_rect
        display_width, display_height = self.page_size(page_index)
        x1 = max(0.0, min(display_width, x1))
        x2 = max(0.0, min(display_width, x2))
        y1 = max(0.0, min(display_height, y1))
        y2 = max(0.0, min(display_height, y2))
        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))
        if right - left < 4.0 or bottom - top < 4.0:
            raise DocumentError("Der Zuschneidebereich ist zu klein.")

        def apply(pdf: pikepdf.Pdf) -> None:
            page = pdf.pages[page_index]
            box = [float(value) for value in page.cropbox]
            cx0, cy0, cx1, cy1 = box
            width = cx1 - cx0
            height = cy1 - cy0
            rotation = int(page.obj.get("/Rotate", 0) or 0) % 360

            def inverse(point_x: float, point_y: float) -> tuple[float, float]:
                if rotation == 0:
                    return point_x, point_y
                if rotation == 90:
                    return point_y, height - point_x
                if rotation == 180:
                    return width - point_x, height - point_y
                if rotation == 270:
                    return width - point_y, point_x
                raise DocumentError("Nicht unterstützte PDF-Seitenrotation.")

            corners = [
                inverse(left, top),
                inverse(right, top),
                inverse(right, bottom),
                inverse(left, bottom),
            ]
            us = [point[0] for point in corners]
            vs = [point[1] for point in corners]
            u_min, u_max = min(us), max(us)
            v_min, v_max = min(vs), max(vs)
            new_x0 = cx0 + u_min
            new_x1 = cx0 + u_max
            new_y0 = cy1 - v_max
            new_y1 = cy1 - v_min
            page.cropbox = [new_x0, new_y0, new_x1, new_y1]

        self._edit(apply)


    def _display_point_to_pdf(self, page, point_x: float, point_y: float) -> tuple[float, float]:
        box = [float(value) for value in page.cropbox]
        cx0, cy0, cx1, cy1 = box
        width = cx1 - cx0
        height = cy1 - cy0
        rotation = int(page.obj.get("/Rotate", 0) or 0) % 360
        if rotation == 0:
            u, v = point_x, point_y
        elif rotation == 90:
            u, v = point_y, height - point_x
        elif rotation == 180:
            u, v = width - point_x, height - point_y
        elif rotation == 270:
            u, v = width - point_y, point_x
        else:
            raise DocumentError("Nicht unterstützte PDF-Seitenrotation.")
        return cx0 + u, cy1 - v

    def _display_rect_to_pdf(self, page, rect: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
        x1, y1, x2, y2 = rect
        points = [
            self._display_point_to_pdf(page, x1, y1),
            self._display_point_to_pdf(page, x2, y1),
            self._display_point_to_pdf(page, x2, y2),
            self._display_point_to_pdf(page, x1, y2),
        ]
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        return min(xs), min(ys), max(xs), max(ys)

    def add_markup(
        self,
        page_index: int,
        kind: str,
        rect: tuple[float, float, float, float] | None = None,
        points: list[tuple[float, float]] | None = None,
        text: str = "",
        color: tuple[float, float, float] = (0.1, 0.45, 0.95),
        width: float = 2.0,
        font_size: float = 18.0,
    ) -> None:
        def apply(pdf: pikepdf.Pdf) -> None:
            page = pdf.pages[page_index]
            annotation = pikepdf.Dictionary({
                "/Type": pikepdf.Name("/Annot"),
                "/F": 4,
                "/C": pikepdf.Array([float(color[0]), float(color[1]), float(color[2])]),
                "/NM": pikepdf.String(f"LiView-{self._history_counter + 1}"),
            })
            annotation["/BS"] = pikepdf.Dictionary({"/W": float(max(0.5, width))})
            if kind == "stift":
                if not points or len(points) < 2:
                    raise DocumentError("Die Freihandlinie ist zu kurz.")
                converted = [self._display_point_to_pdf(page, x, y) for x, y in points]
                xs = [p[0] for p in converted]
                ys = [p[1] for p in converted]
                annotation["/Subtype"] = pikepdf.Name("/Ink")
                annotation["/Rect"] = pikepdf.Array([min(xs) - width, min(ys) - width, max(xs) + width, max(ys) + width])
                annotation["/InkList"] = pikepdf.Array([pikepdf.Array([coord for point in converted for coord in point])])
            elif kind in {"linie", "pfeil"}:
                if rect is None:
                    raise DocumentError("Linienbereich fehlt.")
                x1, y1, x2, y2 = rect
                p1 = self._display_point_to_pdf(page, x1, y1)
                p2 = self._display_point_to_pdf(page, x2, y2)
                annotation["/Subtype"] = pikepdf.Name("/Line")
                annotation["/L"] = pikepdf.Array([p1[0], p1[1], p2[0], p2[1]])
                annotation["/Rect"] = pikepdf.Array([min(p1[0], p2[0]) - 8, min(p1[1], p2[1]) - 8, max(p1[0], p2[0]) + 8, max(p1[1], p2[1]) + 8])
                annotation["/LE"] = pikepdf.Array([pikepdf.Name("/None"), pikepdf.Name("/OpenArrow") if kind == "pfeil" else pikepdf.Name("/None")])
            elif kind in {"rechteck", "ellipse"}:
                if rect is None:
                    raise DocumentError("Formbereich fehlt.")
                pdf_rect = self._display_rect_to_pdf(page, rect)
                annotation["/Subtype"] = pikepdf.Name("/Square" if kind == "rechteck" else "/Circle")
                annotation["/Rect"] = pikepdf.Array(pdf_rect)
            elif kind in {"hervorheben", "unterstreichen", "durchstreichen"}:
                if rect is None:
                    raise DocumentError("Markierungsbereich fehlt.")
                left, bottom, right, top = self._display_rect_to_pdf(page, rect)
                subtype = {
                    "hervorheben": "/Highlight",
                    "unterstreichen": "/Underline",
                    "durchstreichen": "/StrikeOut",
                }[kind]
                annotation["/Subtype"] = pikepdf.Name(subtype)
                annotation["/Rect"] = pikepdf.Array([left, bottom, right, top])
                annotation["/QuadPoints"] = pikepdf.Array([left, top, right, top, left, bottom, right, bottom])
                annotation["/CA"] = 0.45 if kind == "hervorheben" else 1.0
            elif kind == "text":
                if rect is None:
                    raise DocumentError("Textposition fehlt.")
                x, y = rect[0], rect[1]
                p1 = self._display_point_to_pdf(page, x, y)
                p2 = self._display_point_to_pdf(page, x + max(180.0, len(text) * font_size * 0.62), y + max(36.0, font_size * 1.8))
                left, right = sorted((p1[0], p2[0]))
                bottom, top = sorted((p1[1], p2[1]))
                annotation["/Subtype"] = pikepdf.Name("/FreeText")
                annotation["/Rect"] = pikepdf.Array([left, bottom, right, top])
                annotation["/Contents"] = pikepdf.String(text)
                annotation["/DA"] = pikepdf.String(f"/Helv {float(font_size):.1f} Tf {color[0]:.4f} {color[1]:.4f} {color[2]:.4f} rg")
            elif kind == "notiz":
                if rect is None:
                    raise DocumentError("Notizposition fehlt.")
                x, y = self._display_point_to_pdf(page, rect[0], rect[1])
                annotation["/Subtype"] = pikepdf.Name("/Text")
                annotation["/Rect"] = pikepdf.Array([x, y, x + 24, y + 24])
                annotation["/Contents"] = pikepdf.String(text)
                annotation["/Name"] = pikepdf.Name("/Note")
                annotation["/Open"] = False
            else:
                raise DocumentError("Unbekanntes PDF-Anmerkungswerkzeug.")
            annots = page.obj.get("/Annots")
            if annots is None:
                annots = pikepdf.Array()
                page.obj["/Annots"] = annots
            annots.append(pdf.make_indirect(annotation))
        self._edit(apply)

    @staticmethod
    def _pdf_text(value) -> str:
        if value is None:
            return ""
        text = str(value)
        if text.startswith("/"):
            return text[1:]
        return text

    @staticmethod
    def _field_name(parent_name: str, obj) -> str:
        own = PdfDocument._pdf_text(obj.get("/T"))
        if own and parent_name:
            return f"{parent_name}.{own}"
        return own or parent_name

    @staticmethod
    def _button_states(obj) -> list[str]:
        states: list[str] = []
        candidates = [obj]
        kids = obj.get("/Kids")
        if kids is not None:
            candidates.extend(list(kids))
        for candidate in candidates:
            appearance = candidate.get("/AP")
            if appearance is None:
                continue
            normal = appearance.get("/N")
            if not isinstance(normal, pikepdf.Dictionary):
                continue
            for key in normal.keys():
                state = str(key)
                if state != "/Off" and state not in states:
                    states.append(state)
        return states

    @staticmethod
    def _choice_options(obj) -> list[str]:
        options: list[str] = []
        raw_options = obj.get("/Opt")
        if raw_options is None:
            return options
        for item in raw_options:
            if isinstance(item, pikepdf.Array):
                display = item[1] if len(item) > 1 else item[0]
            else:
                display = item
            options.append(PdfDocument._pdf_text(display))
        return options

    @staticmethod
    def _walk_form_fields(pdf: pikepdf.Pdf):
        acro = pdf.Root.get("/AcroForm")
        if acro is None:
            return []
        roots = acro.get("/Fields")
        if roots is None:
            return []
        result = []

        def walk(obj, parent_name: str = "", inherited_ft=None, inherited_ff: int = 0):
            name = PdfDocument._field_name(parent_name, obj)
            ft = obj.get("/FT") or inherited_ft
            ff = int(obj.get("/Ff", inherited_ff) or 0)
            kids = obj.get("/Kids")
            field_kids = []
            if kids is not None:
                for kid in kids:
                    if str(kid.get("/Subtype")) != "/Widget" or kid.get("/T") is not None:
                        field_kids.append(kid)
            if field_kids:
                for kid in field_kids:
                    walk(kid, name, ft, ff)
                return
            if ft is not None and name:
                result.append((name, str(ft), ff, obj))

        for root in roots:
            walk(root)
        return result

    def form_fields(self) -> list[FormFieldInfo]:
        fields: list[FormFieldInfo] = []
        try:
            with pikepdf.Pdf.open(self._work_path) as pdf:
                for name, ft, ff, obj in self._walk_form_fields(pdf):
                    value = obj.get("/V")
                    if ft == "/Tx":
                        fields.append(FormFieldInfo(name, "text", self._pdf_text(value)))
                    elif ft == "/Ch":
                        fields.append(FormFieldInfo(name, "choice", self._pdf_text(value), tuple(self._choice_options(obj))))
                    elif ft == "/Btn":
                        if ff & (1 << 16):
                            fields.append(FormFieldInfo(name, "button", "", (), False))
                            continue
                        states = self._button_states(obj)
                        if ff & (1 << 15):
                            fields.append(FormFieldInfo(name, "radio", self._pdf_text(value), tuple(state[1:] if state.startswith("/") else state for state in states)))
                        else:
                            current = str(value or "/Off")
                            fields.append(FormFieldInfo(name, "checkbox", current != "/Off"))
        except Exception as exc:
            raise DocumentError(f"Formularfelder konnten nicht gelesen werden: {exc}") from exc
        return fields

    @staticmethod
    def _set_button_value(obj, value) -> None:
        kids = list(obj.get("/Kids") or [])
        widgets = kids if kids else [obj]
        states = PdfDocument._button_states(obj)
        if isinstance(value, bool):
            selected = states[0] if value and states else "/Off"
        else:
            raw = str(value or "Off")
            selected = raw if raw.startswith("/") else f"/{raw}"
            if selected not in states:
                selected = "/Off"
        obj["/V"] = pikepdf.Name(selected)
        for widget in widgets:
            widget_states = PdfDocument._button_states(widget)
            widget["/AS"] = pikepdf.Name(selected if selected in widget_states else "/Off")

    def set_form_values(self, values: dict[str, str | bool]) -> None:
        if not values:
            return
        def apply(pdf: pikepdf.Pdf) -> None:
            acro = pdf.Root.get("/AcroForm")
            if acro is None:
                raise DocumentError("Dieses PDF enthält kein AcroForm-Formular.")
            found = set()
            for name, ft, ff, obj in self._walk_form_fields(pdf):
                if name not in values:
                    continue
                found.add(name)
                value = values[name]
                if ft == "/Tx":
                    obj["/V"] = pikepdf.String(str(value))
                elif ft == "/Ch":
                    obj["/V"] = pikepdf.String(str(value))
                    if "/I" in obj:
                        del obj["/I"]
                elif ft == "/Btn" and not (ff & (1 << 16)):
                    self._set_button_value(obj, value)
            missing = set(values) - found
            if missing:
                raise DocumentError("Formularfeld nicht gefunden: " + ", ".join(sorted(missing)))
            acro["/NeedAppearances"] = True
            generator = getattr(pdf, "generate_appearance_streams", None)
            if callable(generator):
                try:
                    generator()
                except Exception:
                    acro["/NeedAppearances"] = True
        self._edit(apply)

    def reset_form(self) -> None:
        def apply(pdf: pikepdf.Pdf) -> None:
            acro = pdf.Root.get("/AcroForm")
            if acro is None:
                raise DocumentError("Dieses PDF enthält kein AcroForm-Formular.")
            for name, ft, ff, obj in self._walk_form_fields(pdf):
                default = obj.get("/DV")
                if ft in {"/Tx", "/Ch"}:
                    if default is None:
                        if "/V" in obj:
                            del obj["/V"]
                    else:
                        obj["/V"] = default
                elif ft == "/Btn" and not (ff & (1 << 16)):
                    if default is None:
                        self._set_button_value(obj, False)
                    else:
                        self._set_button_value(obj, self._pdf_text(default))
            acro["/NeedAppearances"] = True
            generator = getattr(pdf, "generate_appearance_streams", None)
            if callable(generator):
                try:
                    generator()
                except Exception:
                    acro["/NeedAppearances"] = True
        self._edit(apply)

    def add_signature(
        self,
        page_index: int,
        rect: tuple[float, float, float, float],
        strokes: list[list[tuple[float, float]]],
    ) -> None:
        if not strokes or not any(len(stroke) >= 2 for stroke in strokes):
            raise DocumentError("Es wurde keine Unterschrift gezeichnet.")
        def apply(pdf: pikepdf.Pdf) -> None:
            page = pdf.pages[page_index]
            left, bottom, right, top = self._display_rect_to_pdf(page, rect)
            if right - left < 12 or top - bottom < 6:
                raise DocumentError("Der Bereich für die Unterschrift ist zu klein.")
            with tempfile.TemporaryDirectory(prefix="liview-signature-") as directory:
                signature_pdf = os.path.join(directory, "signature.pdf")
                canvas_width = 600.0
                canvas_height = 220.0
                surface = cairo.PDFSurface(signature_pdf, canvas_width, canvas_height)
                cr = cairo.Context(surface)
                cr.set_source_rgb(0.03, 0.03, 0.03)
                cr.set_line_width(4.0)
                cr.set_line_cap(cairo.LINE_CAP_ROUND)
                cr.set_line_join(cairo.LINE_JOIN_ROUND)
                for stroke in strokes:
                    if len(stroke) < 2:
                        continue
                    cr.move_to(stroke[0][0] * canvas_width, stroke[0][1] * canvas_height)
                    for x, y in stroke[1:]:
                        cr.line_to(x * canvas_width, y * canvas_height)
                    cr.stroke()
                surface.finish()
                with pikepdf.Pdf.open(signature_pdf) as signature:
                    page.add_overlay(signature.pages[0], pikepdf.Rectangle(left, bottom, right, top))
        self._edit(apply)

    def optimize_copy(self, target: str) -> None:
        target = os.path.abspath(target)
        if self.source_encrypted and not self._source_password:
            raise DocumentError("Der vorhandene PDF-Schutz kann ohne Öffnungspasswort nicht sicher beibehalten werden.")
        try:
            with pikepdf.Pdf.open(self._work_path) as pdf:
                pdf.remove_unreferenced_resources()
                options = {
                    "compress_streams": True,
                    "recompress_flate": True,
                    "object_stream_mode": pikepdf.ObjectStreamMode.generate,
                }
                if self.source_encrypted:
                    options["encryption"] = pikepdf.Encryption(user=self._source_password, owner=self._source_password)
                pdf.save(target, **options)
        except Exception as exc:
            raise DocumentError(f"PDF konnte nicht optimiert werden: {exc}") from exc

    def protect_copy(self, target: str, password: str) -> None:
        if not password:
            raise DocumentError("Das Passwort darf nicht leer sein.")
        target = os.path.abspath(target)
        try:
            with pikepdf.Pdf.open(self._work_path) as pdf:
                pdf.save(
                    target,
                    encryption=pikepdf.Encryption(user=password, owner=password),
                )
        except Exception as exc:
            raise DocumentError(f"PDF konnte nicht geschützt werden: {exc}") from exc

    def compress_copy(self, target: str, profile: str = "ebook") -> None:
        if shutil.which("gs") is None:
            raise DocumentError("Ghostscript ist nicht installiert.")
        if self.source_encrypted and not self._source_password:
            raise DocumentError("Der vorhandene PDF-Schutz kann ohne Öffnungspasswort nicht sicher beibehalten werden.")
        profiles = {"screen": "/screen", "ebook": "/ebook", "printer": "/printer"}
        setting = profiles.get(profile)
        if setting is None:
            raise DocumentError("Unbekanntes Komprimierungsprofil.")
        target = os.path.abspath(target)
        raw_target = os.path.join(self._tmp.name, "compressed-unencrypted.pdf") if self.source_encrypted else target
        command = [
            "gs",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.7",
            f"-dPDFSETTINGS={setting}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={raw_target}",
            self._work_path,
        ]
        try:
            result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=180)
            if result.returncode != 0 or not os.path.isfile(raw_target):
                raise DocumentError(result.stderr.strip() or "Ghostscript konnte das PDF nicht verkleinern.")
            if self.source_encrypted:
                with pikepdf.Pdf.open(raw_target) as pdf:
                    pdf.save(target, encryption=pikepdf.Encryption(user=self._source_password, owner=self._source_password))
                os.unlink(raw_target)
        except DocumentError:
            if raw_target != target and os.path.exists(raw_target):
                os.unlink(raw_target)
            raise
        except Exception as exc:
            if raw_target != target and os.path.exists(raw_target):
                os.unlink(raw_target)
            raise DocumentError(f"PDF konnte nicht verkleinert werden: {exc}") from exc

    def secure_redact(self, page_index: int, display_rect: tuple[float, float, float, float]) -> None:
        x1, y1, x2, y2 = display_rect
        width, height = self.page_size(page_index)
        left = max(0.0, min(width, min(x1, x2)))
        right = max(0.0, min(width, max(x1, x2)))
        top = max(0.0, min(height, min(y1, y2)))
        bottom = max(0.0, min(height, max(y1, y2)))
        if right - left < 4.0 or bottom - top < 4.0:
            raise DocumentError("Der Schwärzungsbereich ist zu klein.")
        snapshot = self._snapshot(self._undo_paths)
        self._clear_history(self._redo_paths)
        next_path = os.path.join(self._tmp.name, "redacted.pdf")
        try:
            scale = 2.0
            page_path = os.path.join(self._tmp.name, "redacted-page.pdf")
            output = pikepdf.Pdf.new()
            try:
                for index in range(self.page_count):
                    image = self._render_to_pillow(index, scale=scale)
                    if index == page_index:
                        draw = ImageDraw.Draw(image)
                        draw.rectangle(
                            (int(left * scale), int(top * scale), int(right * scale), int(bottom * scale)),
                            fill=(0, 0, 0),
                        )
                    image.save(page_path, format="PDF", resolution=144.0)
                    image.close()
                    with pikepdf.Pdf.open(page_path) as donor:
                        output.pages.extend(donor.pages)
                output.save(next_path)
            finally:
                output.close()
                if os.path.exists(page_path):
                    os.unlink(page_path)
            os.replace(next_path, self._work_path)
            self.dirty = True
            self._reload()
        except Exception as exc:
            if os.path.exists(next_path):
                os.unlink(next_path)
            if self._undo_paths and self._undo_paths[-1] == snapshot:
                self._undo_paths.pop()
            if os.path.exists(snapshot):
                os.unlink(snapshot)
            raise DocumentError(f"Schwärzung fehlgeschlagen: {exc}") from exc

    def _render_to_pillow(self, page_index: int, scale: float = 2.0) -> Image.Image:
        width, height = self.page_size(page_index)
        pixel_width = max(1, int(round(width * scale)))
        pixel_height = max(1, int(round(height * scale)))
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, pixel_width, pixel_height)
        cr = cairo.Context(surface)
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.paint()
        self.render_page(page_index, cr, scale)
        surface.flush()
        buffer = io.BytesIO()
        surface.write_to_png(buffer)
        buffer.seek(0)
        with Image.open(buffer) as image:
            return image.convert("RGB")

    def save(self) -> None:
        if self.source_encrypted:
            if not self._source_password:
                raise DocumentError("Das geschützte Original kann nicht sicher überschrieben werden. Verwende ‚Speichern unter‘.")
            temp_target = os.path.join(self._tmp.name, "encrypted-save.pdf")
            with pikepdf.Pdf.open(self._work_path) as pdf:
                pdf.save(temp_target, encryption=pikepdf.Encryption(user=self._source_password, owner=self._source_password))
            shutil.copy2(temp_target, self.path)
        else:
            shutil.copy2(self._work_path, self.path)
        self.dirty = False

    def save_as(self, target: str) -> None:
        target = os.path.abspath(target)
        if self.source_encrypted:
            if not self._source_password:
                raise DocumentError("Der vorhandene PDF-Schutz kann ohne Öffnungspasswort nicht sicher beibehalten werden.")
            with pikepdf.Pdf.open(self._work_path) as pdf:
                pdf.save(target, encryption=pikepdf.Encryption(user=self._source_password, owner=self._source_password))
        else:
            shutil.copy2(self._work_path, target)
        self.path = target
        self.dirty = False

    def export(self, target: str, page_index: int) -> None:
        target_path = Path(target)
        suffix = target_path.suffix.lower()
        if suffix == ".pdf":
            if self.source_encrypted:
                if not self._source_password:
                    raise DocumentError("Der vorhandene PDF-Schutz kann ohne Öffnungspasswort nicht sicher beibehalten werden.")
                with pikepdf.Pdf.open(self._work_path) as pdf:
                    pdf.save(target_path, encryption=pikepdf.Encryption(user=self._source_password, owner=self._source_password))
            else:
                shutil.copy2(self._work_path, target_path)
            return
        if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}:
            raise DocumentError("Exportformat nicht unterstützt. Verwende PDF, PNG, JPEG, WebP oder TIFF.")
        image = self._render_to_pillow(page_index)
        if suffix in {".jpg", ".jpeg"}:
            image.save(target_path, format="JPEG", quality=95)
        elif suffix == ".png":
            image.save(target_path, format="PNG")
        elif suffix == ".webp":
            image.save(target_path, format="WEBP", quality=95)
        else:
            image.save(target_path, format="TIFF")

    def print_page(self, page_index: int, cr: cairo.Context, width: float, height: float) -> None:
        page = self._page(page_index)
        page_width, page_height = page.get_size()
        scale = min(width / page_width, height / page_height)
        offset_x = (width - page_width * scale) / 2.0
        offset_y = (height - page_height * scale) / 2.0
        cr.save()
        cr.translate(offset_x, offset_y)
        cr.scale(scale, scale)
        page.render_for_printing(cr)
        cr.restore()

    def close(self) -> None:
        self._poppler = None
        self._tmp.cleanup()


class ImageDocument(BaseDocument):
    kind = "image"
    pillow_extensions = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp", ".gif", ".ico", ".avif"}
    heif_extensions = {".heic", ".heif"}
    svg_extensions = {".svg", ".svgz"}
    supported_extensions = pillow_extensions | heif_extensions | svg_extensions

    def __init__(self, path: str):
        super().__init__(path)
        self._source_suffix = Path(self.path).suffix.lower()
        self._frames: list[Image.Image] = []
        self._durations: list[int] = []
        self._frame_index = 0
        self._surface = None
        self._icc_profile = None
        self._exif = None
        self._undo_states: list[list[Image.Image]] = []
        self._redo_states: list[list[Image.Image]] = []
        try:
            if self._source_suffix in self.svg_extensions:
                source = self._open_svg(self.path)
                self._load_frames(source)
            elif self._source_suffix in self.heif_extensions:
                source = self._open_heif(self.path)
                self._load_frames(source)
            else:
                with Image.open(self.path) as source:
                    self._load_frames(source)
        except DocumentError:
            raise
        except Exception as exc:
            raise DocumentError(f"Bild konnte nicht geöffnet werden: {exc}") from exc
        if not self._frames:
            raise DocumentError("Das Bild enthält keine darstellbaren Bilddaten.")

    @property
    def _image(self) -> Image.Image:
        return self._frames[self._frame_index]

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    @property
    def is_animated(self) -> bool:
        return len(self._frames) > 1

    @property
    def frame_duration(self) -> int:
        if not self._durations:
            return 100
        return max(20, min(10000, int(self._durations[self._frame_index])))

    def advance_frame(self) -> None:
        if not self.is_animated:
            return
        self._frame_index = (self._frame_index + 1) % len(self._frames)
        self._surface = None

    @property
    def page_count(self) -> int:
        return 1

    def page_size(self, index: int) -> tuple[float, float]:
        return float(self._image.width), float(self._image.height)

    def _open_svg(self, path: str) -> Image.Image:
        converter = shutil.which("rsvg-convert")
        if converter is None:
            raise DocumentError("SVG-Unterstützung fehlt. Installiere das Paket librsvg2-bin.")
        try:
            process = subprocess.run(
                [converter, "--width=4096", "--height=4096", "--keep-aspect-ratio", path],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.decode("utf-8", errors="replace").strip()
            raise DocumentError(f"SVG konnte nicht gerendert werden: {detail or 'unbekannter Fehler'}") from exc
        return Image.open(io.BytesIO(process.stdout))

    def _open_heif(self, path: str) -> Image.Image:
        converter = shutil.which("heif-convert")
        if converter is None:
            raise DocumentError("HEIC/HEIF-Unterstützung fehlt. Installiere das Paket libheif-examples.")
        with tempfile.TemporaryDirectory(prefix="liview-heif-") as directory:
            target = os.path.join(directory, "decoded.png")
            try:
                process = subprocess.run(
                    [converter, "--quiet", path, target],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            except subprocess.CalledProcessError as exc:
                detail = exc.stderr.decode("utf-8", errors="replace").strip()
                raise DocumentError(f"HEIC/HEIF konnte nicht dekodiert werden: {detail or 'unbekannter Fehler'}") from exc
            if not os.path.isfile(target):
                raise DocumentError("HEIC/HEIF-Dekodierung hat kein Bild erzeugt.")
            with Image.open(target) as image:
                return image.copy()

    def _load_frames(self, source: Image.Image) -> None:
        self._icc_profile = source.info.get("icc_profile")
        first_exif = source.getexif()
        self._exif = first_exif.copy() if hasattr(first_exif, "copy") else first_exif
        if self._exif and 274 in self._exif:
            del self._exif[274]
        frame_count = int(getattr(source, "n_frames", 1))
        for index in range(frame_count):
            source.seek(index)
            frame = ImageOps.exif_transpose(source.copy()).convert("RGBA")
            self._frames.append(frame)
            self._durations.append(int(source.info.get("duration", 100) or 100))
        self._frame_index = 0

    def _cairo_surface(self) -> cairo.ImageSurface:
        if self._surface is None:
            buffer = io.BytesIO()
            self._image.save(buffer, format="PNG")
            buffer.seek(0)
            self._surface = cairo.ImageSurface.create_from_png(buffer)
        return self._surface

    def _invalidate(self) -> None:
        self._surface = None
        self.clear_thumbnail_cache()
        self.dirty = True

    def render_page(self, index: int, cr: cairo.Context, scale: float) -> None:
        cr.save()
        cr.scale(scale, scale)
        cr.set_source_surface(self._cairo_surface(), 0, 0)
        cr.paint()
        cr.restore()

    def _snapshot_frames(self) -> list[Image.Image]:
        return [frame.copy() for frame in self._frames]

    def _push_undo(self) -> None:
        self._undo_states.append(self._snapshot_frames())
        if len(self._undo_states) > 20:
            self._undo_states.pop(0)
        self._redo_states.clear()

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_states)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_states)

    def undo(self) -> None:
        if not self._undo_states:
            return
        self._redo_states.append(self._snapshot_frames())
        self._frames = self._undo_states.pop()
        self._frame_index = min(self._frame_index, len(self._frames) - 1)
        self._invalidate()

    def redo(self) -> None:
        if not self._redo_states:
            return
        self._undo_states.append(self._snapshot_frames())
        self._frames = self._redo_states.pop()
        self._frame_index = min(self._frame_index, len(self._frames) - 1)
        self._invalidate()

    def flip_horizontal(self) -> None:
        self._push_undo()
        self._frames = [frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for frame in self._frames]
        self._invalidate()

    def flip_vertical(self) -> None:
        self._push_undo()
        self._frames = [frame.transpose(Image.Transpose.FLIP_TOP_BOTTOM) for frame in self._frames]
        self._invalidate()

    def add_markup(
        self,
        kind: str,
        rect: tuple[float, float, float, float] | None = None,
        points: list[tuple[float, float]] | None = None,
        text: str = "",
        color: tuple[int, int, int, int] = (30, 115, 240, 255),
        width: int = 3,
        font_size: int = 24,
    ) -> None:
        self._push_undo()
        try:
            for frame in self._frames:
                draw = ImageDraw.Draw(frame, "RGBA")
                if kind == "stift":
                    if not points or len(points) < 2:
                        raise DocumentError("Die Freihandlinie ist zu kurz.")
                    draw.line(points, fill=color, width=max(1, int(width)), joint="curve")
                elif kind == "linie":
                    if rect is None:
                        raise DocumentError("Linienbereich fehlt.")
                    draw.line((rect[0], rect[1], rect[2], rect[3]), fill=color, width=max(1, int(width)))
                elif kind == "pfeil":
                    if rect is None:
                        raise DocumentError("Pfeilbereich fehlt.")
                    x1, y1, x2, y2 = rect
                    draw.line((x1, y1, x2, y2), fill=color, width=max(1, int(width)))
                    import math
                    angle = math.atan2(y2 - y1, x2 - x1)
                    head = max(10.0, width * 4.0)
                    spread = math.radians(28.0)
                    p1 = (x2 - head * math.cos(angle - spread), y2 - head * math.sin(angle - spread))
                    p2 = (x2 - head * math.cos(angle + spread), y2 - head * math.sin(angle + spread))
                    draw.polygon([(x2, y2), p1, p2], fill=color)
                elif kind in {"rechteck", "ellipse"}:
                    if rect is None:
                        raise DocumentError("Formbereich fehlt.")
                    box = (min(rect[0], rect[2]), min(rect[1], rect[3]), max(rect[0], rect[2]), max(rect[1], rect[3]))
                    if kind == "rechteck":
                        draw.rectangle(box, outline=color, width=max(1, int(width)))
                    else:
                        draw.ellipse(box, outline=color, width=max(1, int(width)))
                elif kind == "hervorheben":
                    if rect is None:
                        raise DocumentError("Markierungsbereich fehlt.")
                    box = (min(rect[0], rect[2]), min(rect[1], rect[3]), max(rect[0], rect[2]), max(rect[1], rect[3]))
                    highlight = (color[0], color[1], color[2], 90)
                    draw.rectangle(box, fill=highlight)
                elif kind == "text":
                    if rect is None:
                        raise DocumentError("Textposition fehlt.")
                    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                    try:
                        font = ImageFont.truetype(font_path, max(8, int(font_size)))
                    except OSError:
                        font = ImageFont.load_default()
                    draw.text((rect[0], rect[1]), text, fill=color, font=font)
                else:
                    raise DocumentError("Unbekanntes Bildbearbeitungswerkzeug.")
        except Exception:
            self._frames = self._undo_states.pop()
            raise
        self._invalidate()

    def add_signature(
        self,
        rect: tuple[float, float, float, float],
        strokes: list[list[tuple[float, float]]],
    ) -> None:
        if not strokes or not any(len(stroke) >= 2 for stroke in strokes):
            raise DocumentError("Es wurde keine Unterschrift gezeichnet.")
        left, right = sorted((rect[0], rect[2]))
        top, bottom = sorted((rect[1], rect[3]))
        width = right - left
        height = bottom - top
        if width < 12 or height < 6:
            raise DocumentError("Der Bereich für die Unterschrift ist zu klein.")
        self._push_undo()
        for frame in self._frames:
            draw = ImageDraw.Draw(frame, "RGBA")
            line_width = max(2, int(round(height / 28.0)))
            for stroke in strokes:
                if len(stroke) < 2:
                    continue
                points = [(left + x * width, top + y * height) for x, y in stroke]
                draw.line(points, fill=(8, 8, 8, 255), width=line_width, joint="curve")
        self._invalidate()

    def rotate(self, page_index: int, degrees: int) -> None:
        self._push_undo()
        rotated = []
        for frame in self._frames:
            if degrees == 90:
                rotated.append(frame.transpose(Image.Transpose.ROTATE_270))
            elif degrees == -90:
                rotated.append(frame.transpose(Image.Transpose.ROTATE_90))
            elif abs(degrees) == 180:
                rotated.append(frame.transpose(Image.Transpose.ROTATE_180))
            else:
                raise DocumentError("Nicht unterstützte Bildrotation.")
        self._frames = rotated
        self._invalidate()

    def crop(self, page_index: int, display_rect: tuple[float, float, float, float]) -> None:
        x1, y1, x2, y2 = display_rect
        width, height = self.page_size(0)
        left = int(max(0.0, min(width, min(x1, x2))))
        right = int(max(0.0, min(width, max(x1, x2))))
        top = int(max(0.0, min(height, min(y1, y2))))
        bottom = int(max(0.0, min(height, max(y1, y2))))
        if right - left < 4 or bottom - top < 4:
            raise DocumentError("Der Zuschneidebereich ist zu klein.")
        self._push_undo()
        self._frames = [frame.crop((left, top, right, bottom)) for frame in self._frames]
        self._invalidate()

    def save(self) -> None:
        self._save_image(self.path)
        self.dirty = False

    def save_as(self, target: str) -> None:
        target = os.path.abspath(target)
        self._save_image(target)
        self.path = target
        self._source_suffix = Path(target).suffix.lower()
        self.dirty = False

    def _metadata(self) -> dict:
        metadata = {}
        if self._icc_profile:
            metadata["icc_profile"] = self._icc_profile
        if self._exif:
            metadata["exif"] = self._exif.tobytes()
        return metadata

    def _save_image(self, target: str) -> None:
        suffix = Path(target).suffix.lower()
        metadata = self._metadata()
        if suffix in self.svg_extensions:
            raise DocumentError("SVG wird derzeit nur angezeigt. Für Änderungen verwende Exportieren als PNG, JPEG, WebP, TIFF oder PDF.")
        if suffix in self.heif_extensions:
            raise DocumentError("HEIC/HEIF wird derzeit nur angezeigt. Für Änderungen verwende Exportieren als PNG, JPEG, WebP, TIFF oder PDF.")
        if suffix in {".jpg", ".jpeg"}:
            self._image.convert("RGB").save(target, format="JPEG", quality=95, **metadata)
        elif suffix == ".png":
            self._image.save(target, format="PNG", **metadata)
        elif suffix == ".webp":
            self._image.save(target, format="WEBP", quality=95, **metadata)
        elif suffix in {".tif", ".tiff"}:
            self._image.save(target, format="TIFF", **metadata)
        elif suffix == ".bmp":
            self._image.convert("RGB").save(target, format="BMP")
        elif suffix == ".ico":
            self._image.save(target, format="ICO")
        elif suffix == ".avif":
            try:
                self._image.convert("RGB").save(target, format="AVIF", quality=90, **metadata)
            except Exception as exc:
                raise DocumentError(f"AVIF konnte nicht gespeichert werden: {exc}") from exc
        elif suffix == ".gif":
            frames = [frame.convert("P", palette=Image.Palette.ADAPTIVE) for frame in self._frames]
            frames[0].save(
                target,
                format="GIF",
                save_all=len(frames) > 1,
                append_images=frames[1:],
                duration=self._durations,
                loop=0,
                disposal=2,
            )
        else:
            raise DocumentError("Bildformat nicht unterstützt. Verwende PNG, JPEG, WebP, TIFF, BMP, GIF, ICO oder AVIF.")

    def export(self, target: str, page_index: int) -> None:
        suffix = Path(target).suffix.lower()
        if suffix == ".pdf":
            self._image.convert("RGB").save(target, format="PDF", resolution=144.0)
            return
        self._save_image(target)

    def print_page(self, page_index: int, cr: cairo.Context, width: float, height: float) -> None:
        image_width, image_height = self.page_size(0)
        scale = min(width / image_width, height / image_height)
        offset_x = (width - image_width * scale) / 2.0
        offset_y = (height - image_height * scale) / 2.0
        cr.save()
        cr.translate(offset_x, offset_y)
        cr.scale(scale, scale)
        cr.set_source_surface(self._cairo_surface(), 0, 0)
        cr.paint()
        cr.restore()


def open_document(path: str, password: str = "") -> BaseDocument:
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise DocumentError("Datei nicht gefunden.")
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return PdfDocument(path, password=password)
    if suffix in {".stl", ".obj", ".3mf"}:
        from .stl import StlDocument
        return StlDocument(path)
    if suffix in ImageDocument.supported_extensions:
        return ImageDocument(path)
    from .video import VideoDocument
    if suffix in VideoDocument.supported_extensions:
        return VideoDocument(path)
    raise DocumentError(f"Dateiformat '{suffix or 'ohne Endung'}' wird von LiView noch nicht unterstützt.")
