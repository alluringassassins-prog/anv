import math
import os
import time
import sys
import socket
import threading

from PIL.ImageChops import offset

sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

from Library.ConfigurationFactory import ConfigurationFactory

class MacNetLayer:

    def __init__(self):

        self.state = 'init'
        self.lock = threading.Lock()
        self.bufferLock = threading.Lock()
        self.conf = ConfigurationFactory()

        self.buffer = []

        self.ID = self.conf.get("ID")

        self.waitForJoinRequestsStateTimeOut = None
        self.waitForJoinIntervalStateTimeOut = None
        self.waitForTokenStateTimeOut = None
        self.waitForJoinAckStateTimeOut = None
        self.waitForTokenReplyStateTimeOut = None
        self.waitForJoinRequestsStateTimeOut = None
        self.waitForTokenReplyStateTimeOut = None
        self.detectExistingNetworkStateTimeOut = None
        self.initStateTimeOut = None

        self.tokenOwner = False
        self.joinNeighbour = 0
        self.tokenWaitCycles = 0
        self.hasChild = False
        self.possibleParentNode = -1
        self.parentNode = -1
        self.streamWindowCount = 0

        self.connectivityGraph = []
        for i in range(self.conf.get("NodesCount")):
            self.connectivityGraph.append(0)

        self.eachNodePacketOrder = []
        for i in range(self.conf.get("NodesCount")):
            self.eachNodePacketOrder.append(0)

        self.children = []
        for i in range(self.conf.get("NodesCount")):
            self.children.append(0)

        address = ConfigurationFactory.getInstance().get("network")

        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind((address["Serving"]["address"], address["Serving"]["port"]+self.ID))
        self.serverSocket.listen(10)

        self.serverSocketThread = threading.Thread(target=self.acceptSocket, args=(self.serverSocket,))
        self.serverSocketThread.start()

        self.radioSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.radioSocket.bind((address["Radio"]["address"], address["Radio"]["port"]+self.ID))

        self.radioSocketThread = threading.Thread(target=self.processRadioSocket, args=(self.radioSocket,))
        self.radioSocketThread.start()

        self.initStateTimeOut = threading.Thread(target=self.initStateTimeOutHandler, args=())
        self.initStateTimeOut.start()

    def acceptSocket(self, thesocket: socket.socket):
        while True:
            # print("Waiting for a new connection ...")
            (clientSocket, address) = thesocket.accept()
            threading.Thread(target=self.processSocket, args=(clientSocket,)).start()

    def processSocket(self, thesocket: socket.socket):
        breakCount = 0
        while True:
            try:
                dataLen = thesocket.recv(1)
                if len(dataLen) == 1:
                    data = bytearray()
                    tryCount = 0
                    while len(data) < dataLen[0] and tryCount < 10:
                        data = data + bytearray(thesocket.recv(dataLen[0] - len(data)))
                        tryCount += 1

                    if len(data) == dataLen[0]:
                        packetSenderID = data[0]

                        if len(data) > 1:
                            if self.ID == packetSenderID:
                                with self.bufferLock:
                                    self.buffer.append({'len':len(data),'currentBit':0,'data':bytearray(dataLen)+data})
                    else:
                        print("Received data is not matched with required length!!!")
                        print(f'{dataLen[0]} -> The desired Length')
                        print(f'{data} -> received data')
                        print(f'{tryCount} times have been tried')
                else:
                    time.sleep(0.01)
            except Exception as e:
                breakCount += 1
                if breakCount > 5:
                    break
            else:
                breakCount = 0
            finally:
                pass

    def computeFrameOrderFieldWidthInBits(self):
        return math.ceil(math.log2(self.conf.get("network")["MaxPacketLen"]/self.conf.get("network")["NodeWindow"]))+1+1

    def computeFrameOffsetFieldWidthInBits(self):
        return math.ceil(math.log2(self.conf.get("network")["NodeWindow"]/self.conf.get("network")["RadioWindow"]))+1

    def computeIDFieldWidthInBits(self):
        return math.ceil(math.log2(self.conf.get("network")["NodesCount"]))

    def computeResetOrderThreshold(self):
        return math.ceil((2*self.conf.get("network")["MaxPacketLen"])/self.conf.get("network")["NodeWindow"])

    def processRadioSocket(self, thesocket: socket.socket):
        radioWindowInBytes = self.conf.get("network")["RadioWindow"] / 8
        nodeWindowInBytes = self.conf.get("network")["NodeWindow"] / 8
        currentWindowReceivedBytes = 0
        breakCount = 0
        currentPacket = bytearray()
        currentPacketLen = 0
        while True:
            try:
                data = bytearray()
                tryCount = 0
                while len(data) < radioWindowInBytes and tryCount < 10:
                    data = data + bytearray(thesocket.recv(radioWindowInBytes - len(data)))
                    tryCount += 1

                if len(data) == radioWindowInBytes:
                    radioOffset = 0
                    if currentWindowReceivedBytes == 0:
                        #TODO: Process radio headers like token , connectivity graph, ...
                        pass
                    else:
                        orderFieldWidthInBits = self.computeOrderFieldWidthInBits()
                        packetOrder = data[0]
                        packetOrder = packetOrder >> (8 - orderFieldWidthInBits)
                        finalData = bytearray()
                        for i in range(radioWindowInBytes):
                            if i > 0:
                                finalData[i-1] = finalData[i-1] | (data[i] >> (8 - orderFieldWidthInBits))
                            finalData.append(data[i] << orderFieldWidthInBits)

                        data = finalData
                        if currentPacketLen > 0:
                            currentPacket[len(currentPacket)-1] |= data[0] >> (8 - orderFieldWidthInBits)
                            finalData = bytearray()
                            for i in range(radioWindowInBytes):
                                if i > 0:
                                    finalData[i - 1] = finalData[i - 1] | (data[i] >> (8 - orderFieldWidthInBits))
                                finalData.append(data[i] << orderFieldWidthInBits)
                            data = finalData

                    currentWindowReceivedBytes += radioWindowInBytes
                    if (1+packetOrder) == (currentWindowReceivedBytes/radioWindowInBytes):
                        while radioOffset < radioWindowInBytes:
                            if currentPacketLen == 0:
                                currentPacketLen = int(data[radioOffset])
                                radioOffset += 1
                            currentPacket = currentPacket + data[radioOffset:min(radioOffset + currentPacketLen - len(currentPacket), radioWindowInBytes)-1]
                            radioOffset = min(radioOffset + currentPacketLen - len(currentPacket), radioWindowInBytes)

                            if currentPacketLen == len(currentPacket):
                                #TODO: process packet and its headers and send to tcp client
                                currentPacket = bytearray()
                                currentPacketLen = 0

                    else:
                        print("Received packet order does not matched!!!")
                        print(f'{currentWindowReceivedBytes/radioWindowInBytes} -> The desired order')
                        print(f'{data} -> received data')
                        print(f'{packetOrder} -> received order')
                        currentPacket = bytearray()
                        currentPacketLen = 0

                    if currentWindowReceivedBytes == nodeWindowInBytes:
                        currentWindowReceivedBytes = 0
                else:
                    print("Received data is not matched with required length!!!")
                    print(f'{radioWindowInBytes} -> The desired Length')
                    print(f'{data} -> received data')
                    print(f'{tryCount} times have been tried')
                    print(f'{currentPacket} -> dropped data')
                    print(f'{currentPacketLen} -> desired length of the dropped data')
                    currentPacket = bytearray()
                    currentPacketLen = 0
            except Exception as e:
                breakCount += 1
                if breakCount > 5:
                    break
            else:
                breakCount = 0
            finally:
                pass

    def computePacketTypeFieldWidthInBits(self):
        return math.ceil(math.log2(self.conf.get("network")["PacketTypesCount"]))

    def getTypeIndex(self, packetType: str):
        finalType = packetType.lower()
        match finalType:
            case 'join':
                return 1
            case _:
                return 0

    def placeBitStringInByte(self, currentByte, currentBitPosition, bitString, bitStringLen):

        resultBitString = bytearray()
        if currentByte == None:
            resultBitString += b'\x00'
        else:
            resultBitString += currentByte
        resultPosition = 0
        resultBitPosition = currentBitPosition
        inputBitStringPosition = 0
        for i in range(bitStringLen):
            if i > 0 and resultBitPosition == 0:
                resultBitString += b'\x00'
            if (int(math.pow(2, 7-(i%8))) & bitString[inputBitStringPosition]) > 0:
                resultBitString[resultPosition] = resultBitString[resultPosition] | int(math.pow(2, 7-resultBitPosition))
            resultBitPosition = resultBitPosition + 1
            if resultBitPosition > 7:
                resultBitPosition = resultBitPosition - 7
                resultPosition = resultPosition + 1
            if (i % 8) == 7:
                inputBitStringPosition = inputBitStringPosition + 1

        return {"bitString": resultBitString, "remainingBitString": resultBitString[1:], "currentByte": resultBitString[0], "currentBitPosition": resultBitPosition}

    def adjustBitString(self, inputInteger, integerLength, maximumBitStringLength):
        return int(inputInteger << (8*integerLength - maximumBitStringLength)).to_bytes(integerLength, "big")

    def send(self, header: dict, numberOfRadioPacketsParam: int=0) -> bool:

        if numberOfRadioPacketsParam == 0:
            numberOfRadioPackets = self.conf.get("network")["NodeWindow"] / self.conf.get("network")["RadioWindow"]
        else:
            numberOfRadioPackets = numberOfRadioPacketsParam

        remainingBits = totalBits = numberOfRadioPackets * 8
        currentBit = 0
        currentByte = 0

        packet = bytearray()

        # 0: Paket Order
        packet += b'\x00'

        frameOrder = self.adjustBitString(self.streamWindowCount, math.ceil(self.computeFrameOrderFieldWidthInBits()/8), self.computeFrameOrderFieldWidthInBits())
        tmpBitString = self.placeBitStringInByte(packet[0], 1, frameOrder, self.computeFrameOrderFieldWidthInBits())
        packet[0] = tmpBitString["currentByte"]
        packet += tmpBitString["remainingBitString"]
        currentBit = tmpBitString["currentBitPosition"]
        currentByte = len(packet) - 1

        # 1: Packet type
        packetType = self.getTypeIndex("")
        if "Type" in header:
            packetType = self.getTypeIndex(header["Type"])
        packetType = self.adjustBitString(packetType, math.ceil(self.computePacketTypeFieldWidthInBits()/8), self.computePacketTypeFieldWidthInBits())
        tmpBitString = self.placeBitStringInByte(packet[currentByte], currentBit, packetType, self.computePacketTypeFieldWidthInBits())
        packet[0] = tmpBitString["currentByte"]
        packet += tmpBitString["remainingBitString"]
        currentBit = tmpBitString["currentBitPosition"]
        currentByte = len(packet) - 1

        # 2: Sender
        sender = self.adjustBitString(self.ID, math.ceil(self.computeIDFieldWidthInBits()/8), self.computeIDFieldWidthInBits())
        tmpBitString = self.placeBitStringInByte(packet[currentByte], currentBit, sender, self.computeIDFieldWidthInBits())
        packet[currentByte] = tmpBitString["currentByte"]
        packet += tmpBitString["remainingBitString"]
        currentBit = tmpBitString["currentBitPosition"]
        currentByte = len(packet) - 1

        # 3: Receiver
        receiver = 0
        if "Receiver" in header:
            receiver = header["Receiver"]
        receiver = self.adjustBitString(receiver, math.ceil(self.computeIDFieldWidthInBits()/8), self.computeIDFieldWidthInBits())
        tmpBitString = self.placeBitStringInByte(packet[currentByte], currentBit, receiver, self.computeIDFieldWidthInBits())
        packet[currentByte] = tmpBitString["currentByte"]
        packet += tmpBitString["remainingBitString"]
        currentBit = tmpBitString["currentBitPosition"]
        currentByte = len(packet) - 1

        if "Type" in header and header["Type"] == "Join":
            padding = self.adjustBitString(0, math.ceil((self.conf.get("network")["RadioWindow"] - currentBit)/8), self.conf.get("network")["RadioWindow"] - currentBit)
            tmpBitString = self.placeBitStringInByte(packet[currentByte], currentBit, padding, self.conf.get("network")["RadioWindow"] - currentBit)
            packet[currentByte] = tmpBitString["currentByte"]
            packet += tmpBitString["remainingBitString"]
        else:
            nextTokenOwner = 0
            if "NextTokenOwner" in header:
                nextTokenOwner = header["NextTokenOwner"]
            nextTokenOwner = self.adjustBitString(nextTokenOwner, math.ceil(self.computeIDFieldWidthInBits()/8), self.computeIDFieldWidthInBits())
            tmpBitString = self.placeBitStringInByte(packet[currentByte], currentBit, nextTokenOwner, self.computeIDFieldWidthInBits())
            packet[currentByte] = tmpBitString["currentByte"]
            packet += tmpBitString["remainingBitString"]
            currentBit = tmpBitString["currentBitPosition"]
            currentByte = len(packet) - 1

            with self.bufferLock:

                if len(self.buffer) == 0:
                    return True

                nodesCount = self.conf.get("network")["NodesCount"]
                for i in range(nodesCount):
                    graphNode = self.adjustBitString(self.connectivityGraph[i], math.ceil(math.log2(nodesCount)/8), math.ceil(math.log2(nodesCount)))
                    tmpBitString = self.placeBitStringInByte(packet[currentByte], currentBit, graphNode, math.ceil(math.log2(nodesCount)))
                    packet[currentByte] = tmpBitString["currentByte"]
                    packet += tmpBitString["remainingBitString"]
                    currentBit = tmpBitString["currentBitPosition"]
                    currentByte = len(packet) - 1

                payload = self.buffer[0]

                for i in range(numberOfRadioPackets):

                    if i > 0:
                        packet = bytearray()
                        currentBit = 0
                        currentByte = 0

                        # 0: Paket Order
                        packet += b'\x80'

                        packetOrder = self.adjustBitString(i-1, math.ceil(self.computeFrameOffsetFieldWidthInBits() / 8), self.computeFrameOffsetFieldWidthInBits())
                        tmpBitString = self.placeBitStringInByte(packet[0], 1, packetOrder, self.computeFrameOffsetFieldWidthInBits())
                        packet[0] = tmpBitString["currentByte"]
                        packet += tmpBitString["remainingBitString"]
                        currentBit = tmpBitString["currentBitPosition"]
                        currentByte = len(packet) - 1

                    tmpRemainigBitsAfterFillingCurrentPacket = len(payload['data']) - (self.conf.get("network")["RadioWindow"] - (currentByte * 8 + currentBit))
                    tmpRemainigBitsAfterFillingCurrentFrame = tmpRemainigBitsAfterFillingCurrentPacket - (numberOfRadioPackets - (i + 1)) * self.conf.get("network")["RadioWindow"]
                    tmpEachFrameOverhead = nodesCount*math.ceil(math.log2(nodesCount)) + 3*self.computeIDFieldWidthInBits() + self.computePacketTypeFieldWidthInBits() + self.computeFrameOrderFieldWidthInBits() + self.computeFrameOffsetFieldWidthInBits() * (math.ceil(self.conf.get("network")["NodeWindow"]/self.conf.get("network")["RadioWindow"])-1)
                    tmpEachFrameNetCapacity = self.conf.get("network")["NodeWindow"] - tmpEachFrameOverhead
                    tmpRequiredFrames = math.ceil(tmpRemainigBitsAfterFillingCurrentFrame / tmpEachFrameNetCapacity)

                    if (tmpRequiredFrames + self.streamWindowCount + 1) <= self.computeResetOrderThreshold():
                        pass
                    else:
                        self.streamWindowCount = 0
                        break

                self.streamWindowCount += 1

                return True

    def computeFullCircleWindow(self):
        return (self.conf.get("network")["NodeWindow"]*(2*self.conf.get("NodesCount") - 2)+self.conf.get("network")["JoinWindow"])/self.conf.get("network")["BitRate"]

    def computeJoinWindow(self):
        return self.conf.get("network")["JoinWindow"]/self.conf.get("network")["BitRate"]

    def computeCurrentChildDiameterWindow(self):
        # TODO:
        return self.conf.get("network")["JoinWindow"]/self.conf.get("network")["BitRate"]

    def initStateTimeOutHandler(self):
        self.tokenOwner = False
        self.joinNeighbour = 0
        self.tokenWaitCycles = 0
        self.hasChild = False
        self.possibleParentNode = -1
        self.parentNode = -1

        self.connectivityGraph = []
        for i in range(self.conf.get("NodesCount")):
            self.connectivityGraph.append(0)

        self.children = []
        for i in range(self.conf.get("NodesCount")):
            self.children.append(0)

        time.sleep(self.computeFullCircleWindow())
        if self.state == 'init':
            self.stateMachine('no-activity-seen')

    def getCurrentChild(self):
        currentNode = 0
        for i in range(self.conf.get("NodesCount")):
            if self.children[i] == 2:
                currentNode = i + 1
                break
        return currentNode

    def generateToken(self):
        header = dict()
        self.tokenOwner = True
        success = self.send(header)
        if self.state == 'generate-token':
            if success:
                self.stateMachine('no-activity-seen')
            else:
                self.stateMachine('activity-seen')

    def sendData(self):

        currentNode = self.getCurrentChild()
        header = dict()
        header["NextTokenOwner"] = currentNode
        if self.state == 'wait-for-token-reply':
            success = self.send(header, 1)
        else:
            success = self.send(header)
        if self.state == 'send-data' or self.state == 'wait-for-token-reply':
            if success:
                self.stateMachine('no-activity-seen')
            else:
                self.stateMachine('activity-seen')

    def detectExistingNetworkStateTimeOutHandler(self):
        time.sleep(self.computeFullCircleWindow())
        if self.state == 'detect-existing-network':
            self.stateMachine('no-activity-seen')

    def waitForJoinIntervalStateTimeOutHandler(self):
        time.sleep(self.computeJoinWindow())
        if self.state == 'wait-for-join-interval':
            self.stateMachine('no-activity-seen')

    def waitForJoinAckStateTimeOutHandler(self):
        time.sleep(self.computeJoinWindow())
        if self.state == 'wait-for-join-ack':
            self.stateMachine('no-activity-seen')

    def waitForTokenStateTimeOutHandler(self):
        time.sleep(self.computeNetworkDiameterWindow())
        if self.state == 'wait-for-token':
            self.stateMachine('no-activity-seen')

    def waitForJoinRequestsStateTimeOutHandler(self):
        time.sleep(self.computeJoinWindow())
        if self.state == 'wait-for-join-requests':
            self.stateMachine('no-activity-seen')

    def waitForTokenReplyStateTimeOutHandler(self):
        time.sleep(self.computeCurrentChildDiameterWindow())
        if self.state == 'wait-for-token-reply':
            self.stateMachine('no-activity-seen')

    def join(self):
        header = dict()
        header["Sender"] = self.ID
        header["Receiver"] = self.joinNeighbour
        header["Type"] = "Join"
        success = self.send(header)
        if self.state == 'join':
            if success:
                self.stateMachine('no-activity-seen')
            else:
                self.stateMachine('activity-seen')

    def stateMachine(self, transition=None, packet=None):
        with self.lock:
            match self.state:
                case 'init':
                    if transition and transition == 'no-activity-seen':
                        self.state = 'generate-token'
                        self.generateToken()
                    elif transition and transition == 'activity-seen':
                        self.possibleParentNode = packet['Sender']
                        self.state = 'detect-existing-network'
                        self.detectExistingNetworkStateTimeOut = threading.Thread(target=self.detectExistingNetworkStateTimeOutHandler, args=())
                        self.detectExistingNetworkStateTimeOut.start()
                case 'detect-existing-network':
                    if transition and transition == 'activity-seen':
                        if packet['Sender'] == self.possibleParentNode:
                            self.parentNode = self.possibleParentNode
                            self.state = 'wait-for-join-interval'
                            self.waitForJoinIntervalStateTimeOut = threading.Thread(target=self.waitForJoinIntervalStateTimeOutHandler, args=())
                            self.waitForJoinIntervalStateTimeOut.start()
                        else:
                            self.possibleParentNode = packet['Sender']
                            self.state = 'detect-existing-network'
                            self.detectExistingNetworkStateTimeOut = threading.Thread(target=self.detectExistingNetworkStateTimeOutHandler, args=())
                            self.detectExistingNetworkStateTimeOut.start()
                    elif transition and transition == 'no-activity-seen':
                        self.state = 'generate-token'
                        self.generateToken()
                case 'generate-token':
                    if transition and transition == 'no-activity-seen':
                        self.state = 'wait-for-join-requests'
                        self.waitForJoinRequestsStateTimeOut = threading.Thread(target=self.waitForJoinRequestsStateTimeOutHandler, args=())
                        self.waitForJoinRequestsStateTimeOut.start()
                    elif transition and transition == 'activity-seen':
                        self.possibleParentNode = packet['Sender']
                        self.state = 'detect-existing-network'
                        self.detectExistingNetworkStateTimeOut = threading.Thread(target=self.detectExistingNetworkStateTimeOutHandler, args=())
                        self.detectExistingNetworkStateTimeOut.start()
                case 'wait-for-join-interval':
                    self.state = 'join'
                    self.join()
                case 'join':
                    if transition and transition == 'activity-seen':
                        self.state = 'wait-for-join-interval'
                        self.waitForJoinIntervalStateTimeOut = threading.Thread(target=self.waitForJoinIntervalStateTimeOutHandler, args=())
                        self.waitForJoinIntervalStateTimeOut.start()
                    elif transition and transition == 'no-activity-seen':
                        self.state = 'wait-for-join-ack'
                        self.waitForJoinAckStateTimeOut = threading.Thread(target=self.waitForJoinAckStateTimeOutHandler, args=())
                        self.waitForJoinAckStateTimeOut.start()
                case 'wait-for-join-ack':
                    if transition and transition == 'activity-seen':
                        self.state = 'wait-for-token'
                        self.waitForTokenStateTimeOut = threading.Thread(target=self.waitForTokenStateTimeOutHandler, args=())
                        self.waitForTokenStateTimeOut.start()
                    elif transition and transition == 'no-activity-seen':
                        self.state = 'init'
                        self.initStateTimeOut = threading.Thread(target=self.initStateTimeOutHandler, args=())
                        self.initStateTimeOut.start()
                case 'wait-for-join-requests':
                    self.state = 'wait-for-token'
                    self.waitForTokenStateTimeOut = threading.Thread(target=self.waitForTokenStateTimeOutHandler, args=())
                    self.waitForTokenStateTimeOut.start()
                case 'wait-for-token':
                    if transition and transition == 'activity-seen':
                        self.tokenWaitCycles = 0
                        self.state = 'send-data'
                        for i in range(self.conf.get("NodesCount")):
                            if self.children[i] == 1:
                                self.children[i] = 2
                                break
                        self.sendData()
                    elif transition and transition == 'no-activity-seen':
                        if self.tokenWaitCycles < self.conf.get("network")["MaxTokenWaitCycles"]:
                            self.tokenWaitCycles += 1
                            self.state = 'wait-for-join-requests'
                            self.waitForJoinRequestsStateTimeOut = threading.Thread(target=self.waitForJoinRequestsStateTimeOutHandler, args=())
                            self.waitForJoinRequestsStateTimeOut.start()
                        else:
                            self.state = 'init'
                            self.initStateTimeOut = threading.Thread(target=self.initStateTimeOutHandler, args=())
                            self.initStateTimeOut.start()
                case 'send-data':
                    if transition and transition == 'activity-seen':
                        self.state = 'wait-for-join-requests'
                        self.waitForJoinRequestsStateTimeOut = threading.Thread(target=self.waitForJoinRequestsStateTimeOutHandler, args=())
                        self.waitForJoinRequestsStateTimeOut.start()
                    elif transition and transition == 'no-activity-seen':
                        if self.hasChild:
                            self.state = 'wait-for-token-reply'
                            self.waitForTokenReplyStateTimeOut = threading.Thread(target=self.waitForTokenReplyStateTimeOutHandler, args=())
                            self.waitForTokenReplyStateTimeOut.start()
                        else:
                            self.state = 'wait-for-join-requests'
                            self.waitForJoinRequestsStateTimeOut = threading.Thread(target=self.waitForJoinRequestsStateTimeOutHandler, args=())
                            self.waitForJoinRequestsStateTimeOut.start()
                case 'wait-for-token-reply':
                    someChildFound = False
                    for i in range(self.conf.get("NodesCount")):
                        if self.children[i] == 1:
                            someChildFound = True
                            self.children[i] = 2
                            self.sendData()
                            break
                        elif self.children[i] == 2:
                            self.children[i] = 3
                    if not someChildFound:
                        for i in range(self.conf.get("NodesCount")):
                            if self.children[i] > 1:
                                self.children[i] = 1
                        if not self.tokenOwner:
                            self.sendData()
                        self.state = 'wait-for-join-requests'
                        self.waitForJoinIntervalStateTimeOut = threading.Thread(target=self.waitForJoinIntervalStateTimeOutHandler, args=())
                        self.waitForJoinIntervalStateTimeOut.start()

