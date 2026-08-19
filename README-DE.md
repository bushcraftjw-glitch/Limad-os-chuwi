# LiMaD OS 3.0 RC1 BASE1 V23

## Technische Basis

V23 baut konservativ auf dem funktionierenden V22-Unterbau auf. Installationsquelle bleibt Ubuntu 26.04 Desktop FULL. Canonicals Kernel-, Treiber-, EFI-/Secure-Boot- und OEM-/Drittanbieter-Treiberlogik wird nicht ersetzt.

Die bestehenden V22-Bereiche für Dock, WhiteSur/LiMaD-Design, GNOME 50, LiLink, LiDrop, LiMusic 0.3.22, EasyEffects, Zen Browser, Fensterbuttons und den nur auf Apple `iMac17,1` aktiven Radeon-CIK-Kompatibilitätspfad bleiben unverändert. V23 ergänzt isoliert LiView 1.0.0.

## LiView 1.0.0

LiView ist die native LiMaD-Dateivorschau. Sie wird als `/usr/bin/liview` mit App-ID `de.limad.LiView` ausgeliefert und ist nach der Installation systemweit Standardanwendung für alle von LiView registrierten MIME-Typen.

Unterstützt werden PDF, gängige und moderne Bildformate, Videoformate sowie STL, OBJ und 3MF. LiView enthält außerdem Bildbearbeitung, PDF-Markup, Formulare, handschriftliche Signaturen, OCR, Metadaten/Inspector, Passwortschutz, PDF-Optimierung/Komprimierung und sichere Schwärzung.

Das LiView-Icon wird in LiMaD- und hicolor-Größen von 16 bis 512 Pixel mitgeliefert. Das ausgewählte Design verwendet einen dunklen abgerundeten Hintergrund, ein weißes L und gestapelte violette Dokumentseiten.

## Offline-Abhängigkeiten

V23 lädt beim ISO-Build die vollständige Ubuntu-26.04-Abhängigkeitskette der LiView-Runtime in ein lokales DEB-Repository. Dieses Repository wird in die ISO unter `/limad/offline-packages/` eingebettet.

Während der Betriebssysteminstallation wird die Abhängigkeitskette ausschließlich aus diesem lokalen Repository in das Zielsystem installiert. Danach führt der Installer einen LiView-System-Selbsttest aus. Schlägt Installation oder Selbsttest fehl, gilt die Zielintegration als fehlgeschlagen; LiView wird nicht stillschweigend mit fehlenden Funktionen freigegeben.

Der Selbsttest prüft unter anderem GTK4, Poppler, pikepdf, Pillow/AVIF, HEIF-Komponenten, SVG, Tesseract Deutsch/Englisch, GStreamer/Video, Ghostscript, PDF-Bearbeitung, Formulare, Signaturen, Passwortschutz, Komprimierung, sichere Schwärzung und 3D/STL.

`limad-runtime-deps` bleibt nur als spätere Netzwerk-Reparaturschicht erhalten. Die reguläre Neuinstallation von LiMaD OS benötigt für LiView nach dem ISO-Build keine Runtime-Downloads.

## LiView MIME-Standardzuordnung

V23 aktualisiert `shared-mime-info` und Desktop-Datenbank und erzeugt systemweite Zuordnungen in `/etc/xdg/mimeapps.list`. LiView wird für alle im Desktop-Launcher deklarierten PDF-, Bild-, Video- und 3D-MIME-Typen als Standard gesetzt. Bestehende Zuordnungen anderer Typen werden nicht global überschrieben.

## LiMaD Design

- Dock unten, kompakt und mittig
- LiMaD Icon Theme V3.2 plus hicolor-Fallback
- WhiteSur GTK3 systemweit, gepinnt auf Commit `1b356fe48ad5d05fb2ca6be071efe6801df3ac72`
- GTK4/libadwaita bleibt auf dem stabilen Ubuntu-Unterbau; LiMaD setzt nur den bestehenden Fensterbutton-Override
- Fensterbuttons links: `close,minimize,maximize:`
- LiMaD-Menü als GNOME-50-Erweiterung oben links
- LiLink/LiDrop als systemweite GNOME-50-Erweiterungen
- drei LiMaD-4K-Hintergrundbilder, Wallpaper 01 als Standard
- GDM/Plymouth-Branding wie im stabilen V22-Unterbau
- ISO-Volume-ID: `LIMAD_OS_3_0_RC1`

## Installer-Branding

Der Canonical-Installer-Snap wird nicht geforkt oder verändert. Die vorhandene Whitelabel-Integration bleibt bestehen. Zusätzlich wird das lokale LiView-Paketrepository aus `/cdrom/limad/offline-packages/` in das Zielsystem kopiert und vor Abschluss der Installation verarbeitet.

## Apple iMac17,1 / Radeon R9 M380 Mac Edition

Der vorhandene V22-Kompatibilitätspfad bleibt unverändert. Nur bei erkanntem `iMac17,1` werden beim Live-Boot und im installierten System verwendet:

`radeon.cik_support=1 amdgpu.cik_support=0`

Die gepinnten Radeon-Bonaire-Firmwaredateien bleiben Bestandteil des frühen initramfs und des Zielsystems.

## GitHub

Repository: `bushcraftjw-glitch/Limad-os-chuwi`

Release-Tag:

`base1-ubuntu2604-full-whitesur-v23`

ISO:

`LiMaD-OS-3.0-RC1-BASE1-UBUNTU-26.04-FULL-WHITESUR-V23-amd64.iso`
