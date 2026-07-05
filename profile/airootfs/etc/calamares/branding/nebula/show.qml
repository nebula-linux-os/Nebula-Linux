import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation {
    id: presentation

    Timer {
        interval: 15000
        running: true
        repeat: true
        onTriggered: presentation.goToNextSlide()
    }

    Slide {
        anchors.fill: parent
        Image {
            source: "slide.png"
            anchors.fill: parent
            fillMode: Image.PreserveAspectCrop
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 48
            text: "Welcome to Nebula Linux"
            color: "#efe6ff"
            font.pixelSize: 30
            font.bold: true
        }
    }

    Slide {
        anchors.fill: parent
        Image {
            source: "slide.png"
            anchors.fill: parent
            fillMode: Image.PreserveAspectCrop
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 48
            text: "A Material You desktop — DankMaterialShell on niri"
            color: "#efe6ff"
            font.pixelSize: 24
        }
    }

    Slide {
        anchors.fill: parent
        Image {
            source: "slide.png"
            anchors.fill: parent
            fillMode: Image.PreserveAspectCrop
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 48
            text: "Office, media and everything you need — ready at first boot"
            color: "#efe6ff"
            font.pixelSize: 24
        }
    }
}
