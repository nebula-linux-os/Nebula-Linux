#!/usr/bin/env bash
# Host-side entry: builds the Docker image and runs it to produce the ISO.
# Usage:
#   ./docker_build.sh                  # build image, then build ISO
#   ./docker_build.sh --rebuild        # force full image rebuild
#   ./docker_build.sh --shell          # drop into a shell in the container

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${HERE}/.." && pwd)"
IMAGE="nebula-agent-edition-builder:latest"
OUT_DIR="${HERE}/out"

MODE="build"
FORCE=""
for arg in "$@"; do
    case "$arg" in
        --shell) MODE="shell" ;;
        --rebuild) FORCE="--no-cache" ;;
    esac
done

mkdir -p "${OUT_DIR}"

echo "==> Building Docker image"
docker build ${FORCE} -t "${IMAGE}" "${HERE}"

if [ "${MODE}" = "shell" ]; then
    docker run --rm -it --privileged \
        -v "${REPO_ROOT}/nebula-agent:/build/nebula-agent:ro" \
        -v "${OUT_DIR}:/build/out" \
        "${IMAGE}" /bin/bash
    exit 0
fi

echo "==> Running live-build inside the container"
docker run --rm --privileged \
    -v "${REPO_ROOT}/nebula-agent:/build/nebula-agent:ro" \
    -v "${OUT_DIR}:/build/out" \
    "${IMAGE}"

echo
echo "==> ISO available in ${OUT_DIR}"
ls -lh "${OUT_DIR}/"
