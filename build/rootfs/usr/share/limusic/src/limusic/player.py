from pathlib import Path

import gi

gi.require_version("Gst", "1.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, GObject, Gst, Gtk

Gst.init(None)


class LocalPlayer(GObject.GObject):
    __gsignals__ = {
        "state-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "track-changed": (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
        "position-changed": (GObject.SignalFlags.RUN_FIRST, None, (float, float)),
        "error": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "eos": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        super().__init__()
        self.playbin = Gst.ElementFactory.make("playbin3", "limusic-player")
        if self.playbin is None:
            self.playbin = Gst.ElementFactory.make("playbin", "limusic-player")
        if self.playbin is None:
            raise RuntimeError("GStreamer playbin3/playbin is not available")
        self.video_sink = Gst.ElementFactory.make("gtk4paintablesink", "limusic-video-sink")
        self.paintable = None
        self.video_available = False
        if self.video_sink is not None:
            self.playbin.set_property("video-sink", self.video_sink)
            try:
                self.paintable = self.video_sink.get_property("paintable")
                self.video_available = self.paintable is not None
            except TypeError:
                self.paintable = None
        self.current_path = None
        self.current_title = ""
        self.is_playing = False
        self.duration_seconds = 0.0
        bus = self.playbin.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_bus_message)
        GLib.timeout_add(350, self._poll_position)

    def set_picture(self, picture: Gtk.Picture):
        if self.paintable is not None:
            picture.set_paintable(self.paintable)
            picture.set_can_shrink(True)
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)

    def load(self, path: str, autoplay=True):
        target = Path(path).expanduser().resolve()
        if not target.is_file():
            self.emit("error", f"Datei nicht gefunden: {target}")
            return
        self.playbin.set_state(Gst.State.NULL)
        self.current_path = str(target)
        self.current_title = target.stem
        self.playbin.set_property("uri", Gio.File.new_for_path(str(target)).get_uri())
        self.emit("track-changed", self.current_title, str(target))
        if autoplay:
            self.play()

    def play(self):
        result = self.playbin.set_state(Gst.State.PLAYING)
        if result == Gst.StateChangeReturn.FAILURE:
            self.emit("error", "GStreamer konnte die Wiedergabe nicht starten")
            return
        self.is_playing = True
        self.emit("state-changed", "playing")

    def pause(self):
        self.playbin.set_state(Gst.State.PAUSED)
        self.is_playing = False
        self.emit("state-changed", "paused")

    def toggle(self):
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def stop(self):
        self.playbin.set_state(Gst.State.NULL)
        self.is_playing = False
        self.emit("state-changed", "stopped")

    def seek_relative(self, seconds: float):
        success, position = self.playbin.query_position(Gst.Format.TIME)
        if not success:
            return
        target = max(0, position + int(seconds * Gst.SECOND))
        self.playbin.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, target)

    def seek_absolute(self, seconds: float):
        target = max(0, int(seconds * Gst.SECOND))
        self.playbin.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, target)

    def set_volume(self, value: float):
        self.playbin.set_property("volume", max(0.0, min(1.0, value)))

    def _poll_position(self):
        success_position, position = self.playbin.query_position(Gst.Format.TIME)
        success_duration, duration = self.playbin.query_duration(Gst.Format.TIME)
        if success_duration and duration > 0:
            self.duration_seconds = duration / Gst.SECOND
        if success_position:
            self.emit("position-changed", position / Gst.SECOND, self.duration_seconds)
        return GLib.SOURCE_CONTINUE

    def _on_bus_message(self, _bus, message):
        message_type = message.type
        if message_type == Gst.MessageType.ERROR:
            error, debug = message.parse_error()
            detail = error.message
            if debug:
                detail = f"{detail}\n{debug}"
            self.is_playing = False
            self.emit("state-changed", "stopped")
            self.emit("error", detail)
        elif message_type == Gst.MessageType.EOS:
            self.is_playing = False
            self.emit("state-changed", "stopped")
            self.emit("eos")
        elif message_type == Gst.MessageType.STATE_CHANGED and message.src == self.playbin:
            _old, new, _pending = message.parse_state_changed()
            if new == Gst.State.PLAYING:
                self.is_playing = True
                self.emit("state-changed", "playing")
            elif new == Gst.State.PAUSED:
                self.is_playing = False
                self.emit("state-changed", "paused")
