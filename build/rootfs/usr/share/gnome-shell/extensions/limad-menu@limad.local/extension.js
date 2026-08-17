import Gio from 'gi://Gio';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';

export default class LiMaDMenuExtension extends Extension {
    _spawn(argv) {
        try {
            Gio.Subprocess.new(argv, Gio.SubprocessFlags.NONE);
        } catch (error) {
            console.error(`${this.metadata.name}: ${error}`);
        }
    }

    enable() {
        this._activities = Main.panel.statusArea.activities ?? null;
        this._activities?.hide();

        this._indicator = new PanelMenu.Button(0.0, this.metadata.name, false);
        const icon = new St.Icon({
            gicon: Gio.icon_new_for_string('/usr/share/icons/LiMaD/24x24/apps/de.limad.Logo.png'),
            icon_size: 18,
            style_class: 'system-status-icon',
        });
        this._indicator.add_child(icon);

        this._indicator.menu.addAction('Über LiMaD OS', () => this._spawn(['/usr/local/bin/limad-systeminfo']));
        this._indicator.menu.addAction('Willkommen bei LiMaD', () => this._spawn(['/usr/local/bin/limad-welcome']));
        this._indicator.menu.addAction('Einstellungen', () => this._spawn(['/usr/bin/gnome-control-center']));
        this._indicator.menu.addAction('Dateien', () => this._spawn(['/usr/bin/nautilus', '--new-window']));
        this._indicator.menu.addAction('Terminal', () => this._spawn(['/usr/local/bin/limad-terminal']));
        this._indicator.menu.addAction('LiMaD Updates', () => this._spawn(['/usr/local/bin/limad-updater']));
        this._indicator.menu.addAction('Bildschirm sperren', () => this._spawn(['/usr/bin/loginctl', 'lock-session']));
        this._indicator.menu.addAction('Abmelden', () => this._spawn(['/usr/bin/gnome-session-quit', '--logout', '--no-prompt']));
        this._indicator.menu.addAction('Neustart', () => this._spawn(['/usr/bin/systemctl', 'reboot']));
        this._indicator.menu.addAction('Ausschalten', () => this._spawn(['/usr/bin/systemctl', 'poweroff']));

        Main.panel.addToStatusArea(this.uuid, this._indicator, 0, 'left');
    }

    disable() {
        if (!Main.sessionMode.isLocked)
            this._activities?.show();
        this._activities = null;
        this._indicator?.destroy();
        this._indicator = null;
    }
}
