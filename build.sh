#!/usr/bin/env bash
# Nebula Linux ISO build — runs INSIDE an Arch Linux container (see build.ps1).
set -euo pipefail

SRC=/src
WORK=/build
OUT=/out
PROFILE="$WORK/profile"

echo ">> Installing build tools..."
pacman-key --init >/dev/null 2>&1 || true
pacman -Syu --noconfirm --needed archiso rsync librsvg base-devel git sudo

# ── Calamares: not in official repos, build once from AUR and cache it ──────
PKGCACHE="$OUT/pkgcache"
mkdir -p "$PKGCACHE"
if ! ls "$PKGCACHE"/calamares-*.pkg.tar.* >/dev/null 2>&1; then
    echo ">> Building Calamares from AUR (first time only, this is slow)..."
    useradd -m builder 2>/dev/null || true
    echo 'builder ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/builder
    sudo -u builder bash -c '
        set -e
        cd ~
        rm -rf calamares
        git clone --depth 1 https://aur.archlinux.org/calamares.git
        cd calamares
        makepkg -s --noconfirm --skippgpcheck
    '
    cp /home/builder/calamares/calamares-*.pkg.tar.* "$PKGCACHE/"
else
    echo ">> Using cached Calamares package from $PKGCACHE"
fi
LOCALREPO="$WORK/local-repo"
mkdir -p "$LOCALREPO"
cp "$PKGCACHE"/calamares-*.pkg.tar.* "$LOCALREPO/"
repo-add "$LOCALREPO/nebula-local.db.tar.gz" "$LOCALREPO"/calamares-*.pkg.tar.*

echo ">> Copying releng profile as base..."
rm -rf "$PROFILE"
mkdir -p "$WORK"
cp -r /usr/share/archiso/configs/releng "$PROFILE"

echo ">> Overlaying Nebula airootfs..."
rsync -a "$SRC/profile/airootfs/" "$PROFILE/airootfs/"
# Strip any CRLF that snuck in from the Windows checkout (all overlay files are text).
find "$PROFILE/airootfs" -type f -exec sed -i 's/\r$//' {} +

echo ">> Appending desktop package list..."
sed 's/\r$//' "$SRC/profile/packages-extra.x86_64" >> "$PROFILE/packages.x86_64"
# releng ships the console-only VirtualBox utils; we ship the full (X) variant.
sed -i '/^virtualbox-guest-utils-nox$/d' "$PROFILE/packages.x86_64"

# Calamares from the local repo built above (build-time only; the repo entry
# lives in the profile pacman.conf, not in the live system's).
echo "calamares" >> "$PROFILE/packages.x86_64"
cat >> "$PROFILE/pacman.conf" <<EOF

[nebula-local]
SigLevel = Optional TrustAll
Server = file://$LOCALREPO
EOF

echo ">> Rebranding profile..."
sed -i \
    -e 's|^iso_name=.*|iso_name="nebula-linux"|' \
    -e 's|ARCH_|NEBULA_|g' \
    -e 's|^iso_publisher=.*|iso_publisher="Nebula Linux <https://github.com/nebula-linux>"|' \
    -e 's|^iso_application=.*|iso_application="Nebula Linux Live/Installer"|' \
    "$PROFILE/profiledef.sh"

# Make our scripts executable inside the image.
sed -i '/^file_permissions=(/a\  ["/usr/local/bin/nebula-live-setup"]="0:0:755"\n  ["/usr/local/bin/nebula-install"]="0:0:755"\n  ["/usr/local/bin/nebula-installer"]="0:0:755"\n  ["/usr/local/bin/nebula-target-cleanup"]="0:0:755"\n  ["/usr/local/bin/nebula"]="0:0:755"\n  ["/usr/local/bin/nebula-welcome"]="0:0:755"\n  ["/usr/local/bin/nebula-vm-setup"]="0:0:755"\n  ["/usr/share/nebula/nebula-welcome.py"]="0:0:755"' \
    "$PROFILE/profiledef.sh"

# Rebrand boot menus (GRUB, syslinux, systemd-boot — whatever the profile has).
grep -rl 'Arch Linux' "$PROFILE/grub" "$PROFILE/syslinux" "$PROFILE/efiboot" 2>/dev/null \
    | xargs -r sed -i 's/Arch Linux/Nebula Linux/g'

echo ">> Reworking services: NetworkManager instead of iwd/networkd, greetd session..."
SYS="$PROFILE/airootfs/etc/systemd/system"
# Drop releng's network stack enablement and root tty autologin.
find "$SYS" -type l \( \
    -name 'iwd.service' -o \
    -name 'systemd-networkd.service' -o \
    -name 'systemd-networkd.socket' -o \
    -name 'systemd-networkd-wait-online.service' \) -delete
rm -rf "$SYS/getty@tty1.service.d"

mkdir -p "$SYS/multi-user.target.wants"
ln -sf /usr/lib/systemd/system/NetworkManager.service "$SYS/multi-user.target.wants/NetworkManager.service"
ln -sf /usr/lib/systemd/system/bluetooth.service       "$SYS/multi-user.target.wants/bluetooth.service"
ln -sf /etc/systemd/system/nebula-live-setup.service   "$SYS/multi-user.target.wants/nebula-live-setup.service"
ln -sf /etc/systemd/system/nebula-vm-setup.service     "$SYS/multi-user.target.wants/nebula-vm-setup.service"
# greetd as the display manager, boot to graphical target.
ln -sf /usr/lib/systemd/system/greetd.service    "$SYS/display-manager.service"
ln -sf /usr/lib/systemd/system/graphical.target  "$SYS/default.target"

echo ">> Rendering wallpaper..."
BG="$PROFILE/airootfs/usr/share/backgrounds/nebula"
rsvg-convert -w 3840 -h 2160 -o "$BG/nebula.png" "$BG/nebula.svg"

echo ">> Rendering logos, icons and boot splash..."
NEB="$PROFILE/airootfs/usr/share/nebula"
ICONS="$PROFILE/airootfs/usr/share/icons/hicolor"
for s in 48 64 128 256 512; do
    mkdir -p "$ICONS/${s}x${s}/apps"
    rsvg-convert -w "$s" -h "$s" -o "$ICONS/${s}x${s}/apps/nebula-linux.png" "$NEB/logo.svg"
done
mkdir -p "$ICONS/scalable/apps" "$PROFILE/airootfs/usr/share/pixmaps"
cp "$NEB/logo.svg" "$ICONS/scalable/apps/nebula-linux.svg"
rsvg-convert -w 256 -h 256 -o "$PROFILE/airootfs/usr/share/pixmaps/nebula-linux.png" "$NEB/logo.svg"
rsvg-convert -w 256 -h 256 -o "$NEB/avatar.png" "$NEB/logo.svg"
# GRUB menu background for installed systems.
rsvg-convert -w 1920 -h 1080 -o "$BG/nebula-grub.png" "$BG/nebula.svg"
# BIOS boot menu: background image only (syslinux vesamenu wants 640x480).
if [[ -d "$PROFILE/syslinux" ]]; then
    rsvg-convert -w 640 -h 480 -o "$PROFILE/syslinux/splash.png" "$BG/nebula.svg"
fi
# Calamares branding images.
CALBRAND="$PROFILE/airootfs/etc/calamares/branding/nebula"
rsvg-convert -w 128 -h 128 -o "$CALBRAND/logo.png" "$NEB/logo.svg"
rsvg-convert -w 256 -h 256 -o "$CALBRAND/welcome.png" "$NEB/logo.svg"
rsvg-convert -w 800 -h 450 -o "$CALBRAND/slide.png" "$BG/nebula.svg"

echo ">> Running mkarchiso (grab a coffee)..."
mkdir -p "$OUT"
mkarchiso -v -w /tmp/archiso-work -o "$OUT" "$PROFILE"

echo ">> Build complete:"
ls -lh "$OUT"/*.iso
