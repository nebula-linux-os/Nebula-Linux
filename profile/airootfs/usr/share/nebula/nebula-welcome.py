#!/usr/bin/env python3
"""Nebula Welcome — first-boot onboarding for Nebula Linux."""
import os
import subprocess
import sys

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

FLAG_DIR = os.path.expanduser("~/.config/nebula-welcome")
FLAG = os.path.join(FLAG_DIR, "autostart-disabled")
IS_LIVE = os.path.exists("/run/archiso")
LOGO = "/usr/share/nebula/logo.svg"

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
            "DankMaterialShell documentation", "danklinux.com/docs",
            "docs", lambda: run_detached(["xdg-open", "https://danklinux.com/docs/"]),
            button_label="Open"))
        links.add(self._button_row(
            "Nebula Linux on GitHub", "Report issues, contribute",
            "github", lambda: run_detached(
                ["xdg-open", "https://github.com/nebula-linux"]),
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
        super().__init__(application_id="org.nebulalinux.Welcome",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.get_active_window() or WelcomeWindow(self)
        win.present()


if __name__ == "__main__":
    if "--autostart" in sys.argv and os.path.exists(FLAG):
        sys.exit(0)
    sys.exit(WelcomeApp().run([a for a in sys.argv if a != "--autostart"]))
