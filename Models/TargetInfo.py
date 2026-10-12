import sys
import datetime
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

from Library.ConfigurationFactory import ConfigurationFactory
from Models.Topic import Topic
from Models.Location import Location
from Models.Velocity import Velocity

class TargetInfo(Topic):
    deadline: int
    behave: int
    location: Location
    isReached: bool

    def __init__(self, timeout: int=1, behave: int=2, lat: float=0, lon: float=0, alt: float=0, deadline: str = '', __timestamp__:str=''):

        super().__init__(__timestamp__)

        self.timeout = timeout
        if len(deadline) > 0:
            self.deadline = datetime.datetime.strptime(deadline, "%Y-%m-%d %H:%M:%S")
        else:
            self.deadline = datetime.datetime.strptime(self.timestamp, "%Y-%m-%d %H:%M:%S") + datetime.timedelta(seconds=self.timeout)
        self.behave = behave
        self.isReached = False
        self.location = Location(lat, lon, alt, __timestamp__)
    
    def __str__(self):
        loc = self.location.__str__()
        return f'{{"timeout":{self.timeout},"deadline":"{self.deadline.strftime("%Y-%m-%d %H:%M:%S")}","behave":{self.behave},"location":{loc}}}'

    def serialize(self)->bytes:
        packet = b''

        packet = packet + bytearray(self.timeout.to_bytes(2, 'big'))
        packet = packet + bytes([self.behave.to_bytes(2, 'big')[1]])

        packet = packet + self.location.serialize()

        return packet
    
    def unserialize(self, input: bytes, offset: int, length: int):

        if length == 7:

            self.timeout = int(input[offset])
            self.timeout *= 256
            self.timeout += int(input[offset+1])
            self.deadline = datetime.datetime.strptime(self.timestamp, "%Y-%m-%d %H:%M:%S") + datetime.timedelta(seconds=self.timeout)
            self.behave = int(input[offset+2])
            self.location.unserialize(input, offset+3, 4)

            return json.loads(self.__str__())
        else:
            print("Error in parse TargetInfo, insufficient data")
            return {}


            
