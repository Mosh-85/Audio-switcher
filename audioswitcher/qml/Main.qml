import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: win
    title: "Audio Switcher"
    width: 760
    height: 520
    minimumWidth: 600
    minimumHeight: 400
    visible: false
    // Keep running in the tray when closed.
    onClosing: (close) => { close.accepted = false; win.hide() }

    property string selectedId: ""
    readonly property var selected: {
        for (const g of backend.groups)
            if (g.id === selectedId) return g
        return null
    }

    function indexOfDevice(list, name) {
        for (let i = 0; i < list.length; i++)
            if (list[i].name === name) return i
        return -1
    }

    readonly property var presetIcons: [
        "audio-headset", "audio-headphones", "audio-speakers", "audio-card",
        "audio-input-microphone", "video-display", "computer", "computer-laptop",
        "applications-games", "applications-multimedia", "preferences-system-bluetooth", "phone",
        "media-optical", "preferences-desktop-sound", "network-wireless", "starred-symbolic"
    ]
    property string currentIcon: "audio-headset"

    function groupById(id) {
        for (const g of backend.groups)
            if (g.id === id) return g
        return null
    }

    function loadForm() {
        const g = groupById(selectedId)
        currentIcon = g ? g.icon : "audio-headset"
        nameField.text = g ? g.name : ""
        sinkBox.currentIndex = g ? indexOfDevice(backend.sinks, g.sink) + 1 : 0
        sourceBox.currentIndex = g ? indexOfDevice(backend.sources, g.source) + 1 : 0
    }
    onSelectedIdChanged: loadForm()
    Component.onCompleted: if (backend.groups.length) selectedId = backend.groups[0].id

    header: ToolBar {
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            Label {
                text: "Audio groups"
                font.bold: true
                font.pixelSize: 16
                Layout.fillWidth: true
            }
            CheckBox {
                text: "Start at login"
                checked: backend.autostart
                onToggled: backend.setAutostart(checked)
            }
            ToolButton {
                icon.name: "view-refresh"
                text: "Refresh devices"
                display: AbstractButton.IconOnly
                ToolTip.visible: hovered
                ToolTip.text: "Refresh devices"
                onClicked: { backend.refreshDevices(); win.loadForm() }
            }
        }
    }

    SplitView {
        anchors.fill: parent
        anchors.margins: 12
        orientation: Qt.Horizontal

        // Group list (drag the divider to resize)
        ColumnLayout {
            SplitView.preferredWidth: 300
            SplitView.minimumWidth: 220
            SplitView.maximumWidth: win.width * 0.6
            spacing: 8

            ListView {
                id: list
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 6
                model: backend.groups
                delegate: ItemDelegate {
                    id: row
                    width: ListView.view.width
                    highlighted: modelData.id === win.selectedId
                    onClicked: win.selectedId = modelData.id
                    contentItem: RowLayout {
                        spacing: 6
                        ToolButton {
                            flat: true
                            icon.name: modelData.icon
                            icon.width: 22
                            icon.height: 22
                            display: AbstractButton.IconOnly
                            focusPolicy: Qt.NoFocus
                            onClicked: row.clicked()
                        }
                        Label {
                            text: modelData.name
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            font.bold: modelData.id === backend.activeId
                        }
                        Label {
                            visible: modelData.id === backend.activeId
                            text: "● active"
                            color: row.highlighted ? palette.highlightedText : palette.highlight
                        }
                        Button {
                            text: "Use"
                            enabled: modelData.id !== backend.activeId
                            onClicked: backend.applyGroup(modelData.id)
                        }
                    }
                }
                Label {
                    anchors.centerIn: parent
                    visible: list.count === 0
                    text: "No groups yet"
                    opacity: 0.6
                }
            }
            Button {
                Layout.fillWidth: true
                icon.name: "list-add"
                text: "New group"
                highlighted: true
                onClicked: win.selectedId = backend.addGroup()
            }
        }

        Frame {
            SplitView.fillWidth: true
            SplitView.minimumWidth: 300
            padding: 16
            leftPadding: 16

            ColumnLayout {
                anchors.fill: parent
                visible: win.selected !== null
                spacing: 12

                Label { text: "Name" }
                TextField {
                    id: nameField
                    Layout.fillWidth: true
                    placeholderText: "e.g. Headset"
                }
                Label { text: "Icon" }
                Button {
                    id: iconButton
                    icon.name: win.currentIcon
                    icon.width: 24
                    icon.height: 24
                    text: "Change icon…"
                    onClicked: iconPopup.opened ? iconPopup.close() : iconPopup.open()

                    Popup {
                        id: iconPopup
                        y: parent.height + 4
                        width: 340
                        padding: 12
                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
                        ColumnLayout {
                            width: parent.width
                            spacing: 10
                            GridLayout {
                                columns: 8
                                columnSpacing: 4
                                rowSpacing: 4
                                Repeater {
                                    model: win.presetIcons
                                    delegate: ToolButton {
                                        icon.name: modelData
                                        icon.width: 22
                                        icon.height: 22
                                        checkable: true
                                        checked: win.currentIcon === modelData
                                        onClicked: { win.currentIcon = modelData; iconPopup.close() }
                                        ToolTip.visible: hovered
                                        ToolTip.text: modelData
                                    }
                                }
                            }
                            TextField {
                                Layout.fillWidth: true
                                placeholderText: "Or type any icon name, press Enter"
                                onAccepted: if (text) { win.currentIcon = text; iconPopup.close() }
                            }
                        }
                    }
                }
                Label { text: "Output (speakers / headphones)" }
                ComboBox {
                    id: sinkBox
                    Layout.fillWidth: true
                    textRole: "description"
                    model: [{ name: "", description: "— Don't change —" }].concat(backend.sinks)
                }
                Label { text: "Input (microphone)" }
                ComboBox {
                    id: sourceBox
                    Layout.fillWidth: true
                    textRole: "description"
                    model: [{ name: "", description: "— Don't change —" }].concat(backend.sources)
                }
                Item { Layout.fillHeight: true }
                RowLayout {
                    Button {
                        icon.name: "edit-delete"
                        text: "Delete"
                        onClicked: {
                            const id = win.selectedId
                            win.selectedId = ""
                            backend.deleteGroup(id)
                            if (backend.groups.length) win.selectedId = backend.groups[0].id
                        }
                    }
                    Item { Layout.fillWidth: true }
                    Button {
                        icon.name: "document-save"
                        text: "Save"
                        onClicked: backend.saveGroup(win.selectedId, nameField.text,
                            sinkBox.model[sinkBox.currentIndex].name,
                            sourceBox.model[sourceBox.currentIndex].name,
                            win.currentIcon)
                    }
                    Button {
                        icon.name: "media-playback-start"
                        text: "Save && use"
                        highlighted: true
                        onClicked: {
                            backend.saveGroup(win.selectedId, nameField.text,
                                sinkBox.model[sinkBox.currentIndex].name,
                                sourceBox.model[sourceBox.currentIndex].name,
                                win.currentIcon)
                            backend.applyGroup(win.selectedId)
                        }
                    }
                }
            }
            Label {
                anchors.centerIn: parent
                visible: win.selected === null
                text: "Create a group to choose its output and input devices"
                opacity: 0.6
            }
        }
    }
}
