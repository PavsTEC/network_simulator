class Frame:
    def __init__(self, frame_type: str, seq_num: int, ack_num: int, packet=None):
        self.type = frame_type          # "DATA", "ACK", "NAK"
        self.seq_num = seq_num          # Número de secuencia
        self.ack_num = ack_num          # Número de confirmación
        self.packet = packet            # Objeto Packet o None

        # Solo para tracking interno de PhysicalLayer
        self.corrupted_by_physical = False

    def __str__(self):
        packet_info = f", packet={self.packet}" if self.packet else ""
        corruption = " [CORRUPTED]" if self.corrupted_by_physical else ""
        return f"Frame(type={self.type}, seq={self.seq_num}, ack={self.ack_num}{packet_info}){corruption}"

    def __repr__(self):
        return self.__str__()