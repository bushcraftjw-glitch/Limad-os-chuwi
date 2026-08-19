from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gio", "2.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, GObject, Gtk

from . import __version__
from .documents import BaseDocument, DocumentError, FormFieldInfo, ImageDocument, PdfDocument, PdfPasswordRequired, SearchHit, open_document
from .stl import StlDocument
from .video import VideoDocument
from .inspector import document_info
from .ocr import recognize_text

APP_ID = "de.limad.LiView"


class PageView(Gtk.DrawingArea):
    def __init__(self, window: "DocumentWindow", page_index: int):
        super().__init__()
        self.window = window
        self.page_index = page_index
        self.drag_start: tuple[float, float] | None = None
        self.drag_current: tuple[float, float] | None = None
        self.set_draw_func(self._draw)
        self.set_focusable(True)
        self.set_cursor_from_name("grab" if isinstance(self.window.document, StlDocument) else "text")
        self.model_drag_origin = None
        self.model_pan_origin = None
        self.ink_points: list[tuple[float, float]] = []
        scroll = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.VERTICAL)
        scroll.connect("scroll", self._on_scroll)
        self.add_controller(scroll)
        click = Gtk.GestureClick.new()
        click.connect("pressed", self._on_pressed)
        self.add_controller(click)
        drag = Gtk.GestureDrag.new()
        drag.set_button(1)
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end", self._on_drag_end)
        self.add_controller(drag)
        pan_drag = Gtk.GestureDrag.new()
        pan_drag.set_button(3)
        pan_drag.connect("drag-begin", self._on_pan_begin)
        pan_drag.connect("drag-update", self._on_pan_update)
        pan_drag.connect("drag-end", self._on_pan_end)
        self.add_controller(pan_drag)
        self.refresh_size()

    def refresh_size(self) -> None:
        width, height = self.window.document.page_size(self.page_index)
        zoom = self.window.zoom
        self.set_content_width(max(1, int(round(width * zoom))))
        self.set_content_height(max(1, int(round(height * zoom))))
        self.queue_draw()

    def _on_pressed(self, gesture, count: int, x: float, y: float) -> None:
        self.window.set_current_page(self.page_index)
        self.grab_focus()
        if self.window.mode in {"text", "notiz"}:
            self.window.request_text_markup(self.page_index, x / self.window.zoom, y / self.window.zoom, self.window.mode)

    def _on_drag_begin(self, gesture, x: float, y: float) -> None:
        self.window.set_current_page(self.page_index)
        if isinstance(self.window.document, StlDocument):
            self.model_drag_origin = (self.window.document.yaw, self.window.document.pitch)
            self.set_cursor_from_name("grabbing")
            return
        if self.window.mode in {"text", "notiz"}:
            self.drag_start = None
            self.drag_current = None
            return
        self.drag_start = (x, y)
        self.drag_current = (x, y)
        self.ink_points = [(x, y)] if self.window.mode == "stift" else []
        self.queue_draw()

    def _on_drag_update(self, gesture, offset_x: float, offset_y: float) -> None:
        if isinstance(self.window.document, StlDocument):
            if self.model_drag_origin is None:
                return
            yaw, pitch = self.model_drag_origin
            self.window.document.set_orbit(yaw + math.radians(offset_x * 0.45), pitch + math.radians(offset_y * 0.45))
            self.queue_draw()
            return
        if self.drag_start is None:
            return
        self.drag_current = (self.drag_start[0] + offset_x, self.drag_start[1] + offset_y)
        if self.window.mode == "stift":
            self.ink_points.append(self.drag_current)
        self.queue_draw()

    def _on_drag_end(self, gesture, offset_x: float, offset_y: float) -> None:
        if isinstance(self.window.document, StlDocument):
            self.model_drag_origin = None
            self.set_cursor_from_name("grab")
            self.queue_draw()
            return
        if self.drag_start is None:
            return
        self.drag_current = (self.drag_start[0] + offset_x, self.drag_start[1] + offset_y)
        if self.window.mode == "crop":
            self.window.set_crop_selection(self.page_index, self._page_rect())
        elif self.window.mode in {"stift", "linie", "pfeil", "rechteck", "ellipse", "hervorheben", "unterstreichen", "durchstreichen", "schwaerzen"}:
            points = [(x / self.window.zoom, y / self.window.zoom) for x, y in self.ink_points]
            self.window.commit_markup(self.page_index, self.window.mode, self._page_rect(), points)
            self.drag_start = None
            self.drag_current = None
            self.ink_points = []
        elif self.window.mode == "unterschrift":
            self.window.commit_signature(self.page_index, self._page_rect())
            self.drag_start = None
            self.drag_current = None
            self.ink_points = []
        else:
            self.window.set_text_selection(self.page_index, self._page_rect())
        self.queue_draw()

    def _on_pan_begin(self, gesture, x: float, y: float) -> None:
        if not isinstance(self.window.document, StlDocument):
            return
        self.model_pan_origin = (self.window.document.pan_x, self.window.document.pan_y)
        self.set_cursor_from_name("move")

    def _on_pan_update(self, gesture, offset_x: float, offset_y: float) -> None:
        if not isinstance(self.window.document, StlDocument) or self.model_pan_origin is None:
            return
        pan_x, pan_y = self.model_pan_origin
        self.window.document.pan_model(pan_x + offset_x, pan_y + offset_y)
        self.queue_draw()

    def _on_pan_end(self, gesture, offset_x: float, offset_y: float) -> None:
        if not isinstance(self.window.document, StlDocument):
            return
        self.model_pan_origin = None
        self.set_cursor_from_name("grab")
        self.window._update_title_status()
        self.queue_draw()

    def _on_scroll(self, controller, dx: float, dy: float) -> bool:
        if not isinstance(self.window.document, StlDocument):
            return False
        self.window.document.zoom_model(1.12 if dy < 0 else 1.0 / 1.12)
        self.window._update_title_status()
        self.queue_draw()
        return True

    def clear_drag(self) -> None:
        self.drag_start = None
        self.drag_current = None
        self.ink_points = []
        self.queue_draw()

    def _page_rect(self) -> tuple[float, float, float, float]:
        if self.drag_start is None or self.drag_current is None:
            return (0.0, 0.0, 0.0, 0.0)
        zoom = self.window.zoom
        return (
            self.drag_start[0] / zoom,
            self.drag_start[1] / zoom,
            self.drag_current[0] / zoom,
            self.drag_current[1] / zoom,
        )

    def _draw_search_hits(self, cr: cairo.Context) -> None:
        if not isinstance(self.window.document, PdfDocument):
            return
        page_width, page_height = self.window.document.page_size(self.page_index)
        zoom = self.window.zoom
        for index, hit in enumerate(self.window.search_hits):
            if hit.page_index != self.page_index:
                continue
            x1, y1, x2, y2 = hit.rect
            x = min(x1, x2) * zoom
            y = (page_height - max(y1, y2)) * zoom
            width = abs(x2 - x1) * zoom
            height = abs(y2 - y1) * zoom
            if index == self.window.search_position:
                cr.set_source_rgba(1.0, 0.55, 0.0, 0.48)
            else:
                cr.set_source_rgba(1.0, 0.9, 0.0, 0.34)
            cr.rectangle(x, y, width, height)
            cr.fill()

    def _draw_drag(self, cr: cairo.Context) -> None:
        if self.drag_start is None or self.drag_current is None:
            return
        x1, y1 = self.drag_start
        x2, y2 = self.drag_current
        left = min(x1, x2)
        top = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        red, green, blue = self.window.current_color
        cr.set_line_width(max(1.0, self.window.current_width))
        cr.set_source_rgba(red, green, blue, 0.95)
        if self.window.mode == "stift":
            if len(self.ink_points) >= 2:
                cr.move_to(*self.ink_points[0])
                for point in self.ink_points[1:]:
                    cr.line_to(*point)
                cr.stroke()
            return
        if self.window.mode in {"linie", "pfeil"}:
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.stroke()
            if self.window.mode == "pfeil":
                angle = math.atan2(y2 - y1, x2 - x1)
                head = max(10.0, self.window.current_width * 4.0)
                spread = math.radians(28.0)
                cr.move_to(x2, y2)
                cr.line_to(x2 - head * math.cos(angle - spread), y2 - head * math.sin(angle - spread))
                cr.line_to(x2 - head * math.cos(angle + spread), y2 - head * math.sin(angle + spread))
                cr.close_path()
                cr.fill()
            return
        if self.window.mode == "ellipse":
            cr.save()
            cr.translate(left + width / 2.0, top + height / 2.0)
            cr.scale(max(width / 2.0, 0.001), max(height / 2.0, 0.001))
            cr.arc(0, 0, 1, 0, 2 * math.pi)
            cr.restore()
            cr.stroke()
            return
        if self.window.mode == "unterschrift":
            self.window.draw_signature_preview(cr, left, top, width, height)
            return
        if self.window.mode == "schwaerzen":
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.72)
            cr.rectangle(left, top, width, height)
            cr.fill()
            return
        if self.window.mode in {"hervorheben", "unterstreichen", "durchstreichen"}:
            if self.window.mode == "hervorheben":
                cr.set_source_rgba(red, green, blue, 0.28)
                cr.rectangle(left, top, width, height)
                cr.fill()
            elif self.window.mode == "unterstreichen":
                cr.move_to(left, top + height)
                cr.line_to(left + width, top + height)
                cr.stroke()
            else:
                cr.move_to(left, top + height / 2.0)
                cr.line_to(left + width, top + height / 2.0)
                cr.stroke()
            return
        cr.rectangle(left, top, width, height)
        if self.window.mode == "crop":
            cr.set_source_rgba(0.0, 0.45, 1.0, 0.14)
            cr.fill_preserve()
            cr.set_source_rgba(0.0, 0.45, 1.0, 0.95)
        elif self.window.mode == "rechteck":
            cr.set_source_rgba(red, green, blue, 0.95)
        else:
            cr.set_source_rgba(0.2, 0.5, 1.0, 0.2)
            cr.fill_preserve()
            cr.set_source_rgba(0.2, 0.5, 1.0, 0.85)
        cr.stroke()

    def _draw(self, area, cr: cairo.Context, width: int, height: int) -> None:
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.paint()
        self.window.document.render_page(self.page_index, cr, self.window.zoom)
        self._draw_search_hits(cr)
        self._draw_drag(cr)


class ThumbnailView(Gtk.DrawingArea):
    def __init__(self, surface: cairo.ImageSurface):
        super().__init__()
        self.surface = surface
        self.set_content_width(surface.get_width())
        self.set_content_height(surface.get_height())
        self.set_draw_func(self._draw)

    def _draw(self, area, cr: cairo.Context, width: int, height: int) -> None:
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.paint()
        cr.set_source_surface(self.surface, 0, 0)
        cr.paint()


class DocumentWindow(Gtk.ApplicationWindow):
    def __init__(self, app: "LiViewApplication", document: BaseDocument):
        super().__init__(application=app)
        self.app = app
        self.document = document
        self.zoom = 1.0
        self.current_page = 0
        self.mode = "auswahl"
        self.current_color = (0.12, 0.45, 0.94)
        self.current_width = 3.0
        self.current_font_size = 24.0
        self.signature_strokes: list[list[tuple[float, float]]] = []
        self.markup_modes: list[str] = []
        self.search_hits: list[SearchHit] = []
        self.search_position = -1
        self.selection_page = -1
        self.selection_rect: tuple[float, float, float, float] | None = None
        self.crop_page = -1
        self.crop_rect: tuple[float, float, float, float] | None = None
        self.page_views: list[PageView] = []
        self.thumbnail_rows: list[Gtk.ListBoxRow] = []
        self._syncing_thumbnail = False
        self.video_widget: Gtk.Video | None = None
        self.animation_source_id = 0
        self.thumbnail_source_id = 0
        self.thumbnail_queue: list[Gtk.ListBoxRow] = []
        self.set_default_size(1180, 820)
        self.set_size_request(720, 480)
        self._build_actions()
        self._build_ui()
        self._install_drop_target()
        self._rebuild_document()
        self._force_close = False
        self.connect("close-request", self._on_close_request)
        self.present()

    def _install_drop_target(self) -> None:
        target = Gtk.DropTarget.new(type=GObject.TYPE_NONE, actions=Gdk.DragAction.COPY)
        target.set_gtypes([Gdk.FileList])
        target.connect("drop", self._on_files_dropped)
        self.add_controller(target)

    def _on_files_dropped(self, target, value, x: float, y: float) -> bool:
        if not isinstance(value, Gdk.FileList):
            return False
        opened = False
        for file in value.get_files():
            path = file.get_path()
            if path:
                self.app.open_path(path)
                opened = True
        return opened

    def _build_actions(self) -> None:
        group = Gio.SimpleActionGroup()
        self.action_group = group
        self.insert_action_group("win", group)
        actions = {
            "open": self._action_open,
            "save": self._action_save,
            "save_as": self._action_save_as,
            "export": self._action_export,
            "print": self._action_print,
            "find": self._action_find,
            "copy": self._action_copy,
            "zoom_in": self._action_zoom_in,
            "zoom_out": self._action_zoom_out,
            "actual_size": self._action_actual_size,
            "rotate_left": self._action_rotate_left,
            "rotate_right": self._action_rotate_right,
            "delete_page": self._action_delete_page,
            "duplicate_page": self._action_duplicate_page,
            "move_up": self._action_move_up,
            "move_down": self._action_move_down,
            "append_pdf": self._action_append_pdf,
            "crop_mode": self._action_crop_mode,
            "apply_crop": self._action_apply_crop,
            "fit_view": self._action_fit_view,
            "view_iso": self._action_view_iso,
            "view_front": self._action_view_front,
            "view_back": self._action_view_back,
            "view_left": self._action_view_left,
            "view_right": self._action_view_right,
            "view_top": self._action_view_top,
            "view_bottom": self._action_view_bottom,
            "projection_toggle": self._action_projection_toggle,
            "wireframe_toggle": self._action_wireframe_toggle,
            "grid_toggle": self._action_grid_toggle,
            "undo": self._action_undo,
            "redo": self._action_redo,
            "flip_horizontal": self._action_flip_horizontal,
            "flip_vertical": self._action_flip_vertical,
            "form_fill": self._action_form_fill,
            "form_reset": self._action_form_reset,
            "signature_draw": self._action_signature_draw,
            "ocr": self._action_ocr,
            "pdf_optimize": self._action_pdf_optimize,
            "pdf_compress": self._action_pdf_compress,
            "pdf_protect": self._action_pdf_protect,
        }
        for name, callback in actions.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            group.add_action(action)

    def _icon_button(self, icon: str, tooltip: str, action: str | None = None) -> Gtk.Button:
        button = Gtk.Button()
        button.set_icon_name(icon)
        button.set_tooltip_text(tooltip)
        if action:
            button.set_action_name(action)
        return button

    def _build_ui(self) -> None:
        self.header = Gtk.HeaderBar()
        self.header.set_show_title_buttons(True)
        self.title_label = Gtk.Label()
        self.title_label.add_css_class("title")
        self.header.set_title_widget(self.title_label)

        open_button = self._icon_button("document-open-symbolic", "Öffnen", "win.open")
        self.sidebar_button = Gtk.ToggleButton()
        self.sidebar_button.set_icon_name("sidebar-show-symbolic")
        self.sidebar_button.set_tooltip_text("Seitenleiste")
        self.sidebar_button.set_active(True)
        self.sidebar_button.connect("toggled", self._toggle_sidebar)
        self.header.pack_start(open_button)
        self.header.pack_start(self.sidebar_button)
        self.info_button = Gtk.ToggleButton()
        self.info_button.set_icon_name("dialog-information-symbolic")
        self.info_button.set_tooltip_text("Informationen")
        self.info_button.connect("toggled", self._toggle_inspector)
        self.header.pack_end(self.info_button)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("PDF durchsuchen")
        self.search_entry.set_size_request(220, -1)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("next-match", self._on_search_next)
        self.search_entry.connect("previous-match", self._on_search_previous)
        self.header.pack_end(self._icon_button("document-save-symbolic", "Speichern", "win.save"))
        self.header.pack_end(self._icon_button("document-print-symbolic", "Drucken", "win.print"))
        self.header.pack_end(self._icon_button("object-rotate-right-symbolic", "Rechts drehen", "win.rotate_right"))
        self.header.pack_end(self._icon_button("object-rotate-left-symbolic", "Links drehen", "win.rotate_left"))
        self.header.pack_end(self._icon_button("zoom-in-symbolic", "Vergrößern", "win.zoom_in"))
        self.header.pack_end(self._icon_button("zoom-out-symbolic", "Verkleinern", "win.zoom_out"))
        self.header.pack_end(self.search_entry)

        self.set_titlebar(self.header)

        self.root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.toolbar.add_css_class("secondary-toolbar")
        self.toolbar.set_margin_start(8)
        self.toolbar.set_margin_end(8)
        self.toolbar.set_margin_top(6)
        self.toolbar.set_margin_bottom(6)
        self.toolbar.append(self._icon_button("edit-copy-symbolic", "Auswahl kopieren", "win.copy"))
        self.crop_button = self._icon_button("edit-cut-symbolic", "Zuschneiden", "win.crop_mode")
        self.toolbar.append(self.crop_button)
        self.apply_crop_button = Gtk.Button(label="Zuschneiden anwenden")
        self.apply_crop_button.set_action_name("win.apply_crop")
        self.apply_crop_button.set_visible(False)
        self.toolbar.append(self.apply_crop_button)
        self.toolbar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        self.toolbar.append(self._icon_button("go-up-symbolic", "Seite nach oben", "win.move_up"))
        self.toolbar.append(self._icon_button("go-down-symbolic", "Seite nach unten", "win.move_down"))
        self.toolbar.append(self._icon_button("edit-copy-symbolic", "Seite duplizieren", "win.duplicate_page"))
        self.toolbar.append(self._icon_button("edit-delete-symbolic", "Seite löschen", "win.delete_page"))
        self.toolbar.append(self._icon_button("list-add-symbolic", "PDF anhängen", "win.append_pdf"))
        self.toolbar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        self.toolbar.append(self._icon_button("document-save-as-symbolic", "Speichern unter", "win.save_as"))
        export_button = Gtk.Button(label="Exportieren")
        export_button.set_action_name("win.export")
        self.toolbar.append(export_button)
        self.pdf_menu_button = Gtk.MenuButton(label="PDF")
        pdf_menu = Gio.Menu()
        pdf_menu.append("Optimierte Kopie speichern…", "win.pdf_optimize")
        pdf_menu.append("PDF verkleinern…", "win.pdf_compress")
        pdf_menu.append("Mit Passwort schützen…", "win.pdf_protect")
        self.pdf_menu_button.set_menu_model(pdf_menu)
        self.toolbar.append(self.pdf_menu_button)
        self.root.append(self.toolbar)

        self.markup_toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.markup_toolbar.add_css_class("secondary-toolbar")
        self.markup_toolbar.add_css_class("markup-toolbar")
        self.markup_toolbar.set_margin_start(8)
        self.markup_toolbar.set_margin_end(8)
        self.markup_toolbar.set_margin_top(4)
        self.markup_toolbar.set_margin_bottom(6)
        self.markup_toolbar.append(Gtk.Label(label="Werkzeug:"))
        self.tool_dropdown = Gtk.DropDown.new_from_strings(["Auswahl"])
        self.tool_dropdown.set_size_request(150, -1)
        self.tool_dropdown.connect("notify::selected", self._on_tool_changed)
        self.markup_toolbar.append(self.tool_dropdown)
        self.markup_toolbar.append(Gtk.Label(label="Farbe:"))
        self.color_names = ["Schwarz", "Blau", "Rot", "Grün", "Gelb", "Weiß"]
        self.color_values = [
            (0.05, 0.05, 0.05),
            (0.12, 0.45, 0.94),
            (0.90, 0.16, 0.18),
            (0.10, 0.65, 0.28),
            (0.98, 0.78, 0.08),
            (1.0, 1.0, 1.0),
        ]
        self.color_dropdown = Gtk.DropDown.new_from_strings(self.color_names)
        self.color_dropdown.set_selected(1)
        self.color_dropdown.connect("notify::selected", self._on_color_changed)
        self.markup_toolbar.append(self.color_dropdown)
        self.markup_toolbar.append(Gtk.Label(label="Stärke:"))
        self.width_spin = Gtk.SpinButton.new_with_range(1.0, 20.0, 1.0)
        self.width_spin.set_value(self.current_width)
        self.width_spin.connect("value-changed", self._on_width_changed)
        self.markup_toolbar.append(self.width_spin)
        self.markup_toolbar.append(Gtk.Label(label="Schriftgröße:"))
        self.font_spin = Gtk.SpinButton.new_with_range(8.0, 72.0, 1.0)
        self.font_spin.set_value(self.current_font_size)
        self.font_spin.connect("value-changed", self._on_font_changed)
        self.markup_toolbar.append(self.font_spin)
        self.markup_toolbar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        self.markup_toolbar.append(self._icon_button("edit-undo-symbolic", "Rückgängig", "win.undo"))
        self.markup_toolbar.append(self._icon_button("edit-redo-symbolic", "Wiederholen", "win.redo"))
        self.markup_toolbar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        self.form_button = Gtk.Button(label="Formular ausfüllen")
        self.form_button.set_action_name("win.form_fill")
        self.markup_toolbar.append(self.form_button)
        self.form_reset_button = Gtk.Button(label="Formular zurücksetzen")
        self.form_reset_button.set_action_name("win.form_reset")
        self.markup_toolbar.append(self.form_reset_button)
        self.signature_button = Gtk.Button(label="Unterschrift zeichnen")
        self.signature_button.set_action_name("win.signature_draw")
        self.markup_toolbar.append(self.signature_button)
        self.flip_horizontal_button = Gtk.Button(label="Horizontal spiegeln")
        self.flip_horizontal_button.set_action_name("win.flip_horizontal")
        self.markup_toolbar.append(self.flip_horizontal_button)
        self.flip_vertical_button = Gtk.Button(label="Vertikal spiegeln")
        self.flip_vertical_button.set_action_name("win.flip_vertical")
        self.markup_toolbar.append(self.flip_vertical_button)
        self.root.append(self.markup_toolbar)

        self.stl_toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.stl_toolbar.add_css_class("secondary-toolbar")
        self.stl_toolbar.add_css_class("stl-toolbar")
        self.stl_toolbar.set_margin_start(8)
        self.stl_toolbar.set_margin_end(8)
        self.stl_toolbar.set_margin_top(6)
        self.stl_toolbar.set_margin_bottom(6)
        for label, action_name in (
            ("Einpassen", "win.fit_view"),
            ("Isometrisch", "win.view_iso"),
            ("Vorne", "win.view_front"),
            ("Hinten", "win.view_back"),
            ("Links", "win.view_left"),
            ("Rechts", "win.view_right"),
            ("Oben", "win.view_top"),
            ("Unten", "win.view_bottom"),
        ):
            button = Gtk.Button(label=label)
            button.set_action_name(action_name)
            self.stl_toolbar.append(button)
        self.stl_toolbar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        self.projection_button = Gtk.Button(label="Perspektivisch")
        self.projection_button.set_action_name("win.projection_toggle")
        self.stl_toolbar.append(self.projection_button)
        self.wireframe_button = Gtk.Button(label="Drahtgitter: Aus")
        self.wireframe_button.set_action_name("win.wireframe_toggle")
        self.stl_toolbar.append(self.wireframe_button)
        self.grid_button = Gtk.Button(label="Raster: Ein")
        self.grid_button.set_action_name("win.grid_toggle")
        self.stl_toolbar.append(self.grid_button)
        self.stl_toolbar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        export_3d_button = Gtk.Button(label="PNG/JPEG exportieren")
        export_3d_button.set_action_name("win.export")
        self.stl_toolbar.append(export_3d_button)
        self.stl_toolbar.set_visible(False)
        self.root.append(self.stl_toolbar)

        self.content_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.content_paned.set_position(190)
        self.sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.sidebar.set_size_request(170, -1)
        self.sidebar.add_css_class("sidebar")
        self.sidebar_title = Gtk.Label(label="Seiten")
        self.sidebar_title.add_css_class("heading")
        self.sidebar_title.set_xalign(0.0)
        self.sidebar_title.set_margin_start(12)
        self.sidebar_title.set_margin_top(10)
        self.sidebar_title.set_margin_bottom(8)
        self.sidebar.append(self.sidebar_title)
        self.thumbnail_list = Gtk.ListBox()
        self.thumbnail_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.thumbnail_list.connect("row-selected", self._on_thumbnail_selected)
        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar_scroll.set_child(self.thumbnail_list)
        sidebar_scroll.set_vexpand(True)
        self.sidebar.append(sidebar_scroll)
        self.content_paned.set_start_child(self.sidebar)

        self.document_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22)
        self.document_box.set_halign(Gtk.Align.CENTER)
        self.document_box.set_margin_top(24)
        self.document_box.set_margin_bottom(24)
        self.document_box.set_margin_start(24)
        self.document_box.set_margin_end(24)
        self.document_scroller = Gtk.ScrolledWindow()
        self.document_scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.document_scroller.set_child(self.document_box)
        self.document_scroller.set_hexpand(True)
        self.document_scroller.set_vexpand(True)
        self.document_scroller.add_css_class("document-scroller")
        self.content_paned.set_end_child(self.document_scroller)

        self.inspector_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.inspector_box.set_size_request(290, -1)
        self.inspector_box.add_css_class("sidebar")
        inspector_title = Gtk.Label(label="Informationen")
        inspector_title.add_css_class("heading")
        inspector_title.set_xalign(0.0)
        inspector_title.set_margin_start(14)
        inspector_title.set_margin_top(12)
        self.inspector_box.append(inspector_title)
        self.inspector_list = Gtk.ListBox()
        self.inspector_list.set_selection_mode(Gtk.SelectionMode.NONE)
        inspector_scroll = Gtk.ScrolledWindow()
        inspector_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        inspector_scroll.set_vexpand(True)
        inspector_scroll.set_child(self.inspector_list)
        self.inspector_box.append(inspector_scroll)
        self.ocr_button = Gtk.Button(label="Text erkennen (OCR)")
        self.ocr_button.set_action_name("win.ocr")
        self.ocr_button.set_margin_start(12)
        self.ocr_button.set_margin_end(12)
        self.ocr_button.set_margin_bottom(12)
        self.inspector_box.append(self.ocr_button)
        self.inspector_revealer = Gtk.Revealer()
        self.inspector_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_LEFT)
        self.inspector_revealer.set_reveal_child(False)
        self.inspector_revealer.set_child(self.inspector_box)
        self.content_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.content_paned.set_hexpand(True)
        self.content_row.append(self.content_paned)
        self.content_row.append(self.inspector_revealer)
        self.root.append(self.content_row)

        status = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        status.add_css_class("statusbar")
        status.set_margin_start(12)
        status.set_margin_end(12)
        status.set_margin_top(5)
        status.set_margin_bottom(5)
        self.status_page = Gtk.Label()
        self.status_page.set_xalign(0.0)
        self.status_page.set_hexpand(True)
        self.status_zoom = Gtk.Label()
        self.status_dirty = Gtk.Label()
        status.append(self.status_page)
        status.append(self.status_zoom)
        status.append(self.status_dirty)
        self.root.append(status)
        self.set_child(self.root)

    def _toggle_inspector(self, button: Gtk.ToggleButton) -> None:
        self.inspector_revealer.set_reveal_child(button.get_active())
        if button.get_active():
            self._refresh_inspector()

    def _refresh_inspector(self) -> None:
        self._clear_container(self.inspector_list)
        try:
            rows = document_info(self.document)
        except Exception as exc:
            rows = [("Information", f"Nicht lesbar: {exc}")]
        for label, value in rows:
            row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            row.set_margin_start(12)
            row.set_margin_end(12)
            row.set_margin_top(7)
            row.set_margin_bottom(7)
            name = Gtk.Label(label=label)
            name.add_css_class("dim-label")
            name.set_xalign(0.0)
            text = Gtk.Label(label=value)
            text.set_xalign(0.0)
            text.set_wrap(True)
            text.set_selectable(True)
            row.append(name)
            row.append(text)
            self.inspector_list.append(row)

    def _action_ocr(self, action, parameter) -> None:
        if not isinstance(self.document, (PdfDocument, ImageDocument)):
            return
        try:
            text = recognize_text(self.document, self.current_page)
        except Exception as exc:
            self._show_error("Texterkennung fehlgeschlagen", str(exc))
            return
        dialog = Gtk.AlertDialog()
        dialog.set_message("Erkannter Text")
        dialog.set_detail(text if text else "Es wurde kein Text erkannt.")
        dialog.set_buttons(["Schließen", "Kopieren"])
        dialog.set_cancel_button(0)
        dialog.choose(self, None, lambda d, r: self._finish_ocr_dialog(d, r, text))

    def _finish_ocr_dialog(self, dialog: Gtk.AlertDialog, result, text: str) -> None:
        try:
            choice = dialog.choose_finish(result)
        except GLib.Error:
            return
        if choice == 1 and text:
            display = Gdk.Display.get_default()
            if display is not None:
                display.get_clipboard().set(text)

    def _clear_container(self, container) -> None:
        child = container.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            container.remove(child)
            child = next_child

    def _cancel_thumbnail_loading(self) -> None:
        if self.thumbnail_source_id:
            GLib.source_remove(self.thumbnail_source_id)
            self.thumbnail_source_id = 0
        self.thumbnail_queue = []

    def _render_thumbnail_row(self, row: Gtk.ListBoxRow) -> None:
        if getattr(row, "thumbnail_loaded", False):
            return
        index = int(row.page_index)
        box = row.get_child()
        if box is None:
            return
        placeholder = getattr(row, "thumbnail_placeholder", None)
        try:
            widget = ThumbnailView(self.document.render_thumbnail(index))
        except Exception:
            widget = Gtk.Label(label=f"Seite {index + 1}")
        if placeholder is not None and placeholder.get_parent() is box:
            box.remove(placeholder)
        box.prepend(widget)
        row.thumbnail_loaded = True

    def _load_next_thumbnail(self) -> bool:
        self.thumbnail_source_id = 0
        if not self.thumbnail_queue:
            return GLib.SOURCE_REMOVE
        row = self.thumbnail_queue.pop(0)
        if row.get_parent() is self.thumbnail_list:
            self._render_thumbnail_row(row)
        if self.thumbnail_queue:
            self.thumbnail_source_id = GLib.idle_add(self._load_next_thumbnail)
        return GLib.SOURCE_REMOVE

    def _schedule_thumbnail_loading(self) -> None:
        self._cancel_thumbnail_loading()
        self.thumbnail_queue = [row for row in self.thumbnail_rows if not getattr(row, "thumbnail_loaded", False)]
        if self.thumbnail_queue:
            self.thumbnail_source_id = GLib.idle_add(self._load_next_thumbnail)

    def _rebuild_document(self) -> None:
        self._cancel_animation()
        self._cancel_thumbnail_loading()
        self._clear_container(self.document_box)
        self._clear_container(self.thumbnail_list)
        self.page_views = []
        self.thumbnail_rows = []
        self.video_widget = None
        is_video = isinstance(self.document, VideoDocument)
        is_3d = isinstance(self.document, StlDocument)
        if is_video:
            self.document_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
            self.video_widget = Gtk.Video.new_for_filename(self.document.path)
            self.video_widget.set_autoplay(True)
            self.video_widget.set_loop(False)
            self.video_widget.set_hexpand(True)
            self.video_widget.set_vexpand(True)
            self.video_widget.set_halign(Gtk.Align.FILL)
            self.video_widget.set_valign(Gtk.Align.FILL)
            self.video_widget.set_margin_top(24)
            self.video_widget.set_margin_bottom(24)
            self.video_widget.set_margin_start(24)
            self.video_widget.set_margin_end(24)
            self.document_scroller.set_child(self.video_widget)
        else:
            self.document_scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            self.document_scroller.set_child(self.document_box)
            for page_index in range(self.document.page_count):
                frame = Gtk.Frame()
                frame.add_css_class("page-frame")
                page_view = PageView(self, page_index)
                frame.set_child(page_view)
                self.document_box.append(frame)
                self.page_views.append(page_view)

                row = Gtk.ListBoxRow()
                row.page_index = page_index
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                box.set_margin_top(8)
                box.set_margin_bottom(8)
                box.set_margin_start(8)
                box.set_margin_end(8)
                placeholder = Gtk.Spinner()
                placeholder.set_spinning(True)
                placeholder.set_size_request(132, 80)
                box.append(placeholder)
                row.thumbnail_placeholder = placeholder
                row.thumbnail_loaded = False
                number = Gtk.Label(label="3D" if is_3d else str(page_index + 1))
                number.add_css_class("dim-label")
                box.append(number)
                row.set_child(box)
                self.thumbnail_list.append(row)
                self.thumbnail_rows.append(row)

        if self.thumbnail_rows:
            self._render_thumbnail_row(self.thumbnail_rows[max(0, min(self.current_page, len(self.thumbnail_rows) - 1))])
            self._schedule_thumbnail_loading()

        self.search_entry.set_sensitive(isinstance(self.document, PdfDocument))
        ocr_action = self.lookup_action("ocr")
        if ocr_action is not None:
            ocr_action.set_enabled(isinstance(self.document, (PdfDocument, ImageDocument)))
        self.ocr_button.set_visible(isinstance(self.document, (PdfDocument, ImageDocument)))
        pdf_controls = isinstance(self.document, PdfDocument)
        self.pdf_menu_button.set_visible(pdf_controls)
        for name in ("pdf_optimize", "pdf_compress", "pdf_protect"):
            action = self.lookup_action(name)
            if action is not None:
                action.set_enabled(pdf_controls)
        for name in ("delete_page", "duplicate_page", "move_up", "move_down", "append_pdf"):
            action = self.lookup_action(name)
            if action is not None:
                action.set_enabled(pdf_controls)
        editable_view = not is_3d and not is_video
        for name in ("copy", "crop_mode", "apply_crop"):
            action = self.lookup_action(name)
            if action is not None:
                action.set_enabled(editable_view)
        history_view = isinstance(self.document, (PdfDocument, ImageDocument))
        undo_action = self.lookup_action("undo")
        redo_action = self.lookup_action("redo")
        if undo_action is not None:
            undo_action.set_enabled(history_view and bool(getattr(self.document, "can_undo", False)))
        if redo_action is not None:
            redo_action.set_enabled(history_view and bool(getattr(self.document, "can_redo", False)))
        image_view = isinstance(self.document, ImageDocument)
        form_fields = self.document.form_fields() if isinstance(self.document, PdfDocument) else []
        form_available = bool(form_fields)
        for name in ("form_fill", "form_reset"):
            action = self.lookup_action(name)
            if action is not None:
                action.set_enabled(form_available)
        signature_action = self.lookup_action("signature_draw")
        if signature_action is not None:
            signature_action.set_enabled(isinstance(self.document, (PdfDocument, ImageDocument)))
        self.form_button.set_visible(isinstance(self.document, PdfDocument))
        self.form_button.set_sensitive(form_available)
        self.form_reset_button.set_visible(isinstance(self.document, PdfDocument))
        self.form_reset_button.set_sensitive(form_available)
        self.signature_button.set_visible(isinstance(self.document, (PdfDocument, ImageDocument)))
        for name in ("flip_horizontal", "flip_vertical"):
            action = self.lookup_action(name)
            if action is not None:
                action.set_enabled(image_view)
        for name in ("print", "rotate_left", "rotate_right", "zoom_in", "zoom_out", "actual_size", "export", "save"):
            action = self.lookup_action(name)
            if action is not None:
                action.set_enabled(not is_video)
        save_as_action = self.lookup_action("save_as")
        if save_as_action is not None:
            save_as_action.set_enabled(True)
        self.crop_button.set_sensitive(editable_view)
        self.toolbar.set_visible(editable_view)
        self.markup_toolbar.set_visible(editable_view)
        self._update_markup_controls()
        self.stl_toolbar.set_visible(is_3d)
        self.sidebar_button.set_sensitive(not is_video)
        if is_video:
            self.sidebar_button.set_active(False)
            self.sidebar.set_visible(False)
        if is_3d:
            self.sidebar_title.set_text("3D-Modell")
        elif isinstance(self.document, ImageDocument):
            self.sidebar_title.set_text("Bild")
        else:
            self.sidebar_title.set_text("Seiten")
        self._update_3d_controls()
        self.current_page = max(0, min(self.current_page, self.document.page_count - 1))
        if self.thumbnail_rows:
            self._syncing_thumbnail = True
            self.thumbnail_list.select_row(self.thumbnail_rows[self.current_page])
            self._syncing_thumbnail = False
        if isinstance(self.document, ImageDocument) and self.document.is_animated:
            self._schedule_animation()
        self._update_title_status()

    def _update_markup_controls(self) -> None:
        if not isinstance(self.document, (PdfDocument, ImageDocument)):
            return
        if isinstance(self.document, PdfDocument):
            labels_modes = [
                ("Auswahl", "auswahl"),
                ("Stift", "stift"),
                ("Linie", "linie"),
                ("Pfeil", "pfeil"),
                ("Rechteck", "rechteck"),
                ("Ellipse", "ellipse"),
                ("Text", "text"),
                ("Hervorheben", "hervorheben"),
                ("Unterstreichen", "unterstreichen"),
                ("Durchstreichen", "durchstreichen"),
                ("Schwärzen", "schwaerzen"),
                ("Notiz", "notiz"),
                ("Unterschrift", "unterschrift"),
            ]
        else:
            labels_modes = [
                ("Auswahl", "auswahl"),
                ("Stift", "stift"),
                ("Linie", "linie"),
                ("Pfeil", "pfeil"),
                ("Rechteck", "rechteck"),
                ("Ellipse", "ellipse"),
                ("Text", "text"),
                ("Hervorheben", "hervorheben"),
                ("Unterschrift", "unterschrift"),
            ]
        labels = [item[0] for item in labels_modes]
        self.markup_modes = [item[1] for item in labels_modes]
        selected = self.markup_modes.index(self.mode) if self.mode in self.markup_modes else 0
        self.tool_dropdown.set_model(Gtk.StringList.new(labels))
        self.tool_dropdown.set_selected(selected)
        if self.mode not in self.markup_modes:
            self.mode = "auswahl"
        image_view = isinstance(self.document, ImageDocument)
        self.flip_horizontal_button.set_visible(image_view)
        self.flip_vertical_button.set_visible(image_view)

    def _on_tool_changed(self, dropdown, pspec) -> None:
        selected = int(dropdown.get_selected())
        if selected < 0 or selected >= len(self.markup_modes):
            return
        self.mode = self.markup_modes[selected]
        if self.mode == "unterschrift" and not self.signature_strokes:
            self._action_signature_draw(None, None)
        self.apply_crop_button.set_visible(False)
        self.crop_button.set_tooltip_text("Zuschneiden")
        self._update_page_cursors()

    def _on_color_changed(self, dropdown, pspec) -> None:
        selected = int(dropdown.get_selected())
        if 0 <= selected < len(self.color_values):
            self.current_color = self.color_values[selected]

    def _on_width_changed(self, spin) -> None:
        self.current_width = float(spin.get_value())

    def _on_font_changed(self, spin) -> None:
        self.current_font_size = float(spin.get_value())

    def _update_page_cursors(self) -> None:
        cursor = "text"
        if self.mode in {"crop", "stift", "linie", "pfeil", "rechteck", "ellipse", "hervorheben", "unterstreichen", "durchstreichen", "schwaerzen", "unterschrift"}:
            cursor = "crosshair"
        elif self.mode in {"text", "notiz"}:
            cursor = "cell"
        for page in self.page_views:
            if not isinstance(self.document, StlDocument):
                page.set_cursor_from_name(cursor)

    def _refresh_after_edit(self) -> None:
        self.search_hits = []
        self.search_position = -1
        self.search_entry.set_text("")
        self._clear_drag_selections()
        self._rebuild_document()

    def commit_markup(
        self,
        page_index: int,
        kind: str,
        rect: tuple[float, float, float, float],
        points: list[tuple[float, float]],
    ) -> None:
        try:
            if isinstance(self.document, ImageDocument):
                rgba = tuple(int(round(channel * 255.0)) for channel in self.current_color) + (255,)
                self.document.add_markup(
                    kind,
                    rect=rect,
                    points=points,
                    color=rgba,
                    width=max(1, int(round(self.current_width))),
                    font_size=max(8, int(round(self.current_font_size))),
                )
            elif isinstance(self.document, PdfDocument):
                if kind == "schwaerzen":
                    self._confirm_redaction(page_index, rect)
                    return
                self.document.add_markup(
                    page_index,
                    kind,
                    rect=rect,
                    points=points,
                    color=self.current_color,
                    width=self.current_width,
                    font_size=self.current_font_size,
                )
            else:
                return
            self.current_page = page_index
            self._refresh_after_edit()
        except Exception as exc:
            self._show_error("Anmerkung fehlgeschlagen", str(exc))


    def _confirm_redaction(self, page_index: int, rect: tuple[float, float, float, float]) -> None:
        dialog = Gtk.AlertDialog()
        dialog.set_message("Schwärzung endgültig anwenden?")
        dialog.set_detail(
            "Für eine sichere Schwärzung wird eine neue Bildfassung des gesamten PDFs erzeugt. "
            "Text, Formulare, Links und vorhandene PDF-Strukturen werden dabei entfernt. "
            "Bis zum Speichern kann die Änderung mit Rückgängig widerrufen werden."
        )
        dialog.set_buttons(["Abbrechen", "Schwärzen"])
        dialog.set_cancel_button(0)
        dialog.set_default_button(0)
        dialog.choose(self, None, self._finish_redaction_confirmation, (page_index, rect))

    def _finish_redaction_confirmation(self, dialog: Gtk.AlertDialog, result, payload) -> None:
        try:
            choice = dialog.choose_finish(result)
        except GLib.Error:
            return
        if choice != 1:
            return
        page_index, rect = payload
        try:
            self.document.secure_redact(page_index, rect)
            self.current_page = page_index
            self._refresh_after_edit()
        except Exception as exc:
            self._show_error("Schwärzung fehlgeschlagen", str(exc))

    def draw_signature_preview(self, cr: cairo.Context, left: float, top: float, width: float, height: float) -> None:
        if not self.signature_strokes or width <= 0 or height <= 0:
            return
        cr.save()
        cr.set_source_rgba(0.03, 0.03, 0.03, 0.95)
        cr.set_line_width(max(1.5, height / 28.0))
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        for stroke in self.signature_strokes:
            if len(stroke) < 2:
                continue
            cr.move_to(left + stroke[0][0] * width, top + stroke[0][1] * height)
            for x, y in stroke[1:]:
                cr.line_to(left + x * width, top + y * height)
            cr.stroke()
        cr.restore()

    def commit_signature(self, page_index: int, rect: tuple[float, float, float, float]) -> None:
        if not self.signature_strokes:
            self._show_error("Unterschrift fehlt", "Zeichne zuerst eine Unterschrift über „Unterschrift zeichnen“.")
            return
        try:
            if isinstance(self.document, PdfDocument):
                self.document.add_signature(page_index, rect, self.signature_strokes)
            elif isinstance(self.document, ImageDocument):
                self.document.add_signature(rect, self.signature_strokes)
            else:
                return
            self.current_page = page_index
            self._refresh_after_edit()
        except Exception as exc:
            self._show_error("Unterschrift konnte nicht eingefügt werden", str(exc))

    def _action_signature_draw(self, action, parameter) -> None:
        if not isinstance(self.document, (PdfDocument, ImageDocument)):
            return
        dialog = Gtk.Window(transient_for=self, modal=True)
        dialog.set_title("Unterschrift zeichnen")
        dialog.set_default_size(680, 360)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_top(16)
        root.set_margin_bottom(16)
        root.set_margin_start(16)
        root.set_margin_end(16)
        root.append(Gtk.Label(label="Mit Maus oder Touchpad unterschreiben. Danach auf „Verwenden“ klicken und im Dokument einen Bereich aufziehen."))
        pad = Gtk.DrawingArea()
        pad.set_content_width(620)
        pad.set_content_height(220)
        pad.add_css_class("signature-pad")
        strokes: list[list[tuple[float, float]]] = []
        current: list[tuple[float, float]] = []

        def draw_pad(area, cr, width, height):
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.paint()
            cr.set_source_rgb(0.86, 0.86, 0.86)
            cr.set_line_width(1.0)
            cr.move_to(24, height - 42)
            cr.line_to(width - 24, height - 42)
            cr.stroke()
            cr.set_source_rgb(0.03, 0.03, 0.03)
            cr.set_line_width(4.0)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.set_line_join(cairo.LINE_JOIN_ROUND)
            for stroke in strokes + ([current] if current else []):
                if len(stroke) < 2:
                    continue
                cr.move_to(*stroke[0])
                for point in stroke[1:]:
                    cr.line_to(*point)
                cr.stroke()

        pad.set_draw_func(draw_pad)
        drag = Gtk.GestureDrag.new()
        drag.set_button(1)
        start = [0.0, 0.0]

        def drag_begin(gesture, x, y):
            start[0], start[1] = x, y
            current.clear()
            current.append((x, y))
            pad.queue_draw()

        def drag_update(gesture, dx, dy):
            current.append((start[0] + dx, start[1] + dy))
            pad.queue_draw()

        def drag_end(gesture, dx, dy):
            if len(current) >= 2:
                current.append((start[0] + dx, start[1] + dy))
                strokes.append(list(current))
            current.clear()
            pad.queue_draw()

        drag.connect("drag-begin", drag_begin)
        drag.connect("drag-update", drag_update)
        drag.connect("drag-end", drag_end)
        pad.add_controller(drag)
        root.append(pad)
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        clear = Gtk.Button(label="Löschen")
        cancel = Gtk.Button(label="Abbrechen")
        use = Gtk.Button(label="Verwenden")
        use.add_css_class("suggested-action")
        buttons.append(clear)
        buttons.append(cancel)
        buttons.append(use)
        root.append(buttons)
        dialog.set_child(root)

        def clear_pad(button):
            strokes.clear()
            current.clear()
            pad.queue_draw()

        def use_signature(button):
            if not any(len(stroke) >= 2 for stroke in strokes):
                self._show_error("Unterschrift fehlt", "Bitte zuerst eine Unterschrift zeichnen.")
                return
            width = max(1.0, float(pad.get_width()))
            height = max(1.0, float(pad.get_height()))
            self.signature_strokes = [
                [(max(0.0, min(1.0, x / width)), max(0.0, min(1.0, y / height))) for x, y in stroke]
                for stroke in strokes if len(stroke) >= 2
            ]
            self.mode = "unterschrift"
            self._update_markup_controls()
            self._update_page_cursors()
            dialog.close()

        clear.connect("clicked", clear_pad)
        cancel.connect("clicked", lambda button: dialog.close())
        use.connect("clicked", use_signature)
        dialog.present()

    def _action_form_fill(self, action, parameter) -> None:
        if not isinstance(self.document, PdfDocument):
            return
        try:
            fields = self.document.form_fields()
        except Exception as exc:
            self._show_error("Formular konnte nicht gelesen werden", str(exc))
            return
        if not fields:
            self._show_info("Kein Formular", "Dieses PDF enthält keine ausfüllbaren AcroForm-Felder.")
            return
        dialog = Gtk.Window(transient_for=self, modal=True)
        dialog.set_title("PDF-Formular ausfüllen")
        dialog.set_default_size(560, 620)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(16)
        outer.set_margin_bottom(16)
        outer.set_margin_start(16)
        outer.set_margin_end(16)
        outer.append(Gtk.Label(label=f"{len(fields)} Formularfeld(er) erkannt"))
        grid = Gtk.Grid(column_spacing=12, row_spacing=10)
        grid.set_hexpand(True)
        controls: dict[str, tuple[str, object, list[str]]] = {}
        for row, field in enumerate(fields):
            label = Gtk.Label(label=field.name)
            label.set_xalign(0.0)
            label.set_hexpand(True)
            grid.attach(label, 0, row, 1, 1)
            if field.kind == "text":
                control = Gtk.Entry()
                control.set_text(str(field.value))
                control.set_hexpand(True)
                controls[field.name] = (field.kind, control, [])
            elif field.kind == "checkbox":
                control = Gtk.Switch()
                control.set_active(bool(field.value))
                control.set_halign(Gtk.Align.START)
                controls[field.name] = (field.kind, control, [])
            elif field.kind in {"choice", "radio"}:
                options = list(field.options)
                if field.kind == "choice" and str(field.value) and str(field.value) not in options:
                    options.insert(0, str(field.value))
                if not options:
                    control = Gtk.Entry()
                    control.set_text(str(field.value))
                    controls[field.name] = ("text", control, [])
                else:
                    control = Gtk.DropDown.new_from_strings(options)
                    current = str(field.value)
                    if current in options:
                        control.set_selected(options.index(current))
                    controls[field.name] = (field.kind, control, options)
            else:
                control = Gtk.Label(label="Nicht bearbeitbar")
                control.add_css_class("dim-label")
            grid.attach(control, 1, row, 1, 1)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(grid)
        scroller.set_vexpand(True)
        outer.append(scroller)
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        cancel = Gtk.Button(label="Abbrechen")
        apply_button = Gtk.Button(label="Übernehmen")
        apply_button.add_css_class("suggested-action")
        buttons.append(cancel)
        buttons.append(apply_button)
        outer.append(buttons)
        dialog.set_child(outer)

        def apply_form(button):
            values: dict[str, str | bool] = {}
            for name, (kind, control, options) in controls.items():
                if kind == "text":
                    values[name] = control.get_text()
                elif kind == "checkbox":
                    values[name] = bool(control.get_active())
                elif kind in {"choice", "radio"}:
                    selected = int(control.get_selected())
                    values[name] = options[selected] if 0 <= selected < len(options) else ""
            try:
                self.document.set_form_values(values)
                dialog.close()
                self._refresh_after_edit()
            except Exception as exc:
                self._show_error("Formular konnte nicht gespeichert werden", str(exc))

        cancel.connect("clicked", lambda button: dialog.close())
        apply_button.connect("clicked", apply_form)
        dialog.present()

    def _action_form_reset(self, action, parameter) -> None:
        if not isinstance(self.document, PdfDocument):
            return
        try:
            self.document.reset_form()
            self._refresh_after_edit()
        except Exception as exc:
            self._show_error("Formular konnte nicht zurückgesetzt werden", str(exc))

    def request_text_markup(self, page_index: int, x: float, y: float, kind: str) -> None:
        if kind not in {"text", "notiz"}:
            return
        dialog = Gtk.Window(transient_for=self, modal=True)
        dialog.set_title("Notiz hinzufügen" if kind == "notiz" else "Text hinzufügen")
        dialog.set_default_size(420, 140)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        entry = Gtk.Entry()
        entry.set_placeholder_text("Notiz eingeben" if kind == "notiz" else "Text eingeben")
        entry.set_hexpand(True)
        box.append(entry)
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        cancel = Gtk.Button(label="Abbrechen")
        add = Gtk.Button(label="Hinzufügen")
        add.add_css_class("suggested-action")
        buttons.append(cancel)
        buttons.append(add)
        box.append(buttons)
        dialog.set_child(box)

        def close_dialog(button) -> None:
            dialog.close()

        def add_text(button) -> None:
            text = entry.get_text().strip()
            if not text:
                return
            try:
                if isinstance(self.document, ImageDocument):
                    if kind == "notiz":
                        raise DocumentError("Notizen sind nur in PDF-Dokumenten verfügbar.")
                    rgba = tuple(int(round(channel * 255.0)) for channel in self.current_color) + (255,)
                    self.document.add_markup(
                        "text",
                        rect=(x, y, x, y),
                        text=text,
                        color=rgba,
                        width=max(1, int(round(self.current_width))),
                        font_size=max(8, int(round(self.current_font_size))),
                    )
                elif isinstance(self.document, PdfDocument):
                    self.document.add_markup(
                        page_index,
                        kind,
                        rect=(x, y, x, y),
                        text=text,
                        color=self.current_color,
                        width=self.current_width,
                        font_size=self.current_font_size,
                    )
                else:
                    return
                self.current_page = page_index
                dialog.close()
                self._refresh_after_edit()
            except Exception as exc:
                self._show_error("Text konnte nicht hinzugefügt werden", str(exc))

        cancel.connect("clicked", close_dialog)
        add.connect("clicked", add_text)
        entry.connect("activate", lambda widget: add_text(add))
        dialog.present()
        entry.grab_focus()

    def _cancel_animation(self) -> None:
        if self.animation_source_id:
            GLib.source_remove(self.animation_source_id)
            self.animation_source_id = 0

    def _schedule_animation(self) -> None:
        if not isinstance(self.document, ImageDocument) or not self.document.is_animated:
            return
        self.animation_source_id = GLib.timeout_add(self.document.frame_duration, self._advance_animation)

    def _advance_animation(self) -> bool:
        self.animation_source_id = 0
        if not isinstance(self.document, ImageDocument) or not self.document.is_animated:
            return GLib.SOURCE_REMOVE
        self.document.advance_frame()
        if self.page_views:
            self.page_views[0].queue_draw()
        self._schedule_animation()
        return GLib.SOURCE_REMOVE

    def lookup_action(self, name: str):
        return self.action_group.lookup_action(name)

    def _update_title_status(self) -> None:
        dirty = " •" if self.document.dirty else ""
        self.title_label.set_text(f"{self.document.title}{dirty}")
        self.set_title(f"{self.document.title} — LiView")
        if isinstance(self.document, StlDocument):
            x, y, z = self.document.dimensions
            projection = "Perspektive" if self.document.projection == "perspective" else "Orthografisch"
            mode = "Drahtgitter" if self.document.wireframe else "Schattiert"
            self.status_page.set_text(f"{self.document.format_name} · {self.document.triangle_count:,} Dreiecke · {x:.2f} × {y:.2f} × {z:.2f} mm · {projection} · {mode}")
            self.status_zoom.set_text(f"3D {int(round(self.document.model_zoom * 100))} %")
            self._update_3d_controls()
        elif isinstance(self.document, VideoDocument):
            suffix = self.document.source_suffix.lstrip(".").upper() or "Video"
            self.status_page.set_text(f"Video · {suffix} · Wiedergabe über GStreamer")
            self.status_zoom.set_text("")
        elif isinstance(self.document, ImageDocument) and self.document.is_animated:
            self.status_page.set_text(f"Animiertes Bild · {self.document.frame_count} Einzelbilder")
            self.status_zoom.set_text(f"{int(round(self.zoom * 100))} %")
        else:
            self.status_page.set_text(f"Seite {self.current_page + 1} von {self.document.page_count}")
            self.status_zoom.set_text(f"{int(round(self.zoom * 100))} %")
        self.status_dirty.set_text("  Geändert" if self.document.dirty else "")

    def _update_3d_controls(self) -> None:
        if not isinstance(self.document, StlDocument):
            return
        self.projection_button.set_label("Perspektivisch" if self.document.projection == "perspective" else "Orthografisch")
        self.wireframe_button.set_label("Drahtgitter: Ein" if self.document.wireframe else "Drahtgitter: Aus")
        self.grid_button.set_label("Raster: Ein" if self.document.show_grid else "Raster: Aus")

    def _redraw_3d(self) -> None:
        if not isinstance(self.document, StlDocument) or not self.page_views:
            return
        self.page_views[0].queue_draw()
        self._update_title_status()

    def set_current_page(self, page_index: int) -> None:
        self.current_page = max(0, min(page_index, self.document.page_count - 1))
        if self.thumbnail_rows:
            self._syncing_thumbnail = True
            self.thumbnail_list.select_row(self.thumbnail_rows[self.current_page])
            self._syncing_thumbnail = False
        self._update_title_status()

    def _scroll_to_page(self, page_index: int) -> None:
        if not self.page_views:
            return
        page_index = max(0, min(page_index, len(self.page_views) - 1))
        page = self.page_views[page_index]
        frame = page.get_parent()
        allocation = frame.get_allocation() if frame is not None else page.get_allocation()
        adjustment = self.document_scroller.get_vadjustment()
        adjustment.set_value(max(adjustment.get_lower(), min(float(allocation.y - 24), adjustment.get_upper() - adjustment.get_page_size())))

    def _on_thumbnail_selected(self, box, row) -> None:
        if row is None:
            return
        self._render_thumbnail_row(row)
        self.current_page = int(row.page_index)
        self._update_title_status()
        if not self._syncing_thumbnail:
            GLib.idle_add(self._scroll_to_page, self.current_page)

    def _toggle_sidebar(self, button: Gtk.ToggleButton) -> None:
        self.sidebar.set_visible(button.get_active())

    def set_text_selection(self, page_index: int, rect: tuple[float, float, float, float]) -> None:
        self.selection_page = page_index
        self.selection_rect = rect

    def set_crop_selection(self, page_index: int, rect: tuple[float, float, float, float]) -> None:
        self.crop_page = page_index
        self.crop_rect = rect
        self.apply_crop_button.set_visible(True)

    def _clear_drag_selections(self) -> None:
        for page in self.page_views:
            page.clear_drag()
        self.selection_page = -1
        self.selection_rect = None
        self.crop_page = -1
        self.crop_rect = None

    def _show_error(self, title: str, message: str) -> None:
        dialog = Gtk.AlertDialog()
        dialog.set_modal(True)
        dialog.set_message(title)
        dialog.set_detail(message)
        dialog.show(self)

    def _show_info(self, title: str, message: str) -> None:
        dialog = Gtk.AlertDialog()
        dialog.set_modal(True)
        dialog.set_message(title)
        dialog.set_detail(message)
        dialog.show(self)

    def _open_file_dialog(self, callback, title: str = "Datei öffnen") -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title(title)
        dialog.open(self, None, lambda d, result: self._finish_open_dialog(d, result, callback))

    def _finish_open_dialog(self, dialog: Gtk.FileDialog, result, callback) -> None:
        try:
            file = dialog.open_finish(result)
        except GLib.Error:
            return
        if file is not None:
            callback(file.get_path())

    def _save_file_dialog(self, callback, suggested_name: str) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Datei speichern")
        dialog.set_initial_name(suggested_name)
        dialog.save(self, None, lambda d, result: self._finish_save_dialog(d, result, callback))

    def _finish_save_dialog(self, dialog: Gtk.FileDialog, result, callback) -> None:
        try:
            file = dialog.save_finish(result)
        except GLib.Error:
            return
        if file is not None:
            callback(file.get_path())

    def _action_open(self, action, parameter) -> None:
        self._open_file_dialog(lambda path: self.app.open_path(path))

    def _action_save(self, action, parameter) -> None:
        try:
            self.document.save()
            self._update_title_status()
        except Exception as exc:
            self._show_error("Speichern fehlgeschlagen", str(exc))

    def _action_save_as(self, action, parameter) -> None:
        self._save_file_dialog(self._save_as_target, self.document.title)

    def _save_as_target(self, target: str) -> None:
        if isinstance(self.document, PdfDocument) and Path(target).suffix.lower() != ".pdf":
            self._show_error("PDF-Dateiname erforderlich", "Speichern unter erhält das PDF-Format. Für andere Formate verwende Exportieren.")
            return
        if isinstance(self.document, StlDocument) and Path(target).suffix.lower() != self.document.source_suffix:
            self._show_error(f"{self.document.format_name}-Dateiname erforderlich", f"Speichern unter erhält das {self.document.format_name}-Format. Für ein Vorschaubild verwende Exportieren.")
            return
        if isinstance(self.document, VideoDocument) and Path(target).suffix.lower() != self.document.source_suffix:
            self._show_error("Video-Dateiname erforderlich", f"Speichern unter erhält das ursprüngliche Videoformat {self.document.source_suffix}.")
            return
        try:
            self.document.save_as(target)
            self._update_title_status()
        except Exception as exc:
            self._show_error("Speichern unter fehlgeschlagen", str(exc))

    def _action_export(self, action, parameter) -> None:
        stem = Path(self.document.title).stem
        suggested = f"{stem}-export.pdf" if self.document.kind == "image" else f"{stem}-export.png"
        self._save_file_dialog(self._export_target, suggested)

    def _export_target(self, target: str) -> None:
        try:
            self.document.export(target, self.current_page)
        except Exception as exc:
            self._show_error("Export fehlgeschlagen", str(exc))

    def _action_find(self, action, parameter) -> None:
        self.search_entry.grab_focus()

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        if not isinstance(self.document, PdfDocument):
            return
        query = entry.get_text().strip()
        try:
            self.search_hits = self.document.search(query) if query else []
        except Exception as exc:
            self.search_hits = []
            self._show_error("Suche fehlgeschlagen", str(exc))
        self.search_position = 0 if self.search_hits else -1
        if self.search_position >= 0:
            self.set_current_page(self.search_hits[0].page_index)
            GLib.idle_add(self._scroll_to_page, self.current_page)
        for page in self.page_views:
            page.queue_draw()

    def _on_search_next(self, entry) -> None:
        if not self.search_hits:
            return
        self.search_position = (self.search_position + 1) % len(self.search_hits)
        hit = self.search_hits[self.search_position]
        self.set_current_page(hit.page_index)
        GLib.idle_add(self._scroll_to_page, hit.page_index)
        self.page_views[hit.page_index].queue_draw()

    def _on_search_previous(self, entry) -> None:
        if not self.search_hits:
            return
        self.search_position = (self.search_position - 1) % len(self.search_hits)
        hit = self.search_hits[self.search_position]
        self.set_current_page(hit.page_index)
        GLib.idle_add(self._scroll_to_page, hit.page_index)
        self.page_views[hit.page_index].queue_draw()

    def _action_copy(self, action, parameter) -> None:
        if not isinstance(self.document, PdfDocument) or self.selection_rect is None or self.selection_page < 0:
            return
        try:
            text = self.document.selected_text(self.selection_page, self.selection_rect).strip()
            if not text:
                return
            clipboard = self.get_clipboard()
            clipboard.set(text)
        except Exception as exc:
            self._show_error("Kopieren fehlgeschlagen", str(exc))

    def _set_zoom(self, zoom: float) -> None:
        self.zoom = max(0.2, min(4.0, zoom))
        for page in self.page_views:
            page.refresh_size()
        self._update_title_status()

    def _action_fit_view(self, action, parameter) -> None:
        if not isinstance(self.document, StlDocument):
            return
        self.document.fit_view()
        self._redraw_3d()

    def _set_3d_view(self, name: str) -> None:
        if not isinstance(self.document, StlDocument):
            return
        try:
            self.document.set_view(name)
        except Exception as exc:
            self._show_error("3D-Ansicht fehlgeschlagen", str(exc))
            return
        self._redraw_3d()

    def _action_view_iso(self, action, parameter) -> None:
        self._set_3d_view("iso")

    def _action_view_front(self, action, parameter) -> None:
        self._set_3d_view("front")

    def _action_view_back(self, action, parameter) -> None:
        self._set_3d_view("back")

    def _action_view_left(self, action, parameter) -> None:
        self._set_3d_view("left")

    def _action_view_right(self, action, parameter) -> None:
        self._set_3d_view("right")

    def _action_view_top(self, action, parameter) -> None:
        self._set_3d_view("top")

    def _action_view_bottom(self, action, parameter) -> None:
        self._set_3d_view("bottom")

    def _action_projection_toggle(self, action, parameter) -> None:
        if not isinstance(self.document, StlDocument):
            return
        self.document.toggle_projection()
        self._redraw_3d()

    def _action_wireframe_toggle(self, action, parameter) -> None:
        if not isinstance(self.document, StlDocument):
            return
        self.document.toggle_wireframe()
        self._redraw_3d()

    def _action_grid_toggle(self, action, parameter) -> None:
        if not isinstance(self.document, StlDocument):
            return
        self.document.toggle_grid()
        self._redraw_3d()

    def _action_zoom_in(self, action, parameter) -> None:
        if isinstance(self.document, StlDocument):
            self.document.zoom_model(1.15)
            self.page_views[0].queue_draw()
            self._update_title_status()
            return
        self._set_zoom(self.zoom * 1.15)

    def _action_zoom_out(self, action, parameter) -> None:
        if isinstance(self.document, StlDocument):
            self.document.zoom_model(1.0 / 1.15)
            self.page_views[0].queue_draw()
            self._update_title_status()
            return
        self._set_zoom(self.zoom / 1.15)

    def _action_actual_size(self, action, parameter) -> None:
        if isinstance(self.document, StlDocument):
            self.document.reset_view()
            self.page_views[0].queue_draw()
            self._update_title_status()
            return
        self._set_zoom(1.0)

    def _edit_and_reload(self, callback) -> None:
        try:
            callback()
            self._refresh_after_edit()
        except Exception as exc:
            self._show_error("Bearbeitung fehlgeschlagen", str(exc))

    def _action_rotate_left(self, action, parameter) -> None:
        self._edit_and_reload(lambda: self.document.rotate(self.current_page, -90))

    def _action_rotate_right(self, action, parameter) -> None:
        self._edit_and_reload(lambda: self.document.rotate(self.current_page, 90))

    def _action_delete_page(self, action, parameter) -> None:
        if not isinstance(self.document, PdfDocument):
            return
        index = self.current_page
        self._edit_and_reload(lambda: self.document.delete_page(index))

    def _action_duplicate_page(self, action, parameter) -> None:
        if not isinstance(self.document, PdfDocument):
            return
        index = self.current_page
        def apply() -> None:
            self.document.duplicate_page(index)
            self.current_page = index + 1
        self._edit_and_reload(apply)

    def _action_move_up(self, action, parameter) -> None:
        if not isinstance(self.document, PdfDocument) or self.current_page <= 0:
            return
        index = self.current_page
        def apply() -> None:
            self.current_page = self.document.move_page(index, index - 1)
        self._edit_and_reload(apply)

    def _action_move_down(self, action, parameter) -> None:
        if not isinstance(self.document, PdfDocument) or self.current_page >= self.document.page_count - 1:
            return
        index = self.current_page
        def apply() -> None:
            self.current_page = self.document.move_page(index, index + 1)
        self._edit_and_reload(apply)

    def _action_append_pdf(self, action, parameter) -> None:
        if not isinstance(self.document, PdfDocument):
            return
        self._open_file_dialog(self._append_pdf_target, "PDF anhängen")

    def _append_pdf_target(self, path: str) -> None:
        if Path(path).suffix.lower() != ".pdf":
            self._show_error("PDF erforderlich", "Zum Anhängen muss eine PDF-Datei gewählt werden.")
            return
        self._edit_and_reload(lambda: self.document.append_pdf(path))

    def _action_crop_mode(self, action, parameter) -> None:
        self.mode = "crop" if self.mode != "crop" else "auswahl"
        self.apply_crop_button.set_visible(self.mode == "crop" and self.crop_rect is not None)
        self.crop_button.set_tooltip_text("Zuschneidemodus beenden" if self.mode == "crop" else "Zuschneiden")
        self._update_page_cursors()

    def _action_apply_crop(self, action, parameter) -> None:
        if self.crop_rect is None or self.crop_page < 0:
            return
        page_index = self.crop_page
        rect = self.crop_rect
        def apply() -> None:
            self.document.crop(page_index, rect)
            self.current_page = page_index
            self.mode = "auswahl"
            self.apply_crop_button.set_visible(False)
            self.crop_button.set_tooltip_text("Zuschneiden")
        self._edit_and_reload(apply)

    def _action_undo(self, action, parameter) -> None:
        if not isinstance(self.document, (PdfDocument, ImageDocument)):
            return
        try:
            self.document.undo()
            self._refresh_after_edit()
        except Exception as exc:
            self._show_error("Rückgängig fehlgeschlagen", str(exc))

    def _action_redo(self, action, parameter) -> None:
        if not isinstance(self.document, (PdfDocument, ImageDocument)):
            return
        try:
            self.document.redo()
            self._refresh_after_edit()
        except Exception as exc:
            self._show_error("Wiederholen fehlgeschlagen", str(exc))

    def _action_flip_horizontal(self, action, parameter) -> None:
        if not isinstance(self.document, ImageDocument):
            return
        self._edit_and_reload(self.document.flip_horizontal)

    def _action_flip_vertical(self, action, parameter) -> None:
        if not isinstance(self.document, ImageDocument):
            return
        self._edit_and_reload(self.document.flip_vertical)

    def _action_pdf_optimize(self, action, parameter) -> None:
        if not isinstance(self.document, PdfDocument):
            return
        suggested = f"{Path(self.document.path).stem}-optimiert.pdf"
        self._save_file_dialog(self._pdf_optimize_target, suggested)

    def _pdf_optimize_target(self, target: str) -> None:
        try:
            self.document.optimize_copy(target)
            self._show_info("PDF optimiert", f"Die optimierte Kopie wurde gespeichert:\n{target}")
        except Exception as exc:
            self._show_error("PDF-Optimierung fehlgeschlagen", str(exc))

    def _action_pdf_compress(self, action, parameter) -> None:
        if not isinstance(self.document, PdfDocument):
            return
        dialog = Gtk.AlertDialog()
        dialog.set_message("PDF verkleinern")
        dialog.set_detail("Wähle die Zielqualität. Es wird eine neue visuelle PDF-Kopie erzeugt; Formular- und Anmerkungsstrukturen können dabei vereinfacht werden.")
        dialog.set_buttons(["Abbrechen", "Klein", "Mittel", "Druck"])
        dialog.set_cancel_button(0)
        dialog.set_default_button(2)
        dialog.choose(self, None, self._finish_compress_choice)

    def _finish_compress_choice(self, dialog: Gtk.AlertDialog, result) -> None:
        try:
            choice = dialog.choose_finish(result)
        except GLib.Error:
            return
        profiles = {1: "screen", 2: "ebook", 3: "printer"}
        profile = profiles.get(choice)
        if profile is None:
            return
        self._pending_compress_profile = profile
        suggested = f"{Path(self.document.path).stem}-kleiner.pdf"
        self._save_file_dialog(self._pdf_compress_target, suggested)

    def _pdf_compress_target(self, target: str) -> None:
        try:
            self.document.compress_copy(target, getattr(self, "_pending_compress_profile", "ebook"))
            self._show_info("PDF gespeichert", f"Die verkleinerte Kopie wurde gespeichert:\n{target}")
        except Exception as exc:
            self._show_error("PDF konnte nicht verkleinert werden", str(exc))

    def _action_pdf_protect(self, action, parameter) -> None:
        if not isinstance(self.document, PdfDocument):
            return
        dialog = Gtk.Window(transient_for=self, modal=True)
        dialog.set_title("PDF schützen")
        dialog.set_default_size(420, 180)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(18)
        box.set_margin_bottom(18)
        box.set_margin_start(18)
        box.set_margin_end(18)
        box.append(Gtk.Label(label="Passwort für die geschützte PDF-Kopie:"))
        entry = Gtk.PasswordEntry()
        entry.set_show_peek_icon(True)
        box.append(entry)
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        cancel = Gtk.Button(label="Abbrechen")
        save = Gtk.Button(label="Weiter")
        save.add_css_class("suggested-action")
        cancel.connect("clicked", lambda _b: dialog.close())
        save.connect("clicked", lambda _b: self._protect_password_entered(dialog, entry.get_text()))
        buttons.append(cancel)
        buttons.append(save)
        box.append(buttons)
        dialog.set_child(box)
        dialog.present()

    def _protect_password_entered(self, dialog: Gtk.Window, password: str) -> None:
        if not password:
            self._show_error("Passwort fehlt", "Das Passwort darf nicht leer sein.")
            return
        dialog.close()
        self._pending_pdf_password = password
        suggested = f"{Path(self.document.path).stem}-geschuetzt.pdf"
        self._save_file_dialog(self._pdf_protect_target, suggested)

    def _pdf_protect_target(self, target: str) -> None:
        try:
            self.document.protect_copy(target, getattr(self, "_pending_pdf_password", ""))
            self._show_info("PDF geschützt", f"Die geschützte Kopie wurde gespeichert:\n{target}")
        except Exception as exc:
            self._show_error("PDF konnte nicht geschützt werden", str(exc))
        finally:
            self._pending_pdf_password = ""

    def _action_print(self, action, parameter) -> None:
        operation = Gtk.PrintOperation()
        operation.set_n_pages(self.document.page_count)
        operation.set_job_name(self.document.title)
        operation.connect("draw-page", self._draw_print_page)
        try:
            operation.run(Gtk.PrintOperationAction.PRINT_DIALOG, self)
        except GLib.Error as exc:
            self._show_error("Drucken fehlgeschlagen", exc.message)

    def _draw_print_page(self, operation: Gtk.PrintOperation, context: Gtk.PrintContext, page_number: int) -> None:
        cr = context.get_cairo_context()
        self.document.print_page(page_number, cr, context.get_width(), context.get_height())

    def _on_close_request(self, window) -> bool:
        self._cancel_animation()
        self._cancel_thumbnail_loading()
        if self._force_close:
            return False
        if not self.document.dirty:
            self.document.close()
            return False
        dialog = Gtk.AlertDialog()
        dialog.set_modal(True)
        dialog.set_message("Ungespeicherte Änderungen")
        dialog.set_detail("Die Datei wurde geändert. Vor dem Schließen speichern?")
        dialog.set_buttons(["Abbrechen", "Verwerfen", "Speichern"])
        dialog.set_cancel_button(0)
        dialog.set_default_button(2)
        dialog.choose(self, None, self._on_close_choice)
        return True

    def _on_close_choice(self, dialog: Gtk.AlertDialog, result) -> None:
        try:
            choice = dialog.choose_finish(result)
        except GLib.Error:
            return
        if choice == 0:
            return
        if choice == 2:
            try:
                self.document.save()
            except Exception as exc:
                self._show_error("Speichern fehlgeschlagen", str(exc))
                return
        self.document.close()
        self._force_close = True
        self.close()


class EmptyWindow(Gtk.ApplicationWindow):
    def __init__(self, app: "LiViewApplication"):
        super().__init__(application=app)
        self.app = app
        self.set_title("LiView")
        self.set_default_size(860, 600)
        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        title = Gtk.Label(label="LiView")
        title.add_css_class("title")
        header.set_title_widget(title)
        self.set_titlebar(header)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        icon = Gtk.Image.new_from_icon_name("de.limad.LiView")
        icon.set_pixel_size(96)
        box.append(icon)
        heading = Gtk.Label(label="PDF, Bild, Video oder 3D-Modell öffnen")
        heading.add_css_class("title-1")
        box.append(heading)
        formats = Gtk.Label(label="PDF · Bilder · Videos · STL · OBJ · 3MF")
        formats.add_css_class("dim-label")
        box.append(formats)
        button = Gtk.Button(label="Datei öffnen")
        button.add_css_class("suggested-action")
        button.connect("clicked", self._open)
        box.append(button)
        self.set_child(box)
        target = Gtk.DropTarget.new(type=GObject.TYPE_NONE, actions=Gdk.DragAction.COPY)
        target.set_gtypes([Gdk.FileList])
        target.connect("drop", self._drop_files)
        self.add_controller(target)
        self.present()

    def _drop_files(self, target, value, x, y) -> bool:
        if not isinstance(value, Gdk.FileList):
            return False
        opened = False
        for file in value.get_files():
            path = file.get_path()
            if path:
                self.app.open_path(path)
                opened = True
        if opened:
            self.close()
        return opened

    def _open(self, button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Datei öffnen")
        dialog.open(self, None, self._finished)

    def _finished(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            file = dialog.open_finish(result)
        except GLib.Error:
            return
        if file is not None:
            self.app.open_path(file.get_path())
            self.close()


class LiViewApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.empty_window: EmptyWindow | None = None
        self.connect("startup", self._on_startup)

    def _on_startup(self, app) -> None:
        css_path = "/usr/share/liview/liview/style.css"
        if not os.path.exists(css_path):
            css_path = str(Path(__file__).with_name("style.css"))
        provider = Gtk.CssProvider()
        provider.load_from_path(css_path)
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.set_accels_for_action("win.open", ["<Primary>o"])
        self.set_accels_for_action("win.save", ["<Primary>s"])
        self.set_accels_for_action("win.save_as", ["<Primary><Shift>s"])
        self.set_accels_for_action("win.print", ["<Primary>p"])
        self.set_accels_for_action("win.find", ["<Primary>f"])
        self.set_accels_for_action("win.copy", ["<Primary>c"])
        self.set_accels_for_action("win.undo", ["<Primary>z"])
        self.set_accels_for_action("win.redo", ["<Primary><Shift>z", "<Primary>y"])
        self.set_accels_for_action("win.zoom_in", ["<Primary>plus", "<Primary>equal"])
        self.set_accels_for_action("win.zoom_out", ["<Primary>minus"])
        self.set_accels_for_action("win.actual_size", ["<Primary>0"])

    def do_activate(self) -> None:
        active = self.get_active_window()
        if active is not None:
            active.present()
            return
        self.empty_window = EmptyWindow(self)

    def do_open(self, files, n_files: int, hint: str) -> None:
        opened = False
        for file in files:
            path = file.get_path()
            if path:
                self.open_path(path)
                opened = True
        if not opened:
            self.do_activate()

    def open_path(self, path: str, password: str = "") -> None:
        try:
            document = open_document(path, password=password)
        except PdfPasswordRequired:
            self._request_pdf_password(path)
            return
        except Exception as exc:
            parent = self.get_active_window()
            dialog = Gtk.AlertDialog()
            dialog.set_message("Datei konnte nicht geöffnet werden")
            dialog.set_detail(str(exc))
            dialog.show(parent)
            return
        DocumentWindow(self, document)

    def _request_pdf_password(self, path: str) -> None:
        parent = self.get_active_window()
        dialog = Gtk.Window(transient_for=parent, modal=True)
        dialog.set_title("PDF-Passwort")
        dialog.set_default_size(420, 175)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(18)
        box.set_margin_bottom(18)
        box.set_margin_start(18)
        box.set_margin_end(18)
        box.append(Gtk.Label(label=f"Passwort für {Path(path).name}:"))
        entry = Gtk.PasswordEntry()
        entry.set_show_peek_icon(True)
        box.append(entry)
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        cancel = Gtk.Button(label="Abbrechen")
        open_button = Gtk.Button(label="Öffnen")
        open_button.add_css_class("suggested-action")
        cancel.connect("clicked", lambda _b: dialog.close())
        open_button.connect("clicked", lambda _b: self._retry_pdf_password(dialog, path, entry.get_text()))
        entry.connect("activate", lambda _e: self._retry_pdf_password(dialog, path, entry.get_text()))
        buttons.append(cancel)
        buttons.append(open_button)
        box.append(buttons)
        dialog.set_child(box)
        dialog.present()

    def _retry_pdf_password(self, dialog: Gtk.Window, path: str, password: str) -> None:
        if not password:
            return
        try:
            document = open_document(path, password=password)
        except PdfPasswordRequired:
            self._show_error_on_parent(dialog, "Falsches Passwort", "Das PDF konnte mit diesem Passwort nicht geöffnet werden.")
            return
        except Exception as exc:
            self._show_error_on_parent(dialog, "Datei konnte nicht geöffnet werden", str(exc))
            return
        dialog.close()
        DocumentWindow(self, document)

    @staticmethod
    def _show_error_on_parent(parent: Gtk.Window, title: str, message: str) -> None:
        alert = Gtk.AlertDialog()
        alert.set_message(title)
        alert.set_detail(message)
        alert.show(parent)



def main() -> int:
    app = LiViewApplication()
    return app.run(sys.argv)
