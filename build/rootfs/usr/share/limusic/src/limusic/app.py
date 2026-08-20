import logging
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gst", "1.0")
gi.require_version("WebKit", "6.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango

from . import __version__
from .library import LibraryStore, MediaItem
from .paths import APP_ID, APP_NAME, LOG_FILE
from .player import LocalPlayer
from .youtube import YouTubeMusicView


def format_time(seconds):
    seconds = max(0, int(seconds or 0))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def icon_button(icon_name, tooltip, css_class="icon-button"):
    button = Gtk.Button.new_from_icon_name(icon_name)
    button.set_tooltip_text(tooltip)
    button.add_css_class(css_class)
    return button


class DetachedPlayerWindow(Gtk.ApplicationWindow):
    def __init__(self, owner):
        super().__init__(application=owner.get_application(), title="LiMusic Player")
        self.owner = owner
        self.mode = None
        self.pinned = False
        self.fullscreen_active = False
        self._controls_hide_source = None
        self.set_default_size(680, 420)
        self.set_size_request(420, 260)
        self.set_resizable(True)
        self.connect("close-request", self._on_close_request)
        self.connect("map", self._on_player_mapped)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.add_css_class("detached-root")
        self.set_child(root)

        self.home_button = icon_button("go-home-symbolic", "LiMusic öffnen")
        self.home_button.connect(
            "clicked",
            lambda _button: self.owner.open_main_from_detached(go_home=True),
        )

        self.pin_button = None
        self.pin_state_label = None
        self.pin_gesture = None

        self.overlay = Gtk.Overlay()
        self.overlay.set_hexpand(True)
        self.overlay.set_vexpand(True)
        root.append(self.overlay)

        self.media_host = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.media_host.set_hexpand(True)
        self.media_host.set_vexpand(True)
        self.media_host.add_css_class("detached-media")
        self.overlay.set_child(self.media_host)

        self.detached_top_tools = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=4,
        )
        self.detached_top_tools.add_css_class("detached-top-tools")
        self.detached_top_tools.set_halign(Gtk.Align.END)
        self.detached_top_tools.set_valign(Gtk.Align.START)
        self.detached_top_tools.set_margin_top(4)
        self.detached_top_tools.set_margin_end(4)
        self.detached_top_tools.append(self.home_button)
        self.overlay.add_overlay(self.detached_top_tools)

        self.local_picture = Gtk.Picture()
        self.local_picture.set_hexpand(True)
        self.local_picture.set_vexpand(True)
        self.local_picture.set_can_shrink(True)

        self.controls_revealer = Gtk.Revealer()
        self.controls_revealer.set_transition_type(Gtk.RevealerTransitionType.CROSSFADE)
        self.controls_revealer.set_transition_duration(180)
        self.controls_revealer.set_halign(Gtk.Align.FILL)
        self.controls_revealer.set_valign(Gtk.Align.END)

        controls_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        controls_panel.add_css_class("detached-controls-overlay")
        controls_panel.set_margin_start(10)
        controls_panel.set_margin_end(10)
        controls_panel.set_margin_bottom(10)

        timeline_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.title_label = Gtk.Label(label="Bereit")
        self.title_label.set_xalign(0)
        self.title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.title_label.set_size_request(150, -1)
        self.title_label.add_css_class("detached-track-title")
        timeline_row.append(self.title_label)
        self.elapsed_label = Gtk.Label(label="0:00")
        self.elapsed_label.add_css_class("detached-time")
        timeline_row.append(self.elapsed_label)
        self.time_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.time_scale.set_draw_value(False)
        self.time_scale.set_hexpand(True)
        self.time_scale.add_css_class("detached-scale")
        self.time_scale.connect("change-value", self._on_seek)
        timeline_row.append(self.time_scale)
        self.duration_label = Gtk.Label(label="0:00")
        self.duration_label.add_css_class("detached-time")
        timeline_row.append(self.duration_label)
        controls_panel.append(timeline_row)

        control_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        control_row.set_halign(Gtk.Align.FILL)

        left_spacer = Gtk.Box()
        left_spacer.set_hexpand(True)
        control_row.append(left_spacer)

        previous = icon_button("media-skip-backward-symbolic", "Vorheriger Titel", "detached-control")
        rewind = icon_button("media-seek-backward-symbolic", "10 Sekunden zurück", "detached-control")
        self.play_button = icon_button("media-playback-start-symbolic", "Wiedergabe/Pause", "detached-control-main")
        forward = icon_button("media-seek-forward-symbolic", "10 Sekunden vor", "detached-control")
        next_button = icon_button("media-skip-forward-symbolic", "Nächster Titel", "detached-control")
        fullscreen = icon_button("view-fullscreen-symbolic", "Vollbild", "detached-control")
        previous.connect("clicked", lambda _button: self.owner.previous_track(self.mode))
        rewind.connect("clicked", lambda _button: self.owner.seek_relative(-10, self.mode))
        self.play_button.connect("clicked", lambda _button: self.owner.play_pause(self.mode))
        forward.connect("clicked", lambda _button: self.owner.seek_relative(10, self.mode))
        next_button.connect("clicked", lambda _button: self.owner.next_track(self.mode))
        fullscreen.connect("clicked", self._toggle_fullscreen)
        for widget in (previous, rewind, self.play_button, forward, next_button, fullscreen):
            control_row.append(widget)

        right_spacer = Gtk.Box()
        right_spacer.set_hexpand(True)
        control_row.append(right_spacer)

        volume_icon = Gtk.Image.new_from_icon_name("audio-volume-high-symbolic")
        volume_icon.add_css_class("detached-volume-icon")
        control_row.append(volume_icon)
        self.volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 0.01)
        self.volume.set_value(0.8)
        self.volume.set_draw_value(False)
        self.volume.set_size_request(110, -1)
        self.volume.add_css_class("detached-volume")
        self.volume.connect("value-changed", lambda scale: self.owner.set_volume(scale.get_value(), self.mode))
        control_row.append(self.volume)
        controls_panel.append(control_row)

        self.controls_revealer.set_child(controls_panel)
        self.overlay.add_overlay(self.controls_revealer)

        motion = Gtk.EventControllerMotion()
        motion.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        motion.connect("enter", self._on_pointer_enter)
        motion.connect("motion", self._on_pointer_motion)
        motion.connect("leave", self._on_pointer_leave)
        self.overlay.add_controller(motion)

    def show_local(self):
        self._clear_media_host()
        self.mode = "local"
        self.owner.local_player.set_picture(self.local_picture)
        self.media_host.append(self.local_picture)
        self.title_label.set_text(self.owner.now_title.get_text() or "Lokale Wiedergabe")
        self.present()
        self._show_controls()

    def show_youtube(self, mode="youtube"):
        self._clear_media_host()
        self.mode = mode
        self.owner.move_youtube_to(self.media_host, mode)
        self.title_label.set_text(
            self.owner.now_title.get_text()
            or self.owner._web_label_for_mode(mode)
        )
        self.present()
        self._show_controls()

    def restore_youtube(self):
        if self.mode in ("youtube", "youtube_video"):
            mode = self.mode
            self.owner.restore_youtube(mode)
            self.mode = None

    def set_play_state(self, playing):
        image = Gtk.Image.new_from_icon_name("media-playback-pause-symbolic" if playing else "media-playback-start-symbolic")
        self.play_button.set_child(image)

    def set_position(self, position, duration):
        if duration <= 0:
            self.elapsed_label.set_text(format_time(position))
            self.duration_label.set_text("0:00")
            return
        self.time_scale.set_range(0, max(1, duration))
        if not self.time_scale.has_focus():
            self.time_scale.set_value(position)
        self.elapsed_label.set_text(format_time(position))
        self.duration_label.set_text(format_time(duration))

    def _clear_media_host(self):
        child = self.media_host.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.media_host.remove(child)
            child = next_child

    def _on_seek(self, _scale, _scroll, value):
        if self.mode in ("local", "youtube"):
            self.owner.seek_absolute(value, self.mode)
        return False

    def _toggle_fullscreen(self, _button):
        if self.fullscreen_active:
            self.unfullscreen()
            self.fullscreen_active = False
        else:
            self.fullscreen()
            self.fullscreen_active = True
        self._show_controls()

    def _open_pin_window_menu(self, gesture, _n_press, _x, _y):
        surface = self.get_surface()
        event = gesture.get_current_event()
        if surface is None or event is None or not hasattr(surface, "show_window_menu"):
            self.owner._set_status("Fenstermenü konnte nicht geöffnet werden")
            return

        # Important: no transient parent is set here. The detached player remains
        # completely independent from the minimized/hidden LiMusic main window.
        surface.show_window_menu(event)

    def _sync_pin_state(self, surface=None, _pspec=None):
        surface = surface or self.get_surface()
        if surface is None or not hasattr(surface, "get_state"):
            return

        state = surface.get_state()
        self.pinned = bool(state & Gdk.ToplevelState.ABOVE)

        if self.pin_button is None or self.pin_state_label is None:
            return

        if self.pinned:
            self.pin_state_label.set_text("AN")
            self.pin_state_label.add_css_class("active")
            self.pin_button.add_css_class("pinned")
            self.pin_button.set_tooltip_text("Pin AN · Player bleibt im Vordergrund")
        else:
            self.pin_state_label.set_text("AUS")
            self.pin_state_label.remove_css_class("active")
            self.pin_button.remove_css_class("pinned")
            self.pin_button.set_tooltip_text("Pin AUS · Fensteroptionen öffnen")

    def _on_player_mapped(self, _widget):
        surface = self.get_surface()
        if surface is None or surface is getattr(self, "_pin_surface", None):
            self._sync_pin_state(surface)
            return

        self._pin_surface = surface
        if hasattr(surface, "connect"):
            surface.connect("notify::state", self._sync_pin_state)
        self._sync_pin_state(surface)

    def _on_pointer_enter(self, _controller, _x, _y):
        self._show_controls()

    def _on_pointer_motion(self, _controller, _x, _y):
        self._show_controls()

    def _on_pointer_leave(self, _controller):
        self._schedule_controls_hide(250)

    def _show_controls(self):
        self.controls_revealer.set_reveal_child(True)
        self._schedule_controls_hide(1800)

    def _schedule_controls_hide(self, delay_ms):
        if self._controls_hide_source is not None:
            GLib.source_remove(self._controls_hide_source)
            self._controls_hide_source = None
        self._controls_hide_source = GLib.timeout_add(delay_ms, self._hide_controls)

    def _hide_controls(self):
        self._controls_hide_source = None
        self.controls_revealer.set_reveal_child(False)
        return GLib.SOURCE_REMOVE

    def _on_close_request(self, _window):
        self.owner.open_main_from_detached(go_home=False)
        self.hide()
        return True


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title=f"{APP_NAME} {__version__}")
        self.set_default_size(1460, 900)
        self.set_size_request(980, 680)
        self.connect("close-request", self._on_main_close_request)

        self.library = LibraryStore()
        self.local_player = LocalPlayer()
        self.youtube = YouTubeMusicView(site="music")
        self.youtube_video = YouTubeMusicView(
            site="youtube",
            session=self.youtube.session,
        )
        self.current_mode = "local"
        self.current_queue_index = -1
        self.queue = list(self.library.items)
        self._updating_seek = False
        self.detached = DetachedPlayerWindow(self)

        self.local_player.connect("state-changed", self._on_local_state)
        self.local_player.connect("track-changed", self._on_local_track)
        self.local_player.connect("position-changed", self._on_local_position)
        self.local_player.connect("error", self._on_local_error)
        self.local_player.connect("eos", lambda _player: self.next_track())
        self.youtube.on_status = self._set_status
        self.youtube.on_title = (
            lambda title: self._on_youtube_title("youtube", title)
        )
        self.youtube.on_player_state = (
            lambda state: self._on_youtube_player_state("youtube", state)
        )

        self.youtube_video.on_status = self._set_status
        self.youtube_video.on_title = (
            lambda title: self._on_youtube_title("youtube_video", title)
        )
        self.youtube_video.on_player_state = (
            lambda state: self._on_youtube_player_state(
                "youtube_video",
                state,
            )
        )

        self._build_ui()
        self._refresh_library()
        self.local_player.set_volume(0.8)
        self._set_status("Bereit")

    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.add_css_class("app-root")
        self.set_child(root)

        content = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        content.add_css_class("main-paned")
        content.set_hexpand(True)
        content.set_vexpand(True)
        content.set_wide_handle(True)
        root.append(content)

        sidebar = self._build_sidebar()
        content.set_start_child(sidebar)
        content.set_resize_start_child(False)
        content.set_shrink_start_child(False)

        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        center.set_hexpand(True)
        center.set_vexpand(True)
        content.set_end_child(center)
        content.set_resize_end_child(True)
        content.set_shrink_end_child(False)

        self.sidebar_paned = content
        self.sidebar_paned.set_position(160)
        self.sidebar_paned.connect("notify::position", self._sidebar_position_changed)

        topbar = self._build_topbar()
        center.append(topbar)

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        body.set_hexpand(True)
        body.set_vexpand(True)
        center.append(body)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(180)
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        self.stack.add_named(self._build_home_page(), "home")
        self.stack.add_named(self._build_library_page(), "library")
        self.stack.add_named(self._build_youtube_page(), "youtube")
        self.stack.add_named(
            self._build_youtube_video_page(),
            "youtube_video",
        )
        body.append(self.stack)

        self.queue_panel = self._build_queue_panel()
        body.append(self.queue_panel)

        player_bar = self._build_player_bar()
        center.append(player_bar)

    def _sidebar_position_changed(self, paned, _pspec):
        position = paned.get_position()
        clamped = max(140, min(position, 184))
        if position != clamped:
            paned.set_position(clamped)

    def _build_sidebar(self):
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sidebar.set_size_request(140, -1)
        sidebar.add_css_class("sidebar")
        sidebar.set_margin_top(12)
        sidebar.set_margin_bottom(12)
        sidebar.set_margin_start(12)
        sidebar.set_margin_end(10)

        section = Gtk.Label(label="MUSIK")
        section.set_xalign(0)
        section.add_css_class("sidebar-section")
        sidebar.append(section)

        entries = [
            ("home", "go-home-symbolic", "Startseite"),
            ("library", "folder-music-symbolic", "Mediathek"),
            ("youtube", "media-playback-start-symbolic", "YouTube Music"),
            ("youtube_video", "video-x-generic-symbolic", "YouTube"),
        ]
        self.nav_buttons = {}
        for name, icon, label in entries:
            button = Gtk.Button()
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row.append(Gtk.Image.new_from_icon_name(icon))
            text = Gtk.Label(label=label)
            text.set_xalign(0)
            text.set_hexpand(True)
            text.set_ellipsize(Pango.EllipsizeMode.END)
            row.append(text)
            button.set_child(row)
            button.add_css_class("nav-button")
            button.connect("clicked", self._navigate, name)
            self.nav_buttons[name] = button
            sidebar.append(button)

        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        sidebar.append(spacer)

        brand_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        brand_card.add_css_class("sidebar-brand-card")
        brand_card.set_halign(Gtk.Align.FILL)
        logo_path = Path(__file__).resolve().parents[2] / "data" / "de.limad.LiMusic-sidebar.png"
        logo = Gtk.Picture.new_for_filename(str(logo_path))
        logo.set_can_shrink(False)
        logo.set_size_request(70, 70)
        logo.set_halign(Gtk.Align.CENTER)
        logo.set_valign(Gtk.Align.CENTER)
        logo.add_css_class("sidebar-logo")
        brand_card.append(logo)
        brand_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        brand_text.set_hexpand(True)
        brand_name = Gtk.Label(label="LiMusic")
        brand_name.set_xalign(0)
        brand_name.add_css_class("sidebar-brand-name")
        brand_text.append(brand_name)
        brand_subtitle = Gtk.Label(label="MUSIC · VIDEO")
        brand_subtitle.set_xalign(0)
        brand_subtitle.add_css_class("sidebar-brand-subtitle")
        brand_text.append(brand_subtitle)
        brand_card.append(brand_text)
        sidebar.append(brand_card)
        self._set_active_nav("home")
        return sidebar

    def _build_topbar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bar.add_css_class("topbar")
        bar.set_margin_top(5)
        bar.set_margin_bottom(6)
        bar.set_margin_start(8)
        bar.set_margin_end(10)

        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("Lokale Songs und Videos suchen …")
        self.search.set_hexpand(True)
        self.search.connect("search-changed", self._search_changed)
        self.search.connect("activate", self._search_activated)
        bar.append(self.search)

        self.search_spacer = Gtk.Box()
        self.search_spacer.set_hexpand(True)
        self.search_spacer.set_visible(False)
        bar.append(self.search_spacer)

        self.topbar_actions = Gtk.Stack()
        self.topbar_actions.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.topbar_actions.set_transition_duration(120)

        local_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        add_files = Gtk.Button(label="Dateien")
        add_files.set_icon_name("document-open-symbolic")
        add_files.add_css_class("primary-action")
        add_files.connect("clicked", self._choose_files)
        local_actions.append(add_files)
        add_folder = Gtk.Button(label="Ordner")
        add_folder.set_icon_name("folder-open-symbolic")
        add_folder.connect("clicked", self._choose_folder)
        local_actions.append(add_folder)
        self.topbar_actions.add_named(local_actions, "local")

        youtube_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        youtube_home = icon_button("go-home-symbolic", "YouTube Music Startseite")
        youtube_home.connect("clicked", lambda _button: self.youtube.home())
        youtube_reload = icon_button("view-refresh-symbolic", "YouTube Music neu laden")
        youtube_reload.connect("clicked", lambda _button: self.youtube.reload())

        self.youtube_adblock = Gtk.ToggleButton(label="AD")
        self.youtube_adblock.add_css_class("adblock-toggle")
        self.youtube_adblock.set_active(True)
        self.youtube_adblock.set_tooltip_text("YouTube-Werbeblocker AN · WebKit + Scriptlet")
        self.youtube_adblock.connect("toggled", self._toggle_youtube_adblock)

        youtube_account = icon_button("avatar-default-symbolic", "YouTube-Konto")
        youtube_account.connect("clicked", lambda _button: self.youtube.open_account())
        youtube_detach = icon_button("window-new-symbolic", "Player lösen")
        youtube_detach.add_css_class("detach-button")
        youtube_detach.connect("clicked", lambda _button: self.detach_player("youtube"))
        for widget in (
            youtube_home,
            youtube_reload,
            self.youtube_adblock,
            youtube_account,
            youtube_detach,
        ):
            youtube_actions.append(widget)
        self.topbar_actions.add_named(youtube_actions, "youtube")

        youtube_video_actions = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        youtube_video_home = icon_button(
            "go-home-symbolic",
            "YouTube Startseite",
        )
        youtube_video_home.connect(
            "clicked",
            lambda _button: self.youtube_video.home(),
        )
        youtube_video_reload = icon_button(
            "view-refresh-symbolic",
            "YouTube neu laden",
        )
        youtube_video_reload.connect(
            "clicked",
            lambda _button: self.youtube_video.reload(),
        )

        self.youtube_video_adblock = Gtk.ToggleButton(label="AD")
        self.youtube_video_adblock.add_css_class("adblock-toggle")
        self.youtube_video_adblock.set_active(True)
        self.youtube_video_adblock.set_tooltip_text(
            "YouTube-Werbeblocker AN · WebKit + Scriptlet"
        )
        self.youtube_video_adblock.connect(
            "toggled",
            self._toggle_youtube_video_adblock,
        )

        youtube_video_account = icon_button(
            "avatar-default-symbolic",
            "YouTube-Konto",
        )
        youtube_video_account.connect(
            "clicked",
            lambda _button: self.youtube_video.open_account(),
        )
        youtube_video_detach = icon_button(
            "window-new-symbolic",
            "Player lösen",
        )
        youtube_video_detach.add_css_class("detach-button")
        youtube_video_detach.connect(
            "clicked",
            lambda _button: self.detach_player("youtube_video"),
        )

        for widget in (
            youtube_video_home,
            youtube_video_reload,
            self.youtube_video_adblock,
            youtube_video_account,
            youtube_video_detach,
        ):
            youtube_video_actions.append(widget)

        self.topbar_actions.add_named(
            youtube_video_actions,
            "youtube_video",
        )

        self.topbar_actions.set_visible_child_name("local")
        bar.append(self.topbar_actions)
        return bar

    def _toggle_youtube_adblock(self, button):
        enabled = button.get_active()
        self.youtube.set_adblock_enabled(enabled)
        button.set_tooltip_text(
            "YouTube-Werbeblocker AN · WebKit + Scriptlet"
            if enabled
            else "YouTube-Werbeblocker AUS"
        )
        self._set_status(
            "YouTube-Werbeblocker aktiviert · Seite wird neu gefiltert"
            if enabled
            else "YouTube-Werbeblocker deaktiviert · Seite wird neu geladen"
        )

    def _toggle_youtube_video_adblock(self, button):
        enabled = button.get_active()
        self.youtube_video.set_adblock_enabled(enabled)
        button.set_tooltip_text(
            "YouTube-Werbeblocker AN · WebKit + Scriptlet"
            if enabled
            else "YouTube-Werbeblocker AUS"
        )
        self._set_status(
            "YouTube-Werbeblocker aktiviert · Seite wird neu gefiltert"
            if enabled
            else "YouTube-Werbeblocker deaktiviert · Seite wird neu geladen"
        )

    def _build_home_page(self):
        page = Gtk.ScrolledWindow()
        page.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        inner.set_margin_top(22)
        inner.set_margin_bottom(26)
        inner.set_margin_start(24)
        inner.set_margin_end(24)
        page.set_child(inner)

        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        hero.add_css_class("hero-card")
        kicker = Gtk.Label(label=f"LiMusic Native Preview {__version__}")
        kicker.set_xalign(0)
        kicker.add_css_class("kicker")
        hero.append(kicker)
        headline = Gtk.Label(label="Deine Musik. Deine Videos. Ein Player.")
        headline.set_xalign(0)
        headline.set_wrap(True)
        headline.add_css_class("hero-title")
        hero.append(headline)
        copy = Gtk.Label(label="YouTube Music mit persistenter Sitzung und lokale Medien über GStreamer – in einer nativen GTK4-App.")
        copy.set_xalign(0)
        copy.set_wrap(True)
        copy.add_css_class("hero-copy")
        hero.append(copy)
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        youtube_button = Gtk.Button(label="YouTube Music öffnen")
        youtube_button.add_css_class("accent-action")
        youtube_button.connect("clicked", self._navigate, "youtube")
        local_button = Gtk.Button(label="Lokale Mediathek")
        local_button.connect("clicked", self._navigate, "library")
        actions.append(youtube_button)
        actions.append(local_button)
        hero.append(actions)
        inner.append(hero)

        cards = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        cards.set_homogeneous(True)
        cards.append(self._feature_card("YouTube Music", "Direkt in LiMusic. Die WebKit-Sitzung bleibt gespeichert.", "media-playback-start-symbolic"))
        cards.append(self._feature_card("GStreamer", "Lokale Musik und Videos mit der nativen Linux-Medienengine.", "audio-x-generic-symbolic"))
        cards.append(self._feature_card("Externer Player", "Player lösen, skalieren, anheften und im Vollbild nutzen.", "window-new-symbolic"))
        inner.append(cards)

        recent_title = Gtk.Label(label="Zuletzt in deiner Mediathek")
        recent_title.set_xalign(0)
        recent_title.add_css_class("section-title")
        inner.append(recent_title)
        self.home_recent = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.home_recent.add_css_class("surface-card")
        inner.append(self.home_recent)
        return page

    def _feature_card(self, title, body, icon_name):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.add_css_class("feature-card")
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_halign(Gtk.Align.START)
        icon.set_pixel_size(30)
        icon.add_css_class("feature-icon")
        card.append(icon)
        title_label = Gtk.Label(label=title)
        title_label.set_xalign(0)
        title_label.add_css_class("feature-title")
        card.append(title_label)
        body_label = Gtk.Label(label=body)
        body_label.set_xalign(0)
        body_label.set_wrap(True)
        body_label.add_css_class("muted")
        card.append(body_label)
        return card

    def _build_library_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        page.set_margin_top(16)
        page.set_margin_bottom(16)
        page.set_margin_start(18)
        page.set_margin_end(18)

        heading = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title = Gtk.Label(label="Lokale Mediathek")
        title.set_xalign(0)
        title.add_css_class("page-title")
        titles.append(title)
        subtitle = Gtk.Label(label="Audio und Video direkt über GStreamer", xalign=0)
        subtitle.add_css_class("muted")
        titles.append(subtitle)
        titles.set_hexpand(True)
        heading.append(titles)
        page.append(heading)

        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        content.set_hexpand(True)
        content.set_vexpand(True)

        media_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        media_card.add_css_class("media-card")
        media_card.set_hexpand(True)
        media_card.set_vexpand(True)
        self.local_picture = Gtk.Picture()
        self.local_picture.set_hexpand(True)
        self.local_picture.set_vexpand(True)
        self.local_picture.set_can_shrink(True)
        self.local_player.set_picture(self.local_picture)
        media_card.append(self.local_picture)
        self.media_hint = Gtk.Label(label="Wähle einen Titel aus der Mediathek")
        self.media_hint.add_css_class("media-hint")
        self.media_hint.set_margin_top(8)
        self.media_hint.set_margin_bottom(12)
        media_card.append(self.media_hint)
        content.append(media_card)

        list_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        list_frame.set_size_request(400, -1)
        list_frame.add_css_class("library-panel")
        list_header = Gtk.Label(label="Titel")
        list_header.set_xalign(0)
        list_header.add_css_class("panel-title")
        list_frame.append(list_header)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        self.library_list = Gtk.ListBox()
        self.library_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.library_list.add_css_class("media-list")
        self.library_list.connect("row-activated", self._activate_library_row)
        scroll.set_child(self.library_list)
        list_frame.append(scroll)
        content.append(list_frame)
        page.append(content)
        return page

    def _build_youtube_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        page.set_margin_bottom(12)
        page.set_margin_start(14)
        page.set_margin_end(14)

        self.youtube_host = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.youtube_host.set_hexpand(True)
        self.youtube_host.set_vexpand(True)
        self.youtube_host.add_css_class("youtube-surface")
        self.youtube_host.append(self.youtube.webview)
        page.append(self.youtube_host)
        return page

    def _build_youtube_video_page(self):
        page = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )
        page.set_hexpand(True)
        page.set_vexpand(True)

        self.youtube_video_host = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )
        self.youtube_video_host.set_hexpand(True)
        self.youtube_video_host.set_vexpand(True)
        self.youtube_video_host.add_css_class("youtube-surface")
        self.youtube_video_host.append(self.youtube_video.webview)
        page.append(self.youtube_video_host)
        return page

    def _build_queue_panel(self):
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        panel.set_size_request(340, -1)
        panel.add_css_class("queue-panel")
        panel.set_margin_top(16)
        panel.set_margin_bottom(16)
        panel.set_margin_start(0)
        panel.set_margin_end(14)
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label(label="Nächster Titel")
        title.set_xalign(0)
        title.set_hexpand(True)
        title.add_css_class("panel-title")
        title_row.append(title)
        self.queue_count = Gtk.Label(label="0 Titel")
        self.queue_count.add_css_class("muted")
        title_row.append(self.queue_count)
        panel.append(title_row)

        self.queue_list = Gtk.ListBox()
        self.queue_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.queue_list.add_css_class("queue-list")
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.set_child(self.queue_list)
        panel.append(scroll)
        return panel

    def _build_player_bar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        bar.add_css_class("player-bar")
        bar.set_margin_start(10)
        bar.set_margin_end(14)
        bar.set_margin_bottom(12)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info.set_size_request(260, -1)
        self.now_title = Gtk.Label(label="Kein Titel")
        self.now_title.set_xalign(0)
        self.now_title.set_ellipsize(Pango.EllipsizeMode.END)
        self.now_title.add_css_class("now-title")
        info.append(self.now_title)
        self.now_source = Gtk.Label(label="LiMusic bereit")
        self.now_source.set_xalign(0)
        self.now_source.set_ellipsize(Pango.EllipsizeMode.END)
        self.now_source.add_css_class("muted")
        info.append(self.now_source)
        bar.append(info)

        transport = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        previous = icon_button("media-skip-backward-symbolic", "Vorheriger Titel")
        rewind = icon_button("media-seek-backward-symbolic", "10 Sekunden zurück")
        self.play_button = icon_button("media-playback-start-symbolic", "Wiedergabe/Pause", "transport-main")
        forward = icon_button("media-seek-forward-symbolic", "10 Sekunden vor")
        next_button = icon_button("media-skip-forward-symbolic", "Nächster Titel")
        previous.connect("clicked", lambda _button: self.previous_track())
        rewind.connect("clicked", lambda _button: self.seek_relative(-10))
        self.play_button.connect("clicked", lambda _button: self.play_pause())
        forward.connect("clicked", lambda _button: self.seek_relative(10))
        next_button.connect("clicked", lambda _button: self.next_track())
        for widget in (previous, rewind, self.play_button, forward, next_button):
            transport.append(widget)
        bar.append(transport)

        timeline = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        timeline.set_hexpand(True)
        self.elapsed = Gtk.Label(label="0:00")
        self.seek = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.seek.set_draw_value(False)
        self.seek.set_hexpand(True)
        self.seek.connect("change-value", self._on_main_seek)
        self.duration = Gtk.Label(label="0:00")
        timeline.append(self.elapsed)
        timeline.append(self.seek)
        timeline.append(self.duration)
        bar.append(timeline)

        volume_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        volume_box.append(Gtk.Image.new_from_icon_name("audio-volume-high-symbolic"))
        self.volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 0.01)
        self.volume.set_size_request(100, -1)
        self.volume.set_value(0.8)
        self.volume.set_draw_value(False)
        self.volume.connect("value-changed", lambda scale: self.set_volume(scale.get_value()))
        volume_box.append(self.volume)
        bar.append(volume_box)

        detach = icon_button("window-new-symbolic", "Player lösen")
        detach.add_css_class("detach-button")
        detach.connect("clicked", lambda _button: self.detach_player(self.current_mode))
        bar.append(detach)
        return bar

    def _navigate(self, _button, target):
        self.stack.set_visible_child_name(target)
        self._set_active_nav(target)
        if target == "youtube":
            self.current_mode = "youtube"
            self.search.set_visible(True)
            self.search_spacer.set_visible(False)
            self.search.set_placeholder_text("YouTube Music durchsuchen …")
            self.topbar_actions.set_visible_child_name("youtube")
            self.queue_panel.set_visible(False)
            self.youtube.load()
            self.youtube.apply_integrated_mode()
        elif target == "youtube_video":
            self.current_mode = "youtube_video"
            self.search.set_visible(False)
            self.search_spacer.set_visible(True)
            self.topbar_actions.set_visible_child_name("youtube_video")
            self.queue_panel.set_visible(False)
            self.youtube_video.load()
            self.youtube_video.webview.grab_focus()
            self.youtube_video.apply_integrated_mode()
        elif target == "library":
            self.current_mode = "local"
            self.search.set_visible(True)
            self.search_spacer.set_visible(False)
            self.search.set_placeholder_text("Lokale Songs und Videos suchen …")
            self.topbar_actions.set_visible_child_name("local")
            self.queue_panel.set_visible(True)
        else:
            self.search.set_visible(True)
            self.search_spacer.set_visible(False)
            self.search.set_placeholder_text("Lokale Songs und Videos suchen …")
            self.topbar_actions.set_visible_child_name("local")
            self.queue_panel.set_visible(True)

    def _search_changed(self, _entry):
        if self.current_mode not in ("youtube", "youtube_video"):
            self._refresh_library()

    def _search_activated(self, entry):
        if self.current_mode == "youtube":
            self.youtube.search(entry.get_text())
        elif self.current_mode == "youtube_video":
            self.youtube_video.search(entry.get_text())
        else:
            self._refresh_library()

    def _set_active_nav(self, target):
        for name, button in self.nav_buttons.items():
            if name == target:
                button.add_css_class("active")
            else:
                button.remove_css_class("active")

    def _choose_files(self, _button):
        chooser = Gtk.FileChooserNative.new("Medien auswählen", self, Gtk.FileChooserAction.OPEN, "Hinzufügen", "Abbrechen")
        chooser.set_select_multiple(True)
        chooser.connect("response", self._files_selected)
        chooser.show()

    def _files_selected(self, chooser, response):
        if response == Gtk.ResponseType.ACCEPT:
            model = chooser.get_files()
            paths = []
            for index in range(model.get_n_items()):
                file = model.get_item(index)
                path = file.get_path()
                if path:
                    paths.append(Path(path))
            added = self.library.add_paths(paths)
            self.queue = list(self.library.items)
            self._refresh_library()
            self._set_status(f"{len(added)} Mediendatei(en) hinzugefügt")
        chooser.destroy()

    def _choose_folder(self, _button):
        chooser = Gtk.FileChooserNative.new("Medienordner auswählen", self, Gtk.FileChooserAction.SELECT_FOLDER, "Scannen", "Abbrechen")
        chooser.connect("response", self._folder_selected)
        chooser.show()

    def _folder_selected(self, chooser, response):
        if response == Gtk.ResponseType.ACCEPT:
            file = chooser.get_file()
            path = file.get_path() if file else None
            if path:
                added = self.library.scan_folder(Path(path))
                self.queue = list(self.library.items)
                self._refresh_library()
                self._set_status(f"{len(added)} neue Mediendatei(en) gefunden")
        chooser.destroy()

    def _refresh_library(self):
        if not hasattr(self, "library_list"):
            return
        query = self.search.get_text().strip().casefold() if hasattr(self, "search") else ""
        child = self.library_list.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.library_list.remove(child)
            child = next_child
        visible_items = [item for item in self.library.items if not query or query in item.title.casefold()]
        for item in visible_items:
            row = Gtk.ListBoxRow()
            row.media_item = item
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            box.set_margin_top(8)
            box.set_margin_bottom(8)
            box.set_margin_start(8)
            box.set_margin_end(8)
            icon = Gtk.Image.new_from_icon_name("video-x-generic-symbolic" if item.media_type == "video" else "audio-x-generic-symbolic")
            box.append(icon)
            labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            labels.set_hexpand(True)
            title = Gtk.Label(label=item.title)
            title.set_xalign(0)
            title.set_ellipsize(Pango.EllipsizeMode.END)
            labels.append(title)
            detail = Gtk.Label(label="Video" if item.media_type == "video" else "Audio")
            detail.set_xalign(0)
            detail.add_css_class("muted")
            labels.append(detail)
            box.append(labels)
            row.set_child(box)
            self.library_list.append(row)
        self._refresh_queue()
        self._refresh_home_recent()

    def _refresh_queue(self):
        if not hasattr(self, "queue_list"):
            return
        child = self.queue_list.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.queue_list.remove(child)
            child = next_child
        for index, item in enumerate(self.queue[:80]):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.set_margin_top(7)
            row.set_margin_bottom(7)
            row.set_margin_start(8)
            row.set_margin_end(8)
            number = Gtk.Label(label=str(index + 1))
            number.add_css_class("queue-number")
            row.append(number)
            text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            text.set_hexpand(True)
            title = Gtk.Label(label=item.title)
            title.set_xalign(0)
            title.set_ellipsize(Pango.EllipsizeMode.END)
            text.append(title)
            source = Gtk.Label(label="Lokal · Video" if item.media_type == "video" else "Lokal · Audio")
            source.set_xalign(0)
            source.add_css_class("muted")
            text.append(source)
            row.append(text)
            play = icon_button("media-playback-start-symbolic", f"{item.title} abspielen")
            play.connect("clicked", self._queue_play_clicked, index)
            row.append(play)
            self.queue_list.append(row)
        self.queue_count.set_text(f"{len(self.queue)} Titel")

    def _refresh_home_recent(self):
        if not hasattr(self, "home_recent"):
            return
        child = self.home_recent.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.home_recent.remove(child)
            child = next_child
        if not self.library.items:
            empty = Gtk.Label(label="Noch keine lokalen Medien. Füge Dateien oder einen Ordner hinzu.")
            empty.set_xalign(0)
            empty.add_css_class("muted")
            self.home_recent.append(empty)
            return
        for item in self.library.items[-5:][::-1]:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            icon = Gtk.Image.new_from_icon_name("video-x-generic-symbolic" if item.media_type == "video" else "audio-x-generic-symbolic")
            row.append(icon)
            label = Gtk.Label(label=item.title)
            label.set_xalign(0)
            label.set_hexpand(True)
            row.append(label)
            self.home_recent.append(row)

    def _activate_library_row(self, _listbox, row):
        item = row.media_item
        self.play_item(item)

    def _queue_play_clicked(self, _button, index):
        if 0 <= index < len(self.queue):
            self.current_queue_index = index
            self.play_item(self.queue[index])

    def play_item(self, item: MediaItem):
        self.current_mode = "local"
        try:
            self.current_queue_index = next(index for index, candidate in enumerate(self.queue) if candidate.path == item.path)
        except StopIteration:
            self.current_queue_index = -1
        self.local_player.load(item.path, autoplay=True)
        self.stack.set_visible_child_name("library")
        self._set_active_nav("library")
        self.media_hint.set_text("GStreamer · " + ("Video" if item.media_type == "video" else "Audio"))
        if item.media_type == "video" and not self.local_player.video_available:
            self.media_hint.set_text("Video-Sink fehlt: gtk4paintablesink ist auf diesem System nicht verfügbar")

    def _web_view_for_mode(self, mode):
        if mode == "youtube_video":
            return self.youtube_video
        return self.youtube

    def _web_host_for_mode(self, mode):
        if mode == "youtube_video":
            return self.youtube_video_host
        return self.youtube_host

    def _web_label_for_mode(self, mode):
        if mode == "youtube_video":
            return "YouTube"
        return "YouTube Music"

    def play_pause(self, mode=None):
        active_mode = mode or self.current_mode
        if active_mode in ("youtube", "youtube_video"):
            self._web_view_for_mode(active_mode).play_pause()
        else:
            self.local_player.toggle()

    def seek_relative(self, seconds, mode=None):
        active_mode = mode or self.current_mode
        if active_mode in ("youtube", "youtube_video"):
            self._web_view_for_mode(active_mode).seek_relative(seconds)
        else:
            self.local_player.seek_relative(seconds)

    def seek_absolute(self, seconds, mode=None):
        active_mode = mode or self.current_mode
        if active_mode in ("youtube", "youtube_video"):
            self._web_view_for_mode(active_mode).seek_absolute(seconds)
        else:
            self.local_player.seek_absolute(seconds)

    def next_track(self, mode=None):
        active_mode = mode or self.current_mode
        if active_mode in ("youtube", "youtube_video"):
            self._web_view_for_mode(active_mode).next_track()
            return
        if not self.queue:
            return
        next_index = 0 if self.current_queue_index < 0 else (self.current_queue_index + 1) % len(self.queue)
        self.current_queue_index = next_index
        self.play_item(self.queue[next_index])

    def previous_track(self, mode=None):
        active_mode = mode or self.current_mode
        if active_mode in ("youtube", "youtube_video"):
            self._web_view_for_mode(active_mode).previous_track()
            return
        if not self.queue:
            return
        previous_index = len(self.queue) - 1 if self.current_queue_index <= 0 else self.current_queue_index - 1
        self.current_queue_index = previous_index
        self.play_item(self.queue[previous_index])

    def set_volume(self, value, mode=None):
        active_mode = mode or self.current_mode
        if active_mode in ("youtube", "youtube_video"):
            self._web_view_for_mode(active_mode).set_volume(value)
        else:
            self.local_player.set_volume(value)

    def detach_player(self, mode):
        if mode in ("youtube", "youtube_video"):
            self.current_mode = mode
            view = self._web_view_for_mode(mode)
            view.load()
            self.detached.show_youtube(mode)
        else:
            self.current_mode = "local"
            self.detached.show_local()

    def move_youtube_to(self, destination, mode="youtube"):
        view = self._web_view_for_mode(mode)
        host = self._web_host_for_mode(mode)
        label = self._web_label_for_mode(mode)

        view.set_detached_mode(True)
        parent = view.webview.get_parent()
        if parent is not None and hasattr(parent, "remove"):
            parent.remove(view.webview)
        destination.append(view.webview)

        if host.get_first_child() is None:
            message = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=8,
            )
            message.set_halign(Gtk.Align.CENTER)
            message.set_valign(Gtk.Align.CENTER)
            message.add_css_class("detached-message")
            message.append(
                Gtk.Image.new_from_icon_name("window-new-symbolic")
            )
            title = Gtk.Label(
                label=f"{label} läuft im externen Player"
            )
            title.add_css_class("section-title")
            message.append(title)
            restore = Gtk.Button(label="Player zurückholen")
            restore.add_css_class("accent-action")
            restore.connect(
                "clicked",
                lambda _button: self.detached.restore_youtube(),
            )
            message.append(restore)
            host.append(message)

    def restore_youtube(self, mode=None):
        mode = mode or self.detached.mode or self.current_mode
        if mode not in ("youtube", "youtube_video"):
            mode = "youtube"

        view = self._web_view_for_mode(mode)
        host = self._web_host_for_mode(mode)
        view.set_detached_mode(False)

        parent = view.webview.get_parent()
        if parent is not None and hasattr(parent, "remove"):
            parent.remove(view.webview)

        child = host.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            host.remove(child)
            child = next_child

        host.append(view.webview)
        self.detached.mode = None
        self.stack.set_visible_child_name(mode)
        self._set_active_nav(mode)
        self.current_mode = mode

    def open_main_from_detached(self, go_home=False):
        mode = self.detached.mode
        if mode in ("youtube", "youtube_video"):
            self.restore_youtube(mode)
            if go_home:
                self._web_view_for_mode(mode).home()
        elif mode == "local":
            self.local_player.set_picture(self.local_picture)
            self.stack.set_visible_child_name("library")
            self._set_active_nav("library")
            self.current_mode = "local"
            self.detached.mode = None
        self.set_visible(True)
        self.present()
        self.detached.hide()

    def _on_main_close_request(self, _window):
        if (
            self.detached.get_visible()
            and self.detached.mode in ("local", "youtube", "youtube_video")
        ):
            self.hide()
            return True
        self.get_application().quit()
        return True

    def _on_main_seek(self, _scale, _scroll, value):
        if not self._updating_seek:
            self.seek_absolute(value)
        return False

    def _on_local_state(self, _player, state):
        playing = state == "playing"
        image_name = "media-playback-pause-symbolic" if playing else "media-playback-start-symbolic"
        self.play_button.set_child(Gtk.Image.new_from_icon_name(image_name))
        self.detached.set_play_state(playing)

    def _on_local_track(self, _player, title, path):
        self.now_title.set_text(title)
        self.now_source.set_text(f"Lokal · {Path(path).suffix.lower().lstrip('.').upper()}")
        self.detached.title_label.set_text(title)
        self._set_status(f"Wiedergabe: {title}")

    def _on_local_position(self, _player, position, duration):
        self._updating_seek = True
        self.seek.set_range(0, max(1, duration))
        if not self.seek.has_focus():
            self.seek.set_value(position)
        self.elapsed.set_text(format_time(position))
        self.duration.set_text(format_time(duration))
        self._updating_seek = False
        self.detached.set_position(position, duration)

    def _on_local_error(self, _player, message):
        self._set_status("Wiedergabefehler")
        dialog = Gtk.AlertDialog()
        dialog.set_message("GStreamer-Wiedergabefehler")
        dialog.set_detail(message)
        dialog.show(self)


    def _on_youtube_player_state(self, mode, state):
        if self.current_mode != mode and self.detached.mode != mode:
            return
        position = max(0.0, float(state.get("current") or 0))
        duration = max(0.0, float(state.get("duration") or 0))
        playing = bool(state.get("playing"))
        title = str(state.get("title") or "").strip()
        artist = str(state.get("artist") or "").strip()
        if self.current_mode == "youtube":
            self._updating_seek = True
            self.seek.set_range(0, max(1, duration))
            if not self.seek.has_focus():
                self.seek.set_value(position)
            self.elapsed.set_text(format_time(position))
            self.duration.set_text(format_time(duration))
            self._updating_seek = False
            image_name = "media-playback-pause-symbolic" if playing else "media-playback-start-symbolic"
            self.play_button.set_child(Gtk.Image.new_from_icon_name(image_name))
            if title:
                self.now_title.set_text(title)
            source_label = self._web_label_for_mode(mode)
            self.now_source.set_text(
                f"{source_label} · {artist}"
                if artist
                else source_label
            )
        if self.detached.mode == mode:
            if title:
                self.detached.title_label.set_text(title)
            self.detached.set_play_state(playing)
            self.detached.set_position(position, duration)

    def _on_youtube_title(self, mode, title):
        if self.current_mode == mode:
            self.now_title.set_text(title)
            self.now_source.set_text(
                self._web_label_for_mode(mode)
            )

    def _set_status(self, message):
        self.set_title(f"LiMusic {__version__}")


class LiMusicApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.window = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self._load_css()

    def do_activate(self):
        if self.window is None:
            self.window = MainWindow(self)
        self.window.present()

    def _load_css(self):
        base = Path(__file__).resolve().parents[2]
        css_path = base / "data" / "style.css"
        provider = Gtk.CssProvider()
        provider.load_from_path(str(css_path))
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stderr)],
    )


def main():
    configure_logging()
    app = LiMusicApplication()
    return app.run(sys.argv)
