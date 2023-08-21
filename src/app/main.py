from Controller import Controller
from ConfigManager import ConfigManager
from EventHandler import EventHandler


### application entrypoint
if __name__ == "__main__":
    controller = Controller()
    controller.run()