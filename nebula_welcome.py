#!/usr/bin/env python3
import sys
import subprocess
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class WelcomeApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Welcome to Nebula Linux')
        self.setFixedSize(650, 450)
        self.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4;")

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Welcome to Nebula Linux")
        title.setFont(QFont("Arial", 28, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Your journey begins here. Fast, beautiful, and secure.")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # Get system info via fastfetch
        try:
            info = subprocess.check_output(['fastfetch', '--logo', 'none', '--pipe'], text=True)
            info_label = QLabel(info)
            info_label.setFont(QFont("Courier", 10))
            info_label.setAlignment(Qt.AlignCenter)
            info_label.setStyleSheet("color: #a6e3a1;")
            layout.addWidget(info_label)
        except Exception:
            pass

        # Force KDE to apply the Nebula wallpaper upon first boot
        try:
            subprocess.run(['plasma-apply-wallpaperimage', '/usr/share/wallpapers/Nebula/contents/images/1920x1080.png'], check=False)
        except Exception:
            pass

        layout.addSpacing(20)

        btn_layout = QHBoxLayout()
        
        btn_software = QPushButton("Open App Store (Discover)")
        btn_software.setStyleSheet("background-color: #89b4fa; color: #11111b; padding: 12px; font-weight: bold; border-radius: 5px;")
        btn_software.clicked.connect(lambda: subprocess.Popen(["plasma-discover"]))
        
        btn_close = QPushButton("Close")
        btn_close.setStyleSheet("background-color: #f38ba8; color: #11111b; padding: 12px; font-weight: bold; border-radius: 5px;")
        btn_close.clicked.connect(self.close)

        btn_layout.addWidget(btn_software)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = WelcomeApp()
    ex.show()
    sys.exit(app.exec_())
