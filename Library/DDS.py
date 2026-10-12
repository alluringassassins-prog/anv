import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

import socket
import threading
from collections.abc import Callable
from Library.ConfigurationFactory import ConfigurationFactory
from Library.localDB import localDB
from Models.Location import Location
from Models.ObjectInfo import ObjectInfo
from Models.WayPoint import WayPoint
import time
import traceback
import json
import datetime
import base64

class DDS:

    receiveHistory = False
    receiveHistoryWindow = 0
    instance = None
    myID = 0x00
    lock = None
    DB = None
    clientSocket = None
    clientThread = None
    reverseSubscribers = {}
    subscribers = {}
    localSubscribers = {}
    topicsMapping = {}
    reverseTopicMapping = {}

    instanceLock = threading.Lock()

    @staticmethod
    def getInstance(ID: int):
        if DDS.instance == None:
            with DDS.instanceLock:
                if DDS.instance == None:
                    DDS.instance = DDS(ID)
        return DDS.instance

    def publish(self, data: dict, broadcast:bool = False, specifiedTarget: int = 0):

        for key in data.keys():
            if broadcast or key in self.subscribers.keys():
                try:
                    packetLen = b''
                    packet = bytearray(b'\x00\x00\x00')
                    packet = packet + bytearray(base64.b64decode(data[key].encode('ascii')))
                    packetLen += bytes([len(packet).to_bytes(2, 'big')[1]])
                    packet[0] = self.myID
                    packet[1] = self.topicsMapping[key].to_bytes(2, 'big')[1]
                    if broadcast:
                        packet[2] = packet[2] | 0x80
                        with self.lock:

                            # if self.myID == 110:
                            #     print("Publish DDS")
                            #     print(packet)

                            self.clientSocket.send(packetLen)
                            self.clientSocket.send(bytes(packet))
                    else:
                        if specifiedTarget > 0:
                            packet[2] = specifiedTarget.to_bytes(2, 'big')[1]

                            # if self.myID == 110:
                            #     print("Publish DDS")
                            #     print(packet)

                            self.clientSocket.send(packetLen)
                            self.clientSocket.send(bytes(packet))
                        else:
                            for agent in self.subscribers[key]:
                                with self.lock:
                                    packet[2] = agent.to_bytes(2, 'big')[1]

                                    # if self.myID == 110:
                                    #     print("Publish DDS")
                                    #     print(packet)

                                    self.clientSocket.send(packetLen)
                                    self.clientSocket.send(bytes(packet))
                    
                    self.DB.insert("Publish", {key:data[key]})
                except (RuntimeError, OSError):
                    pass
                else:
                    pass
                finally:
                    pass
            if specifiedTarget == 0 and key in self.localSubscribers.keys():
                try:
                    packet = {}
                    packet["Len"] = 0
                    packet["Sender"] = self.myID
                    packet["Receiver"] = self.myID
                    packet["IsBroadcast"] = broadcast
                    packet["Topic"] = key
                    packet[key] = data[key]
                    for callback in self.localSubscribers[key]:
                        callback(packet)
                except (RuntimeError, OSError):
                    pass
                else:
                    pass
                finally:
                    pass

    def processSocket(self, thesocket: socket.socket):
        while True:
            try:
                with self.lock:
                    thesocket.settimeout(0.1)
                    dataLen = thesocket.recv(1)
                    if len(dataLen) == 1:
                        tryCounter = 0
                        data = bytearray(thesocket.recv(dataLen[0]))
                        while len(data) < dataLen[0]:
                            tmp = thesocket.recv(dataLen[0] - len(data))
                            if len(tmp) > 0:
                                data = data + bytearray(tmp)
                            if tryCounter > 10:
                                break
                            tryCounter += 1
                        
                        # print("Subscribe callback DDS")
                        # print(data)

                        if len(data) == dataLen[0] and dataLen[0] > 2:
                            if len(data) == 3:
                                # TODO: Check for a history of data
                                # topic = "nothing"
                                if int(data[1]) in self.reverseTopicMapping:
                                    topic = self.reverseTopicMapping[int(data[1])]

                                    # if topic == 'WayPoint':
                                    #     toT = datetime.datetime.now()
                                    #     waypoints = self.DB.query("Targets", "2000-01-01 00:00:01", toT.strftime("%Y-%m-%d %H:%M:%S"))
                                    #     waypoint = WayPoint()
                                    #     for i in range(0,len(waypoints["Targets"])):
                                    #         t = TargetInfo(waypoints["Targets"][i]["timeout"])

                                    if not topic in self.subscribers:
                                        self.subscribers[topic] = []

                                    if not int(data[0]) in self.subscribers[topic]:
                                        self.subscribers[topic].append(int(data[0]))

                                    if not int(data[0]) in self.reverseSubscribers:
                                        self.reverseSubscribers[int(data[0])] = []

                                    if not topic in self.reverseSubscribers[int(data[0])]:
                                        self.reverseSubscribers[int(data[0])].append(topic)

                                    if topic in self.topicsWindowMapping:
                                        fromdate = (datetime.datetime.now() - datetime.timedelta(self.topicsWindowMapping[topic])).strftime("%Y-%m-%d %H:%M:%S")
                                        res = self.DB.query("DDS_"+topic, fromdate, None)

                                        if res:
                                            for row in res:

                                                receiveTimeStamp = row['__timestamp__']
                                                receiveTimeStamp = datetime.datetime.strptime(receiveTimeStamp, "%Y-%m-%d %H:%M:%S")

                                                timeOffset = datetime.datetime.now() - receiveTimeStamp
                                                timeOffset = timeOffset.seconds

                                                subscribePacketLen = b'\x04'
                                                subscribePacket = b''
                                                subscribePacket = subscribePacket + bytes([self.myID.to_bytes(2, 'big')[1]])
                                                subscribePacket = subscribePacket + bytes([timeOffset.to_bytes(2, 'big')[0]])
                                                subscribePacket = subscribePacket + bytes([data[0]])
                                                subscribePacket = subscribePacket + bytes([timeOffset.to_bytes(2, 'big')[1]])

                                                self.clientSocket.send(subscribePacketLen)
                                                self.clientSocket.send(bytes(subscribePacket))

                                                self.publish({topic:row[topic]}, False, int(data[0]))

                                    self.DB.insert("Subscribers", {"Topic":topic,"ID":int(data[0])})

                            elif len(data) == 4:
                                if self.myID == int(data[2]):
                                    self.receiveHistory = True
                                    self.receiveHistoryWindow = int(data[1])
                                    self.receiveHistoryWindow = self.receiveHistoryWindow * 256
                                    self.receiveHistoryWindow += int(data[3])
                            else:
                                packet = {}
                                packet["Len"] = int(dataLen[0])
                                packet["Sender"] = int(data[0])
                                packet["Receiver"] = int(data[2] & 0x7f)
                                packet["IsBroadcast"] = 1 if data[2] > 0x7f else 0

                                if int(data[1]) in self.reverseTopicMapping:
                                    packet["Topic"] = self.reverseTopicMapping[int(data[1])]
                                    packet[packet["Topic"]] = base64.b64encode(data[3:]).decode("ascii")
                                else:
                                    packet["Topic"] = 0

                                if self.receiveHistory:
                                    packet["__timestamp__"] = (datetime.datetime.now() - datetime.timedelta(seconds=self.receiveHistoryWindow)).strftime("%Y-%m-%d %H:%M:%S")
                                    self.receiveHistory = False
                                else:
                                    packet["__timestamp__"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                                if packet["Topic"] in self.localSubscribers:
                                    try:
                                        if packet["Topic"] in self.localSubscribers:
                                            for subscriber in self.localSubscribers[packet["Topic"]]:
                                                subscriber(packet)
                                    except Exception as e:
                                        packet.pop(packet["Topic"], None)

                                if type(packet["Topic"]) is str and packet["Topic"] in packet:
                                    self.DB.insert("DDS_"+packet["Topic"], {packet["Topic"]:packet[packet["Topic"]], "__timestamp__":packet["__timestamp__"]})

            except socket.timeout:
                time.sleep(0.01)
            except Exception as e:
                #TODO: do something like log an error
                print(e)
                print("Error is occured in reading from socket ...")
                print(traceback.format_exc())
                break
            else:
                pass
            finally:
                pass

    def __init__(self, ID: int):
        self.myID = ID.to_bytes(2, 'big')[1]
        self.topicsMapping = ConfigurationFactory.getInstance().get('topics')
        self.topicsWindowMapping = ConfigurationFactory.getInstance().get('topicsTimeWindow')
        self.reverseTopicMapping = { self.topicsMapping[k]:k for k in self.topicsMapping}

        self.DB = localDB.getInstance(f'./{self.myID}/')

        address = ConfigurationFactory.getInstance().get('DDS')["address"]
        port = ConfigurationFactory.getInstance().get('DDS')["port"]

        self.lock = threading.Lock()
        self.clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clientSocket.connect((address, port))

        registerPacketLen = b'\x01'
        self.clientSocket.send(registerPacketLen)
        registerPacket = bytearray([self.myID.to_bytes(2, 'big')[1]])
        self.clientSocket.send(bytes(registerPacket))

        self.clientThread = threading.Thread(target=self.processSocket, args=(self.clientSocket, ))
        self.clientThread.start()

        DDS.instance = self

    def subscribe(self, subscriber: Callable[[dict], None], topic: str):
        if not topic in self.localSubscribers:
            self.localSubscribers[topic] = []

        self.localSubscribers[topic].append(subscriber)

        if topic in self.topicsMapping:
            subscribePacketLen = b'\x03'
            subscribePacket = bytearray(b'\x00\x00\x80')
            subscribePacket[0] = self.myID.to_bytes(2, 'big')[1]
            subscribePacket[1] = self.topicsMapping[topic].to_bytes(2, 'big')[1]
            self.clientSocket.send(subscribePacketLen)
            self.clientSocket.send(bytes(subscribePacket))
