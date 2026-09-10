# Nebula Agent Edition (ISO)

An Ubuntu 24.04 + XFCE live/installable ISO with Nova
([nebula-agent](../nebula-agent)) and Ollama pre-installed. Boots to a
lightweight desktop, walks the user through pulling a starter model on
first login, and drops them into a working local-AI workstation.

## What's baked in

- **Ubuntu 24.04 (noble)** base — LTS, stable, driver-friendly.
- **XFCE desktop** — light, boring, ~2 GB RAM to run.
- **Ollama** installed system-wide as a systemd service on `127.0.0.1:11434`.
- **Nova** at `/opt/nebula-agent` with a system Python venv, wrapped by
  `/usr/local/bin/nebula-agent`.
- **First-boot script** pulls `qwen2.5:7b` and `nomic-embed-text`, then
  launches Nova's tray icon.
- **Autostart** — Nova's tray daemon starts on every login after first boot.
- **Calamares** graphical installer for putting it on disk.
- Firefox, Thunar, Mousepad, GParted, htop, and other everyday tools.
- **Nebula branding** — shared with the Arch edition: Plymouth boot
  splash (rotating orbit around a logo), custom GRUB theme, dark
  wallpaper, dark XFCE (Adwaita-dark), LightDM greeter with the
  Nebula backdrop.

## Build

Requires Docker on the host. Build produces `out/nebula-agent-edition-YYYY.MM.DD-x86_64.iso`.

```bash
cd agent-edition
./docker_build.sh                # first build takes ~40 min
./docker_build.sh --rebuild      # force fresh image
./docker_build.sh --shell        # drop into the container
```

The build mounts `../nebula-agent/` read-only into the container so
whatever's on disk gets baked into the ISO — no separate release step
needed. The container runs Debian live-build (`lb config` + `lb build`)
targeting Ubuntu's Noble archives.

## Layout

```
agent-edition/
├── Dockerfile              # debian:bookworm + live-build toolchain
├── build.sh                # inside-container entrypoint
├── docker_build.sh         # host-side entrypoint
├── config/
│   ├── auto/config         # lb config invocation (distro, mirrors, boot)
│   ├── package-lists/
│   │   ├── desktop.list.chroot     # XFCE + LightDM + firmware
│   │   ├── nova.list.chroot        # Python + system deps for Nova
│   │   └── utilities.list.chroot   # Firefox, Thunar, Calamares, etc.
│   ├── hooks/live/
│   │   ├── 0010-install-ollama.hook.chroot
│   │   ├── 0020-install-nova.hook.chroot
│   │   ├── 0030-services.hook.chroot
│   │   ├── 0040-defaults.hook.chroot
│   │   └── 0050-branding.hook.chroot
│   └── includes.chroot/
│       ├── etc/skel/.config/autostart/
│       │   ├── nebula-first-boot.desktop   # runs once at first login
│       │   └── nebula-agent.desktop        # launches tray on every login
│       ├── etc/systemd/system/ollama.service
│       ├── usr/local/bin/nebula-first-boot
│       └── usr/share/applications/nebula-agent.desktop
└── out/                    # ISO lands here
```

## First-boot flow

1. LightDM autologin drops the user into XFCE.
2. `nebula-first-boot.desktop` fires, calls `/usr/local/bin/nebula-first-boot`.
3. Script asks (via zenity) whether to pull the starter model.
4. Opens `xfce4-terminal` and runs `ollama pull qwen2.5:7b` +
   `ollama pull nomic-embed-text` so the user sees download progress.
5. Launches `nebula-agent --tray`.
6. Removes its own autostart entry so it never runs again.

From that point on, every login just starts the tray daemon (via
`nebula-agent.desktop`) and Ollama is already up on port 11434.

## Testing the ISO

```bash
# Boot in QEMU (needs 4+ GB RAM for the pull)
qemu-system-x86_64 -enable-kvm -m 6G -cdrom out/*.iso -boot d

# Or VirtualBox: New VM → Ubuntu (64-bit), 6 GB RAM, mount the ISO.
```

## Status

Scaffolded and reviewable, not yet built end-to-end. The build is Linux/
Docker-only — Windows dev host works via Docker Desktop, but the actual
ISO produced needs to be tested in a VM. First real build will surface
whatever's wrong with the package selection.
