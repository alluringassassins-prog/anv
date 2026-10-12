import sys
import os
import requests
import json
import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from urllib import parse
import traceback

sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

from Library.ConfigurationFactory import *
from Library.localDB import *
from Library.DDS import *
from Models.Direction import *
from Models.Location import *
from Models.ObjectInfo import *
from Models.TargetInfo import *
from Models.Velocity import *
from Models.WayPoint import *

class DDSWrapper:

    instanceLock = threading.Lock()
    instance = None

    @staticmethod
    def getInstance(ID: int):
        if DDSWrapper.instance == None:
            with DDSWrapper.instanceLock:
                if DDSWrapper.instance == None:
                    DDSWrapper.instance = DDSWrapper(ID)
        return DDSWrapper.instance

    def publish(self, data: dict, broadcast: bool):
        url = self.config.get('agent')['DDSDeploymentAddress']['schema']+'://'+self.config.get('agent')['DDSDeploymentAddress']['address']+':'+(str)(self.config.get('agent')['DDSServicePortOffset']+self.ID)+'/Publish'

        # if self.ID == 110:
        #     print("Publish DDSWrapper")

        payload = {}
        payload["broadcast"] = broadcast
        for topic in data.keys():
            # if self.ID == 110:
            #     print(data[topic].__str__())
    
            payload["data"] = f'{{"{topic}":"{base64.b64encode(bytearray(data[topic].serialize())).decode("ascii")}"}}'

            try:
                response = requests.post(url, params = payload)
                if response.ok :
                    try:
                        data = json.loads(response.content)
                    except:
                        raise Exception("Json loading ERROR!!!")
                else:
                    print("Error in call publish of DDS Service, fail response!!!")
                    print(url)
                    print(payload)
            except:
                print("Error in call publish of DDS service!!!")
                print(url)

    def subscribe_callback(self, data: str):
        try:
            # print("Subscribe callback DDSWrapper")
            # print(data)

            dataObject = json.loads(data)

            if not "__timestamp__" in dataObject.keys():
                dataObject["__timestamp__"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if dataObject != None:
                for topic in dataObject.keys():
                    if topic in self.localSubscribers.keys():
                        unserializedTopic = None
                        # TODO: Add other data types here
                        match topic:
                            case "Direction":
                                unserializedTopic = Direction(__timestamp__=dataObject["__timestamp__"])
                            case "location":
                                unserializedTopic = Location(__timestamp__=dataObject["__timestamp__"])
                            case "ObjectInfo":
                                unserializedTopic = ObjectInfo(__timestamp__=dataObject["__timestamp__"])
                            case "TargetInfo":
                                unserializedTopic = TargetInfo(__timestamp__=dataObject["__timestamp__"])
                            case "Velocity":
                                unserializedTopic = Velocity(__timestamp__=dataObject["__timestamp__"])
                            case "WayPoint":
                                unserializedTopic = WayPoint(__timestamp__=dataObject["__timestamp__"])
                        if unserializedTopic != None:
                            dataByteArray = bytearray(base64.b64decode(dataObject[topic].encode('ascii')))
                            resultjson = unserializedTopic.unserialize(dataByteArray, 0, len(dataByteArray))
                            if len(resultjson.keys()) > 0:
                                dataObject[topic] = unserializedTopic
                                for subscriber in self.localSubscribers[topic]:
                                    subscriber(dataObject)
            else:
                if data != 'null':
                    print("Json loading ERROR in creating Object!!! => "+data)
                    print(traceback.format_exc())
        except:
            if data != 'null':
                print("Json loading ERROR in parse!!! => " + data)
                print(traceback.format_exc())

    def subscribe(self, subscriber: Callable[[dict], None], topic: str):
        if not topic in self.localSubscribers:
            self.localSubscribers[topic] = []

        self.localSubscribers[topic].append(subscriber)

        url = self.config.get('agent')['DDSDeploymentAddress']['schema']+'://'+self.config.get('agent')['DDSDeploymentAddress']['address']+':'+(str)(self.config.get('agent')['DDSServicePortOffset']+self.ID)+'/Subscribe'

        payload = {}
        payload["topic"] = topic
        payload["subscriber"] = self.config.get('agent')['DeploymentAddress']['schema']+'://'+self.config.get('agent')['DeploymentAddress']['address']+':'+(str)(self.config.get('agent')['ServicePortOffset']+self.ID)+'/CallBack'

        try:
            response = requests.post(url, params = payload)
            if response.ok :
                try:
                    data = json.loads(response.content)
                except:
                    raise Exception("Json loading ERROR!!!")
        except:
            print("Error in call subscribe of DDS service!!!")
            print(url)

    def __init__(self, ID : int):
        self.ID = ID
        dir_path = f'./{ID}/'
        self.localSubscribers = {}
        self.config = ConfigurationFactory()
        self.DB = localDB.getInstance(dir_path)
        DDSWrapper.instance = self
