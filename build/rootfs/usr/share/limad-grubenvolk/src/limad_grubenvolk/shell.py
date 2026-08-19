from __future__ import annotations
import os
import sys
from datetime import datetime
from pathlib import Path
from . import APP_ID, APP_NAME, VERSION


def _root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _state_dir() -> Path:
    root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "limad-grubenvolk"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _log(message: str) -> None:
    line = f"{datetime.now().isoformat(timespec='seconds')} {message}\n"
    try:
        with (_state_dir() / "startup.log").open("a", encoding="utf-8") as handle:
            handle.write(line)
    except OSError:
        pass
    print(line, end="", file=sys.stderr)


def _load_native_runtime():
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("WebKit", "6.0")
    from gi.repository import Gio, GLib, Gtk, WebKit
    return Gio, GLib, Gtk, WebKit


def launch() -> int:
    Gio, GLib, Gtk, WebKit = _load_native_runtime()
    game_file = _root_dir() / "web" / "index.html"
    if not game_file.is_file():
        _log(f"Spieloberfläche fehlt: {game_file}")
        return 1
    game_uri = game_file.as_uri()

    class Application(Gtk.Application):
        def __init__(self):
            super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
            self.window = None
            self.view = None

        def do_activate(self):
            if self.window:
                self.window.present()
                return
            self.window = Gtk.ApplicationWindow(application=self)
            self.window.set_title(APP_NAME)
            self.window.set_default_size(1460, 920)
            self.window.set_size_request(980, 650)
            self._show_loading()
            self.window.present()
            GLib.idle_add(self._create_webview)

        def _show_loading(self):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
            box.set_halign(Gtk.Align.CENTER)
            box.set_valign(Gtk.Align.CENTER)
            spinner = Gtk.Spinner()
            spinner.start()
            label = Gtk.Label(label="GRUBENVOLK wird gestartet …")
            label.add_css_class("title-2")
            box.append(spinner)
            box.append(label)
            self.window.set_child(box)

        def _show_error(self, detail: str):
            _log(detail)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
            box.set_margin_top(36)
            box.set_margin_bottom(36)
            box.set_margin_start(36)
            box.set_margin_end(36)
            title = Gtk.Label(label="GRUBENVOLK konnte nicht gestartet werden")
            title.add_css_class("title-1")
            title.set_wrap(True)
            message = Gtk.Label(label=f"{detail}\n\nProtokoll: {_state_dir() / 'startup.log'}")
            message.set_wrap(True)
            message.set_selectable(True)
            retry = Gtk.Button(label="Erneut versuchen")
            retry.connect("clicked", lambda *_: self._reload())
            box.append(title)
            box.append(message)
            box.append(retry)
            self.window.set_child(box)

        def _create_webview(self):
            settings = WebKit.Settings()
            settings.set_enable_developer_extras(os.environ.get("LIMAD_GRUBENVOLK_DEVTOOLS") == "1")
            settings.set_enable_smooth_scrolling(True)
            for method_name in ("set_enable_javascript", "set_enable_html5_local_storage"):
                try:
                    getattr(settings, method_name)(True)
                except (AttributeError, TypeError):
                    pass
            try:
                settings.set_user_agent_with_application_details(APP_NAME, VERSION)
            except (AttributeError, TypeError):
                pass
            self.view = WebKit.WebView(settings=settings)
            self.view.set_hexpand(True)
            self.view.set_vexpand(True)
            self.view.connect("load-changed", self._load_changed)
            self.view.connect("load-failed", self._load_failed)
            try:
                self.view.connect("web-process-terminated", self._web_process_terminated)
            except TypeError:
                pass
            self.window.set_child(self.view)
            self.view.load_uri(game_uri)
            return False

        def _load_changed(self, view, event):
            if event == WebKit.LoadEvent.FINISHED:
                _log(f"Spiel geladen: {view.get_uri()}")
                view.grab_focus()

        def _load_failed(self, view, event, failing_uri, error):
            detail = f"Ladefehler bei {failing_uri}: {error.message if error else 'unbekannter Fehler'}"
            self._show_error(detail)
            return True

        def _web_process_terminated(self, view, reason):
            self._show_error(f"Der native WebKit-Prozess wurde beendet: {reason}")

        def _reload(self):
            if self.view:
                self.view.load_uri(game_uri)
                self.window.set_child(self.view)
            else:
                self._show_loading()
                GLib.idle_add(self._create_webview)

    app = Application()
    return app.run(sys.argv)
