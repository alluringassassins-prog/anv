import datetime

class Topic:

    timestamp = datetime.datetime.now()

    def __init__(self, timestamp: str):
        if len(timestamp) > 0:
            try:
                tmp = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                self.timestamp = timestamp
            except Exception as e:
                self.timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            self.timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')