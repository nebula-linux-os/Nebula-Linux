# Nebula Agent Edition — build container
# Runs Debian live-build inside a controlled environment so the ISO is
# reproducible regardless of the host OS.
#
# NOTE: this Dockerfile expects the REPO ROOT as build context, not
# agent-edition/. That lets us COPY nebula-agent/ into the image without
# any host-side runtime mount — which sidesteps the well-known "space
# in Windows path breaks Docker -v" trap that already burned the Arch
# build.
FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        live-build \
        debootstrap \
        squashfs-tools \
        xorriso \
        isolinux \
        syslinux-common \
        grub-pc-bin \
        grub-efi-amd64-bin \
        mtools \
        ca-certificates \
        wget \
        curl \
        git \
        rsync \
        sudo \
        python3 \
        python3-pip \
        librsvg2-bin \
        imagemagick \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Build context is the repo root. Pull in both the agent-edition
# directory (as /build) and the sibling nebula-agent/ (as /build/nebula-agent).
COPY agent-edition/ /build/
COPY nebula-agent/ /build/nebula-agent/

RUN chmod +x /build/build.sh

CMD ["/build/build.sh"]
