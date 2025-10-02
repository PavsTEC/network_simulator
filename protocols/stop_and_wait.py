"""
Protocolo Stop and Wait - Versión básica
- Envía un frame y espera ACK
- Sin timeouts (versión simplificada)
- Números de secuencia alternantes (0,1)
"""

from models.frame import Frame
from models.events import Event, EventType
from protocols.protocol_interface import ProtocolInterface


class StopAndWaitProtocol(ProtocolInterface):
    """Protocolo Stop and Wait básico."""

    def __init__(self, machine_id: str):
        """Inicializa el protocolo Stop and Wait."""
        super().__init__(machine_id)
        
        # Estado del protocolo
        self.seq_num = 0  # Número de secuencia actual (0 o 1)
        self.expected_seq = 0  # Secuencia esperada en receptor
        self.waiting_for_ack = False  # ¿Esperando ACK?

    def handle_network_layer_ready(self, network_layer, data_link_layer, simulator) -> dict:
        """Decide qué hacer cuando hay datos listos en Network Layer."""
        
        # Solo procesar si no estamos esperando ACK
        if self.waiting_for_ack:
            print(f"[StopWait-{self.machine_id}] Esperando ACK, no se pueden enviar más datos")
            return {'action': 'no_action'}
        
        if network_layer.has_data_ready():
            packet, destination = network_layer.get_packet()
            if packet and destination:
                # Crear frame DATA con número de secuencia
                frame = Frame("DATA", self.seq_num, 0, packet)
                self.waiting_for_ack = True
                
                print(f"[StopWait-{self.machine_id}] Enviando frame seq={self.seq_num}")
                
                return {
                    'action': 'send_frame',
                    'frame': frame,
                    'destination': destination
                }
        
        return {'action': 'no_action'}

    def handle_frame_arrival(self, frame) -> dict:
        """Decide qué hacer con un frame recibido."""
        
        if frame.type == "DATA":
            # Frame de datos recibido - siempre enviar ACK en Stop and Wait básico
            print(f"[StopWait-{self.machine_id}] Frame seq={frame.seq_num} recibido, enviando ACK")
            
            if frame.seq_num == self.expected_seq:
                # Secuencia correcta - entregar
                self.expected_seq = 1 - self.expected_seq  # Alternar entre 0 y 1
                
                return {
                    'action': 'deliver_packet_and_send_ack',
                    'packet': frame.packet,
                    'ack_seq': frame.seq_num
                }
            else:
                # Secuencia duplicada - solo ACK (no entregar)
                return {
                    'action': 'send_ack_only',
                    'ack_seq': frame.seq_num
                }
        
        elif frame.type == "ACK":
            # ACK recibido
            if self.waiting_for_ack and frame.ack_num == self.seq_num:
                # ACK correcto - avanzar secuencia
                print(f"[StopWait-{self.machine_id}] ACK seq={frame.ack_num} recibido correctamente")
                
                self.seq_num = 1 - self.seq_num  # Alternar entre 0 y 1
                self.waiting_for_ack = False
                
                return {'action': 'continue_sending'}
            else:
                # ACK incorrecto o no esperado
                print(f"[StopWait-{self.machine_id}] ACK seq={frame.ack_num} incorrecto o no esperado")
                return {'action': 'no_action'}
        
        return {'action': 'no_action'}

    def handle_frame_corruption(self, frame) -> dict:
        """Decide qué hacer con un frame corrupto."""
        print(f"[StopWait-{self.machine_id}] Frame corrupto recibido - ignorando")
        # Stop and Wait básico: ignorar frames corruptos
        return {'action': 'no_action'}

    def get_stats(self) -> dict:
        """Retorna estadísticas del protocolo."""
        stats = super().get_stats()
        stats.update({
            'current_seq': self.seq_num,
            'expected_seq': self.expected_seq,
            'waiting_for_ack': self.waiting_for_ack
        })
        return stats

    def get_protocol_name(self) -> str:
        """Obtiene el nombre del protocolo."""
        return "Stop and Wait"