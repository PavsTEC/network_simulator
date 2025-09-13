import time

class Packet:
    def __init__(self, data: str):
        self.data = data
        self.timestamp = time.time()
        self.id = id(self)  # ID único para debugging
    
    def __str__(self):
        return f"Packet(data='{self.data}')"
    
    def __repr__(self):
        return self.__str__()