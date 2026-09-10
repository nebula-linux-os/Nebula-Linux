#!/usr/bin/env bash
# Nebula Agent Edition — live-build entrypoint
# Runs inside the build container; produces an ISO in ./out/.

set -euo pipefail

BUILD_ROOT="/build"
ISO_NAME="nebula-agent-edition-$(date +%Y.%m.%d)-x86_64.iso"
OUT_DIR="${BUILD_ROOT}/out"

echo "==> Nebula Agent Edition build"
echo "    output: ${OUT_DIR}/${ISO_NAME}"

# 1. Copy the current Nova source into the includes tree so it lands in
#    /opt/nebula-agent on the live system.
if [ -d "${BUILD_ROOT}/../nebula-agent" ]; then
    NOVA_SRC="${BUILD_ROOT}/../nebula-agent"
elif [ -d "${BUILD_ROOT}/nebula-agent" ]; then
    NOVA_SRC="${BUILD_ROOT}/nebula-agent"
else
    echo "!! nebula-agent source not found next to agent-edition/" >&2
    exit 1
fi

DEST_NOVA="${BUILD_ROOT}/config/includes.chroot/opt/nebula-agent"
mkdir -p "${DEST_NOVA}"
echo "==> Staging Nova source from ${NOVA_SRC}"
rsync -a \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'dist/' \
    --exclude 'build/' \
    --exclude '.venv/' \
    --exclude 'sessions/' \
    "${NOVA_SRC}/" "${DEST_NOVA}/"

# 2. Render brand assets — Plymouth logo/orbit/wordmark, GRUB bg + logo,
#    hicolor icons, pixmap, and the desktop wallpaper — all from SVG.
INCLUDES="${BUILD_ROOT}/config/includes.chroot"
BG="${INCLUDES}/usr/share/backgrounds/nebula"
NEB="${INCLUDES}/usr/share/nebula"
PLY="${INCLUDES}/usr/share/plymouth/themes/nebula"
GRUB_THEME="${INCLUDES}/usr/share/grub/themes/nebula"
ICONS="${INCLUDES}/usr/share/icons/hicolor"

echo "==> Rendering wallpaper"
rsvg-convert -w 3840 -h 2160 -o "${BG}/nebula.png" "${BG}/nebula.svg"

echo "==> Rendering hicolor icons"
for s in 48 64 128 256 512; do
    mkdir -p "${ICONS}/${s}x${s}/apps"
    rsvg-convert -w "$s" -h "$s" -o "${ICONS}/${s}x${s}/apps/nebula-linux.png" "${NEB}/logo.svg"
done
mkdir -p "${ICONS}/scalable/apps" "${INCLUDES}/usr/share/pixmaps"
cp "${NEB}/logo.svg" "${ICONS}/scalable/apps/nebula-linux.svg"
rsvg-convert -w 256 -h 256 -o "${INCLUDES}/usr/share/pixmaps/nebula-linux.png" "${NEB}/logo.svg"

echo "==> Rendering Plymouth theme"
rsvg-convert -w 220 -h 220 -o "${PLY}/logo.png"     "${NEB}/logo.svg"
rsvg-convert -w 512 -h 512 -o "${PLY}/orbit.png"    "${NEB}/plymouth-orbit.svg"
rsvg-convert -w 420 -h  56 -o "${PLY}/wordmark.png" "${NEB}/plymouth-wordmark.svg"

echo "==> Rendering GRUB theme"
rsvg-convert -w 1920 -h 1080 -o "${GRUB_THEME}/background.png" "${BG}/nebula.svg"
rsvg-convert -w   96 -h   96 -o "${GRUB_THEME}/logo.png"       "${NEB}/logo.svg"

# 3. Fix ownership + permissions on files we shipped.
#    Docker COPY strips executable bits on Windows-authored files, so we
#    have to re-apply them here or hooks silently skip and lb config
#    silently ignores auto/config.
chmod +x "${BUILD_ROOT}/auto/config"
chmod 755 "${BUILD_ROOT}/config/includes.chroot/usr/local/bin/"*
find "${BUILD_ROOT}/config/hooks" -name '*.hook.chroot' -exec chmod +x {} \;

# 3. Run live-build
cd "${BUILD_ROOT}"
echo "==> lb config"
lb config

echo "==> lb build (this takes a while)"
lb build

# 4. Move ISO to out/
mkdir -p "${OUT_DIR}"
if compgen -G "${BUILD_ROOT}/live-image-amd64.hybrid.iso" > /dev/null; then
    mv "${BUILD_ROOT}"/live-image-amd64.hybrid.iso "${OUT_DIR}/${ISO_NAME}"
elif compgen -G "${BUILD_ROOT}/binary.hybrid.iso" > /dev/null; then
    mv "${BUILD_ROOT}"/binary.hybrid.iso "${OUT_DIR}/${ISO_NAME}"
else
    echo "!! no ISO artifact found after lb build" >&2
    exit 2
fi

echo "==> Done: ${OUT_DIR}/${ISO_NAME}"
ls -lh "${OUT_DIR}/${ISO_NAME}"
