# LiMusic 0.3.22 Native Purple Preview

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
