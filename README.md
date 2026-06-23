# 🌌 Nebula Linux

> Fast, Minimalist, and Beautiful. A custom, bleeding-edge Linux Distribution powered by Debian Trixie and KDE Plasma 6.

![Nebula Linux](assets/wallpaper.png)

## ✨ Features
- **Plasma 6 Architecture**: Built on the latest KDE Qt6 framework with native Wayland integration.
- **Ultra Minimalist**: Ships with the beautiful `arc-theme` and `papirus-dark` icon set out of the box.
- **Buttery Smooth**: Configured with 0.5x window animation speeds for an incredibly snappy experience.
- **Out of the Box Ready**: Pre-installed with Flatpak, Flathub, LibreOffice, Firefox, VLC, and native Wi-Fi drivers.
- **Custom Welcome App**: A Python-based welcome screen featuring `fastfetch` system information.

## 📥 Download
*Pre-compiled ISO coming soon to GitHub Releases / SourceForge!*

## 🛠️ Build it Yourself
You can compile your own custom version of Nebula Linux using our robust Docker build script.

### Prerequisites
- Windows, macOS, or Linux host.
- Docker Engine / Docker Desktop installed and running.

### Instructions
1. Clone this repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/nebula-linux.git
   cd nebula-linux
   ```
2. Place any custom images you want in the `assets/` folder (`splash.png` and `wallpaper.png`).
3. Run the automated Docker build script:
   ```bash
   docker build -t custom-os-builder .
   docker run --privileged -v "$PWD/output:/output" custom-os-builder
   ```
4. The final `.iso` will be generated in the `output/` folder!

## 📜 License
This project is open-source and free to use.
