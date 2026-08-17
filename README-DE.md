# LiMaD OS 3.0 RC1 BASE1 V14

## Technische Basis

V14 baut auf dem bereits funktionierenden Ubuntu-26.04-FULL-Unterbau auf. Installationsquelle bleibt ausschließlich `ubuntu-desktop` FULL. Canonicals Kernel-, Treiber-, EFI-/Secure-Boot- und OEM-/Drittanbieter-Treiberlogik wird nicht ersetzt.

V14 ergänzt gezielt zwei Bereiche: sichtbares LiMaD-Branding und einen nur für Apple `iMac17,1` aktivierten Grafik-Kompatibilitätspfad.

## LiMaD Design

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

Der Canonical-Installer-Snap wird nicht geforkt oder verändert. V14 nutzt die offizielle Whitelabel-Schnittstelle des Ubuntu Desktop Provision Installers:

- Fenstertitel: `LiMaD OS Installer`
- LiMaD-Logo auf unterstützten Installer-Seiten
- LiMaD-Akzentfarbe
- eigene deutsche und englische LiMaD-Installationsfolie mit kurzer Beschreibung des Betriebssystems

Die Whitelabel-Dateien werden beim Live-Boot über einen `casper-bottom`-Hook in die beschreibbare Live-Root nach `/usr/share/desktop-provision/` eingebracht. Damit liegen sie tatsächlich am vom Installer erwarteten Pfad, ohne das signierte Installer-Snap zu patchen.

## Apple iMac17,1 / Radeon R9 M380 Mac Edition

Der normale Ubuntu-Grafikpfad bleibt für alle anderen Geräte unverändert. Nur wenn GRUB per SMBIOS das Modell `iMac17,1` erkennt, ergänzt V14 beim Live-Boot:

`radeon.cik_support=1 amdgpu.cik_support=0`

Damit wird für dieses CIK-Gerät gezielt der ältere Radeon-Treiberpfad gewählt. Zusätzlich enthält V14 die gepinnten Radeon-Bonaire-Firmwaredateien aus `linux-firmware` Tag `20250509` sowohl früh im Live-initramfs als auch im installierten Zielsystem. Nach der Installation wird dieselbe Treiberauswahl nur auf `iMac17,1` unter `/etc/modprobe.d/` persistent gesetzt und anschließend das Ziel-initramfs aktualisiert.

Der ursprüngliche Canonical-initramfs-Inhalt bleibt erhalten und wird hinter einem kleinen unkomprimierten CPIO-Präfix weiterverwendet.

## Bekannte Einschränkung

LiDrop bleibt für Browser-, Smartphone- und lokale Geräteübertragung erhalten. Die experimentelle AirDrop/OpenDrop/OWL/AWDL-Kompatibilität wird in V14 bewusst vollständig aus Oberfläche, API und Systemkomponenten entfernt. LiLink besitzt in V14 zusätzlich einen systemweiten User-Service, Autostart und lokalen Health-Check.

## GitHub

Repository: `bushcraftjw-glitch/Limad-os-chuwi`

Release-Tag:

`base1-ubuntu2604-full-whitesur-v14`

ISO:

`LiMaD-OS-3.0-RC1-BASE1-UBUNTU-26.04-FULL-WHITESUR-V14-amd64.iso`
