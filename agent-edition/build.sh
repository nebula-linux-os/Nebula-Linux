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

# 2. Fix ownership + permissions on files we shipped
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
