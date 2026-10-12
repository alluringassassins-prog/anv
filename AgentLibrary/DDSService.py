import sys
import os
import requests
import json
import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

from Library.ConfigurationFactory import *
from Library.localDB import *
from Library.DDS import *

class DDSService:

    def publish(self, data: str, broadcast: bool):
        # if self.ID == 110:
        #     print("Publish DDSService")
        #     print(data)

        dataObject = json.loads(data)
        self.DDS.publish(dataObject, broadcast)
        return {"response":"ok"}

    def subscribe_callback(self, data: dict):
        for topic in data.keys():
            # print("Subscribe callback DDSService")
            # print(json.dumps(data))

            if topic in self.localSubscribers.keys():
                for url in self.localSubscribers[topic]:
                    payload = {}
                    payload["data"] = json.dumps(data)

                    try:
                        response = requests.post(url, params = payload)
                        if response.ok :
                            try:
                                data = json.loads(response.content)
                            except:
                                raise Exception("Json loading ERROR!!!")
                    except:
                        print("Error in call CallBackApi!!!")
                        print(url)

    def subscribe(self, topic: str, subscriber: str):
        if not topic in self.localSubscribers:
            self.localSubscribers[topic] = []

        self.localSubscribers[topic].append(subscriber)

        self.DDS.subscribe(self.subscribe_callback, topic)

        return {"response":"ok"}

    def __init__(self, ID : str):
        dir_path = f'./{ID}/'

        # List all files in the directory
        if os.path.exists(dir_path):
            for filename in os.listdir(dir_path):
                file_path = os.path.join(dir_path, filename)
                
                # Check if it is a file (not a subdirectory)
                if os.path.isfile(file_path):
                    os.remove(file_path)  # Remove the file

        self.ID = int(ID)
        dir_path = f'./{ID}/'
        self.config = ConfigurationFactory()
        self.DB = localDB(f'./{self.ID}/')
        self.DDS = DDS(self.ID)
        self.localSubscribers = {}
        
        app = FastAPI()

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        app.add_api_route("/Publish", self.publish, methods=["POST"])
        app.add_api_route("/Subscribe", self.subscribe, methods=["POST"])

        uvicorn.run(app, host="0.0.0.0", port=self.config.get("agent")["DDSServicePortOffset"]+self.ID, log_config=None, log_level="info")
