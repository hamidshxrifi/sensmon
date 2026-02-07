import subprocess

def safe_float(value):
    try:
        return float(value.strip())
    except(ValueError, TypeError):
        return 0.0

class Metric:
    def __init__(self, value: float) -> None:
        self.currentValue = value
        self.maxValue = value
        self.minValue = value

    def update(self, value: float) -> None:
        self.currentValue = value
        self.maxValue = max(self.maxValue, value)
        self.minValue = min(self.minValue, value)

class NvGPU:
    def __init__(self, idNum: str, model: str, temp: str, power: str, gc: str, mc: str) -> None:
        self.id = idNum
        self.model = model

        self.temp = Metric(safe_float(temp))
        self.power = Metric(safe_float(power))
        self.graphicsClock= Metric(safe_float(gc))
        self.memoryClock = Metric(safe_float(mc))

    def updateStats(self, temp: str, power: str, gc: str, mc: str):
        self.temp.update(safe_float(temp))
        self.power.update(safe_float(power))
        self.graphicsClock.update(safe_float(gc))
        self.memoryClock.update(safe_float(mc))

class NvManager:
    def __init__(self) -> None:
        self.gpus = {}

    def refresh(self) -> None:
        try:
            out = subprocess.check_output([
                "nvidia-smi",
                "--query-gpu=index,name,temperature.gpu,power.draw,clocks.gr,clocks.mem",
                "--format=csv,noheader,nounits"
            ], text=True)
        except subprocess.CalledProcessError:
            print("Error: Could not query nvidia-smi")
            return
        
        for line in out.strip().splitlines():
            data = [x.strip() for x in line.split(",")]

            if len(data) != 6: 
                continue 

            idx, name, temp, power, gc, mc = data

            if idx in self.gpus:
                self.gpus[idx].updateStats(temp, power, gc, mc)
            else:
                self.gpus[idx] = NvGPU(idx, name, temp, power, gc, mc)

