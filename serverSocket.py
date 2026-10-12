import socket
import threading
import time
from Library.ConfigurationFactory import ConfigurationFactory

clientIDS = {}
Exceptions = []

def processSocket(thesocket:socket.socket):
    # len/sender/receiver[>127 means it is not real receiver and receives in broadcast]/type/data...
    # data = b'\x0c\x0a\x8f\x01\x12\x13\x14\x15\x16\x17\x18\x19\x20'
    global Exceptions
    global clientIDS
    socketIsAssigned = False
    myID = 0x00
    breakCount = 0
    while True:
        try:
            dataLen = thesocket.recv(1)
            if len(dataLen) == 1:
                data = bytearray(thesocket.recv(dataLen[0]))
                tryCount = 0
                while len(data) < dataLen[0] and tryCount < 10:
                    data = data + bytearray(thesocket.recv(dataLen[0] - len(data)))
                    ++tryCount

                # print("Bus received data")
                # print(data)

                # if len(data) > 3 and data[1] == 0x06:
                #     print("Bus received data")
                #     print(data)
                #     print(clientIDS)
                #     print()

                if len(data) == dataLen[0]:
                    if not socketIsAssigned:
                        clientIDS[data[0]] = thesocket
                        myID = data[0]
                        socketIsAssigned = True

                    if len(data) > 1:
                        for id in clientIDS:
                            if id != myID:
                                broken = False
                                for exp in Exceptions:
                                    if exp[0] == myID and exp[1] == id:
                                        broken = True
                                        break
                                if not broken:
                                    if (data[2] & 0x80) > 0 or data[2] == id:
                                        tmpData = data
                                        tmpData[2] = (data[2] & 0x80) | id
                                        sendBreakCount = 0
                                        while sendBreakCount < 5:
                                            try:
                                                clientIDS[id].send(dataLen)
                                                clientIDS[id].send(bytes(tmpData))
                                                break
                                            except:
                                                time.sleep(0.001)
                                            ++sendBreakCount
                                        if sendBreakCount >= 5:
                                            clientIDS.pop(id)
                else:
                    print("Received data is not matched with required length!!!")
                    print(f'{dataLen[0]} -> The desired Length')
                    print(f'{data} -> received data')
                    print(f'{tryCount} times have been tried')
            else:
                time.sleep(0.01)
        except Exception as e:
            #TODO: do something like log an error
            # print(e)
            # print(f'BreakCount: {breakCount}')
            ++breakCount
            if breakCount > 5:
                clientIDS.pop(myID)
                break
        else:
            pass
        finally:
            pass

def acceptSocket(thesocket:socket.socket):
    while True:
        # print("Waiting for a new connection ...")
        (clientSocket, address) = thesocket.accept()
        threading.Thread(target=processSocket, args=(clientSocket, )).start()

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

def terminate():
    print("    Bye!!!", end='', flush=True)
    for i in range(10):
        time.sleep(0.1)
        print(".", end='', flush=True)
    exit()

def printEdges():
    global Exceptions
    global clientIDS
    for src in clientIDS:
        print(src, end=': ')
        for dst in clientIDS:
            excepted = False
            for exp in Exceptions:
                if exp[0] == src and exp[1] == dst:
                    excepted = True
                    break
            if excepted == False:
                print(dst, end=' ')
        print("")

def removeEdge():
    global Exceptions
    global clientIDS
    while True:
        try:
            src = int(input("Enter edge source ID: "))
            break
        except:
            print("ID should be an integer.")
    while True:
        try:
            dst = int(input("Enter edge destination ID: "))
            break
        except:
            print("ID should be an integer.")

    Exceptions.append([src, dst])
    Exceptions.append([dst, src])

    printEdges()

def addEdge():
    global Exceptions
    global clientIDS
    while True:
        try:
            src = int(input("Enter edge source ID: "))
            break
        except:
            print("ID should be an integer.")
    while True:
        try:
            dst = int(input("Enter edge destination ID: "))
            break
        except:
            print("ID should be an integer.")
    newExceptions = []
    for exp in Exceptions:
        if not ((exp[0] == src and exp[1] == dst) or (exp[1] == src and exp[0] == dst)):
            newExceptions.append(exp)

    Exceptions = newExceptions

    printEdges()

def removeNode():
    global Exceptions
    global clientIDS
    while True:
        try:
            node = int(input("Enter node ID: "))
            break
        except:
            print("ID should be an integer.")

    for id in clientIDS:
        Exceptions.append([id, node])
        Exceptions.append([node, id])

    printEdges()

def addNode():
    global Exceptions
    global clientIDS
    while True:
        try:
            node = int(input("Enter node ID: "))
            break
        except:
            print("ID should be an integer.")

    newExceptions = []
    for exp in Exceptions:
        if not ((exp[0] == node) or (exp[1] == node)):
            newExceptions.append(exp)

    Exceptions = newExceptions

    printEdges()

switcher = {
    1: removeEdge,
    2: addEdge,
    3: removeNode,
    4: addNode,
    9: terminate
}

menu = {
    1: "Break an edge",
    2: "Repair an edge",
    3: "Break a node",
    4: "Repair a node",
    9: "Exit"
}

if __name__ == '__main__':
    address = ConfigurationFactory.getInstance().get("DDS")

    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.bind((address["address"], address["port"]))
    serverSocket.listen(10)

    threading.Thread(target=acceptSocket, args=(serverSocket, )).start()

    while True:
        choice = showMenu(menu)
        switcher.get(choice, lambda: "unknown")()




