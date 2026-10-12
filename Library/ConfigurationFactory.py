import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

# from Library.DDS import *
import json
import threading

class ConfigurationFactory:

    def receiveConfig(self, data: dict):
        for var in data:
            self.configuration[var] = data[var]

    def set(self, key: str, data):
        self.configuration[key] = data

    def get(self, var: str):
        if var in self.configuration:
            return self.configuration[var]
        return None

    def __init__(self):
        self.configuration = {}

        with open(os.path.dirname(os.path.abspath(__file__))+"/../config.ini", "r") as file:
            content = file.read()
            try:
                self.configuration = json.loads(content)
            except:
                raise Exception("Json loading ERROR in reading config file!!!")

        # self.dds = DDS.getInstance(self.get('ID'), self.get('DDS')["address"], self.get('DDS')["port"])
        # self.dds.subscribe(self.receiveConfig, "Config")

        ConfigurationFactory.instance = self

    instance = None

    lock = threading.Lock()

    @staticmethod
    def getInstance():
        if ConfigurationFactory.instance == None:
            with ConfigurationFactory.lock:
                if ConfigurationFactory.instance == None:
                    ConfigurationFactory.instance = ConfigurationFactory()
        return ConfigurationFactory.instance

