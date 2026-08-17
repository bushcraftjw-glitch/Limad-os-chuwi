import Gio from 'gi://Gio';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import * as Util from 'resource:///org/gnome/shell/misc/util.js';

export default class LiLinkStatusExtension extends Extension {
    enable() {
        Util.spawnCommandLine('systemctl --user start limad-link.service');

        this._indicator = new PanelMenu.Button(0.0, 'LiLink', false);
        const icon = new St.Icon({
            gicon: Gio.icon_new_for_string(`${this.path}/lilink.svg`),
            style_class: 'system-status-icon',
        });
        this._indicator.add_child(icon);

        const openItem = new PopupMenu.PopupMenuItem('LiLink öffnen');
        openItem.connect('activate', () => Util.spawnCommandLine('/usr/local/bin/lilink'));
        this._indicator.menu.addMenuItem(openItem);

        const restartItem = new PopupMenu.PopupMenuItem('LiLink-Dienst neu starten');
        restartItem.connect('activate', () => Util.spawnCommandLine('systemctl --user restart limad-link.service'));
        this._indicator.menu.addMenuItem(restartItem);

        Main.panel.addToStatusArea(this.uuid, this._indicator);
    }

    disable() {
        this._indicator?.destroy();
        this._indicator = null;
    }
}
