import sys
import os
import traceback
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

from Library.DDSWrapper import *
from Library.localDB import *

class StateAggregator:

    def setReached(self, index: int):
        self.status["Targets"].targets[index].isReached = True

    def getAgentStatus(self):

        if "Targets" in self.status and ((not "OldTargets" in self.status) or self.status["Targets"].count > 0):
            self.status["OldTargets"] = self.status["Targets"]

        res = self.DB.query("Targets", "2000-01-01 00:00:01", None)
        if res and len(res) > 0:
            w = WayPoint()
            counter = 0
            for t in res[-1]["Targets"]:
                ti = TargetInfo(t["timeout"], t["behave"], t["location"]["lat"], t["location"]["lon"], t["location"]["alt"], t['deadline'])
                ti.isReached = False
                if "OldTargets" in self.status and counter < len(self.status["OldTargets"].targets) and "isReached" in self.status["OldTargets"].targets[counter].__dict__:
                    ti.isReached = self.status["OldTargets"].targets[counter].isReached
                w.append(ti)
                counter = counter + 1

            self.status["Targets"] = w
        else:
            self.status.pop("Targets", None)

        return self.status

    def receiveEnvironment(self, data: dict):
        newObjects = []
        if "objects" in self.status:
            for obj in self.status["objects"]:
                if "Cooperation" in obj and obj["Cooperation"] == 1:
                    newObjects.append(obj)
            
        if "objects" in data:
            if isinstance(data["objects"], list):
                for obj in data["objects"]:
                    newObjects.append(obj)
                    self.DB.insert("Object", obj)
                    if obj["object_id"] == self.ID:
                        pubObj = ObjectInfo(self.ID, obj["type"],obj["party"],obj["location"]["lat"],obj["location"]["lon"],obj["location"]["alt"],obj["velocity"]["speed"],obj["velocity"]["acceleration"],obj["velocity"]["direction"]["alpha"],obj["velocity"]["direction"]["beta"],obj["velocity"]["direction"]["gamma"])
                        self.dds.publish({"ObjectInfo":pubObj}, True)

        # if self.ID == 10:
        #     print(newObjects)
        self.status["objects"] = newObjects

    def receiveNodes(self, data: dict):
        if "ObjectInfo" in data:
            dictData = json.loads(data["ObjectInfo"].__str__())
            dictData["object_id"] = data["Sender"]
            dictData["Cooperation"] = 1
            self.DB.insert("Object", dictData)
            if not "objects" in self.status:
                self.status["objects"] = []
            counter = 0
            found = False
            for obj in self.status["objects"]:
                if obj["object_id"] == dictData["object_id"]:
                    found = True
                    self.status["objects"][counter]["location"].update(dictData["location"])
                    self.status["objects"][counter]["velocity"].update(dictData["velocity"])
                    self.status["objects"][counter]["type"] = dictData["type"]
                    self.status["objects"][counter]["party"] = dictData["party"]
                    self.status["objects"][counter]["object_id"] = dictData["object_id"]
                counter += 1
            if not found:
                self.status["objects"].append(dictData)

    def receiveTargets(self, data: dict):
        eachDegreeScale = 100000000 / 90
        minTimeInterval = self.conf.get("minLegalDistance") / self.conf.get("maxLegalSpeed")
        minLegalDistance = self.conf.get("minLegalDistance")
        minLegalDistance = minLegalDistance / (2 * eachDegreeScale)
        nowTime = datetime.datetime.now()
        if "WayPoint" in data:
            TargetShouldBeInserted = True
            res = self.DB.query("Targets", "2000-01-01 00:00:01", None)
            if res and len(res) > 0:
                if len(data["WayPoint"].targets) == len(res[-1]["Targets"]):
                    TargetShouldBeInserted = False
                    counter = 0
                    for t in res[-1]["Targets"]:
                        distance = ((t["location"]["lat"] - data["WayPoint"].targets[counter].location.latitude)**2+(t["location"]["lon"] - data["WayPoint"].targets[counter].location.longitude)**2+(t["location"]["alt"] - data["WayPoint"].targets[counter].location.altitude)**2)**0.5
                        timeDistance = (datetime.datetime.strptime(t["deadline"], "%Y-%m-%d %H:%M:%S") - data["WayPoint"].targets[counter].deadline).seconds
                        if distance > minLegalDistance or timeDistance > minTimeInterval:
                            TargetShouldBeInserted = True
                            break
                        counter = counter + 1

            if TargetShouldBeInserted:

                finalWayPoint = WayPoint()
                counter = 0
                for i in range(data["WayPoint"].count):
                    if data["WayPoint"].targets[i].deadline > nowTime:
                        finalWayPoint.append(data["WayPoint"].targets[i])

                self.status["Targets"] = finalWayPoint
                # print(data["WayPoint"].__str__())
                # print(json.loads(data["WayPoint"].__str__()))
                self.DB.insert("Targets", json.loads(finalWayPoint.__str__()))
                # print(traceback.format_exc())
                # print("====================")

    def subscribeWayPoint(self):
        self.dds.subscribe(self.receiveTargets, "WayPoint")

    def __init__(self, ID):
        self.ID = ID
        self.dds = DDSWrapper.getInstance(self.ID)
        self.conf = ConfigurationFactory.getInstance()
        self.dds.subscribe(self.receiveNodes, "ObjectInfo")
        self.dds.subscribe(self.receiveTargets, "WayPoint")
        self.DB = localDB.getInstance(f'./{self.ID}/')
        self.status = {}
        StateAggregator.instance = self

    instance = None

    lock = threading.Lock()

    @staticmethod
    def getInstance(ID):
        if StateAggregator.instance == None:
            with StateAggregator.lock:
                if StateAggregator.instance == None:
                    StateAggregator.instance = StateAggregator(ID)
        return StateAggregator.instance
