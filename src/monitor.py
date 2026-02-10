import sys
import subprocess
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeWidgetItem
from PyQt6.QtCore import QSize
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

        self.hasNvidia = self.detectNvidia()
        if self.hasNvidia:
            self.nvidia = nvidiaGPU.NvManager()
            self.nvidia.refresh()
            for gpu in self.nvidia.gpus.values():
                self.addNvidiaEntry(gpu)

        for hwmon in self.components.hwmonx:
            self.addHwmonEntry(hwmon)

    def detectNvidia(self) -> bool:
        try:
            subprocess.check_output(["nvidia-smi"], stderr = subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def addNvidiaEntry(self, gpu: nvidiaGPU.NvGPU):
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

    def addHwmonEntry(self, hwmon: sensors.HwmonDevice):
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

    def convertTemp(self, temp: float, isCelcius: bool) -> float:
        if isCelcius:
            return temp
        return round((temp * 9/5) + 32, 2)

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

        
