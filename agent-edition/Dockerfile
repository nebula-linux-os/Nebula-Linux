# Nebula Agent Edition — build container
# Runs Debian live-build inside a controlled environment so the ISO is
# reproducible regardless of the host OS. Same pattern as the Arch build,
# but targeting Ubuntu 24.04 + XFCE + Nova.
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
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY . /build/

RUN chmod +x /build/build.sh

CMD ["/build/build.sh"]
