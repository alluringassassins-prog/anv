#fastapi run EnvironmentCreator.py --host 0.0.0.0 --port 8000

import random
from fastapi import FastAPI
from pydantic import BaseModel
from enum import Enum
from fastapi.middleware.cors import CORSMiddleware
import threading
import math
import time
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

from Library.ConfigurationFactory import *

class ReceiptBehaviour(Enum):
    Stop = 1
    Pass = 2

class Location(BaseModel):
    lat: float
    lon: float
    alt: float

class Direction(BaseModel):
    alpha: float
    beta: float
    gamma: float

class Velocity(BaseModel):
    speed: float
    direction: Direction
    acceleration: float

class ObjectInfo(BaseModel):
    type: str
    party: str
    location: Location
    velocity: Velocity

class DateTime(BaseModel):
    hour: int
    minute: int
    second: int

class TargetInfo(BaseModel):
    location: Location
    timeout: float
    finalPointMode: ReceiptBehaviour

class Environment:
    objects: None

    def computeLocations(self, refreshRate: float):
        eachDegreeScale = 100000000 / 90

        refreshRate = ConfigurationFactory.getInstance().get("SensingSentivity")

        while True:
            time.sleep(refreshRate)
            counter = 0
            for object in self.objects:
                self.objects[counter]["location"]["lat"] = object["location"]["lat"] + ((math.cos((object["velocity"]["direction"]["alpha"] * math.pi)/180.0)*(0.5 * refreshRate * refreshRate * object["velocity"]["acceleration"] + refreshRate * object["velocity"]["speed"] ))/eachDegreeScale)
                self.objects[counter]["location"]["lon"] = object["location"]["lon"] + ((math.cos((object["velocity"]["direction"]["beta"] * math.pi)/180.0)*(0.5 * refreshRate * refreshRate * object["velocity"]["acceleration"] + refreshRate * object["velocity"]["speed"] ))/eachDegreeScale)
                self.objects[counter]["location"]["alt"] = object["location"]["alt"] + ((math.cos((object["velocity"]["direction"]["gamma"] * math.pi)/180.0)*(0.5 * refreshRate * refreshRate * object["velocity"]["acceleration"] + refreshRate * object["velocity"]["speed"] ))/eachDegreeScale)

                tmpSpeed = object["velocity"]["speed"] + object["velocity"]["acceleration"] * refreshRate
                if tmpSpeed > ConfigurationFactory.getInstance().get("maxLegalSpeed"):
                    tmpSpeed = ConfigurationFactory.getInstance().get("maxLegalSpeed")
                self.objects[counter]["velocity"]["speed"] = tmpSpeed
                counter = counter + 1

    def __init__(self):
        self.objects = []

        self.clientThread = threading.Thread(target=self.computeLocations, args=(0.1, ))
        self.clientThread.start()

    def getObjects(self, id: int=0, radius: float = 0):
        if id == 0:
            return self.objects
        else:

            eachDegreeScale = 100000000 / 90

            result = []
            myloc = None
            for obj in self.objects:
                if id == obj["object_id"]:
                    myloc = obj
                    break
            
            if myloc == None:
                return []
            else:
                for obj in self.objects:
                    if obj["object_id"] == id:
                        result.append(obj)
                    else:
                        dist = (obj["location"]["lat"] - myloc["location"]["lat"])**2
                        dist += (obj["location"]["lon"] - myloc["location"]["lon"])**2
                        dist += (obj["location"]["alt"] - myloc["location"]["alt"])**2
                        dist = dist**0.5
                        dist *= eachDegreeScale

                        if dist <= radius:
                            result.append(obj)
                
                return result
    
    def gotoLocation(self, id, target: TargetInfo):
        eachDegreeScale = 100000000 / 90

        counter = 0
        for obj in self.objects:
            if obj["object_id"] == id:
                if target.timeout > 0:
                    d_lat = target.location.lat - obj["location"]["lat"]
                    d_lon = target.location.lon - obj["location"]["lon"]
                    d_alt = target.location.alt - obj["location"]["alt"]

                    d_size = (d_lat ** 2 + d_lon ** 2 + d_alt **2 ) ** 0.5

                    if d_size > 0:
                        self.objects[counter]["velocity"]["direction"]["alpha"] = (180*math.acos(d_lat/d_size))/math.pi
                        self.objects[counter]["velocity"]["direction"]["beta"] = (180*math.acos(d_lon/d_size))/math.pi
                        self.objects[counter]["velocity"]["direction"]["gamma"] = (180*math.acos(d_alt/d_size))/math.pi

                    self.objects[counter]["velocity"]["acceleration"] = 0
                    tmpSpeed = (d_size*eachDegreeScale)/target.timeout
                    if tmpSpeed > ConfigurationFactory.getInstance().get("maxLegalSpeed"):
                        tmpSpeed = ConfigurationFactory.getInstance().get("maxLegalSpeed")
                    self.objects[counter]["velocity"]["speed"] = tmpSpeed
                else:
                    self.objects[counter]["location"]["lat"] = target.location.lat
                    self.objects[counter]["location"]["lon"] = target.location.lon
                    self.objects[counter]["location"]["alt"] = target.location.alt
                    self.objects[counter]["velocity"]["acceleration"] = 0
                    self.objects[counter]["velocity"]["speed"] = 0
                    self.objects[counter]["velocity"]["direction"]["alpha"] = 45
                    self.objects[counter]["velocity"]["direction"]["beta"] = 45
                    self.objects[counter]["velocity"]["direction"]["gamma"] = 45
                
                return self.objects[counter]

            counter = counter + 1

    def stop(self, id):
        counter = 0
        for obj in self.objects:
            if obj["object_id"] == id:
                self.objects[counter]["velocity"]["speed"] = 0
                self.objects[counter]["velocity"]["acceleration"] = 0
                return self.objects[counter]
            
            counter = counter + 1 

    def doManoeuver(self, id, velocity: Velocity):
        eachDegreeScale = 100000000 / 90

        counter = 0
        for obj in self.objects:
            if obj["object_id"] == id:
                self.objects[counter]["velocity"]["speed"] = velocity.speed
                self.objects[counter]["velocity"]["acceleration"] = velocity.acceleration
                self.objects[counter]["velocity"]["direction"]["alpha"] = velocity.direction.alpha
                self.objects[counter]["velocity"]["direction"]["beta"] = velocity.direction.beta
                self.objects[counter]["velocity"]["direction"]["gamma"] = velocity.direction.gamma

                return self.objects[counter]
            
            counter = counter + 1

    def addObject(self, object):
        for obj in self.objects:
            if obj["object_id"] == object["object_id"]:
                return obj

        newObj = {}
        newObj["object_id"] = object["object_id"]
        newObj["location"] = {}
        newObj["location"]["lat"] = object["info"].location.lat
        newObj["location"]["lon"] = object["info"].location.lon
        newObj["location"]["alt"] = object["info"].location.alt
        newObj["velocity"] = {}
        newObj["velocity"]["direction"] = {}
        newObj["velocity"]["direction"]["alpha"] = object["info"].velocity.direction.alpha
        newObj["velocity"]["direction"]["beta"] = object["info"].velocity.direction.beta
        newObj["velocity"]["direction"]["gamma"] = object["info"].velocity.direction.gamma
        newObj["velocity"]["speed"] = object["info"].velocity.speed
        newObj["velocity"]["acceleration"] = object["info"].velocity.acceleration
        newObj["party"] = object["info"].party
        newObj["type"] = object["info"].type
        self.objects.append(newObj)
        return newObj
    
env = Environment()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/environment")
def detectAll():
    return {"objects":env.getObjects()}

@app.get("/environment/{object_id}/{radius}")
def detect(object_id: int, radius: float):
    return {"me": object_id, "objects":env.getObjects(object_id, radius)}

@app.post("/goto/{object_id}")
def goto(object_id: int, target: TargetInfo):
    tmp = env.gotoLocation(object_id, target)
    return {"object": object_id, "final_location":tmp["location"]}

@app.post("/move/{object_id}")
def move(object_id: int, velocity: Velocity):
    tmp = env.doManoeuver(object_id, velocity)
    return {"object": object_id, "final_location":tmp["location"]}

@app.post("/stop/{object_id}")
def stop(object_id: int):
    tmp = env.stop(object_id)
    return {"object": object_id, "final_location":tmp["location"]}

@app.put("/put/{object_id}")
def put(object_id: int, object_info: ObjectInfo):
    tmp = {}
    tmp["object_id"] = object_id
    tmp["info"] = object_info
    newObj = env.addObject(tmp)
    return {"object": object_id, "final_location":newObj["location"]}
