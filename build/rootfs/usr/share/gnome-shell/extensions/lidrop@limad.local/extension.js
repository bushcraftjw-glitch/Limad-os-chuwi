import Gio from 'gi://Gio';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import * as Util from 'resource:///org/gnome/shell/misc/util.js';

export default class LiDropStatusExtension extends Extension {
    enable() {
        this._indicator = new PanelMenu.Button(0.0, 'LiDrop', false);
        const icon = new St.Icon({
            gicon: Gio.icon_new_for_string(`${this.path}/lidrop.svg`),
            style_class: 'system-status-icon',
        });
        this._indicator.add_child(icon);

        const openItem = new PopupMenu.PopupMenuItem('LiDrop öffnen');
        openItem.connect('activate', () => Util.spawnCommandLine('/usr/local/bin/limad-drop'));
        this._indicator.menu.addMenuItem(openItem);

        Main.panel.addToStatusArea(this.uuid, this._indicator);
    }

    disable() {
        this._indicator?.destroy();
        this._indicator = null;
    }
}
