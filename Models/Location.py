import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

from Library.ConfigurationFactory import ConfigurationFactory
from Models.Topic import Topic

class Location(Topic):
    def __init__(self, lat: float=0, lon: float=0, alt: float=0, __timestamp__:str=''):

        super().__init__(__timestamp__)

        self.latitude = lat
        self.longitude = lon
        self.altitude = alt
    
    def __str__(self):
        return f'{{"lat":{self.latitude},"lon":{self.longitude},"alt":{self.altitude}}}'

    def serialize(self, dimensionLen: int=1)->bytes:
        zoomlevel = ConfigurationFactory.getInstance().get("Extent")["zoomlevel"]
        extent = ConfigurationFactory.getInstance().get("Extent")["center"]

        scaleDiscretization = pow(2,dimensionLen*8) 
        max_possible_delta = 180/pow(2,zoomlevel)
        scaleQuantum = max_possible_delta / scaleDiscretization

        d_lat = abs(self.latitude - extent["lat"])
        d_lon = abs(self.longitude - extent["lon"])
        d_alt = abs(self.altitude - extent["alt"])
        
        signs = 0x00

        if self.latitude < extent["lat"]:
            signs = signs | 0x01

        if self.longitude < extent["lon"]:
            signs = signs | 0x02

        if self.altitude < extent["alt"]:
            signs = signs | 0x04

        packet = b''

        d_lat = int(d_lat / scaleQuantum)
        d_lon = int(d_lon / scaleQuantum)
        d_alt = int(d_alt / scaleQuantum)

        if dimensionLen == 1:
            packet = packet + bytes([d_lat.to_bytes(2, 'big')[1]])
        else:
            packet = packet + d_lat.to_bytes(dimensionLen, 'big')

        if dimensionLen == 1:
            packet = packet + bytes([d_lon.to_bytes(2, 'big')[1]])
        else:
            packet = packet + d_lon.to_bytes(dimensionLen, 'big')

        if dimensionLen == 1:
            packet = packet + bytes([d_alt.to_bytes(2, 'big')[1]])
        else:
            packet = packet + d_alt.to_bytes(dimensionLen, 'big')

        packet = packet + bytes([signs])

        return packet
    
    def unserialize(self, input: bytes, offset: int, length: int, dimensionLen: int=1):

        lat = 0.0
        lon = 0.0
        alt = 0.0

        if length == (dimensionLen*3 + 1):
            zoomlevel = ConfigurationFactory.getInstance().get("Extent")["zoomlevel"]
            extent = ConfigurationFactory.getInstance().get("Extent")["center"]

            scaleDiscretization = pow(2,dimensionLen*8)
            max_possible_delta = 180/pow(2,zoomlevel)
            scaleQuantum = max_possible_delta / scaleDiscretization

            if dimensionLen == 1:
                lat = int(input[offset+0])
            else:
                lat = int(input[offset+0])
                lat *= 256
                lat += int(input[offset+1])

            if dimensionLen == 1:
                lon = int(input[offset+1])
            else:
                lon = int(input[offset+2])
                lon *= 256
                lon += int(input[offset+3])

            if dimensionLen == 1:
                alt = int(input[offset+2])
            else:
                alt = int(input[offset+4])
                alt *= 256
                alt += int(input[offset+5])

            lat *= scaleQuantum
            lon *= scaleQuantum
            alt *= scaleQuantum

            signs = input[offset+dimensionLen*3]

            latSign = signs & 0x01
            lonSign = signs & 0x02
            altSign = signs & 0x04

            if latSign > 0:
                lat = extent["lat"] - lat
            else:
                lat = lat + extent["lat"]

            if lonSign > 0:
                lon = extent["lon"] - lon
            else:
                lon = lon + extent["lon"]

            if altSign > 0:
                alt = extent["alt"] - alt
            else:
                alt = alt + extent["alt"]

            self.latitude = lat
            self.longitude = lon
            self.altitude = alt

            return {"latitude": lat, "longitude": lon, "altitude": alt}
        else:
            print("Error in parse location, insufficient data")
            return {}



            
