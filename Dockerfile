FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive

# Change Debian mirror to bypass potential CDN blocks
RUN echo "deb http://ftp.us.debian.org/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb http://ftp.us.debian.org/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb http://security.debian.org/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    rm -f /etc/apt/sources.list.d/debian.sources

# Install dependencies required for live-build
RUN apt-get update && \
    apt-get install -y \
    live-build \
    debootstrap \
    squashfs-tools \
    xorriso \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# Create a working directory
WORKDIR /build

# Copy the build script and branding assets into the container
COPY docker_build.sh /build/docker_build.sh
COPY assets /build/assets
COPY nebula_welcome.py /build/nebula_welcome.py
RUN chmod +x /build/docker_build.sh

# Run the build script when the container starts
CMD ["/build/docker_build.sh"]
