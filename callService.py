import sys
import time
import requests
import json
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

url = "http://127.0.0.1:8000/"

clear = lambda: os.system('clear')

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

def putObject():
    body = {}
    ID = input("Enter the object ID: ")
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
    body["location"] = getLocation()
    body["velocity"] = getVelocity()
    body["type"] = objectType
    body["party"] = party

    service = url + "put/" + ID

    try:
        response = requests.post(service, data=json.dumps(body))

        print("\n\nService Response:")
        print("    ", end="")
        print(response.text)
        print("\n\n")
    except:
        print("Error in connecting to environment server or bad response")

def gotoLocation():
    body = {}
    ID = input("Enter the object ID: ")
    body["location"] = getLocation()
    while True:
        try:
            timeout = int(input("Enter timeout in seconds: "))
            break
        except:
            print("Invalid input! Try again.")
    body["timeout"] = timeout
    while True:
        mode = input("Enter receipt behaviour ([P]ass/[S]top): ")
        mode = mode.upper()
        if mode == 'P' or mode == 'S':
            match mode:
                case "P":
                    mode = 2
                case "S":
                    mode = 1
            break
        else:
            print("Invalid receipt behaviour! Try again.")
    body["finalPointMode"] = mode

    service = url + "goto/" + ID

    try:
        response = requests.post(service, data=json.dumps(body))

        print("\n\nService Response:")
        print("    ", end="")
        print(response.text)
        print("\n\n")
    except:
        print("Error in connecting to environment server or bad response")

def doManeuver():
    body = {}
    ID = input("Enter the object ID: ")
    body = getVelocity()

    service = url + "move/" + ID

    try:
        response = requests.post(service, data=json.dumps(body))

        print("\n\nService Response:")
        print("    ", end="")
        print(response.text)
        print("\n\n")
    except:
        print("Error in connecting to environment server or bad response")

def stopObject():
    body = {}
    ID = input("Enter the object ID: ")

    service = url + "stop/" + ID

    try:
        response = requests.post(service, data=json.dumps(body))

        print("\n\nService Response:")
        print("    ", end="")
        print(response.text)
        print("\n\n")
    except:
        print("Error in connecting to environment server or bad response")

def getLocalEnvironment():
    ID = input("Enter the object ID: ")
    while True:
        try:
            radius = float(input("Enter sight radius: "))
            break
        except:
            print("Invalid input! Try again.")
    service = url + "environment/" + ID + "/" + str(radius)

    try:
        response = requests.get(service)

        print("\n\nService Response:")
        print("    ", end="")
        print(response.text)
        print("\n\n")
    except:
        print("Error in connecting to environment server or bad response")

def getEnvironment():
    service = url + "environment"

    try:
        response = requests.get(service)

        print("\n\nService Response:")
        print("    ", end="")
        print(response.text)
        print("\n\n")
    except:
        print("Error in connecting to environment server or bad response")

def showMenu() -> int:
    print("Select one of theses services:")
    print("[1] put object")
    print("[2] get around an object")
    print("[3] get entire of the environment")
    print("[4] goto a location")
    print("[5] do a maneuver")
    print("[6] stop an object")
    print("[7] exit")

    while True:
        try:
            choice = int(input("what is your choice? "))
            if choice > 0 and choice < 8:
                return choice
            else:
                print("Invalid option! Try again.")
        except:
            print("Invalid input! Try again.")

clear()
while True:
    choice = showMenu()
    match choice:
        case 1:
            putObject()
        case 2:
            getLocalEnvironment()
        case 3:
            getEnvironment()
        case 4:
            gotoLocation()
        case 5:
            doManeuver()
        case 6:
            stopObject()
        case 7:
            print("Bye!!!")
            for i in range(20):
                print(".", end="", flush=True)
                time.sleep(0.1)
            clear()
            break
        case _:
            print("Invalid option! Try again.")