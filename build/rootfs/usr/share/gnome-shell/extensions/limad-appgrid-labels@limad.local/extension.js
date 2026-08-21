import Pango from 'gi://Pango';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

export default class LiMaDAppGridLabelsExtension extends Extension {
    enable() {
        this._states = new Map();
        this._appDisplay = Main.overview._overview?.controls?.appDisplay ?? null;
        if (!this._appDisplay)
            return;

        this._viewLoadedId = this._appDisplay.connect('view-loaded', () => this._apply());
        this._apply();
    }

    disable() {
        if (this._appDisplay && this._viewLoadedId) {
            this._appDisplay.disconnect(this._viewLoadedId);
            this._viewLoadedId = 0;
        }

        for (const [item, state] of this._states ?? []) {
            const label = item.icon?.label ?? null;
            const clutterText = label?.clutter_text ?? null;
            if (!label || !clutterText)
                continue;

            item._expandTitleOnHover = state.expandTitleOnHover;
            label.remove_style_class_name('limad-app-grid-two-line');
            label.clip_to_allocation = state.clipToAllocation;
            clutterText.set({
                line_wrap: false,
                line_wrap_mode: Pango.WrapMode.NONE,
                ellipsize: Pango.EllipsizeMode.END,
            });
            item._updateMultiline?.();
        }

        this._states?.clear();
        this._states = null;
        this._appDisplay = null;
    }

    _apply() {
        for (const item of this._appDisplay?.getAllItems() ?? []) {
            const label = item.icon?.label ?? null;
            const clutterText = label?.clutter_text ?? null;
            if (!label || !clutterText)
                continue;

            if (!this._states.has(item)) {
                this._states.set(item, {
                    expandTitleOnHover: item._expandTitleOnHover,
                    clipToAllocation: label.clip_to_allocation,
                });
            }

            item._expandTitleOnHover = false;
            label.add_style_class_name('limad-app-grid-two-line');
            label.clip_to_allocation = true;
            clutterText.set({
                line_wrap: true,
                line_wrap_mode: Pango.WrapMode.WORD_CHAR,
                ellipsize: Pango.EllipsizeMode.END,
            });
        }
    }
}
