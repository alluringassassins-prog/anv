import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

from Library.ConfigurationFactory import ConfigurationFactory
from Models.Topic import Topic
from Models.TargetInfo import TargetInfo

class WayPoint(Topic):
    count: int
    targets=None

    def __init__(self, count: int=0, deadline: int=1, behave: int=2, lat: float=0, lon: float=0, alt: float=0, __timestamp__:str=''):

        super().__init__(__timestamp__)

        self.count = count
        self.targets = []
        for i in range(count):
            self.targets.append(TargetInfo(deadline, behave, lat, lon, alt))
    
    def __str__(self):
        loc = ""
        for i in range(self.count):
            if i > 0:
                loc += ","
            loc += self.targets[i].__str__()
        return f'{{"count":{self.count},"Targets":[{loc}]}}'

    def serialize(self)->bytes:
        packet = b''

        packet = packet + bytes([self.count.to_bytes(2, 'big')[1]])

        for i in range(self.count):
            packet = packet + self.targets[i].serialize()

        return packet
    
    def unserialize(self, input: bytes, offset: int, length: int):

        self.count = int(input[offset])
        if length == (self.count*7+1):
            self.targets = []
            for i in range(self.count):
                self.targets.append(TargetInfo(__timestamp__=self.timestamp))
                self.targets[i].unserialize(input, offset+1+i*7, 7)

            return json.loads(self.__str__())
        else:
            print("Error in parse WayPoint, insufficient data")
            return {}

    def append(self, target: TargetInfo):
        self.targets.append(target)
        self.count = len(self.targets)


            
