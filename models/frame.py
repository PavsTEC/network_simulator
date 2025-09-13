import hashlib
import time

class Frame:
    def __init__(self, frame_type: str, seq_num: int, ack_num: int, packet=None):
        self.type = frame_type          # "DATA", "ACK", "NAK"
        self.seq_num = seq_num          # Número de secuencia
        self.ack_num = ack_num          # Número de confirmación
        self.packet = packet            # Objeto Packet o None
        self.checksum = self._calculate_checksum()
        self.corrupted = False
        self.timestamp = time.time()
    
    def _calculate_checksum(self):
        # Checksum simple basado en el contenido
        content = f"{self.type}{self.seq_num}{self.ack_num}"
        if self.packet:
            content += self.packet.data
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def corrupt_frame(self):
        """Simula corrupción del frame"""
        self.corrupted = True
        self.checksum = "CORRUPTED"
    
    def is_valid(self):
        """Verifica si el frame es válido"""
        if self.corrupted:
            return False
        expected_checksum = self._calculate_checksum()
        return self.checksum == expected_checksum
    
    def __str__(self):
        packet_info = f", packet={self.packet}" if self.packet else ""
        corruption = " [CORRUPTED]" if self.corrupted else ""
        return f"Frame(type={self.type}, seq={self.seq_num}, ack={self.ack_num}{packet_info}){corruption}"
    
    def __repr__(self):
        return self.__str__()