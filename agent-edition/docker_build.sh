#!/usr/bin/env bash
# Host-side entry: builds the Docker image (from the REPO ROOT context so
# both agent-edition/ and nebula-agent/ get baked in), then runs it to
# produce the ISO. The ISO comes back to the host via `docker cp` — we
# don't use runtime bind-mounts because Windows paths with spaces silently
# break docker -v mounts (the same trap that broke the Arch build).
#
# Usage:
#   ./docker_build.sh                  # build image, then build ISO
#   ./docker_build.sh --rebuild        # force full image rebuild
#   ./docker_build.sh --shell          # drop into a shell in the container

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${HERE}/.." && pwd)"
IMAGE="nebula-agent-edition-builder:latest"
CONTAINER="nebula-agent-build-$(date +%s)"
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

echo "==> Building Docker image (context: ${REPO_ROOT})"
docker build ${FORCE} \
    -t "${IMAGE}" \
    -f "${HERE}/Dockerfile" \
    "${REPO_ROOT}"

if [ "${MODE}" = "shell" ]; then
    docker run --rm -it --privileged --name "${CONTAINER}" "${IMAGE}" /bin/bash
    exit 0
fi

echo "==> Running live-build inside the container"
# --privileged is needed for lb build (mount, chroot, loop devices).
# We keep the container after exit so we can docker cp the ISO out.
docker run --privileged --name "${CONTAINER}" "${IMAGE}" || {
    rc=$?
    echo "!! Container exited with code ${rc}. Inspect with: docker logs ${CONTAINER}"
    exit ${rc}
}

echo "==> Copying ISO out of container"
docker cp "${CONTAINER}:/build/out/." "${OUT_DIR}/" || {
    echo "!! docker cp failed — the ISO may not have been produced."
    docker rm "${CONTAINER}" >/dev/null 2>&1 || true
    exit 1
}
docker rm "${CONTAINER}" >/dev/null 2>&1 || true

echo
echo "==> ISO available in ${OUT_DIR}"
ls -lh "${OUT_DIR}/"
