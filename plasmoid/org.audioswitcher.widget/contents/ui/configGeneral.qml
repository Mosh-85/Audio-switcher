import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.FormLayout {
    property alias cfg_iconsOnly: iconsOnly.checked

    QQC2.CheckBox {
        id: iconsOnly
        Kirigami.FormData.label: "Appearance:"
        text: "Show only icons"
    }
}
