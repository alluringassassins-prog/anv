import sys
import os
import requests
import json
import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

from Library.ConfigurationFactory import *
from Library.StateAggregator import *
from Library.localDB import *

class Actuator:
    def __init__(self, ID):
        self.config = ConfigurationFactory.getInstance()
        self.envServer = self.config.get("environment")
        self.objectID = ID
        self.DB = localDB.getInstance(f'./{self.objectID}/')

    def iAmTired(self):
        url = f'{self.envServer["server"]["schema"]}://{self.envServer["server"]["address"]}:{self.envServer["server"]["port"]}/stop/{self.objectID}'

        try:
            response = requests.post(url)
            if response.ok :
                try:
                    data = json.loads(response.content)
                except:
                    raise Exception("Json loading ERROR!!!")
        except:
            print("Error in connecting to environment server or bad response")

        self.DB.insert("Action", {"action":"stop"})

    def moveMe(self, speed: float, directionX: float, directionY: float, directionZ: float, acceleration: float):
        url = f'{self.envServer["server"]["schema"]}://{self.envServer["server"]["address"]}:{self.envServer["server"]["port"]}/move/{self.objectID}'

        data = {}
        data["speed"] = speed
        data["acceleration"] = acceleration
        data["direction"] = {}
        data["direction"]["alpha"] = directionX
        data["direction"]["beta"] = directionY
        data["direction"]["gamma"] = directionZ

        try:
            response = requests.post(url, data = json.dumps(data))
            if response.ok :
                try:
                    data = json.loads(response.content)
                except:
                    raise Exception("Json loading ERROR!!!")
        except:
            print("Error in connecting to environment server or bad response")

        self.DB.insert("Action", {**{"action":"move"}, **data})

    def goto(self, latitude: float, longitude: float, altitude: float, timeout: int, finalPointMode: int):
        url = f'{self.envServer["server"]["schema"]}://{self.envServer["server"]["address"]}:{self.envServer["server"]["port"]}/goto/{self.objectID}'

        data = {}
        data["timeout"] = timeout
        data["finalPointMode"] = finalPointMode
        data["location"] = {}
        data["location"]["lat"] = latitude
        data["location"]["lon"] = longitude
        data["location"]["alt"] = altitude

        try:
            response = requests.post(url, data = json.dumps(data))
            if response.ok :
                try:
                    data = json.loads(response.content)
                except:
                    raise Exception("Json loading ERROR!!!")
        except:
            print("Error in connecting to environment server or bad response")

        self.DB.insert("Action", {**{"action":"goto"}, **data})

    def putMeOnLocation(self, type: str, party: str, latitude: float, longitude: float, altitude: float, speed: float, directionX: float, directionY: float, directionZ: float, acceleration: float):
        url = f'{self.envServer["server"]["schema"]}://{self.envServer["server"]["address"]}:{self.envServer["server"]["port"]}/put/{self.objectID}'

        data = {}
        data["type"] = type
        data["party"] = party
        data["location"] = {}
        data["location"]["lat"] = latitude
        data["location"]["lon"] = longitude
        data["location"]["alt"] = altitude
        data["velocity"] = {}
        data["velocity"]["speed"] = speed
        data["velocity"]["acceleration"] = acceleration
        data["velocity"]["direction"] = {}
        data["velocity"]["direction"]["alpha"] = directionX
        data["velocity"]["direction"]["beta"] = directionY
        data["velocity"]["direction"]["gamma"] = directionZ

        try:
            response = requests.post(url, data = json.dumps(data))
            if response.ok :
                try:
                    data = json.loads(response.content)
                except:
                    raise Exception("Json loading ERROR!!!")
        except:
            print("Error in connecting to environment server or bad response")

        self.DB.insert("Action", {**{"action":"put"}, **data})
