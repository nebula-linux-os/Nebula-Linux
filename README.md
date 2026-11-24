# Nebula Linux — Beta 1.1

An Arch-based Linux distribution featuring
[Dux Modular Shell](https://github.com/duxlabs-dev/dux-shell) (DMS, formerly
DankMaterialShell — a Material 3 desktop shell built on Quickshell) running on
the **niri** scrollable-tiling Wayland compositor.

**New in Beta 1.1:** Dux Modular Shell 2.1 (formerly DankMaterialShell) with
the dux-greeter login screen, current Arch packages, no root SSH password login
on installed systems, and an EFI fallback loader so installs survive lost
firmware boot entries.

**New in Beta 1.0:** 4 curated wallpaper themes with instant matugen retuning,
Plymouth animated boot splash, full GRUB theme for installed systems,
`nebula wallpaper` and `nebula bugreport` CLI subcommands, wallpaper picker
in Nebula Welcome, and weekly auto-built ISOs via GitHub Actions.

> ⚠️ **UEFI required.** Legacy BIOS boot is not supported in Beta 1.1 —
> `grub-install`'s device-path canonicalization has a confirmed bug in this
> GRUB build when `/boot` is on its own partition (required for reliable
> btrfs booting; see [Desktop stack](#desktop-stack) below). UEFI installs
> use a different GRUB target (`x86_64-efi`) that doesn't hit this bug.
> The installer detects legacy BIOS mode and warns you before proceeding.
> Enable UEFI in your firmware/VM settings first.

```
 ███╗   ██╗███████╗██████╗ ██╗   ██╗██╗      █████╗
 ████╗  ██║██╔════╝██╔══██╗██║   ██║██║     ██╔══██╗
 ██╔██╗ ██║█████╗  ██████╔╝██║   ██║██║     ███████║
 ██║╚██╗██║██╔══╝  ██╔══██╗██║   ██║██║     ██╔══██║
 ██║ ╚████║███████╗██████╔╝╚██████╔╝███████╗██║  ██║
 ╚═╝  ╚═══╝╚══════╝╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝
              L  I  N  U  X
```

## Download

**[⬇ Download the ISO from SourceForge](https://sourceforge.net/projects/nebula-linux-arch-edition-niri/files/nebula-linux-2026.11.24-x86_64.iso/download)** (~2.1 GB)

`SHA256: 82c1b4caf120ad151ff78594504590d7ba38f8e5e7de8b685c3d203b59dee2e6`

This is **Beta 1.1** (November 24, 2026): Dux Modular Shell 2.1
(formerly DankMaterialShell), current Arch packages, and safer installs. See the
[release notes](https://github.com/nebula-linux-os/Nebula-Linux/releases/tag/arch-beta-1.1).
**Already on Beta 1.0?** Read the upgrade notes there before `pacman -Syu`:
the old login screen needs a one-time fix.

Flash it with [Rufus](https://rufus.ie) or [BalenaEtcher](https://etcher.balena.io), or boot it
in a VM (4+ GB RAM). Or [build it yourself](#building-the-iso).

## Screenshots

![Nebula Linux — fastfetch showing the Arch base on the niri compositor](screenshots/Homescreen.png)

| | |
|---|---|
| ![Desktop](screenshots/desktop.png) | ![Welcome app](screenshots/welcome.png) |
| The live desktop — DMS bar on niri | Nebula Welcome onboarding |
| ![Installer](screenshots/installer.png) | ![DMS settings](screenshots/settings-about.png) |
| Branded Calamares installer | DankMaterialShell settings |
| ![Desktop apps](screenshots/desktop-1.png) | ![Boot menu](screenshots/bootloader.png) |
| Apps on the scrollable-tiling desktop | Boot menu with nebula background |

## What you get

- **Live ISO** that boots straight into a full Dux Modular Shell desktop
  (niri + DMS) as user `nebula` — no login required.
- **Nebula branding everywhere**: os-release, hostname, boot menus + BIOS boot
  splash, MOTD, TTY login prompt, logo (hicolor icons + pixmaps, shown in DMS
  Settings → About), default wallpaper (also the lock screen background, and
  matugen derives the whole Material color scheme from it), lock-screen user
  avatar, fastfetch ASCII logo, installer banner. The installer also rebrands
  the target's bootloader (systemd-boot entries / `GRUB_DISTRIBUTOR`).
- **Installer**: launch **"Install Nebula Linux"** from the app launcher
  (Super+Space) — a fully Nebula-branded **Calamares** GUI that installs by
  copying the live system, then strips the live-only pieces and sets up GRUB
  with the nebula background. (Calamares is built from the AUR during the ISO
  build and cached in `out\pkgcache-*\`.) A CLI fallback, `nebula-install`
  (archinstall wrapper), is also on the ISO.

## Desktop stack

| Component     | Package(s)                                          |
| ------------- | --------------------------------------------------- |
| Shell / UI    | `dux-shell` (Dux Modular Shell / DMS from Arch extra) |
| Compositor    | `niri` + `xwayland-satellite`                        |
| Login         | `greetd` (autologin in live session)                 |
| Audio         | PipeWire + WirePlumber                               |
| Network       | NetworkManager, bluez                                |
| Terminal      | `foot` (CPU-rendered — works in VMs)                 |
| Apps          | Firefox, Nautilus, LibreOffice, Celluloid (video), Loupe, Evince, File Roller, Calculator, Text Editor |
| Theming       | `matugen` (wallpaper-based Material colors) + adw-gtk3-dark, Papirus icons, qt6ct |
| Installer     | Calamares (Nebula-branded, AUR-built at ISO build time) |
| Snapshots     | btrfs by default + snapper + snap-pac + grub-btrfs (boot old snapshots from GRUB) |
| Login         | DMS graphical greeter (`dux-greeter-bin`, AUR-built at ISO build time) on installed systems (`nebula greeter <dms\|text>` to switch) |
| Onboarding    | Nebula Welcome app (install, niri tour, app bundles, Flathub) |
| Control       | `nebula` CLI: update / snapshots / rollback / drivers / doctor / windows / wallpaper / bugreport |
| Themes        | 4 bundled wallpaper themes (`nebula wallpaper list`) — matugen retunes the whole desktop on switch |
| Boot splash   | Plymouth "nebula" theme with orbiting singularity animation (installed systems, silent boot) |
| GRUB theme    | Branded GRUB menu for installed systems (background, logo, wordmark, selection pixmaps) |
| Window modes  | scrollable tiling by default; `nebula windows floating` for classic windows (also a switch in Nebula Welcome) |
| VM support    | guest tools auto-start under QEMU/KVM, VirtualBox, VMware |
| Performance   | zram swap (zstd), fstrim timer |

## Building the ISO

`mkarchiso` only runs on Arch Linux, so the build happens inside a Docker
container. You need **Docker Desktop** (WSL2 backend) with ~15 GB free space.

```powershell
.\build.ps1
```

The first build downloads several GB of packages (a named Docker volume
`nebula-pacman-cache` caches them for subsequent builds). The finished ISO
lands in `out\nebula-linux-YYYY.MM.DD-x86_64.iso`.

Packages come from the live Arch mirrors. To build against a fixed
[Arch Linux Archive](https://archive.archlinux.org/) date instead, set
`$env:ARCH_SNAPSHOT = "YYYY/MM/DD"` before running `build.ps1` (the date must
already have `dux-shell`).

Test it in a VM (Hyper-V, VirtualBox, VMware, or QEMU). Give it **4+ GB RAM**
and enable **EFI** if available. Boot, and the DMS desktop appears
automatically.

### Publishing to SourceForge

[upload.ps1](upload.ps1) writes `<iso>.sha256` next to the ISO and uploads both
to the SourceForge project's Files area with `scp` (password prompt, or an SSH
key added under SourceForge's *Shell Services*):

```powershell
$env:SF_USER = "your-sourceforge-username"
.\upload.ps1 -DryRun     # check the ISO, target and download URL
.\upload.ps1             # newest ISO in out\; -Iso <path> / -Folder <subdir> to override
```

Add `-SetDefault` (with `$env:SF_API_KEY` from *Account > Preferences*) to make
it the project's "Download Latest Version". Then update the download link and
SHA256 at the top of this README and in `docs/index.html`.

### Handy keys in the live session

| Key                | Action                        |
| ------------------ | ----------------------------- |
| `Super+Space`      | App launcher (Spotlight)      |
| `Super+Return`     | Terminal (foot)               |
| `Super+O`          | Overview                      |
| `Super+Q`          | Close window                  |
| `Super+,`          | DMS settings                  |
| `Super+Escape`     | Lock screen                   |
| `Super+Shift+/`    | Show all keybindings          |

## How the build works

1. `build.ps1` starts an `archlinux:latest` privileged container with this
   repo mounted read-only at `/src` and `out\` at `/out`.
2. `build.sh` (inside the container) installs `archiso`, copies the official
   **releng** profile, then:
   - overlays everything under [profile/airootfs/](profile/airootfs/) onto it,
   - appends [profile/packages-extra.x86_64](profile/packages-extra.x86_64) to the package list,
   - rebrands `profiledef.sh`, GRUB/syslinux boot menus (`Arch Linux` → `Nebula Linux`),
   - a [pacman hook](profile/airootfs/etc/pacman.d/hooks/zz-nebula-branding.hook)
     overwrites `/usr/lib/os-release` with [Nebula branding](profile/airootfs/usr/share/nebula/os-release)
     during pacstrap (and again on every future `filesystem` package upgrade),
   - swaps releng's iwd/systemd-networkd for NetworkManager, removes the
     root tty autologin, enables `greetd` + graphical target,
   - renders the wallpaper SVG to PNG,
   - runs `mkarchiso`.
3. The live ISO creates the `nebula` user at boot
   ([nebula-live-setup](profile/airootfs/usr/local/bin/nebula-live-setup)) and
   greetd autologs it into `niri-session`; niri spawns `dms run`.

## Repo layout

```
build.ps1                        Windows entry point (Docker)
build.sh                         Container-side build script
upload.ps1                       Upload ISO + SHA256 to SourceForge
profile/
  packages-extra.x86_64          Desktop packages appended to releng list
  airootfs/                      Files overlaid into the live filesystem
    etc/greetd/config.toml       Autologin session config
    etc/skel/.config/niri/       niri config (spawns DMS, keybinds)
    etc/systemd/system/          nebula-live-setup.service
    usr/lib/os-release           Nebula branding
    usr/local/bin/nebula-install     Installer wrapper (archinstall + nebulaize)
    usr/local/bin/nebula-live-setup  Live user creation
    usr/share/backgrounds/nebula/    Wallpaper (SVG, rendered at build time)
```

## Roadmap

- [x] Calamares graphical installer (AUR build + local pacman repo on the ISO)
- [x] DMS graphical greeter for installed systems (`dux-greeter-bin`, built from the AUR)
- [x] Snapshot rollback stack (btrfs + snapper + snap-pac + grub-btrfs)
- [x] Nebula Welcome onboarding app + niri tour
- [x] `nebula` control-center CLI
- [ ] `nebula-release` / `nebula-branding` pacman packages + own package repo
- [ ] Plymouth boot splash, GRUB theme for installed systems
- [ ] Custom Material icon theme & default DMS settings preset
- [ ] Hyprland edition (`dux-shell` on Hyprland)
- [ ] Weekly auto-built ISOs (GitHub Actions) + signed checksums
