import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

from Library.ConfigurationFactory import ConfigurationFactory
from Models.Location import Location
from Models.Velocity import Velocity
from Models.Topic import Topic

class ObjectInfo(Topic):
    type: str
    party: str
    location: Location
    velocity: Velocity

    def __init__(self, ID:int=0,type: str='drone', party: str='friend', lat: float=0, lon: float=0, alt: float=0, speed: int=0, acceleration: int=0, alpha: int=0, beta: int=0, gamma: int=0, __timestamp__:str=''):

        super().__init__(__timestamp__)

        self.type = type
        self.party = party
        self.ID = ID
        self.location = Location(lat, lon, alt, __timestamp__)
        self.velocity = Velocity(speed, acceleration, alpha, beta, gamma, __timestamp__)
    
    def __str__(self):
        loc = self.location.__str__()
        vel = self.velocity.__str__()
        return f'{{"ID":{self.ID},"type":"{self.type}","party":"{self.party}","location":{loc},"velocity":{vel}}}'

    def serialize(self)->bytes:
        packet = b''

        data = 0

        match self.type:
            case "boat":
                data = 1
            case "drone":
                data = 2
            case "ship":
                data = 3

        data *= 16

        match self.party:
            case "enemy":
                data += 1
            case "friend":
                data += 2
            case "gray":
                data += 3
            case "neutral":
                data += 4

        packet = packet + bytes([self.ID.to_bytes(2, 'big')[1]])

        packet = packet + bytes([data.to_bytes(2, 'big')[1]])

        packet = packet + self.location.serialize()
        packet = packet + self.velocity.serialize()

        return packet
    
    def unserialize(self, input: bytes, offset: int, length: int):

        self.type = "drone"
        self.party = "friend"

        if length > 6:

            self.ID = int(input[offset])

            dataType = int(input[offset+1])
            dataType = int(dataType/16)
            dataParty = int(input[offset+1])
            dataParty = dataParty % 16

            match dataType:
                case 1:
                    self.type = "boat"
                case 2:
                    self.type = "drone"
                case 3:
                    self.type = "ship"

            match dataParty:
                case 1:
                    self.party = "enemy"
                case 2:
                    self.party = "friend"
                case 3:
                    self.party = "gray"
                case 4:
                    self.party = "neutral"

            self.location.unserialize(input, offset+2, 4)
            self.velocity.unserialize(input, offset+6, length-6)

            return json.loads(self.__str__())
        else:
            print("Error in parse ObjectInfo, insufficient data")
            return {}


            
