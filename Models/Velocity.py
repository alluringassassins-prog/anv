import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

from Library.ConfigurationFactory import ConfigurationFactory
from Models.Topic import Topic
from Models.Direction import Direction

class Velocity(Topic):
    def __init__(self, speed: int=0, acceleration: int=0, alpha: int=0, beta: int=0, gamma: int=0, __timestamp__:str=''):

        super().__init__(__timestamp__)

        self.speed = speed
        self.acceleration = acceleration
        self.direction = Direction(alpha, beta, gamma, __timestamp__)
    
    def __str__(self):
        direction = self.direction.__str__()
        return f'{{"speed":{self.speed},"acceleration":{self.acceleration},"direction":{direction}}}'

    def serialize(self)->bytes:
        packet = b''

        tmp = bytearray(int(abs(self.speed)).to_bytes(2, 'big'))
        if self.speed < 0:
            tmp[0] = tmp[0] | 0x80
        packet = packet + tmp

        tmp = bytes([int(abs(self.acceleration)).to_bytes(2, 'big')[1]])
        tmp = bytearray(tmp)
        if self.acceleration < 0:
            tmp[0] = tmp[0] | 0x80
        packet = packet + tmp

        packet = packet + self.direction.serialize()

        return packet
    
    def unserialize(self, input: bytes, offset: int, length: int):
        speed = 0
        acceleration = 0

        if length > 3:
            speed = int(input[offset+0] & 0x7f)
            speed *= 256
            speed += int(input[offset+1])

            if input[offset+0] & 0x80 > 0:
                speed *= -1

            acceleration = int(input[offset+2] & 0x7f)
            if input[offset+2] & 0x80 > 0:
                acceleration *= -1

            self.speed = speed
            self.acceleration = acceleration

            self.direction.unserialize(input, offset+3, length-3)

            return json.loads(self.__str__())
        else:
            print("Error in parse Velocity, insufficient data")
            return {}



            
