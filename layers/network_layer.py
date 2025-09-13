import random
import time
from models.packet import Packet

class NetworkLayer:
    def __init__(self, machine_id: str):
        self.machine_id = machine_id
        self.packet_counter = 0
        self.ready_probability = 0.7  # 70% probabilidad de tener datos
        self.received_packets = []
    
    def has_data_ready(self) -> bool:
        """Simula disponibilidad aleatoria de datos"""
        return random.random() < self.ready_probability
    
    def get_packet(self) -> Packet:
        """Genera un nuevo packet para enviar"""
        self.packet_counter += 1
        data = f"Data_{self.machine_id}_{self.packet_counter}"
        packet = Packet(data)
        print(f"  [NetworkLayer-{self.machine_id}] Generado: {packet}")
        return packet
    
    def deliver_packet(self, packet: Packet):
        """Entrega un packet recibido a la aplicación"""
        self.received_packets.append(packet)
        print(f"  [NetworkLayer-{self.machine_id}] Entregado a aplicación: {packet}")
    
    def get_stats(self):
        return {
            'packets_sent': self.packet_counter,
            'packets_received': len(self.received_packets)
        }