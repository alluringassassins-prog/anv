import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

from Library.ConfigurationFactory import ConfigurationFactory
from Models.Topic import Topic

class Direction(Topic) :
    def __init__(self, alpha: int=0, beta: int=0, gamma: int=0, __timestamp__:str=''):

        super().__init__(__timestamp__)

        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

        if self.alpha < 0:
            self.alpha *= -1
        if self.beta < 0:
            self.beta *= -1
        if self.gamma < 0:
            self.gamma *= -1
            
        if self.alpha > 180:
            self.alpha = self.alpha % 180
    
        if self.beta > 180:
            self.beta = self.beta % 180
    
        if self.gamma > 180:
            self.gamma = self.gamma % 180

    def __str__(self):
        return f'{{"alpha":{self.alpha},"beta":{self.beta},"gamma":{self.gamma}}}'

    def serialize(self)->bytes:
        packet = b''

        packet = packet + bytes([int(self.alpha).to_bytes(2, 'big')[1]])
        packet = packet + bytes([int(self.beta).to_bytes(2, 'big')[1]])
        packet = packet + bytes([int(self.gamma).to_bytes(2, 'big')[1]])

        return packet
    
    def unserialize(self, input: bytes, offset: int, length: int):

        self.alpha = 0
        self.beta = 0
        self.gamma = 0

        if length == 3:
            self.alpha = int(input[offset+0])
            self.beta = int(input[offset+1])
            self.gamma = int(input[offset+2])
            return {"alpha": self.alpha, "beta": self.beta, "gamma": self.gamma}
        else:
            print("Error in parse direction, insufficient data")
            return {}


            
