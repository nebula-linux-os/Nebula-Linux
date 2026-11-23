#!/usr/bin/env bash
# Nebula Linux ISO build — runs INSIDE an Arch Linux container (see build.ps1).
set -euo pipefail

SRC=/src
WORK=/build
OUT=/out
PROFILE="$WORK/profile"

# ── Package snapshot ────────────────────────────────────────────────────────
# By default the ISO is built from the live Arch mirrors. Set ARCH_SNAPSHOT
# to build against a fixed Arch Linux Archive date instead, so every package
# in the ISO (and Calamares, built below) comes from one consistent set.
# The snapshot must already carry dux-shell (Dux Modular Shell, the renamed
# DankMaterialShell 2.x); the 2026/09/03 snapshot used for the 1.5.3-based
# releases predates it and no longer works with this profile.
#
# Override: ARCH_SNAPSHOT=YYYY/MM/DD, or ARCH_SNAPSHOT=none (default).
ARCH_SNAPSHOT="${ARCH_SNAPSHOT:-none}"
if [[ "$ARCH_SNAPSHOT" != "none" ]]; then
    echo ">> Pinning packages to Arch Linux Archive snapshot $ARCH_SNAPSHOT"
    echo "Server = https://archive.archlinux.org/repos/$ARCH_SNAPSHOT/\$repo/os/\$arch" \
        > /etc/pacman.d/mirrorlist
    SYNC_FLAGS="-Syyuu"   # uu: allow downgrading the newer container image
    CACHE_TAG="${ARCH_SNAPSHOT//\//-}"
    # archive.archlinux.org is a single, often slow host: stalls trip
    # pacman's "Operation too slow" abort mid-mkarchiso. Don't time out,
    # and don't hammer it with parallel downloads. (Applied to the
    # profile's pacman.conf too, below.)
    ARCHIVE_PACMAN_OPTS=$'DisableDownloadTimeout\nParallelDownloads = 2'
    sed -i '/^#\?ParallelDownloads/d; /^\[options\]/r /dev/stdin' /etc/pacman.conf <<<"$ARCHIVE_PACMAN_OPTS"
else
    SYNC_FLAGS="-Syu"
    CACHE_TAG=""   # derived from library versions after the sync, below
fi

echo ">> Installing build tools..."
pacman-key --init >/dev/null 2>&1 || true
pacman "$SYNC_FLAGS" --noconfirm --needed archiso rsync librsvg base-devel git sudo

if [[ -z "$CACHE_TAG" ]]; then
    # Live mirrors: key the Calamares cache by the versions of the libraries
    # it links against, so a soname bump (boost, kpmcore, Qt, ICU, yaml-cpp)
    # forces a rebuild instead of shipping an installer that won't start.
    CACHE_TAG="live-$(pacman -Si qt6-base qt6-declarative kpmcore boost-libs yaml-cpp icu \
        | awk '/^Version/ {print $3}' | sha1sum | cut -c1-10)"
fi

# ── AUR packages: built here, served to mkarchiso from a local repo ─────────
useradd -m builder 2>/dev/null || true
echo 'builder ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/builder
AUR_BEFORE=""
if [[ "$ARCH_SNAPSHOT" != "none" ]]; then
    # Use PKGBUILDs as they were on the snapshot date, so their deps match.
    AUR_BEFORE="$(date -d "${ARCH_SNAPSHOT//\//-} + 1 day" +%Y-%m-%d)"
fi

# aur_build <pkgname> <destdir> [makepkg flags...]
# Builds an AUR package as the unprivileged builder user and copies the
# result (without the -debug split package) to <destdir>.
aur_build() {
    local pkg="$1" dest="$2"; shift 2
    sudo -u builder AUR_BEFORE="$AUR_BEFORE" PKG="$pkg" bash -s -- "$@" <<'EOS'
set -e
cd ~
rm -rf "$PKG"
git clone -q "https://aur.archlinux.org/$PKG.git"
cd "$PKG"
if [[ -n "$AUR_BEFORE" ]]; then
    rev=$(git rev-list -1 --before="$AUR_BEFORE" HEAD)
    if [[ -n "$rev" ]]; then
        echo ">> Using AUR $PKG PKGBUILD at $rev (before $AUR_BEFORE)"
        git checkout -q "$rev"
    else
        echo ">> AUR $PKG has no commit before $AUR_BEFORE; using its current PKGBUILD"
    fi
fi
makepkg --noconfirm "$@"
EOS
    find "/home/builder/$pkg" -maxdepth 1 -name "$pkg-*.pkg.tar.*" \
        ! -name "$pkg-debug-*" -exec cp {} "$dest/" \;
}

# Calamares: slow to build, so cache it. The cache is keyed by snapshot (or
# by library versions on live mirrors): a Calamares built against one set of
# Qt/kpmcore/boost libraries won't load against another.
PKGCACHE="$OUT/pkgcache-$CACHE_TAG"
mkdir -p "$PKGCACHE"
if ! ls "$PKGCACHE"/calamares-*.pkg.tar.* >/dev/null 2>&1; then
    echo ">> Building Calamares from AUR (once per library set, this is slow)..."
    aur_build calamares "$PKGCACHE" -s --skippgpcheck
else
    echo ">> Using cached Calamares package from $PKGCACHE"
fi

LOCALREPO="$WORK/local-repo"
rm -rf "$LOCALREPO"
mkdir -p "$LOCALREPO"
find "$PKGCACHE" -maxdepth 1 -name 'calamares-*.pkg.tar.*' ! -name 'calamares-debug-*' \
    -exec cp {} "$LOCALREPO/" \;

# DMS greeter (dms-greeter): dux-shell no longer ships it; upstream moved it
# to the AUR as dux-greeter-bin. It only repackages a prebuilt binary, so it
# is quick to rebuild every time (always the current AUR version) and needs
# none of its runtime deps (greetd, quickshell, qt6-declarative) at build time.
echo ">> Building dux-greeter-bin (DMS greeter) from AUR..."
aur_build dux-greeter-bin "$LOCALREPO" -d

repo-add "$LOCALREPO/nebula-local.db.tar.gz" "$LOCALREPO"/*.pkg.tar.*

echo ">> Copying releng profile as base..."
rm -rf "$PROFILE"
mkdir -p "$WORK"
cp -r /usr/share/archiso/configs/releng "$PROFILE"

echo ">> Overlaying Nebula airootfs..."
rsync -a "$SRC/profile/airootfs/" "$PROFILE/airootfs/"

# DMS shows a "What's New" dialog once per release line (2.1, 2.2, ...)
# unless ~/.config/dms/.changelog-<line> exists. Its own first-launch check
# would skip it, but our skel ships settings.json, so every new user (live
# and installed) would get it on first login. Seed the marker for the
# dux-shell line going into this ISO; a later upgrade to a new line still
# shows that line's notes.
DMS_LINE="$(pacman -Si dux-shell | awk '/^Version/ {print $3; exit}' | grep -oE '^[0-9]+\.[0-9]+')"
if [[ -n "$DMS_LINE" ]]; then
    mkdir -p "$PROFILE/airootfs/etc/skel/.config/dms"
    echo "$DMS_LINE" > "$PROFILE/airootfs/etc/skel/.config/dms/.changelog-$DMS_LINE"
    echo ">> Seeded DMS changelog marker for $DMS_LINE"
else
    echo ">> WARNING: could not read the dux-shell version; new users will see DMS's What's New dialog"
fi
# Strip any CRLF that snuck in from the Windows checkout — TEXT FILES ONLY.
# A naive `find … | sed -i` would corrupt binary content (PNGs, ICO, ...).
# `grep -Il ""` tests whether a file is textual before sed touches it.
find "$PROFILE/airootfs" -type f -print0 | \
    xargs -0 -I{} bash -c '
        f="$1"
        if grep -Iq "" "$f" 2>/dev/null; then
            sed -i "s/\r$//" "$f"
        fi
    ' _ {}

echo ">> Appending desktop package list..."
sed 's/\r$//' "$SRC/profile/packages-extra.x86_64" >> "$PROFILE/packages.x86_64"
# releng ships the console-only VirtualBox utils; we ship the full (X) variant.
sed -i '/^virtualbox-guest-utils-nox$/d' "$PROFILE/packages.x86_64"

# AUR packages from the local repo built above (build-time only; the repo
# entry lives in the profile pacman.conf, not in the live system's).
echo "calamares" >> "$PROFILE/packages.x86_64"
echo "dux-greeter-bin" >> "$PROFILE/packages.x86_64"
if [[ -n "${ARCHIVE_PACMAN_OPTS:-}" ]]; then
    sed -i '/^#\?ParallelDownloads/d; /^\[options\]/r /dev/stdin' "$PROFILE/pacman.conf" <<<"$ARCHIVE_PACMAN_OPTS"
fi
cat >> "$PROFILE/pacman.conf" <<EOF

[nebula-local]
SigLevel = Optional TrustAll
Server = file://$LOCALREPO
EOF

echo ">> Rebranding profile..."
sed -i \
    -e 's|^iso_name=.*|iso_name="nebula-linux"|' \
    -e 's|ARCH_|NEBULA_|g' \
    -e 's|^iso_publisher=.*|iso_publisher="Nebula Linux <https://nebula-linux-os.github.io/Nebula-Linux/>"|' \
    -e 's|^iso_application=.*|iso_application="Nebula Linux Live/Installer"|' \
    "$PROFILE/profiledef.sh"

# Make our scripts executable inside the image.
sed -i '/^file_permissions=(/a\  ["/usr/local/bin/nebula-live-setup"]="0:0:755"\n  ["/usr/local/bin/nebula-install"]="0:0:755"\n  ["/usr/local/bin/nebula-installer"]="0:0:755"\n  ["/usr/local/bin/nebula-target-cleanup"]="0:0:755"\n  ["/usr/local/bin/nebula"]="0:0:755"\n  ["/usr/local/bin/nebula-welcome"]="0:0:755"\n  ["/usr/local/bin/nebula-vm-setup"]="0:0:755"\n  ["/usr/local/bin/nebula-plymouth-setup"]="0:0:755"\n  ["/usr/share/nebula/nebula-welcome.py"]="0:0:755"' \
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

echo ">> Rendering Plymouth theme assets..."
PLY="$PROFILE/airootfs/usr/share/plymouth/themes/nebula"
mkdir -p "$PLY"
rsvg-convert -w 220 -h 220 -o "$PLY/logo.png"     "$NEB/logo.svg"
rsvg-convert -w 512 -h 512 -o "$PLY/orbit.png"    "$NEB/plymouth-orbit.svg"
rsvg-convert -w 420 -h  56 -o "$PLY/wordmark.png" "$NEB/plymouth-wordmark.svg"

echo ">> Rendering GRUB theme assets..."
GRUB_THEME="$PROFILE/airootfs/usr/share/grub/themes/nebula"
mkdir -p "$GRUB_THEME"
rsvg-convert -w 1920 -h 1080 -o "$GRUB_THEME/background.png" "$BG/nebula.svg"
# NOTE: this size MUST match the width/height declared for the "logo" image
# component in theme.txt. GRUB does not reliably scale image components to the
# declared box, so a mismatch makes the logo render at its native size and
# overlap whatever sits below it (this is what buried the wordmark).
rsvg-convert -w 96   -h 96   -o "$GRUB_THEME/logo.png"       "$NEB/logo.svg"

echo ">> Running mkarchiso (grab a coffee)..."
mkdir -p "$OUT"
mkarchiso -v -w /tmp/archiso-work -o "$OUT" "$PROFILE"

echo ">> Build complete:"
ls -lh "$OUT"/*.iso
