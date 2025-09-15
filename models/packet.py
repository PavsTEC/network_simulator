class Packet:
    def __init__(self, data: str):
        self.data = data
    
    def __str__(self):
        return f"Packet(data='{self.data}')"
    
    def __repr__(self):
        return self.__str__()