# LiMaD OS 3.0 RC1 BASE1 V20

## Technische Basis

V20 baut auf dem bereits funktionierenden Ubuntu-26.04-FULL-Unterbau auf. Installationsquelle bleibt ausschließlich `ubuntu-desktop` FULL. Canonicals Kernel-, Treiber-, EFI-/Secure-Boot- und OEM-/Drittanbieter-Treiberlogik wird nicht ersetzt.

V20 ergänzt gezielt zwei Bereiche: sichtbares LiMaD-Branding und einen nur für Apple `iMac17,1` aktivierten Grafik-Kompatibilitätspfad.

## LiMaD Design

V20 ist ein gezielter Design-Repair auf Basis des V15-Desktopstands. Der Desktop-Core (dconf, Dock, Icons) ist installationskritisch und vom optionalen GDM/Plymouth-Branding getrennt. Die GNOME-Grundeinstellungen werden vor dem ersten Login als systemweite, nicht gesperrte dconf-Defaults installiert und danach in zwei Durchläufen verifiziert. LiLink/LiDrop sind vom Desktop-Core entkoppelt und können Dock, Icons oder Fensterdesign nicht mehr blockieren.

- Dock unten, kompakt und mittig; dconf-Default plus First-Login-Zweitpass
- LiMaD Icon Theme V3.2 plus hicolor-Fallback für alle 17 LiMaD-Launcher
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

Der Canonical-Installer-Snap wird nicht geforkt oder verändert. V20 nutzt die offizielle Whitelabel-Schnittstelle des Ubuntu Desktop Provision Installers:

- Fenstertitel: `LiMaD OS Installer`
- LiMaD-Logo auf unterstützten Installer-Seiten
- LiMaD-Akzentfarbe
- eigene deutsche und englische LiMaD-Installationsfolie mit kurzer Beschreibung des Betriebssystems

Die Whitelabel-Dateien werden beim Live-Boot über einen `casper-bottom`-Hook in die beschreibbare Live-Root nach `/usr/share/desktop-provision/` eingebracht. Damit liegen sie tatsächlich am vom Installer erwarteten Pfad, ohne das signierte Installer-Snap zu patchen.

## Apple iMac17,1 / Radeon R9 M380 Mac Edition

Der normale Ubuntu-Grafikpfad bleibt für alle anderen Geräte unverändert. Nur wenn GRUB per SMBIOS das Modell `iMac17,1` erkennt, ergänzt V20 beim Live-Boot:

`radeon.cik_support=1 amdgpu.cik_support=0`

Damit wird für dieses CIK-Gerät gezielt der ältere Radeon-Treiberpfad gewählt. Zusätzlich enthält V20 die gepinnten Radeon-Bonaire-Firmwaredateien aus `linux-firmware` Tag `20250509` sowohl früh im Live-initramfs als auch im installierten Zielsystem. Nach der Installation wird dieselbe Treiberauswahl nur auf `iMac17,1` unter `/etc/modprobe.d/` persistent gesetzt und anschließend das Ziel-initramfs aktualisiert.

Der ursprüngliche Canonical-initramfs-Inhalt bleibt erhalten und wird hinter einem kleinen unkomprimierten CPIO-Präfix weiterverwendet.

## Bekannte Einschränkung

LiDrop bleibt für Browser-, Smartphone- und lokale Geräteübertragung erhalten. Die experimentelle AirDrop/OpenDrop/OWL/AWDL-Kompatibilität wird in V20 bewusst vollständig aus Oberfläche, API und Systemkomponenten entfernt. LiLink besitzt in V20 zusätzlich einen systemweiten User-Service, Autostart und lokalen Health-Check.

## GitHub

Repository: `bushcraftjw-glitch/Limad-os-chuwi`

Release-Tag:

`base1-ubuntu2604-full-whitesur-v20`

ISO:

`LiMaD-OS-3.0-RC1-BASE1-UBUNTU-26.04-FULL-WHITESUR-V20-amd64.iso`


## V20 Design-Sicherungen

GTK4-Benutzerkonfiguration wird nicht gelöscht. LiMaD bindet nur `limad-titlebuttons.css` ein und lässt native Button-Geometrie unangetastet. Das LiMaD-Menü ersetzt links oben den Activities-Indikator, ohne eine zusätzliche Fremderweiterung einzuführen.
