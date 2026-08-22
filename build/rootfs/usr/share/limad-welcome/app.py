#!/usr/bin/env python3
import gi, os, subprocess
gi.require_version("Gtk","4.0")
from gi.repository import Gtk
MARK=os.path.expanduser("~/.config/limad/welcome-3.0.done")
class App(Gtk.Application):
    def __init__(self): super().__init__(application_id="de.limad.Welcome")
    def do_activate(self):
        w=Gtk.ApplicationWindow(application=self,title="Willkommen bei LiMaD OS"); w.set_default_size(820,570)
        b=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=16); b.set_margin_top(32); b.set_margin_bottom(26); b.set_margin_start(34); b.set_margin_end(34)
        t=Gtk.Label(); t.set_markup("<span size='xx-large' weight='bold'>Willkommen bei LiMaD OS 3.0</span>"); t.set_xalign(0); b.append(t)
        p=Gtk.Label(label="Ihr LiMaD-System ist eingerichtet. Hier finden Sie die wichtigsten ersten Schritte."); p.set_xalign(0); b.append(p)
        grid=Gtk.Grid(column_spacing=12,row_spacing=12); grid.set_hexpand(True); grid.set_vexpand(True)
        items=[
            ("System aktualisieren","LiMaD OS und Systempakete auf den aktuellen Stand bringen.",["/usr/local/bin/limad-system-update"]),
            ("LiMaD Updates","Updates für LiMaD-Programme unabhängig vom Betriebssystem.",["/usr/local/bin/limad-updater"]),
            ("Systeminfo & Diagnose","Hardware, Firmware, Kernel und Diagnosebericht anzeigen.",["/usr/local/bin/limad-systeminfo"]),
            ("Wiederherstellung","Desktop, Paketsystem oder Bootloader reparieren.",["/usr/local/bin/limad-recovery"]),
            ("Einstellungen","WLAN, Bluetooth, Anzeige, Energie und Geräte konfigurieren.",["gnome-control-center"]),
            ("Dateien","Persönliche Dateien und Laufwerke öffnen.",["nautilus"]),
        ]
        for i,(title,desc,cmd) in enumerate(items):
            box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=5); box.set_margin_top(14); box.set_margin_bottom(14); box.set_margin_start(14); box.set_margin_end(14)
            l=Gtk.Label(); l.set_markup(f"<b>{title}</b>"); l.set_xalign(0); box.append(l)
            d=Gtk.Label(label=desc); d.set_xalign(0); d.set_wrap(True); box.append(d)
            bt=Gtk.Button(label="Öffnen"); bt.connect("clicked",lambda _b,c=cmd: subprocess.Popen(c)); box.append(bt)
            f=Gtk.Frame(); f.set_child(box); grid.attach(f,i%2,i//2,1,1)
        b.append(grid)
        bottom=Gtk.Box(spacing=10)
        again=Gtk.CheckButton(label="Beim nächsten Start wieder anzeigen")
        again.set_active(False); bottom.append(again)
        done=Gtk.Button(label="Los geht’s"); done.set_hexpand(True)
        def persist_choice():
            os.makedirs(os.path.dirname(MARK),exist_ok=True)
            if again.get_active():
                try: os.remove(MARK)
                except FileNotFoundError: pass
            else:
                with open(MARK,"w",encoding="utf-8") as marker: marker.write("done\n")
        def finish(_):
            persist_choice()
            w.close()
        def close_request(_window):
            persist_choice()
            return False
        done.connect("clicked",finish); bottom.append(done); b.append(bottom)
        w.connect("close-request",close_request)
        w.set_child(b); w.present()
App().run()
