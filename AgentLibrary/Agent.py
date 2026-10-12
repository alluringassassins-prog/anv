import json
import math
import datetime
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from shapely.geometry import Polygon
from shapely.validation import make_valid
import numpy as np
import traceback
import warnings
from scipy.optimize import OptimizeWarning
import sys
import os
import random
from multiprocessing import Process

sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

from Library.StateAggregator import *
from Library.ConfigurationFactory import *
from Library.localDB import *
from AgentLibrary.DDSService import *
from AgentLibrary.Actuator import *
from AgentLibrary.DecisionMaker import *
from Library.DDSWrapper import *
from Library.Environment import *
from scipy.spatial import ConvexHull
from scipy.optimize import curve_fit

warnings.simplefilter("error", OptimizeWarning)

class Agent:

    def recentActions(self):
        toT = datetime.datetime.now()
        res = self.DB.query("Action", self.lastActionTime, toT.strftime("%Y-%m-%d %H:%M:%S"))
        self.lastActionTime = toT.strftime("%Y-%m-%d %H:%M:%S")
        return res

    def recentDecisions(self):
        toT = datetime.datetime.now()
        res = self.DB.query("Decisions", self.lastDecisionsTime, toT.strftime("%Y-%m-%d %H:%M:%S"))
        self.lastDecisionsTime = toT.strftime("%Y-%m-%d %H:%M:%S")
        return res

    def recentObjects(self):
        toT = datetime.datetime.now()
        res = self.DB.query("Object", self.lastObjectTime, toT.strftime("%Y-%m-%d %H:%M:%S"))
        self.lastObjectTime = toT.strftime("%Y-%m-%d %H:%M:%S")
        return res

    def recentPublishes(self):
        toT = datetime.datetime.now()
        res = self.DB.query("Publish", self.lastObjectTime, toT.strftime("%Y-%m-%d %H:%M:%S"))
        self.lastPublishTime = toT.strftime("%Y-%m-%d %H:%M:%S")
        return res

    def recentTargets(self):
        toT = datetime.datetime.now()
        res = self.DB.query("Targets", self.lastObjectTime, toT.strftime("%Y-%m-%d %H:%M:%S"))
        self.lastTargetTime = toT.strftime("%Y-%m-%d %H:%M:%S")
        return res

    def getAllActions(self):
        toT = datetime.datetime.now()
        res = self.DB.query("Action", "2000-01-01 00:00:01", toT.strftime("%Y-%m-%d %H:%M:%S"))
        self.lastActionTime = toT.strftime("%Y-%m-%d %H:%M:%S")
        return res

    def getAllDecisions(self):
        toT = datetime.datetime.now()
        res = self.DB.query("Decisions", "2000-01-01 00:00:01", toT.strftime("%Y-%m-%d %H:%M:%S"))
        self.lastDecisionsTime = toT.strftime("%Y-%m-%d %H:%M:%S")
        return res

    def getAllObjects(self):
        toT = datetime.datetime.now()
        res = self.DB.query("Object", "2000-01-01 00:00:01", toT.strftime("%Y-%m-%d %H:%M:%S"))
        self.lastObjectTime = toT.strftime("%Y-%m-%d %H:%M:%S")
        return res

    def getAllPublishes(self):
        toT = datetime.datetime.now()
        res = self.DB.query("Publish", "2000-01-01 00:00:01", toT.strftime("%Y-%m-%d %H:%M:%S"))
        self.lastPublishTime = toT.strftime("%Y-%m-%d %H:%M:%S")
        return res

    def getAllTargets(self):
        toT = datetime.datetime.now()
        res = self.DB.query("Targets", "2000-01-01 00:00:01", toT.strftime("%Y-%m-%d %H:%M:%S"))
        self.lastTargetTime = toT.strftime("%Y-%m-%d %H:%M:%S")
        return res
    
    def truncateActions(self):
        self.DB.truncate("Action")
        return {"response":"ok"}

    def truncateDecisions(self):
        self.DB.truncate("Decisions")
        return {"response":"ok"}

    def truncateTargets(self):
        self.DB.truncate("Targets")
        return {"response":"ok"}

    def truncateObjects(self):
        self.DB.truncate("Object")
        return {"response":"ok"}

    def truncatePublishes(self):
        self.DB.truncate("Publish")
        return {"response":"ok"}

    def initiateDDSService(self, ID):
        self.ddsService = DDSService(self.ID)

    def testTargetElimination(self, ID):
        time.sleep(180)
        self.truncateTargets()

    def __init__(self, ID: int):

        self.ID = ID

        self.config = ConfigurationFactory()

        self.ddsServiceProcess = Process(target=self.initiateDDSService, args=(self.ID,))
        self.ddsServiceProcess.start()

        time.sleep(self.config.get("warmupDuration"))

        # if self.ID == 15:
        #     self.testTargetEliminationProcess = threading.Thread(target=self.testTargetElimination, args=(self.ID,))
        #     self.testTargetEliminationProcess.start()

        self.DB = localDB(f'./{self.ID}/')
        self.DDS = DDSWrapper(self.ID)

        self.DecisionMaker = DecisionMaker(self.ID)

        self.lastActionTime = "2010-01-01 00:00:01"
        self.lastDecisionsTime = "2010-01-01 00:00:01"
        self.lastObjectTime = "2010-01-01 00:00:01"
        self.lastPublishTime = "2010-01-01 00:00:01"
        self.lastTargetTime = "2010-01-01 00:00:01"

        app = FastAPI()

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        app.add_api_route("/RecentActions", self.recentActions, methods=["GET"])
        app.add_api_route("/RecentDecisions", self.recentDecisions, methods=["GET"])
        app.add_api_route("/RecentObjects", self.recentObjects, methods=["GET"])
        app.add_api_route("/RecentPublishes", self.recentPublishes, methods=["GET"])
        app.add_api_route("/RecentTargets", self.recentTargets, methods=["GET"])

        app.add_api_route("/AllActions", self.getAllActions, methods=["GET"])
        app.add_api_route("/AllDecisions", self.getAllDecisions, methods=["GET"])
        app.add_api_route("/AllObjects", self.getAllObjects, methods=["GET"])
        app.add_api_route("/AllPublishes", self.getAllPublishes, methods=["GET"])
        app.add_api_route("/AllTargets", self.getAllTargets, methods=["GET"])

        app.add_api_route("/TruncateActions", self.truncateActions, methods=["DELETE"])
        app.add_api_route("/TruncateDecisions", self.truncateDecisions, methods=["DELETE"])
        app.add_api_route("/TruncateObjects", self.truncateObjects, methods=["DELETE"])
        app.add_api_route("/TruncatePublishes", self.truncatePublishes, methods=["DELETE"])
        app.add_api_route("/TruncateTargets", self.truncateTargets, methods=["DELETE"])

        app.add_api_route("/CallBack", self.DDS.subscribe_callback, methods=["POST"])

        uvicorn.run(app, host="0.0.0.0", port=self.config.get("agent")["ServicePortOffset"]+self.ID, log_config=None)


if __name__ == '__main__':
    config = ConfigurationFactory()
    id = config.get("ID")
    if len(sys.argv) > 1:
        id = sys.argv[1]
    agent = Agent(int(id))