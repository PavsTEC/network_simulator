import time
from models.packet import Packet

class NetworkLayer:
    def __init__(self, machine_id: str):
        self.machine_id = machine_id
        self.packet_counter = 0  # Contador de paquetes enviados
        self.received_packets = []  # Lista de paquetes recibidos

    def has_data_ready(self) -> bool:
        # Siempre hay datos disponibles para enviar
        return True

    def get_packet(self) -> Packet:
        # Genera un nuevo paquete con datos únicos
        self.packet_counter += 1
        data = f"Data_{self.machine_id}_{self.packet_counter}"
        packet = Packet(data)
        print(f"  [NetworkLayer-{self.machine_id}] Generado: {packet}")
        return packet

    def deliver_packet(self, packet: Packet):
        # Entrega el paquete recibido a la aplicación
        self.received_packets.append(packet)
        print(f"  [NetworkLayer-{self.machine_id}] Entregado a aplicación: {packet}")

    def get_stats(self):
        # Retorna estadísticas de envío y recepción
        return {
            'packets_sent': self.packet_counter,
            'packets_received': len(self.received_packets)
        }