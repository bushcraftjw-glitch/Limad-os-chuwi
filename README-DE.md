# LiMaD OS 3.0 RC1 BASE1 V24

## Technische Basis

V24 baut auf dem stabilen V23-Unterbau mit Ubuntu 26.04 FULL auf. Installationsquelle bleibt ausschließlich `ubuntu-desktop` FULL. Canonicals Kernel-, Treiber-, EFI-/Secure-Boot- und OEM-/Drittanbieter-Treiberlogik wird nicht ersetzt.

V24 lässt Dock, Fensterbuttons, LiDrop/LiLink, LiMusic 0.3.22, LiView 1.0.0 und den vorhandenen nur für Apple `iMac17,1` aktivierten Grafik-Kompatibilitätspfad unverändert. Neu ist ein vollständiger Gaming-Stack mit Steam, Lutris, Wine/Winetricks, Protontricks, GameMode, MangoHud, Gamescope, Vulkan-Werkzeugen, vkBasalt und GOverlay. Die Ubuntu-Pakete werden inklusive amd64-/i386-Abhängigkeiten in die ISO eingebettet.


## LiView 1.0.0

LiView ist seit V23 eine native LiMaD-Systemanwendung. PDF, Bilder, Video sowie STL/OBJ/3MF werden direkt geöffnet. PDF-Markup, Formulare, Unterschriften, OCR, sichere Schwärzung und grundlegende Bildbearbeitung sind enthalten. Das ausgewählte LiMaD-Icon wird in LiMaD- und hicolor-Größen ausgeliefert.

Alle von LiView deklarierten MIME-Typen werden über `/etc/xdg/mimeapps.list` systemweit als Standard auf `de.limad.LiView.desktop` gesetzt. Für rohe H.264/H.265/VP8/VP9/AV1-, MPEG-M1V/M2V/M2P-, NUT- und Y4M-Dateien liefert LiMaD zusätzliche Shared-MIME-Info-Definitionen.

Die für LiView benötigten Ubuntu-26.04-Pakete werden beim ISO-Build aus dem signierten Ubuntu-Archiv samt Abhängigkeitsabschluss heruntergeladen, als lokales DEB-Repository in die ISO eingebettet und während der Zielinstallation ausschließlich aus diesem lokalen Repository installiert. Der Installer prüft anschließend Python/GTK4/Poppler/pikepdf/Pillow, SVG/HEIF, OCR, FFmpeg, Ghostscript und GStreamer.

LiView ist außerdem als `de.limad.LiView` im LiMaD-Updater registriert. Der Starter `/usr/local/bin/liview` verwendet dieselbe System-/Benutzer-Payload-Auswahl wie die bestehenden aktualisierbaren LiMaD-Apps, sodass spätere `*.limad-update.zip`-Versionen ohne Austausch des Systemstarters aktiviert und auf die Systemversion zurückgesetzt werden können.

## Gaming in V24

Steam und Lutris werden als Ubuntu-26.04-Systempakete installiert. Zusätzlich sind Protontricks, Wine/Winetricks, GameMode, MangoHud, Gamescope, Vulkan-Werkzeuge, Mesa-Vulkan für amd64 und i386, vkBasalt sowie GOverlay enthalten. `steam-installer` zieht dabei die Ubuntu-Metapakete `steam-libs` und `steam-libs-i386` samt 32-Bit-Laufzeit nach.

Valve Proton wird bewusst nicht als fest eingefrorene Fremdkopie in die ISO gelegt: Steam verwaltet die offiziellen Proton-Versionen selbst. ProtonUp-Qt (`net.davidotek.pupgui2`) wird wie EasyEffects über Flathub für den Benutzer eingerichtet und ermöglicht bei Bedarf zusätzliche Compatibility-Tools wie GE-Proton für Steam und Lutris.

Die Gaming-DEBs werden beim ISO-Build aus dem signierten Ubuntu-26.04-Archiv für `amd64` und `i386` samt Abhängigkeitsabschluss heruntergeladen. Während der Zielinstallation wird `i386` aktiviert und ausschließlich das lokale Gaming-Repository aus der ISO verwendet. Der Installationsschritt ist kritisch und prüft danach Steam, Lutris, Protontricks, Wine/Winetricks, GameMode, MangoHud, Gamescope und Vulkan-Werkzeuge.

EasyEffects bleibt als Flathub-App `com.github.wwmm.easyeffects`, weil LiMaD Klang den Flatpak-Pfad verwendet. V24 aktualisiert eine bereits benutzerseitig installierte EasyEffects-Version beim Einrichtungsdurchlauf, statt sie durch das ältere Ubuntu-Systempaket zu ersetzen.

## LiMaD Design

Der V22-Desktop-Core bleibt in V24 unverändert und eingefroren. Der Desktop-Core (dconf, Dock, Icons) ist installationskritisch und vom optionalen GDM/Plymouth-Branding getrennt. Die GNOME-Grundeinstellungen werden vor dem ersten Login als systemweite, nicht gesperrte dconf-Defaults installiert und danach in zwei Durchläufen verifiziert. LiLink/LiDrop sind vom Desktop-Core entkoppelt und können Dock, Icons oder Fensterdesign nicht mehr blockieren.

- Dock unten, kompakt und mittig; dconf-Default plus First-Login-Zweitpass
- LiMaD Icon Theme V3.2 plus hicolor-Fallback für alle 18 LiMaD-Launcher
- GTK4/libadwaita bleibt nativ; nur 12px Traffic-Light-SVGs werden auf die nativen Fensterknöpfe gelegt
- LiMaD-Menü als GNOME-50-Erweiterung oben links

- WhiteSur GTK3 systemweit, gepinnt auf Commit `1b356fe48ad5d05fb2ca6be071efe6801df3ac72`
- GTK4/libadwaita bleibt auf dem stabilen Ubuntu-Unterbau; LiMaD setzt nur einen kleinen rot/gelb/grünen Fensterbutton-Override, damit moderne GNOME-Apps keine Headerbar-Regressions bekommen
- LiLink/LiDrop GNOME-50-Statussymbole werden als systemweite GNOME-Shell-Erweiterungen mitgeliefert und beim ersten Login geprüft
- Fensterbuttons links: `close,minimize,maximize:`
- LiMaD Icon Theme V3.2
- drei LiMaD 4K-Hintergrundbilder, Wallpaper 01 als Standard
- Ubuntu Dock unten, kompakt und zentriert (`extend-height=false`, 60px Icons)
- GDM mit LiMaD-Logo und LiMaD-Lockscreen
- Plymouth basiert auf Ubuntus vorhandenem `spinner`-Theme; Branding wird nur aktiviert, wenn die erwartete Struktur vorhanden ist
- ISO-Volume-ID: `LIMAD_OS_3_0_RC1`
- sichtbare Ubuntu-GRUB-Menütitel werden zu `LiMaD OS`

## LiMaD Installer-Branding

Der Canonical-Installer-Snap wird nicht geforkt oder verändert. V22 nutzt die offizielle Whitelabel-Schnittstelle des Ubuntu Desktop Provision Installers:

- Fenstertitel: `LiMaD OS Installer`
- LiMaD-Logo auf unterstützten Installer-Seiten
- LiMaD-Akzentfarbe
- eigene deutsche und englische LiMaD-Installationsfolie mit kurzer Beschreibung des Betriebssystems

Die Whitelabel-Dateien werden beim Live-Boot über einen `casper-bottom`-Hook in die beschreibbare Live-Root nach `/usr/share/desktop-provision/` eingebracht. Damit liegen sie tatsächlich am vom Installer erwarteten Pfad, ohne das signierte Installer-Snap zu patchen.

## Apple iMac17,1 / Radeon R9 M380 Mac Edition

Der normale Ubuntu-Grafikpfad bleibt für alle anderen Geräte unverändert. Nur wenn GRUB per SMBIOS das Modell `iMac17,1` erkennt, ergänzt V22 beim Live-Boot:

`radeon.cik_support=1 amdgpu.cik_support=0`

Damit wird für dieses CIK-Gerät gezielt der ältere Radeon-Treiberpfad gewählt. Zusätzlich enthält V22 die gepinnten Radeon-Bonaire-Firmwaredateien aus `linux-firmware` Tag `20250509` sowohl früh im Live-initramfs als auch im installierten Zielsystem. Nach der Installation wird dieselbe Treiberauswahl nur auf `iMac17,1` unter `/etc/modprobe.d/` persistent gesetzt und anschließend das Ziel-initramfs aktualisiert.

Der ursprüngliche Canonical-initramfs-Inhalt bleibt erhalten und wird hinter einem kleinen unkomprimierten CPIO-Präfix weiterverwendet.

## Bekannte Einschränkung

LiDrop bleibt für Browser-, Smartphone- und lokale Geräteübertragung erhalten. Die experimentelle AirDrop/OpenDrop/OWL/AWDL-Kompatibilität wird in V22 bewusst vollständig aus Oberfläche, API und Systemkomponenten entfernt. LiLink besitzt in V22 zusätzlich einen systemweiten User-Service, Autostart und lokalen Health-Check.

## GitHub

Repository: `bushcraftjw-glitch/Limad-os-chuwi`

Release-Tag:

`base1-ubuntu2604-full-whitesur-v24`

ISO:

`LiMaD-OS-3.0-RC1-BASE1-UBUNTU-26.04-FULL-WHITESUR-V24-amd64.iso`


## V24 Sicherungen

GTK4-Benutzerkonfiguration wird nicht gelöscht. LiMaD bindet nur `limad-titlebuttons.css` ein und lässt native Button-Geometrie unangetastet. Das LiMaD-Menü ersetzt links oben den Activities-Indikator, ohne eine zusätzliche Fremderweiterung einzuführen.
