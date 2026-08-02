#!/usr/bin/env python3
"""Nebula Welcome — first-boot onboarding for Nebula Linux."""
import json
import os
import subprocess
import sys

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

FLAG_DIR = os.path.expanduser("~/.config/nebula-welcome")
FLAG = os.path.join(FLAG_DIR, "autostart-disabled")
IS_LIVE = os.path.exists("/run/archiso")
LOGO = "/usr/share/nebula/logo.svg"
NIRI_CONFIG = os.path.expanduser("~/.config/niri/config.kdl")
REPO_URL = "https://github.com/nebula-linux-os/Nebula-Linux"
SITE_URL = "https://nebula-linux-os.github.io/Nebula-Linux/"
THEMES_MANIFEST = "/usr/share/backgrounds/nebula/themes/themes.json"
THEMES_DIR = "/usr/share/backgrounds/nebula/themes"

BUNDLES = {
    "Development": ["git", "base-devel", "code", "python"],
    "Gaming": ["lutris", "gamemode", "mangohud"],
    "Creative": ["gimp", "inkscape", "obs-studio"],
    "Internet & Chat": ["telegram-desktop", "qbittorrent", "discord"],
}

NIRI_TIPS = (
    ("Scrollable tiling", "Windows line up in an endless horizontal strip — "
     "no shrinking, no fighting for space. Scroll through them instead."),
    ("Super + Space", "Open the app launcher. Type a few letters, hit Enter."),
    ("Super + Return", "Open a terminal."),
    ("Super + ← / →", "Move between windows."),
    ("Super + O", "Bird's-eye overview of all workspaces."),
    ("Super + 1…9", "Jump between workspaces."),
    ("Super + ,", "Open DankMaterialShell settings (wallpaper, theming…)."),
    ("Super + Shift + /", "The full keybinding cheat sheet, any time."),
)


def run_detached(argv):
    try:
        subprocess.Popen(argv, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def run_in_terminal(shell_cmd):
    run_detached(["foot", "-e", "bash", "-lc",
                  shell_cmd + "; echo; read -rp 'Finished. Press Enter to close.'"])


def window_mode_is_floating():
    try:
        with open(NIRI_CONFIG, encoding="utf-8") as f:
            text = f.read()
        start = text.find("NEBULA-WINDOW-MODE-START")
        end = text.find("NEBULA-WINDOW-MODE-END")
        return start != -1 and "open-floating true" in text[start:end]
    except OSError:
        return False


class WelcomeWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Welcome to Nebula Linux")
        self.set_default_size(560, 720)

        page = Adw.PreferencesPage()

        # ── Header ──────────────────────────────────────────────
        header = Adw.PreferencesGroup()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                      margin_top=18, margin_bottom=6)
        if os.path.exists(LOGO):
            logo = Gtk.Picture.new_for_filename(LOGO)
            logo.set_size_request(-1, 96)
            logo.set_can_shrink(True)
            box.append(logo)
        title = Gtk.Label(label="Welcome to Nebula Linux")
        title.add_css_class("title-1")
        sub = Gtk.Label(label="A Material You desktop, powered by "
                              "DankMaterialShell and niri")
        sub.add_css_class("dim-label")
        box.append(title)
        box.append(sub)
        header.add(box)
        page.add(header)

        # ── Get started ─────────────────────────────────────────
        start = Adw.PreferencesGroup(title="Get started")
        if IS_LIVE:
            start.add(self._button_row(
                "Install Nebula Linux", "Set up Nebula on this computer",
                "installer", lambda: run_detached(["/usr/local/bin/nebula-installer"]),
                suggested=True))
        start.add(self._button_row(
            "Desktop settings", "Wallpaper, theming, widgets and more",
            "settings",
            lambda: run_detached(["dms", "ipc", "call", "settings", "toggle"])))
        start.add(self._button_row(
            "Enable Flathub", "Add the Flatpak app store repository",
            "flathub",
            lambda: run_in_terminal(
                "sudo flatpak remote-add --if-not-exists flathub "
                "https://dl.flathub.org/repo/flathub.flatpakrepo && "
                "echo 'Flathub enabled.'")))
        page.add(start)

        # ── Wallpaper & theme ───────────────────────────────────
        themes = self._load_themes()
        if themes:
            theme_group = Adw.PreferencesGroup(
                title="Choose your theme",
                description="Wallpapers retune the whole desktop — bar, "
                            "launcher, apps and lock screen all recolor.")
            grid = Gtk.FlowBox(
                selection_mode=Gtk.SelectionMode.NONE,
                homogeneous=True,
                max_children_per_line=4,
                min_children_per_line=2,
                column_spacing=10,
                row_spacing=10,
                margin_top=6, margin_bottom=6,
                margin_start=6, margin_end=6)
            for t in themes:
                grid.append(self._theme_card(t))
            wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            wrap.append(grid)
            theme_group.add(wrap)
            page.add(theme_group)

        # ── Window behavior ─────────────────────────────────────
        windows = Adw.PreferencesGroup(
            title="Window behavior",
            description="Tiling is the Nebula default, but it's your desktop.")
        float_row = Adw.SwitchRow(
            title="Classic floating windows",
            subtitle="Open new windows floating instead of tiling them "
                     "(Super+Shift+Space toggles a single window any time)")
        float_row.set_active(window_mode_is_floating())
        float_row.connect("notify::active", self._on_float_toggle)
        windows.add(float_row)
        page.add(windows)

        # ── Learn niri ──────────────────────────────────────────
        learn = Adw.PreferencesGroup(
            title="Learn the desktop",
            description="niri works differently — in a good way.")
        for keys, tip in NIRI_TIPS:
            row = Adw.ActionRow(title=keys, subtitle=tip)
            learn.add(row)
        page.add(learn)

        # ── App bundles ─────────────────────────────────────────
        bundles = Adw.PreferencesGroup(
            title="App bundles",
            description="Optional extras, installed from the Arch repositories.")
        for name, pkgs in BUNDLES.items():
            bundles.add(self._button_row(
                name, ", ".join(pkgs), f"bundle-{name}",
                lambda p=pkgs: run_in_terminal(
                    "sudo pacman -S --needed " + " ".join(p)),
                button_label="Install"))
        page.add(bundles)

        # ── Links ───────────────────────────────────────────────
        links = Adw.PreferencesGroup(title="Help & community")
        links.add(self._button_row(
            "Nebula Linux website", "nebula-linux-os.github.io/Nebula-Linux",
            "website", lambda: run_detached(["xdg-open", SITE_URL]),
            button_label="Open"))
        links.add(self._button_row(
            "Nebula Linux on GitHub", "Report issues, contribute",
            "github", lambda: run_detached(["xdg-open", REPO_URL]),
            button_label="Open"))
        links.add(self._button_row(
            "DankMaterialShell documentation", "danklinux.com/docs",
            "docs", lambda: run_detached(["xdg-open", "https://danklinux.com/docs/"]),
            button_label="Open"))
        page.add(links)

        # ── Autostart toggle ────────────────────────────────────
        footer = Adw.PreferencesGroup()
        toggle = Adw.SwitchRow(title="Show this window on startup")
        toggle.set_active(not os.path.exists(FLAG))
        toggle.connect("notify::active", self._on_toggle)
        footer.add(toggle)
        page.add(footer)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(page)
        toolbar.set_content(scroll)
        self.set_content(toolbar)

    def _button_row(self, title, subtitle, _id, callback,
                    button_label="Open", suggested=False):
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        btn = Gtk.Button(label=button_label, valign=Gtk.Align.CENTER)
        if suggested:
            btn.add_css_class("suggested-action")
        btn.connect("clicked", lambda *_: callback())
        row.add_suffix(btn)
        row.set_activatable_widget(btn)
        return row

    @staticmethod
    def _load_themes():
        try:
            with open(THEMES_MANIFEST, encoding="utf-8") as f:
                return json.load(f).get("themes", [])
        except (OSError, ValueError):
            return []

    def _theme_card(self, theme):
        card = Gtk.Button()
        card.add_css_class("card")
        card.set_size_request(200, 160)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                      margin_top=8, margin_bottom=8,
                      margin_start=8, margin_end=8)

        path = os.path.join(THEMES_DIR, theme["file"])
        if os.path.exists(path):
            # Gtk.Picture with Gdk.Texture is the most reliable way to render
            # a bitmap thumbnail inside a Gtk4 Button — Gtk.Picture alone
            # collapses to zero size without a strong content-fit hint.
            try:
                texture = Gdk.Texture.new_from_filename(path)
                pic = Gtk.Picture.new_for_paintable(texture)
                pic.set_content_fit(Gtk.ContentFit.COVER)
                pic.set_size_request(180, 90)
                pic.set_can_shrink(True)
                pic.add_css_class("card")
                box.append(pic)
            except GLib.Error:
                placeholder = Gtk.Label(label="🖼️")
                placeholder.set_size_request(180, 90)
                box.append(placeholder)
        label = Gtk.Label(label=theme["name"])
        label.add_css_class("caption-heading")
        box.append(label)
        sub = Gtk.Label(label=theme.get("tagline", ""))
        sub.add_css_class("caption")
        sub.add_css_class("dim-label")
        sub.set_wrap(True)
        sub.set_max_width_chars(24)
        box.append(sub)

        card.set_child(box)
        card.connect("clicked", lambda btn, t=theme: self._apply_theme(btn, t))
        return card

    def _apply_theme(self, button, theme):
        # Provide visible feedback so the user knows the click landed.
        original = button.get_child()
        toast_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4,
                            margin_top=20, margin_bottom=20)
        toast_box.append(Gtk.Label(label=f"Applying {theme['name']}…"))
        spinner = Gtk.Spinner(spinning=True)
        toast_box.append(spinner)
        button.set_child(toast_box)
        button.set_sensitive(False)

        def finished(*_):
            button.set_child(original)
            button.set_sensitive(True)
            return False

        try:
            subprocess.Popen(
                ["/usr/local/bin/nebula", "wallpaper", "set", theme["id"]],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass
        # Restore the card after 1.5s so subsequent clicks work.
        GLib.timeout_add(1500, finished)

    @staticmethod
    def _on_float_toggle(row, _pspec):
        mode = "floating" if row.get_active() else "tiling"
        try:
            subprocess.run(["/usr/local/bin/nebula", "windows", mode],
                           check=False, timeout=10,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired):
            pass

    @staticmethod
    def _on_toggle(row, _pspec):
        os.makedirs(FLAG_DIR, exist_ok=True)
        if row.get_active():
            try:
                os.remove(FLAG)
            except FileNotFoundError:
                pass
        else:
            open(FLAG, "w").close()


class WelcomeApp(Adw.Application):
    def __init__(self):
        # NON_UNIQUE so every `nebula-welcome` invocation is a fresh window,
        # even if a previous instance's app registration is still lingering
        # in the DBus session. This is what makes "close then re-open" work.
        super().__init__(application_id="org.nebulalinux.Welcome",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)

    def do_activate(self):
        # Always present a fresh window — never reuse a torn-down one.
        WelcomeWindow(self).present()


if __name__ == "__main__":
    if "--autostart" in sys.argv and os.path.exists(FLAG):
        sys.exit(0)
    sys.exit(WelcomeApp().run([a for a in sys.argv if a != "--autostart"]))
