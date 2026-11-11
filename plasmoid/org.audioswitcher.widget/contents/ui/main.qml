import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents
import org.kde.plasma.plasma5support as P5Support
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root

    property var groups: []
    property string activeId: ""
    readonly property string ctl: "PATH=\"$HOME/.local/bin:$PATH\" audio-switcher-ctl"
    readonly property var activeGroup: groups.find(g => g.id === activeId) || null

    Plasmoid.icon: activeGroup ? activeGroup.icon : "audio-headset"
    toolTipMainText: "Audio Switcher"
    toolTipSubText: activeGroup ? activeGroup.name : "No group active"

    P5Support.DataSource {
        id: exec
        engine: "executable"
        connectedSources: []
        onNewData: (source, data) => {
            disconnectSource(source)
            if (source.indexOf(" list") !== -1 && data["exit code"] === 0) {
                try {
                    const r = JSON.parse(data["stdout"])
                    root.groups = r.groups
                    root.activeId = r.active
                } catch (e) {}
            }
        }
    }

    function refresh() { exec.connectSource(ctl + " list") }
    function apply(id) {
        exec.connectSource(ctl + " apply " + id)
        refreshTimer.restart()
    }

    Timer {
        id: refreshTimer
        interval: 800
        onTriggered: root.refresh()
    }
    Timer {
        interval: 3000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: root.refresh()
    }

    readonly property bool iconsOnly: Plasmoid.configuration.iconsOnly

    Plasmoid.onActivated: root.expanded = !root.expanded

    // Icons-only look: one button per group (row in panels, column on vertical panels)
    compactRepresentation: Item {
        id: compact
        readonly property bool vertical: Plasmoid.formFactor === PlasmaCore.Types.Vertical
        Layout.minimumWidth: iconsOnly ? strip.implicitWidth : Kirigami.Units.iconSizes.medium
        Layout.minimumHeight: iconsOnly ? strip.implicitHeight : Kirigami.Units.iconSizes.medium

        Kirigami.Icon {
            anchors.fill: parent
            visible: !root.iconsOnly
            source: Plasmoid.icon
            MouseArea { anchors.fill: parent; onClicked: root.expanded = !root.expanded }
        }
        GridLayout {
            id: strip
            anchors.centerIn: parent
            width: Math.min(parent.width, implicitWidth)
            height: Math.min(parent.height, implicitHeight)
            visible: root.iconsOnly
            flow: compact.vertical ? GridLayout.TopToBottom : GridLayout.LeftToRight
            rows: compact.vertical ? -1 : 1
            columns: compact.vertical ? 1 : -1
            columnSpacing: 2
            rowSpacing: 2
            Repeater {
                model: root.groups
                delegate: PlasmaComponents.ToolButton {
                    Layout.fillHeight: !compact.vertical
                    Layout.fillWidth: compact.vertical
                    icon.name: modelData.icon
                    checkable: true
                    checked: modelData.id === root.activeId
                    display: QQC2.AbstractButton.IconOnly
                    onClicked: root.apply(modelData.id)
                    PlasmaComponents.ToolTip { text: modelData.name }
                }
            }
        }
    }

    fullRepresentation: ColumnLayout {
        id: full
        Layout.preferredWidth: Kirigami.Units.gridUnit * 18
        Layout.minimumHeight: Kirigami.Units.gridUnit * 6
        spacing: Kirigami.Units.smallSpacing

        PlasmaComponents.Label {
            visible: root.groups.length === 0
            Layout.fillWidth: true
            Layout.margins: Kirigami.Units.largeSpacing
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            text: "No groups yet. Open Audio Switcher to create some."
            opacity: 0.7
        }

        Item {
            visible: root.iconsOnly
            Layout.fillWidth: true
            Layout.fillHeight: root.iconsOnly
            Layout.margins: Kirigami.Units.smallSpacing
            Flow {
                id: iconGrid
                readonly property real cellWidth: Math.min(parent.width,
                    Kirigami.Units.iconSizes.large + 2 * Kirigami.Units.largeSpacing)
                readonly property int columns: cellWidth > 0
                    ? Math.max(1, Math.floor((parent.width + spacing) / (cellWidth + spacing))) : 1
                anchors.centerIn: parent
                width: Math.max(0, Math.min(root.groups.length, columns) * (cellWidth + spacing) - spacing)
                height: childrenRect.height
                spacing: Kirigami.Units.smallSpacing
                Repeater {
                    model: root.iconsOnly ? root.groups : []
                    delegate: PlasmaComponents.ToolButton {
                        width: iconGrid.cellWidth
                        icon.name: modelData.icon
                        icon.width: Kirigami.Units.iconSizes.large
                        icon.height: Kirigami.Units.iconSizes.large
                        checkable: true
                        checked: modelData.id === root.activeId
                        display: QQC2.AbstractButton.IconOnly
                        onClicked: root.apply(modelData.id)
                        PlasmaComponents.ToolTip { text: modelData.name }
                    }
                }
            }
        }

        Repeater {
            model: root.iconsOnly ? [] : root.groups
            delegate: PlasmaComponents.ItemDelegate {
                Layout.fillWidth: true
                Layout.fillHeight: false
                highlighted: modelData.id === root.activeId
                icon.name: modelData.icon
                text: modelData.name
                onClicked: root.apply(modelData.id)

                PlasmaComponents.Label {
                    anchors.right: parent.right
                    anchors.rightMargin: Kirigami.Units.largeSpacing
                    anchors.verticalCenter: parent.verticalCenter
                    visible: modelData.id === root.activeId
                    text: "Active"
                    color: Kirigami.Theme.highlightColor
                }
            }
        }

        Item { visible: !root.iconsOnly; Layout.fillHeight: !root.iconsOnly }
    }
}
