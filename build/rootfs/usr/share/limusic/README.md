# LiMusic 0.3.27 Native Purple Preview

## Changes in 0.3.27

- YouTube and YouTube Music cookies are stored persistently in `~/.local/share/limusic/webkit-data/cookies.sqlite`.
- The original LiMusic headphone/note artwork is retained and only the opaque outer canvas is made transparent.
- The inconsistent generic `de.limad.LiMusic.svg` fallback is removed so it cannot replace the original artwork.
- YouTube search behavior is unchanged from 0.3.26.

## Changes in 0.3.26

- The app-level search field is hidden in the YouTube tab so the native YouTube search is the only visible search field there.
- The embedded YouTube WebView explicitly accepts keyboard focus and receives focus when the YouTube tab is opened.
- The existing YouTube Music app-level search activation typo is corrected.

## Changes in 0.3.25

- WebKitGTK is started with shared-memory DMA-BUF transport to avoid corrupted YouTube and YouTube Music rendering on affected Linux GPU/driver combinations.

## Changes in 0.3.23

- Closing the main window now terminates LiMusic when no detached player is active.

LiMusic 0.3.22 keeps the tested 0.3.3 GTK4/WebKitGTK/GStreamer playback logic unchanged and applies the LiMaD purple visual identity to the real application.

## Changes in 0.3.22

- Red/pink LiMusic accents changed to the LiMaD violet palette.
- Main window and detached player use the same purple controls, progress bars, volume sliders, hover states and glow.
- The approved purple headphone LiMusic artwork is included as the real application icon.
- Standard 64/128/256/512 px Linux hicolor PNG icons are installed in addition to the scalable fallback SVG.
- Sidebar branding uses the new purple headphone icon at compact size.
- Playback, YouTube integration, detached-player behavior and media control logic are intentionally unchanged from 0.3.3.

## Direkt testen

```bash
chmod +x START-LIMUSIC.sh diagnose.sh
./START-LIMUSIC.sh
```

## Benutzerlokal installieren

```bash
chmod +x install.sh
./install.sh
~/.local/bin/limusic
```

Danach erscheint `LiMusic` zusätzlich im GNOME-App-Menü.

## Diagnose

```bash
./diagnose.sh
```

Logdateien:

```text
~/.local/state/limusic/launcher.log
~/.local/state/limusic/limusic.log
```

## Deinstallation

```bash
./uninstall.sh
```

Die Deinstallation lässt die Mediathek und die gespeicherte YouTube-Sitzung bestehen.
