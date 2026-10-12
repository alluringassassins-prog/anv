import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

import requests
import threading
from Library.StateAggregator import *
from Library.ConfigurationFactory import *
from Library.DDSWrapper import *
import json
import time

class Environment:

    def fetchEnvironment(self):

        time.sleep(self.config.get("warmupDuration"))

        url = f'{self.envServer["server"]["schema"]}://{self.envServer["server"]["address"]}:{self.envServer["server"]["port"]}/environment/{self.objectID}/{self.envServer["radius"]}'

        while True:
            try:
                response = requests.get(url)
                if response.ok :
                    try:
                        data = json.loads(response.content.decode("utf-8"))
                    except:
                        raise Exception("Json loading ERROR!!!", response.content.decode("utf-8"))
                    else:
                        self.state.receiveEnvironment(data)
            except:
                print("Error in connecting to environment server or bad response")

            time.sleep(1.5*self.config.get("SensingSentivity"))

    def __init__(self, ID):

        self.state = StateAggregator.getInstance(ID)
        self.config = ConfigurationFactory.getInstance()

        self.envServer = self.config.get("environment")
        self.objectID = ID

        self.DDS = DDSWrapper.getInstance(self.objectID)

        self.envWatch = threading.Thread(target=self.fetchEnvironment, args=())
        self.envWatch.start()

        Environment.instance = self

    instance = None

    lock = threading.Lock()

    @staticmethod
    def getInstance(ID):
        if Environment.instance == None:
            with Environment.lock:
                if Environment.instance == None:
                    Environment.instance = Environment(ID)
        return Environment.instance

