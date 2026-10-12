import time
import os
import requests
import json
import sys
import random
from multiprocessing import Process
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

from Library.DDSWrapper import *
from Library.ConfigurationFactory import *
from AgentLibrary.Agent import *
from AgentLibrary.DDSService import *
from Models.Location import Location
from Models.TargetInfo import TargetInfo

clear = lambda: os.system('clear')
url = ""
bots = []
objects = {}

dir_path = './110/'

# List all files in the directory
if os.path.exists(dir_path):
    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)

        # Check if it is a file (not a subdirectory)
        if os.path.isfile(file_path):
            os.remove(file_path)  # Remove the file

dds = DDSWrapper.getInstance(110)

def getVelocity() -> dict:
    while True:
        try:
            alpha = float(input("Enter direction Alpha angel: "))
            break
        except:
            print("Invalid input! Try again.")
    while True:
        try:
            beta = float(input("Enter direction Beta angel: "))
            break
        except:
            print("Invalid input! Try again.")
    while True:
        try:
            gamma = float(input("Enter direction Gamma angel: "))
            break
        except:
            print("Invalid input! Try again.")
    while True:
        try:
            speed = float(input("Enter Speed: "))
            break
        except:
            print("Invalid input! Try again.")
    while True:
        try:
            acceleration = float(input("Enter Acceleration: "))
            break
        except:
            print("Invalid input! Try again.")
    return {"direction":{"alpha":alpha,"beta":beta,"gamma":gamma},"speed":speed,"acceleration":acceleration}

def getLocation() -> dict:
    while True:
        try:
            latitude = float(input("Enter location Latitude: "))
            break
        except:
            print("Invalid input! Try again.")
    while True:
        try:
            longitude = float(input("Enter location Longitude: "))
            break
        except:
            print("Invalid input! Try again.")
    while True:
        try:
            altitude = float(input("Enter location Altitude: "))
            break
        except:
            print("Invalid input! Try again.")
    return {"lat":latitude,"lon":longitude,"alt":altitude}

def showMenu(menu: dict)->int:
    for key,value in menu.items():
        print(f'[{key}] {value}')
    print("    What is your choice: ", end='')

    while True:
        choice = input()
        try:
            result = int(choice)
            if menu.get(result) == None:
                print("    Your input should be one of the menu item numbers.")
                print("    What is your choice: ", end='')
            else:
                return result
        except:
            print("    Your input should be one of the menu item numbers.")
            print("    What is your choice: ", end='')

def initiateBot(conf: dict):
    d = Agent(int(conf["ID"]))
    #TODO: set initial speed and location
    while True:
        time.sleep(10)

def initiateBotDDS(conf: dict):
    d = DDSService(int(conf["ID"]))
    #TODO: set initial speed and location
    while True:
        time.sleep(10)

def putAnObject(pID=0,pType=None,pParty=None,lat=None,lon=None,alt=None,speed=None,acceleration=None,alpha=None,beta=None,gamma=None):
    body = {}
    if int(pID) > 0:
        ID = int(pID)
    else:
        while True:
            try:
                ID = int(input("Enter the object ID: "))
                if ID in objects:
                    print("This ID has been put earlier and should not been put again.")
                else:
                    break
            except:
                print("ID should be an integer!!!")
    if pType != None:
        objectType = pType
    else:
        while True:
            objectType = input("Enter object type ([B]oat/[D]rone/[S]hip): ")
            objectType = objectType.upper()
            if objectType == 'B' or objectType == 'D' or objectType == 'S':
                match objectType:
                    case "B":
                        objectType = "boat"
                    case "D":
                        objectType = "drone"
                    case "S":
                        objectType = "ship"
                break
            else:
                print("Invalid object type! Try again.")
    if pParty != None:
        party = pParty
    else:
        while True:
            party = input("Enter party ([E]nemy/[F]riend/[G]ray/[N]eutral): ")
            party = party.upper()
            if party == 'E' or party == 'F' or party == 'G' or party == 'N':
                match party:
                    case "E":
                        party = "enemy"
                    case "F":
                        party = "friend"
                    case "G":
                        party = "gray"
                    case "N":
                        party = "neutral"
                break
            else:
                print("Invalid object type! Try again.")

    if lat != None and lon != None and alt != None:
        body["location"] = {"lat":lat,"lon":lon,"alt":alt}
    else:
        body["location"] = getLocation()
    if speed != None and acceleration != None and alpha != None and beta != None and gamma != None:
        body["velocity"] = {"direction":{"alpha":alpha,"beta":beta,"gamma":gamma},"speed":speed,"acceleration":acceleration}
    else:
        body["velocity"] = getVelocity()
    body["type"] = objectType
    body["party"] = party

    objects[ID] = body

    if ConfigurationFactory.getInstance().get("InformEnvironment") == 1:
        service = url + "put/" + str(ID)
        try:
            response = requests.put(service, json=body)

            if int(pID) < 1:
                print("\n\nService Response:")
                print("    ", end="")
                print(response.text)
                print("\n\n")
        except:
            print("Error in connecting to environment server or bad response")

    if body["party"] == 'friend' and ConfigurationFactory.getInstance().get("InitiateProcess") == 1:
        body["ID"] = ID
        p = Process(target=initiateBot, args=(body,))
        p.start()
        bots.append(p)

def putRandomObjects(count: int=0, ID:int=0,lat:float=0,lon:float=0,alt:float=0,objectType:str=None):
    zoomlevel = ConfigurationFactory.getInstance().get("Extent")["zoomlevel"]
    eachDegreeScale = 100000000 / 90

    body = {}
    if count < 1:
        while True:
            try:
                count = int(input("Enter the number of objects: "))
                break
            except:
                print("Objects count should be an integer!!!")

    if ID < 1:
        while True:
            try:
                ID = int(input("Enter the first object ID: "))
                if ID in objects:
                    print("This ID has been put earlier and should not been put again.")
                else:
                    break
            except:
                print("ID should be an integer!!!")
    if lat == 0:
        location = getLocation()
    else:
        location = {"lat":lat, "lon":lon, "alt":alt}
    party = "friend"
    velocity = {"direction":{"alpha":0,"beta":0,"gamma":0}, "speed":0, "acceleration":0}

    if objectType == None:
        while True:
            objectType = input("Enter object type ([B]oat/[D]rone/[S]hip): ")
            objectType = objectType.upper()
            if objectType == 'B' or objectType == 'D' or objectType == 'S':
                match objectType:
                    case "B":
                        objectType = "boat"
                    case "D":
                        objectType = "drone"
                    case "S":
                        objectType = "ship"
                break
            else:
                print("Invalid object type! Try again.")

    for i in range(count):

        tmpLocation = location

        tmpLocation["lat"] += ((random.random() - 0.5) * ConfigurationFactory.getInstance().get("maxLegalDistance")) / eachDegreeScale
        tmpLocation["lon"] += ((random.random() - 0.5) * ConfigurationFactory.getInstance().get("maxLegalDistance")) / eachDegreeScale
        tmpLocation["alt"] += ((random.random() - 0.5) * ConfigurationFactory.getInstance().get("maxLegalDistance")) / eachDegreeScale

        body = {"location":tmpLocation,"velocity":velocity,"type":objectType,"party":"friend"}

        objects[ID+i] = body

        if ConfigurationFactory.getInstance().get("InformEnvironment") == 1:
            service = url + "put/" + str(ID+i)
            try:
                response = requests.put(service, json=body)
            except:
                print("Error in connecting to environment server or bad response")

        if ConfigurationFactory.getInstance().get("InitiateProcess") == 1:
            body["ID"] = ID+i
            p = Process(target=initiateBot, args=(body,))
            p.start()
            bots.append(p)

def sendNewTarget():
    print("Get new target info")
    while True:
        try:
            deadline = int(input("Enter deadline in seconds: "))
            break
        except:
            print("Deadline should be an integer and it's in seconds.")
    while True:
        try:
            behave = int(input("Enter receive behaviour: [1] Stop [2] Pass: "))
            if behave != 1 and behave != 2:
                print("Input should be 1 or 2.")
            else:
                break
        except:
            print("Input should be 1 or 2.")
    
    location = getLocation()

    specific_bot = input("Enter agent id (leave empty to match all agents): ")
    specific_bot = specific_bot.strip()

    if ConfigurationFactory.getInstance().get("InformEnvironment") == 1:
        body = {}
        body['timeout'] = deadline
        body['location'] = location
        body['finalPointMode'] = behave
        for obj_id in objects:
            if objects[obj_id]["party"] == 'friend' and (len(specific_bot) == 0 or specific_bot == obj_id):
                service = url + "goto/" + obj_id
                try:
                    response = requests.post(service, json=body)

                    print("\n\nService Response:")
                    print("    ", end="")
                    print(response.text)
                    print("\n\n")
                except:
                    print("Error in connecting to environment server or bad response")

    #TODO: Send to DDS

def sendTargets():
    zoomlevel = ConfigurationFactory.getInstance().get("Extent")["zoomlevel"]
    eachDegreeScale = 100000000 / 90

    print("Get targets info")
    while True:
        try:
            count = int(input("Enter the number of way points: "))
            break
        except:
            print("Count should be an integer.")

    targets = []
    w = WayPoint()
    for i in range(count):
        print("Enter next way point")
        while True:
            try:
                deadline = int(input("Enter deadline in seconds: "))
                break
            except:
                print("Deadline should be an integer and it's in seconds.")
        if i == (count-1):
            while True:
                try:
                    behave = int(input("Enter receive behaviour: [1] Stop [2] Pass: "))
                    if behave != 1 and behave != 2:
                        print("Input should be 1 or 2.")
                    else:
                        break
                except:
                    print("Input should be 1 or 2.")
        else:
            behave = 2
    
        location = getLocation()

        putAnObject(str(random.randint(200,250)), "boat", "neutral",location["lat"],location["lon"],location["alt"],0,0,0,0,0)
        w.append(TargetInfo(deadline,behave,location["lat"],location["lon"],location["alt"]))

        if i == (count-1):
            tmpLocation = location
            tmpLocation["lat"] += ((random.random() - 0.5) * 2 * ConfigurationFactory.getInstance().get("minLegalDistance")) / eachDegreeScale
            tmpLocation["lon"] += ((random.random() - 0.5) * 2 * ConfigurationFactory.getInstance().get("minLegalDistance")) / eachDegreeScale
            tmpLocation["alt"] += ((random.random() - 0.5) * 2 * ConfigurationFactory.getInstance().get("minLegalDistance")) / eachDegreeScale
            putAnObject(str(random.randint(200,250)), "boat", "enemy",tmpLocation["lat"],tmpLocation["lon"],tmpLocation["alt"],0,0,0,0,0)
    
    dds.publish({"WayPoint":w}, True)    

def loadDefault():
    zoomlevel = ConfigurationFactory.getInstance().get("Extent")["zoomlevel"]
    eachDegreeScale = 100000000 / 90

    with open("waypoints.json") as scenFile:
        scenario = json.load(scenFile)

        putRandomObjects(scenario["scenario"]["count"],scenario["scenario"]["ID"],scenario["scenario"]["lat"],scenario["scenario"]["lon"],scenario["scenario"]["alt"],scenario["scenario"]["type"])

        if ConfigurationFactory.getInstance().get("InitiateProcess") != 1:
            input("If all agents are running press enter to continue. ")
        else:
            time.sleep(3*ConfigurationFactory.getInstance().get("warmupDuration"))

        w = WayPoint()
        for i in range(len(scenario["waypoints"])):
            if i == (len(scenario["waypoints"])-1):
                behave = scenario["waypoints"][i]["behave"]
            else:
                behave = 2
        
            w.append(TargetInfo(scenario["waypoints"][i]["timeout"],behave,scenario["waypoints"][i]["lat"],scenario["waypoints"][i]["lon"],scenario["waypoints"][i]["alt"]))
            putAnObject(str(random.randint(200,250)), "boat", "neutral",scenario["waypoints"][i]["lat"],scenario["waypoints"][i]["lon"],scenario["waypoints"][i]["alt"],0,0,0,0,0)

            if i == (len(scenario["waypoints"])-1):
                tmpLocation = {}
                tmpLocation["lat"] = (scenario["waypoints"][i-1]["lat"]+scenario["waypoints"][i]["lat"])/2
                tmpLocation["lon"] = (scenario["waypoints"][i-1]["lon"]+scenario["waypoints"][i]["lon"])/2
                tmpLocation["alt"] = (scenario["waypoints"][i-1]["alt"]+scenario["waypoints"][i]["alt"])/2
                # tmpLocation = scenario["waypoints"][i]
                tmpLocation["lat"] += ((random.random() - 0.5) * 2 * ConfigurationFactory.getInstance().get("minLegalDistance")) / eachDegreeScale
                tmpLocation["lon"] += ((random.random() - 0.5) * 2 * ConfigurationFactory.getInstance().get("minLegalDistance")) / eachDegreeScale
                tmpLocation["alt"] += ((random.random() - 0.5) * 2 * ConfigurationFactory.getInstance().get("minLegalDistance")) / eachDegreeScale
                putAnObject(str(random.randint(200,250)), "boat", "enemy",tmpLocation["lat"],tmpLocation["lon"],tmpLocation["alt"],0,0,0,0,0)

        
        dds.publish({"WayPoint":w}, True)    


def setMinDistanceParam():
    while True:
        try:
            minDistance = int(input("Enter minimum acceptable distance between agents (in meters): "))
            break
        except:
            print("Minimum distance should be an integer and it's in meters.")
    #TODO: Send to DDS

def setMaxDistanceParam():
    while True:
        try:
            minDistance = int(input("Enter maximum acceptable distance between agents (in meters): "))
            break
        except:
            print("Maximum distance should be an integer and it's in meters.")
    #TODO: Send to DDS

def doManoeuver():
    print("Get manoeuver info")
    manoeuver = getVelocity()

    specific_bot = input("Enter agent id (leave empty to match all agents): ")
    specific_bot = specific_bot.strip()

    if ConfigurationFactory.getInstance().get("InformEnvironment") == 1:
        for obj_id in objects:
            if objects[obj_id]["party"] == 'friend' and (len(specific_bot) == 0 or specific_bot == obj_id):
                service = url + "move/" + obj_id
                try:
                    response = requests.post(service, json=manoeuver)

                    print("\n\nService Response:")
                    print("    ", end="")
                    print(response.text)
                    print("\n\n")
                except:
                    print("Error in connecting to environment server or bad response")

    #TODO: Send to DDS

def stop():
    specific_bot = input("Enter agent id: ")
    specific_bot = specific_bot.strip()

    if ConfigurationFactory.getInstance().get("InformEnvironment") == 1:
        for obj_id in objects:
            if specific_bot == obj_id:
                service = url + "stop/" + obj_id
                try:
                    response = requests.post(service)

                    print("\n\nService Response:")
                    print("    ", end="")
                    print(response.text)
                    print("\n\n")
                except:
                    print("Error in connecting to environment server or bad response")

    #TODO: Send to DDS

def terminate():
    print("    Bye!!!", end='', flush=True)
    for p in bots:
        p.kill()
    for i in range(10):
        time.sleep(0.1)
        print(".", end='', flush=True)
    exit()

def sendNewApproach():
    pass

def showStatus():
    pass

switcher = {
    1: putAnObject,
    2: putRandomObjects,
    3: sendTargets,
    4: loadDefault,
    # 4: setMinDistanceParam,
    # 5: setMaxDistanceParam,
    6: doManoeuver,
    7: stop,
    #8: sendNewApproach,
    #9: showStatus,
    9: terminate
}

menu = {
    1: "Put an object in environment",
    2: "Put random objects in environment",
    3: "Set way point and the target",
    4: "Load default waypoint and scenario",
    #4: "Set min legal distance between bots",
    #5: "Set max legal distance between bots",
    6: "Do a manoeuver",
    7: "Stop an agent",
    #8: "Set approach points",
    #9: "Show current status",
    9: "Exit"
}

if __name__ == '__main__':
    env = ConfigurationFactory.getInstance().get("environment")
    url = env['server']['schema'] + "://" + env['server']['address'] + ":" + env['server']['port'] + "/"

    body = {}
    body["ID"] = 110
    p = Process(target=initiateBotDDS, args=(body,))
    p.start()

    print("Loading", end="", flush=True)
    for i in range(10):
        print(".", end="", flush=True)
        time.sleep(0.5)
    print(flush=True)

    while True:
        choice = showMenu(menu)
        switcher.get(choice, lambda: "unknown")()
