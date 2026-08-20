#!/usr/bin/python3
from __future__ import annotations

import ast
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "build/rootfs/usr/share/liview/liview/app.py"
STL = ROOT / "build/rootfs/usr/share/liview/liview/stl.py"

app_text = APP.read_text(encoding="utf-8")
stl_text = STL.read_text(encoding="utf-8")

for needle in (
    "PDF_INITIAL_PAGE_BATCH = 6",
    "PDF_SCROLL_PAGE_BATCH = 6",
    "PDF_THUMBNAIL_RADIUS = 4",
    "MODEL_REFINE_DELAY_MS = 280",
    "initial_page_count = min(self.document.page_count, PDF_INITIAL_PAGE_BATCH)",
    "self._ensure_pdf_pages_loaded(len(self.page_views) + PDF_SCROLL_PAGE_BATCH)",
    "self.document.render_thumbnail(index, 112, 150)",
    "placeholder = Gtk.Label(label=\"…\")",
    "self._ensure_pdf_pages_loaded(self.current_page + 1)",
    "self._ensure_pdf_pages_loaded(page_index + 1)",
    "self.document.set_preview_draft(True)",
    "GLib.timeout_add(MODEL_REFINE_DELAY_MS, self._finish_3d_refine)",
):
    if needle not in app_text:
        raise AssertionError(f"LiView V26 lazy/draft marker missing: {needle}")

if "Gtk.Spinner()" in app_text[app_text.index("def _append_thumbnail_row"):app_text.index("def _ensure_pdf_pages_loaded")]:
    raise AssertionError("LiView PDF thumbnail rows still create active spinners")

for needle in (
    "self.preview_draft = True",
    "MODEL_PREVIEW_TRIANGLE_LIMIT = 40000",
    "MODEL_DRAFT_FACE_LIMIT = 8000",
    "MODEL_STANDARD_FACE_LIMIT = 24000",
    "self.triangles = self._limit_preview_triangles(self.triangles, MODEL_PREVIEW_TRIANGLE_LIMIT)",
    "preview_limit = MODEL_PREVIEW_TRIANGLE_LIMIT",
    "step = max(1, math.ceil(count / preview_limit))",
    "self._source_triangle_count = parsed",
    "max_faces = MODEL_DRAFT_FACE_LIMIT if self.preview_draft else MODEL_STANDARD_FACE_LIMIT",
):
    if needle not in stl_text:
        raise AssertionError(f"LiView V26 mesh-preview marker missing: {needle}")


render_start = stl_text.index("    def render_page")
render_end = stl_text.index("    def save", render_start)
render_block = stl_text[render_start:render_end]
if "cr.fill_preserve()" in render_block:
    raise AssertionError("LiView 3D normal preview still draws per-face outline strokes")
if "cr.fill()" not in render_block:
    raise AssertionError("LiView 3D normal preview does not fill object faces")

module = ast.parse(stl_text, filename=str(STL))
class_node = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "StlDocument")
function_node = next(node for node in class_node.body if isinstance(node, ast.FunctionDef) and node.name == "_limit_preview_triangles")
standalone = ast.Module(body=[function_node], type_ignores=[])
ast.fix_missing_locations(standalone)
namespace = {"math": math}
exec(compile(standalone, str(STL), "exec"), namespace)
limit_preview_triangles = namespace["_limit_preview_triangles"]

small = list(range(10))
if limit_preview_triangles(small, 20) is not small:
    raise AssertionError("small mesh preview must remain unchanged")
large = list(range(250000))
limited = limit_preview_triangles(large, 40000)
if not 0 < len(limited) <= 40000:
    raise AssertionError(f"large mesh preview was not bounded: {len(limited)}")
if limited[0] != 0:
    raise AssertionError("mesh preview sampling lost the first triangle")

print("V26 LIVIEW PERFORMANCE TEST: PASS")
