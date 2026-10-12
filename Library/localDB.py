import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

from tinydb import Query, TinyDB
import datetime
import threading

class localDB:
    def __init__(self, path: str):
        self.topics = {}

        if not os.path.isdir(path):
            os.makedirs(path)

        if os.path.isdir(path):
            if not path.endswith("/"):
                path += "/"
            self.path = path
        else:
            self.path = "./"

        localDB.instance = self

    instance = None

    lock = threading.Lock()

    @staticmethod
    def getInstance(path: str=None):
        if path == None and localDB.instance == None:
            print("In first instantiation of DB, the path should be determined!!!")
            return None
        
        if localDB.instance == None:
            with localDB.lock:
                if localDB.instance == None:
                    localDB.instance = localDB(path)
        return localDB.instance

    def insert(self, topic: str, data: dict):
        if not topic in self.topics:
            self.topics[topic] = {}
            self.topics[topic]["DB"] = TinyDB(f'{self.path}/{topic}.json')
            self.topics[topic]["QueryFactory"] = Query()
            self.topics[topic]["Lock"] = threading.Lock()

        if not "__timestamp__" in data:
            data["__timestamp__"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # print(data)
        try:
            with self.topics[topic]["Lock"]:
                self.topics[topic]["DB"].insert(data)
        except Exception as e:
            print("Error in insert: ")
            print(threading.get_ident())
            print(e)
            print(data)

    
    def truncate(self, topic: str):
        if topic in self.topics:
            with self.topics[topic]["Lock"]:
                self.topics[topic]["DB"].truncate()

    def query(self, topic: str, fromtimestamp: str, totimestamp: str):
        res = None
        if topic in self.topics:
            with self.topics[topic]["Lock"]:
                if fromtimestamp != None and totimestamp != None:
                    res = self.topics[topic]["DB"].search((self.topics[topic]["QueryFactory"].__timestamp__ >= fromtimestamp) & (self.topics[topic]["QueryFactory"].__timestamp__ <= totimestamp))
                elif fromtimestamp != None:
                    res = self.topics[topic]["DB"].search(self.topics[topic]["QueryFactory"].__timestamp__ >= fromtimestamp)
                elif totimestamp != None:
                    res = self.topics[topic]["DB"].search(self.topics[topic]["QueryFactory"].__timestamp__ <= totimestamp)
        return res