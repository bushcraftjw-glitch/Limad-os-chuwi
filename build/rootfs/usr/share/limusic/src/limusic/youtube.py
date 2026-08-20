import json
from pathlib import Path
from urllib.parse import quote_plus

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import Gio, GLib, Gtk, WebKit

from .paths import STATE_DIR, WEBKIT_CACHE_DIR, WEBKIT_DATA_DIR
from .adblock_engine import ENGINE_BOOTSTRAP_SCRIPT, ENGINE_RUNTIME_SCRIPT

YOUTUBE_MUSIC_URL = "https://music.youtube.com/"
YOUTUBE_URL = "https://www.youtube.com/"

ADBLOCK_FILTER_ID = "limusic-youtube-adblock-v3-ubo-compat"
ADBLOCK_FILTER_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "youtube-adblock-webkit.json"
)
ADBLOCK_DIAG_LOG = STATE_DIR / "adblock-diagnostic.log"

ADBLOCK_BOOTSTRAP_SCRIPT = ENGINE_BOOTSTRAP_SCRIPT
ADBLOCK_SCRIPT = ENGINE_RUNTIME_SCRIPT

INTEGRATED_STYLE_SCRIPT = r"""
(() => {
  let style = document.getElementById('limusic-integrated-style');
  if (!style) {
    style = document.createElement('style');
    style.id = 'limusic-integrated-style';
    document.documentElement.appendChild(style);
  }
  style.textContent = `
    ytmusic-nav-bar,
    ytmusic-guide-renderer,
    ytmusic-player-bar,
    tp-yt-app-drawer,
    #nav-bar-background,
    #mini-guide,
    #guide-wrapper,
    #guide-content {
      display: none !important;
      visibility: hidden !important;
    }
    html, body, ytmusic-app, ytmusic-app-layout {
      background: #050608 !important;
    }
    ytmusic-app-layout {
      --ytmusic-nav-bar-height: 0px !important;
      --ytmusic-guide-width: 0px !important;
      --ytmusic-mini-guide-width: 0px !important;
      padding-top: 0 !important;
    }
    ytmusic-app-layout > #content,
    #content,
    #main-panel,
    ytmusic-browse-response,
    ytmusic-search-page {
      margin-left: 0 !important;
      margin-top: 0 !important;
      padding-top: 0 !important;
      width: 100% !important;
      max-width: none !important;
    }
    ytmusic-app-layout[guide-collapsed] > #content,
    ytmusic-app-layout:not([guide-collapsed]) > #content {
      margin-left: 0 !important;
    }
    ::-webkit-scrollbar {
      width: 10px !important;
      height: 10px !important;
    }
    ::-webkit-scrollbar-track {
      background: #0b0e12 !important;
    }
    ::-webkit-scrollbar-thumb {
      background: #343a45 !important;
      border-radius: 999px !important;
      border: 2px solid #0b0e12 !important;
    }
  `;
  document.documentElement.classList.add('limusic-integrated');
  return true;
})();
"""

YOUTUBE_INTEGRATED_STYLE_SCRIPT = r"""\
(() => {
  let style = document.getElementById('limusic-youtube-integrated-style');
  if (!style) {
    style = document.createElement('style');
    style.id = 'limusic-youtube-integrated-style';
    document.documentElement.appendChild(style);
  }
  style.textContent = `
    ytd-masthead,
    ytd-mini-guide-renderer,
    tp-yt-app-drawer,
    #guide-wrapper,
    #guide-content {
      display: none !important;
      visibility: hidden !important;
    }
    html, body, ytd-app {
      background: #050608 !important;
    }
    ytd-app {
      --ytd-masthead-height: 0px !important;
    }
    ytd-page-manager,
    #page-manager {
      margin-top: 0 !important;
      margin-left: 0 !important;
      padding-top: 0 !important;
      width: 100% !important;
      max-width: none !important;
    }
    ytd-watch-flexy,
    ytd-browse,
    ytd-search {
      margin-top: 0 !important;
      padding-top: 0 !important;
    }
    ::-webkit-scrollbar {
      width: 10px !important;
      height: 10px !important;
    }
    ::-webkit-scrollbar-track {
      background: #0b0e12 !important;
    }
    ::-webkit-scrollbar-thumb {
      background: #343a45 !important;
      border-radius: 999px !important;
      border: 2px solid #0b0e12 !important;
    }
  `;
  document.documentElement.classList.add('limusic-youtube-integrated');
  return true;
})();
"""

DETACHED_PLAYER_STYLE_SCRIPT = r"""
(() => {
  let style = document.getElementById('limusic-detached-player-style');
  if (!style) {
    style = document.createElement('style');
    style.id = 'limusic-detached-player-style';
    document.documentElement.appendChild(style);
  }
  document.querySelectorAll('.limusic-video-ancestor').forEach((element) => element.classList.remove('limusic-video-ancestor'));
  const media = document.querySelector('video');
  if (media) {
    let node = media.parentElement;
    while (node && node !== document.body) {
      node.classList.add('limusic-video-ancestor');
      node = node.parentElement;
    }
  }
  style.textContent = `
    html.limusic-detached-player,
    html.limusic-detached-player body {
      margin: 0 !important;
      padding: 0 !important;
      width: 100% !important;
      height: 100% !important;
      overflow: hidden !important;
      background: #000 !important;
    }
    html.limusic-detached-player body * {
      visibility: hidden !important;
    }
    html.limusic-detached-player .limusic-video-ancestor {
      visibility: visible !important;
      transform: none !important;
      filter: none !important;
      perspective: none !important;
      contain: none !important;
      overflow: visible !important;
    }
    html.limusic-detached-player video {
      visibility: visible !important;
      display: block !important;
      position: fixed !important;
      inset: 0 !important;
      width: 100vw !important;
      height: 100vh !important;
      min-width: 100vw !important;
      min-height: 100vh !important;
      max-width: none !important;
      max-height: none !important;
      margin: 0 !important;
      padding: 0 !important;
      object-fit: contain !important;
      background: #000 !important;
      opacity: 1 !important;
      z-index: 2147483647 !important;
      pointer-events: none !important;
    }
  `;
  document.documentElement.classList.add('limusic-detached-player');
  return true;
})();
"""

EXIT_DETACHED_PLAYER_SCRIPT = r"""
(() => {
  document.documentElement.classList.remove('limusic-detached-player');
  document.querySelectorAll('.limusic-video-ancestor').forEach((element) => element.classList.remove('limusic-video-ancestor'));
  const style = document.getElementById('limusic-detached-player-style');
  if (style) style.remove();
  return true;
})();
"""

PLAYER_STATE_SCRIPT = r"""
(() => {
  const bar = document.querySelector('ytmusic-app-layout>ytmusic-player-bar');
  const api = bar && bar.playerApi ? bar.playerApi : null;
  const media = document.querySelector('video, audio');
  const safeCall = (name, fallback) => {
    try {
      return api && typeof api[name] === 'function' ? api[name]() : fallback;
    } catch (_) {
      return fallback;
    }
  };
  let response = null;
  try {
    response = api && typeof api.getPlayerResponse === 'function' ? api.getPlayerResponse() : null;
  } catch (_) {
    response = null;
  }
  const sessionMetadata = navigator.mediaSession && navigator.mediaSession.metadata ? navigator.mediaSession.metadata : null;
  const current = Number(safeCall('getCurrentTime', media ? media.currentTime : 0)) || 0;
  const duration = Number(safeCall('getDuration', media ? media.duration : 0)) || 0;
  const playerState = Number(safeCall('getPlayerState', media && !media.paused ? 1 : 2));
  const title = (sessionMetadata && sessionMetadata.title) ||
    (response && response.videoDetails && response.videoDetails.title) ||
    (bar && bar.querySelector('.title') ? bar.querySelector('.title').textContent.trim() : '') || '';
  const artist = (sessionMetadata && sessionMetadata.artist) ||
    (response && response.videoDetails && response.videoDetails.author) ||
    (bar && bar.querySelector('.byline') ? bar.querySelector('.byline').textContent.trim() : '') || '';
  const videoId = response && response.videoDetails ? response.videoDetails.videoId || '' : '';
  const volume = Number(safeCall('getVolume', 80));
  return JSON.stringify({
    ready: Boolean(api || media),
    current,
    duration,
    playing: Boolean((bar && bar.playing) || playerState === 1 || (media && !media.paused)),
    title,
    artist,
    videoId,
    volume: Number.isFinite(volume) ? volume / 100 : 0.8
  });
})();
"""


class YouTubeMusicView:
    def __init__(self, site="music", session=None):
        self.site = site
        self.site_label = "YouTube" if site == "youtube" else "YouTube Music"
        self.base_url = YOUTUBE_URL if site == "youtube" else YOUTUBE_MUSIC_URL
        if session is None:
            self.session = WebKit.NetworkSession.new(
                str(WEBKIT_DATA_DIR),
                str(WEBKIT_CACHE_DIR),
            )
            cookie_manager = self.session.get_cookie_manager()
            cookie_manager.set_persistent_storage(
                str(WEBKIT_DATA_DIR / "cookies.sqlite"),
                WebKit.CookiePersistentStorage.SQLITE,
            )
        else:
            self.session = session
        self.content_manager = WebKit.UserContentManager.new()
        self.webview = WebKit.WebView(
            network_session=self.session,
            user_content_manager=self.content_manager,
        )
        settings = self.webview.get_settings()
        settings.set_property("media-playback-requires-user-gesture", False)
        self.webview.set_hexpand(True)
        self.webview.set_vexpand(True)
        self.webview.set_focusable(True)
        self.webview.connect("create", self._on_create)
        self.webview.connect("load-changed", self._on_load_changed)
        self.webview.connect("notify::title", self._on_title_changed)
        self.popup_windows = []
        self.on_status = None
        self.on_title = None
        self.on_player_state = None
        self.loaded_once = False
        self._poll_source_id = None
        self._poll_inflight = False
        self.detached_mode = False
        self.adblock_enabled = True
        self._adblock_user_script = None
        self._adblock_runtime_user_script = None
        self._adblock_script_installed = False
        self._adblock_filter_store = None
        self._adblock_filter = None
        self._adblock_filter_ready = False
        self._adblock_filter_installed = False
        self._adblock_filter_setup_started = False
        self._adblock_filter_error = None
        self._pending_uri = None
        self._pending_uri_timeout = None
        self._ad_diag_handler_registered = False

        self._setup_adblock_diagnostics()
        self._install_adblock_bootstrap()
        self._start_adblock_filter_setup()

    def load(self):
        if not self.loaded_once:
            self.loaded_once = True
            self._navigate(self.base_url)

    def home(self):
        self._navigate(self.base_url)

    def reload(self):
        self.webview.reload()

    def back(self):
        if self.webview.can_go_back():
            self.webview.go_back()

    def forward(self):
        if self.webview.can_go_forward():
            self.webview.go_forward()

    def search(self, query):
        text = query.strip()
        if not text:
            self.home()
            return
        if self.site == "youtube":
            self._navigate(
                f"{YOUTUBE_URL}results?search_query={quote_plus(text)}"
            )
        else:
            self._navigate(
                f"{YOUTUBE_MUSIC_URL}search?q={quote_plus(text)}"
            )

    def open_account(self):
        script = r"""
(() => {
  const candidates = Array.from(document.querySelectorAll('button, tp-yt-paper-icon-button, yt-button-shape button, a'));
  const labels = ['account', 'konto', 'profile', 'profil', 'sign in', 'anmelden'];
  const target = candidates.find((element) => {
    const text = [
      element.getAttribute('aria-label'),
      element.getAttribute('title'),
      element.textContent
    ].filter(Boolean).join(' ').trim().toLowerCase();
    return labels.some((label) => text.includes(label));
  });
  if (target) {
    target.click();
    return true;
  }
  return false;
})();
"""
        self._evaluate(script)

    def _ad_diag_write(self, message):
        text = str(message).replace("\n", " ").strip()
        line = f"[LiMusic AD-DIAG {self.site_label}] {text}"
        print(line, flush=True)
        try:
            ADBLOCK_DIAG_LOG.parent.mkdir(parents=True, exist_ok=True)
            with ADBLOCK_DIAG_LOG.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except Exception:
            pass

    def _setup_adblock_diagnostics(self):
        if self._ad_diag_handler_registered:
            return
        try:
            self.content_manager.connect(
                "script-message-received::limusicAdDiag",
                self._on_ad_diag_message,
            )
            try:
                registered = self.content_manager.register_script_message_handler(
                    "limusicAdDiag",
                    None,
                )
            except TypeError:
                registered = self.content_manager.register_script_message_handler(
                    "limusicAdDiag"
                )
            self._ad_diag_handler_registered = bool(registered)
            self._ad_diag_write(
                json.dumps(
                    {"event": "diag-handler", "registered": bool(registered)},
                    ensure_ascii=False,
                )
            )
        except Exception as exc:
            self._ad_diag_write(
                json.dumps(
                    {"event": "diag-handler-error", "error": str(exc)},
                    ensure_ascii=False,
                )
            )

    def _on_ad_diag_message(self, _manager, value):
        try:
            if hasattr(value, "get_js_value"):
                value = value.get_js_value()
            text = value.to_string() if hasattr(value, "to_string") else str(value)
            self._ad_diag_write(text)
        except Exception as exc:
            self._ad_diag_write(
                json.dumps(
                    {"event": "diag-message-error", "error": str(exc)},
                    ensure_ascii=False,
                )
            )

    @staticmethod
    def _enum_member(enum_type, *names, fallback=0):
        for name in names:
            value = getattr(enum_type, name, None)
            if value is not None:
                return value
        return fallback

    def _install_adblock_bootstrap(self):
        if self._adblock_script_installed:
            return

        try:
            injected_frames = self._enum_member(
                WebKit.UserContentInjectedFrames,
                "ALL_FRAMES",
                "WEBKIT_USER_CONTENT_INJECT_ALL_FRAMES",
                fallback=0,
            )
            document_start = self._enum_member(
                WebKit.UserScriptInjectionTime,
                "DOCUMENT_START",
                "START",
                "WEBKIT_USER_SCRIPT_INJECT_AT_DOCUMENT_START",
                fallback=0,
            )
            document_end = self._enum_member(
                WebKit.UserScriptInjectionTime,
                "DOCUMENT_END",
                "END",
                "WEBKIT_USER_SCRIPT_INJECT_AT_DOCUMENT_END",
                fallback=1,
            )

            if self._adblock_user_script is None:
                self._adblock_user_script = WebKit.UserScript.new(
                    ADBLOCK_BOOTSTRAP_SCRIPT,
                    injected_frames,
                    document_start,
                    None,
                    None,
                )

            if self._adblock_runtime_user_script is None:
                self._adblock_runtime_user_script = WebKit.UserScript.new(
                    ADBLOCK_SCRIPT,
                    injected_frames,
                    document_end,
                    None,
                    None,
                )

            self.content_manager.add_script(self._adblock_user_script)
            self._ad_diag_write(
                json.dumps(
                    {
                        "event": "scriptlet-engine-user-script-added",
                        "phase": "document-start",
                    },
                    ensure_ascii=False,
                )
            )

            self.content_manager.add_script(
                self._adblock_runtime_user_script
            )
            self._ad_diag_write(
                json.dumps(
                    {
                        "event": "scriptlet-engine-user-script-added",
                        "phase": "document-end",
                    },
                    ensure_ascii=False,
                )
            )

            self._adblock_script_installed = True
        except Exception as exc:
            self._adblock_filter_error = (
                f"Scriptlet-Engine-UserScript: {exc}"
            )
            self._adblock_script_installed = False
            self._ad_diag_write(
                json.dumps(
                    {
                        "event": "scriptlet-engine-user-script-error",
                        "error": str(exc),
                    },
                    ensure_ascii=False,
                )
            )

    def _start_adblock_filter_setup(self):
        if self._adblock_filter_setup_started:
            return
        self._adblock_filter_setup_started = True

        try:
            store_path = WEBKIT_DATA_DIR / "content-filters"
            store_path.mkdir(parents=True, exist_ok=True)
            self._adblock_filter_store = WebKit.UserContentFilterStore.new(
                str(store_path)
            )
            source_file = Gio.File.new_for_path(str(ADBLOCK_FILTER_FILE))
            filter_id = f"{ADBLOCK_FILTER_ID}-{self.site}"
            self._adblock_filter_store.save_from_file(
                filter_id,
                source_file,
                None,
                self._on_adblock_filter_saved,
                None,
            )
        except Exception as exc:
            self._adblock_filter_error = f"WebKit-Filter: {exc}"
            self._adblock_filter_ready = True
            self._continue_pending_navigation()

    def _on_adblock_filter_saved(self, store, result, _user_data):
        try:
            try:
                content_filter = store.save_from_file_finish(result)
            except AttributeError:
                content_filter = store.save_finish(result)

            self._adblock_filter = content_filter
            self._adblock_filter_ready = True
            self._ad_diag_write(
                json.dumps(
                    {"event": "webkit-filter-compiled", "filter_id": f"{ADBLOCK_FILTER_ID}-{self.site}"},
                    ensure_ascii=False,
                )
            )
            if self.adblock_enabled:
                self._install_network_filter()
        except Exception as exc:
            self._adblock_filter_error = f"WebKit-Filter: {exc}"
            self._ad_diag_write(
                json.dumps(
                    {"event": "webkit-filter-error", "error": str(exc)},
                    ensure_ascii=False,
                )
            )
            self._adblock_filter_ready = True
        finally:
            self._continue_pending_navigation()

    def _install_network_filter(self):
        if (
            not self.adblock_enabled
            or self._adblock_filter is None
            or self._adblock_filter_installed
        ):
            return

        try:
            self.content_manager.add_filter(self._adblock_filter)
            self._adblock_filter_installed = True
            self._ad_diag_write(
                json.dumps(
                    {"event": "webkit-filter-installed", "filter_id": f"{ADBLOCK_FILTER_ID}-{self.site}"},
                    ensure_ascii=False,
                )
            )
        except Exception as exc:
            self._adblock_filter_error = f"WebKit-Netzwerkfilter: {exc}"
            self._ad_diag_write(
                json.dumps(
                    {"event": "webkit-filter-install-error", "error": str(exc)},
                    ensure_ascii=False,
                )
            )

    def _remove_adblock_content(self):
        try:
            self.content_manager.remove_all_filters()
        except Exception:
            pass
        self._adblock_filter_installed = False

        try:
            self.content_manager.remove_all_scripts()
            self._ad_diag_write(
                json.dumps(
                    {"event": "webkit-user-scripts-removed"},
                    ensure_ascii=False,
                )
            )
        except Exception as exc:
            self._ad_diag_write(
                json.dumps(
                    {
                        "event": "webkit-user-scripts-remove-error",
                        "error": str(exc),
                    },
                    ensure_ascii=False,
                )
            )
        self._adblock_script_installed = False

    def _navigate(self, uri):
        if (
            self.adblock_enabled
            and self._adblock_filter_setup_started
            and not self._adblock_filter_ready
        ):
            self._pending_uri = uri
            if self._pending_uri_timeout is None:
                self._pending_uri_timeout = GLib.timeout_add(
                    2000,
                    self._filter_wait_timeout,
                )
            return

        self.webview.load_uri(uri)

    def _filter_wait_timeout(self):
        self._pending_uri_timeout = None
        self._continue_pending_navigation(force=True)
        return GLib.SOURCE_REMOVE

    def _continue_pending_navigation(self, force=False):
        if self._pending_uri is None:
            return

        if (
            not force
            and self.adblock_enabled
            and self._adblock_filter_setup_started
            and not self._adblock_filter_ready
        ):
            return

        uri = self._pending_uri
        self._pending_uri = None

        if self._pending_uri_timeout is not None:
            GLib.source_remove(self._pending_uri_timeout)
            self._pending_uri_timeout = None

        self.webview.load_uri(uri)

    def set_adblock_enabled(self, enabled):
        enabled = bool(enabled)
        changed = enabled != self.adblock_enabled
        self.adblock_enabled = enabled

        if enabled:
            self._install_adblock_bootstrap()
            if self._adblock_filter_ready:
                self._install_network_filter()
            else:
                self._start_adblock_filter_setup()
            self.apply_adblock()
        else:
            self._evaluate(
                "window.__limusicSetAdBlockEnabled && "
                "window.__limusicSetAdBlockEnabled(false);"
            )
            self._remove_adblock_content()

        if changed and self.loaded_once and not self.webview.is_loading():
            self.webview.reload()

    def apply_adblock(self):
        if self.adblock_enabled:
            self._evaluate_adblock(
                ADBLOCK_SCRIPT,
                "runtime-evaluate",
            )

    def _evaluate_adblock(self, script, label):
        try:
            self.webview.evaluate_javascript(
                script,
                -1,
                None,
                None,
                None,
                self._on_adblock_evaluate_finished,
                label,
            )
        except Exception as exc:
            self._ad_diag_write(
                json.dumps(
                    {
                        "event": "adblock-evaluate-call-error",
                        "label": label,
                        "error": str(exc),
                    },
                    ensure_ascii=False,
                )
            )

    def _on_adblock_evaluate_finished(
        self,
        webview,
        result,
        label,
    ):
        try:
            webview.evaluate_javascript_finish(result)
            self._ad_diag_write(
                json.dumps(
                    {
                        "event": "adblock-evaluate-ok",
                        "label": label,
                    },
                    ensure_ascii=False,
                )
            )
        except Exception as exc:
            self._ad_diag_write(
                json.dumps(
                    {
                        "event": "adblock-evaluate-error",
                        "label": label,
                        "error": str(exc),
                    },
                    ensure_ascii=False,
                )
            )

    def play_pause(self):
        self._run_media_script("toggle")

    def seek_relative(self, seconds):
        self._run_media_script("seek", seconds)

    def seek_absolute(self, seconds):
        self._run_media_script("seek_absolute", seconds)

    def set_volume(self, value):
        self._run_media_script("volume", value)

    def next_track(self):
        self._run_media_script("next")

    def previous_track(self):
        self._run_media_script("previous")

    def apply_integrated_mode(self):
        if self.site == "youtube":
            self._evaluate(YOUTUBE_INTEGRATED_STYLE_SCRIPT)
        else:
            self._evaluate(INTEGRATED_STYLE_SCRIPT)

    def set_detached_mode(self, detached):
        self.detached_mode = bool(detached)
        if self.detached_mode:
            self._evaluate(DETACHED_PLAYER_STYLE_SCRIPT)
        else:
            self._evaluate(EXIT_DETACHED_PLAYER_SCRIPT)
            self.apply_integrated_mode()

    def _run_media_script(self, action, value=None):
        payload = json.dumps({"action": action, "value": value})
        script = f"""
(() => {{
  const payload = {payload};
  const bar = document.querySelector('ytmusic-app-layout>ytmusic-player-bar');
  const api = bar && bar.playerApi ? bar.playerApi : null;
  const media = document.querySelector('video, audio');
  if (api) {{
    try {{
      if (payload.action === 'toggle') {{
        if ((bar && bar.playing) || (typeof api.getPlayerState === 'function' && api.getPlayerState() === 1)) api.pauseVideo();
        else api.playVideo();
        return true;
      }}
      if (payload.action === 'seek') {{
        const current = typeof api.getCurrentTime === 'function' ? api.getCurrentTime() : (media ? media.currentTime : 0);
        api.seekTo(Math.max(0, Number(current || 0) + Number(payload.value || 0)));
        return true;
      }}
      if (payload.action === 'seek_absolute') {{
        api.seekTo(Math.max(0, Number(payload.value || 0)));
        return true;
      }}
      if (payload.action === 'volume') {{
        api.setVolume(Math.max(0, Math.min(100, Number(payload.value || 0) * 100)));
        return true;
      }}
      if (payload.action === 'next') {{
        api.nextVideo();
        return true;
      }}
      if (payload.action === 'previous') {{
        api.previousVideo();
        return true;
      }}
    }} catch (_) {{}}
  }}
  if (payload.action === 'toggle' && media) {{
    if (media.paused) media.play(); else media.pause();
    return true;
  }}
  if (payload.action === 'seek' && media) {{
    media.currentTime = Math.max(0, media.currentTime + Number(payload.value || 0));
    return true;
  }}
  if (payload.action === 'seek_absolute' && media) {{
    media.currentTime = Math.max(0, Number(payload.value || 0));
    return true;
  }}
  if (payload.action === 'volume' && media) {{
    media.volume = Math.max(0, Math.min(1, Number(payload.value || 0)));
    return true;
  }}
  const selector = payload.action === 'next'
    ? 'ytmusic-player-bar #next-button, ytmusic-player-bar [aria-label*="Next"], ytmusic-player-bar [aria-label*="Nächster"]'
    : 'ytmusic-player-bar #previous-button, ytmusic-player-bar [aria-label*="Previous"], ytmusic-player-bar [aria-label*="Vorheriger"]';
  const target = document.querySelector(selector);
  if (target) {{
    target.click();
    return true;
  }}
  return false;
}})();
"""
        self._evaluate(script)

    def _evaluate(self, script):
        try:
            self.webview.evaluate_javascript(script, -1, None, None, None, None, None)
        except Exception:
            pass

    def _ensure_player_polling(self):
        if self._poll_source_id is None:
            self._poll_source_id = GLib.timeout_add(500, self._poll_player_state)

    def _poll_player_state(self):
        if self._poll_inflight or self.webview.is_loading():
            return GLib.SOURCE_CONTINUE
        if self.adblock_enabled:
            self._evaluate_adblock(
                "window.__limusicAdBlockTick && "
                "window.__limusicAdBlockTick();",
                "runtime-tick",
            )
        if self.detached_mode:
            self._evaluate(DETACHED_PLAYER_STYLE_SCRIPT)
        self._poll_inflight = True
        try:
            self.webview.evaluate_javascript(
                PLAYER_STATE_SCRIPT,
                -1,
                None,
                None,
                None,
                self._on_player_state_result,
                None,
            )
        except Exception:
            self._poll_inflight = False
        return GLib.SOURCE_CONTINUE

    def _on_player_state_result(self, webview, result, _user_data):
        self._poll_inflight = False
        try:
            value = webview.evaluate_javascript_finish(result)
            state = json.loads(value.to_string())
        except Exception:
            return
        if self.on_player_state is not None:
            self.on_player_state(state)

    def _reapply_adblock(self):
        if self.adblock_enabled:
            self.apply_adblock()
        return GLib.SOURCE_REMOVE

    def _reapply_integrated_mode(self):
        if not self.detached_mode:
            self.apply_integrated_mode()
        return GLib.SOURCE_REMOVE

    def _reapply_detached_mode(self):
        if self.detached_mode:
            self._evaluate(DETACHED_PLAYER_STYLE_SCRIPT)
        return GLib.SOURCE_REMOVE

    def _on_create(self, source, _navigation_action):
        popup = WebKit.WebView(related_view=source)
        popup.connect("ready-to-show", self._show_popup)
        popup.connect("close", self._close_popup)
        return popup

    def _show_popup(self, webview):
        window = Gtk.Window(title="LiMusic – Anmeldung")
        window.set_default_size(520, 720)
        window.set_child(webview)
        window.connect("close-request", self._popup_window_closed, webview)
        self.popup_windows.append(window)
        window.present()

    def _close_popup(self, webview):
        for window in list(self.popup_windows):
            if window.get_child() == webview:
                window.close()
        return True

    def _popup_window_closed(self, window, _webview):
        if window in self.popup_windows:
            self.popup_windows.remove(window)
        return False

    def _on_load_changed(self, _webview, event):
        if event == WebKit.LoadEvent.STARTED:
            if self.on_status is not None:
                self.on_status(f"{self.site_label} wird geladen …")
        elif event == WebKit.LoadEvent.COMMITTED:
            if self.adblock_enabled:
                self._evaluate_adblock(
                    ADBLOCK_BOOTSTRAP_SCRIPT,
                    "scriptlet-engine-committed",
                )
        elif event == WebKit.LoadEvent.FINISHED:
            if self.adblock_enabled:
                self._evaluate_adblock(
                    ADBLOCK_BOOTSTRAP_SCRIPT,
                    "scriptlet-engine-finished",
                )
                self.apply_adblock()
                GLib.timeout_add(350, self._reapply_adblock)
                GLib.timeout_add(1200, self._reapply_adblock)
            if self.detached_mode:
                self._evaluate(DETACHED_PLAYER_STYLE_SCRIPT)
                GLib.timeout_add(350, self._reapply_detached_mode)
                GLib.timeout_add(1200, self._reapply_detached_mode)
            else:
                self.apply_integrated_mode()
                GLib.timeout_add(350, self._reapply_integrated_mode)
                GLib.timeout_add(1200, self._reapply_integrated_mode)
            self._ensure_player_polling()
            if self.on_status is not None:
                self.on_status(f"{self.site_label} bereit")

    def _on_title_changed(self, webview, _pspec):
        if self.on_title is not None:
            self.on_title(webview.get_title() or self.site_label)
