from os import name, path, sysconf_names
from pathlib import Path
import subprocess

MOTHERBOARDS = ("gigabyte_wmi", "it87", "it86", "thinkpad-isa")

class Sensor:
    def __init__(self, inputPath: Path, label: str, sensType: str) -> None:
        self.inputPath = inputPath
        self.label = label
        self.sensType = sensType
        self.initValue = True
        self.currentValue = 0
        self.maxValue = 0
        self.minValue = 0

    def getCurrent(self) -> float:
        return float(self.currentValue)

    def getMax(self) -> float:
        return float(self.maxValue)

    def getMin(self) -> float:
        return float(self.minValue)

    def read(self) -> None:
        try:
            readValue = self.inputPath.read_text().strip()
            self.currentValue = readValue
            if self.initValue:
                self.maxValue = readValue
                self.minValue = readValue
                self.initValue= False
            else:
                if int(self.currentValue) > int(self.maxValue):
                    self.maxValue = readValue
                if int(self.currentValue) < int(self.minValue):
                    self.minValue = readValue
        except ():
            pass

class HwmonDevice:
    def __init__(self, name: str, path: Path) -> None:
        self.name = name
        self.path = path
        self.id = ""
        self.sensors = []
        self.sensorType = {
            "temp": "Temperature",
            "in": "Voltage",
            "fan": "RPM",
            "power": "Power",
            "freq": "Clock"
        }

    def findSensors(self) -> None:
        sortOrder = {"Temperature": 0, "Voltage": 1, "RPM": 2, "Power": 3, "Clock": 4}

        for file in self.path.iterdir():
            if self.isValidSensor(file):
                labelPath = self.path / file.name.replace("input", "label")
                if labelPath.exists():
                    label = labelPath.read_text().strip()
                else:
                    label = file.name

                sensType = self.getSensorType(str(file.name))

                sensor = Sensor(file, label, sensType)
                self.sensors.append(sensor)
        
        self.sensors.sort(key=lambda s: (
            sortOrder.get(s.sensType, 99), 
            Path(s.inputPath).name
        ))
    
    def getSensorType(self, fileName: str) -> str:
        return next((self.sensorType[prefix] for prefix in self.sensorType if fileName.startswith(prefix)), "Other")

    def isValidSensor(self, file: Path) -> bool:
        if file.is_file() and file.name.endswith("_input"):
            for sType in self.sensorType:
                if file.name.startswith(sType):
                    return True
        return False

    def printSensors(self) -> None:
        print('-' + self.id)
        for i in self.sensors:
            print(i.label, end='=')
            print(i.getCurrent(), end=' ')
        print("")

class HwmonManager:
    def __init__(self) -> None:
        self.hwmonx = []
        self.path = Path("/sys/class/hwmon/")
        self.devNum = 0

    def getDeviceDisplayName(self, hwmonPath: Path, defaultName: str) -> str:

        # motherboard check
        if any(mb in defaultName for mb in MOTHERBOARDS):
            vendor = Path("/sys/class/dmi/id/board_vendor").read_text().strip()
            board = Path("/sys/class/dmi/id/board_name").read_text().strip()
            return f"{vendor} {board}"

        # cpu check
        if defaultName in ["k10temp", "coretemp"]:
            cpuInfo = Path("/proc/cpuinfo")
            if cpuInfo.exists():
                for line in cpuInfo.read_text().splitlines():
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
            else:
                return defaultName

        # nvme check
        if "nvme" in defaultName:
            modelPath = hwmonPath / "device/model"
            if modelPath.exists():
                return modelPath.read_text().strip()
            else:
                return defaultName

        # gpu check
        if "gpu" in defaultName:
            try:
                out = subprocess.check_output(["glxinfo", "-B"], text = True)
                for line in out.splitlines():
                    line = line.strip()
                    if line.startswith("OpenGL renderer string:"):
                        return line.split(":", 1)[1].strip()
            except:
                return defaultName

        return defaultName

    def findDevices(self) -> None:
        if not self.path.exists():
            return

        hwmonDirs = sorted(
            self.path.iterdir(),
            key=lambda p: int(p.name.replace("hwmon", ""))
        )

        for hwmonPath in hwmonDirs:
            if (hwmonPath / "name").exists():
                sensorPath = hwmonPath
            elif (hwmonPath / "device/name").exists():
                sensorPath = hwmonPath / "device"
            else:
                continue

            deviceName = (sensorPath / "name").read_text().strip()
            displayName = self.getDeviceDisplayName(hwmonPath, deviceName)

            dev = HwmonDevice(displayName, sensorPath)
            dev.id = f"hwmon{self.devNum}{deviceName}"
            self.devNum += 1
            dev.findSensors()

            if displayName != deviceName:
                self.hwmonx.insert(0, dev)
            else:
                self.hwmonx.append(dev)

if __name__ == "__main__":

    test = HwmonManager()
    test.findDevices()
    for i in test.hwmonx:
        i.printSensors() 

     
