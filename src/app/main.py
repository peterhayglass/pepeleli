from Controller import Controller
from ConfigManager import ConfigManager
from EventHandler import EventHandler


### application entrypoint
if __name__ == "__main__":
    config_manager = ConfigManager()
    event_handler = EventHandler()
    controller = Controller(config_manager, event_handler)
    controller.run()