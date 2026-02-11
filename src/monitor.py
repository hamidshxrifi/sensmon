import sys
import subprocess
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeWidgetItem
from PyQt6.QtCore import QSize, QTimer
from PyQt6 import uic
from PyQt6.QtGui import QIcon

import sensors
import nvidiaGPU

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.darkMode = True
        self.isCelcius = True

        self.hasNvidia = False
        self.nvidia = None

        self.components = sensors.HwmonManager()
        self.components.findDevices()
        self.sensorRows = {}
        self. nvRows = {}

        uic.loadUi('ui/monitor.ui', self)
        self.treeWidget.setSelectionMode(self.treeWidget.SelectionMode.NoSelection)
        self.treeWidget.setColumnWidth(0, 350)
        self.treeWidget.setIndentation(40)
        self.treeWidget.setIconSize(QSize(18, 18))
        self.resize(800,1000)

        self.actionExitProgram.triggered.connect(QApplication.quit)
        self.actionSwitchUnits.triggered.connect(self.switchUnits)
        self.actionSwitchTheme.triggered.connect(self.changeTheme)
        self.actionResetValues.triggered.connect(self.resetMinMax)

        self.hasNvidia = self.detectNvidia()
        if self.hasNvidia:
            self.nvidia = nvidiaGPU.NvManager()
            self.nvidia.refresh()
            for gpu in self.nvidia.gpus.values():
                self.addNvidiaEntry(gpu)

        for hwmon in self.components.hwmonx:
            self.addHwmonEntry(hwmon)

        self.timer = QTimer()
        self.timer.timeout.connect(self.updateValues)
        self.timer.start(1000)

    def detectNvidia(self) -> bool:
        try:
            subprocess.check_output(["nvidia-smi"], stderr = subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def addNvidiaEntry(self, gpu: nvidiaGPU.NvGPU) -> None:
        entry = QTreeWidgetItem([f"{gpu.model} (GPU {gpu.id})"])
        self.treeWidget.addTopLevelItem(entry)
        
        entryType = QTreeWidgetItem(["Temperature"])
        entryType.setIcon(0, QIcon('../assets/icons/Temperature.svg'))
        entry.addChild(entryType)
        unit = "°C" if self.isCelcius else "°F" 

        dataRow = QTreeWidgetItem([
            "Temperature",
            f"{self.convertTemp(gpu.temp.currentValue, self.isCelcius)} {unit}",
            f"{self.convertTemp(gpu.temp.minValue, self.isCelcius)} {unit}",
            f"{self.convertTemp(gpu.temp.maxValue, self.isCelcius)} {unit}"
        ])

        entryType.addChild(dataRow)
        self.nvRows[f"GPU{gpu.id}_temp"] = (dataRow, gpu)
        entryType.setExpanded(True)

        entryType = QTreeWidgetItem(["Power"])
        entryType.setIcon(0, QIcon('../assets/icons/Power.svg'))
        entry.addChild(entryType)

        dataRow = QTreeWidgetItem([
            "Power",
            f"{gpu.power.currentValue} W",
            f"{gpu.power.minValue} W",
            f"{gpu.power.maxValue} W"
        ])

        entryType.addChild(dataRow)
        self.nvRows[f"GPU{gpu.id}_pwr"] = (dataRow, gpu)
        entryType.setExpanded(True)

        clockEntry = QTreeWidgetItem(["Clock"])
        clockEntry.setIcon(0, QIcon('../assets/icons/Clock.svg'))
        entry.addChild(clockEntry)
        
        gcRow = QTreeWidgetItem([
            "Graphics",
            f"{gpu.graphicsClock.currentValue} MHz",
            f"{gpu.graphicsClock.minValue} MHz",
            f"{gpu.graphicsClock.maxValue} MHz"
        ])

        mcRow = QTreeWidgetItem([
            "Memory",
            f"{gpu.memoryClock.currentValue} MHz",
            f"{gpu.memoryClock.minValue} MHz",
            f"{gpu.memoryClock.maxValue} MHz"
        ])

        clockEntry.addChild(gcRow)
        clockEntry.addChild(mcRow)
        self.nvRows[f"GPU{gpu.id}_gc"] = (gcRow, gpu)
        self.nvRows[f"GPU{gpu.id}_mc"] = (mcRow, gpu)
        
        clockEntry.setExpanded(True)
        entry.setExpanded(True)

    def addHwmonEntry(self, hwmon: sensors.HwmonDevice) -> None:
        device = QTreeWidgetItem([hwmon.name])
        self.treeWidget.addTopLevelItem(device)
        sensType = ""
        entryType = QTreeWidgetItem([sensType])

        for sensor in hwmon.sensors:
            sensor.read()
            if sensor.sensType != sensType:
                entryType.setExpanded(True)
                sensType = sensor.sensType
                entryType = QTreeWidgetItem([sensType])
                entryType.setIcon(0, QIcon(f'../assets/icons/{sensType}.svg'))
                device.addChild(entryType)

            dataRow = self.createSensorRow(sensor)

            unique_id = f"{hwmon.id}_{sensor.label}"
            self.sensorRows[unique_id] = (dataRow, sensor)

            entryType.addChild(dataRow)

        device.setExpanded(True)
        entryType.setExpanded(True)

    def createSensorRow(self, sensor:sensors.Sensor) -> QTreeWidgetItem:
        tempDiv = 1000
        voltDiv = 1000
        clockDiv = 1000000

        if sensor.sensType == "Temperature":
            unit = "°C" if self.isCelcius else "°F" 
            return QTreeWidgetItem([
                sensor.label,
                f"{self.convertTemp(sensor.getCurrent()/tempDiv, self.isCelcius)} {unit}",
                f"{self.convertTemp(sensor.getMin()/tempDiv, self.isCelcius)} {unit}",
                f"{self.convertTemp(sensor.getMax()/tempDiv, self.isCelcius)} {unit}"
            ])

        elif sensor.sensType == "Voltage":
            return QTreeWidgetItem([
                sensor.label,
                f"{sensor.getCurrent()/voltDiv} V",
                f"{sensor.getMin()/voltDiv} V",
                f"{sensor.getMax()/voltDiv} V"
            ])

        elif sensor.sensType == "Clock":
            return QTreeWidgetItem([
                sensor.label,
                f"{sensor.getCurrent()/clockDiv} MHz",
                f"{sensor.getMin()/clockDiv} MHz",
                f"{sensor.getMax()/clockDiv} MHz"
            ])

        elif sensor.sensType == "RPM":
            return QTreeWidgetItem([
                sensor.label,
                f"{sensor.getCurrent()} RPM",
                f"{sensor.getMin()} RPM",
                f"{sensor.getMax()} RPM"
            ])

        return QTreeWidgetItem([
            sensor.label,
            f"{sensor.getCurrent()}",
            f"{sensor.getMin()}",
            f"{sensor.getMax()}"
        ])

    def updateValues(self) -> None:
        if self.nvidia: 
            self.nvidia.refresh()
            for unique_id, (item, gpu) in self.nvRows.items():
                if "_temp" in unique_id:
                    unit = "°C" if self.isCelcius else "°F" 
                    item.setText(1, f"{self.convertTemp(gpu.temp.currentValue,self.isCelcius)} {unit}")
                    item.setText(2, f"{self.convertTemp(gpu.temp.minValue, self.isCelcius)} {unit}")
                    item.setText(3, f"{self.convertTemp(gpu.temp.maxValue, self.isCelcius)} {unit}")
                elif "_pwr" in unique_id:
                    item.setText(1, f"{gpu.power.currentValue} W")
                    item.setText(2, f"{gpu.power.minValue} W")
                    item.setText(3, f"{gpu.power.maxValue} W")
                elif "_gc" in unique_id:
                    item.setText(1, f"{gpu.graphicsClock.currentValue} MHz")
                    item.setText(2, f"{gpu.graphicsClock.minValue} MHz")
                    item.setText(3, f"{gpu.graphicsClock.maxValue} MHz")
                elif "_mc" in unique_id:
                    item.setText(1, f"{gpu.memoryClock.currentValue} MHz")
                    item.setText(2, f"{gpu.memoryClock.minValue} MHz")
                    item.setText(3, f"{gpu.memoryClock.maxValue} MHz")
                
        for unique_id, (item, sensor) in self.sensorRows.items():
            sensor.read()
            tempDiv = 1000
            voltDiv = 1000
            clockDiv = 1000000
            
            if sensor.sensType == "Temperature":
                vCurr = self.convertTemp(sensor.getCurrent()/tempDiv, self.isCelcius)
                vMin = self.convertTemp(sensor.getMin()/tempDiv, self.isCelcius)
                vMax = self.convertTemp(sensor.getMax()/tempDiv, self.isCelcius)
                unit = ("°C" if self.isCelcius else "°F")
            elif sensor.sensType == "Voltage":
                vCurr = sensor.getCurrent()/voltDiv
                vMin = sensor.getMin()/voltDiv
                vMax = sensor.getMax()/voltDiv
                unit = "V"
            elif sensor.sensType == "Clock":
                vCurr = sensor.getCurrent()/clockDiv
                vMin = sensor.getMin()/clockDiv
                vMax = sensor.getMax()/clockDiv
                unit = "MHz"
            else:
                vCurr = sensor.getCurrent()
                vMin = sensor.getMin()
                vMax = sensor.getMax()
                unit = "RPM"

            item.setText(1, f"{vCurr} {unit}")
            item.setText(2, f"{vMin} {unit}")
            item.setText(3, f"{vMax} {unit}")

    def resetMinMax(self) -> None:
        for i in self.components.hwmonx:
            for j in i.sensors:
                j.maxValue = j.currentValue
                j.minValue = j.currentValue
        if self.nvidia:
            self.nvidia.resetValues()

        self.updateValues()

    def convertTemp(self, temp: float, isCelcius: bool) -> float:
        if isCelcius:
            return round(temp, 2)
        return round((temp * 9/5) + 32, 2)

    def switchUnits(self) -> None:
        self.isCelcius = not self.isCelcius
        self.updateValues()

    def changeTheme(self) -> None:
        self.darkMode = not self.darkMode
        self.applyStyle()

    def applyStyle(self) -> None:
        if self.darkMode:
            darkStyle = """
                QHeaderView::section {
                    color: white;
                    background-color: #292c30;
                }
                QTreeWidget {
                    color: white 
                }
                QTreeWidget::item {
                    background-color: #141618;
                }
                QTreeWidget::item:alternate {
                    background-color: #1d1f22;
                }
            """

            self.setStyleSheet(darkStyle)
        if not self.darkMode:
            lightStyle = """
                QHeaderView::section {
                    color: black;
                    background-color: white;
                }
                QTreeWidget {
                    background-color: #f7f7f7;
                    color: black;
                }
                QTreeWidget::item {
                    background-color: #f2f2f2;
                }
                QTreeWidget::item:alternate {
                    background-color: #d5d5d5;
                }
            """

            self.setStyleSheet(lightStyle)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet('''
        QWidget {
            font-size: 14px;
        }
    ''')

    sensmon = MainWindow()
    sensmon.show()

    try:
        sys.exit(app.exec())
    except SystemExit:
        print('Closing Window...')

        
