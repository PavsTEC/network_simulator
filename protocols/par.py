"""
Protocolo PAR (Positive Acknowledgment with Retransmission)
- Comunicación unidireccional: A envía, B recibe
- Control de flujo con ACK/NAK
- Timeout y reenvío automático
- Números de secuencia alternantes (0,1)
"""

from models.frame import Frame
from models.events import Event, EventType


class PARProtocol:
    """Protocolo PAR con ACK/NAK y timeout."""

    def __init__(self, machine_id: str):
        """Inicializa el protocolo PAR."""
        self.machine_id = machine_id
        
        # Estado del protocolo
        self.seq_num = 0  # Número de secuencia actual (0 o 1)
        self.expected_seq = 0  # Secuencia esperada en receptor
        
        # Control de reenvío
        self.waiting_for_ack = False  # ¿Esperando ACK?
        self.last_frame_sent = None  # Último frame enviado (para reenvío)
        self.last_destination = None  # Destino del último frame
        
        # Timeouts
        self.timeout_duration = 5.0  # Segundos para timeout
        self.timeout_event_scheduled = False

    def handle_network_layer_ready(self, network_layer, data_link_layer, simulator) -> dict:
        """Decide qué hacer cuando hay datos listos en Network Layer."""
        
        # Solo procesar si no estamos esperando ACK
        if self.waiting_for_ack:
            print(f"[PAR-{self.machine_id}] Esperando ACK, no se pueden enviar más datos")
            return {'action': 'no_action'}
        
        if network_layer.has_data_ready():
            packet, destination = network_layer.get_packet()
            if packet and destination:
                # Crear frame DATA con número de secuencia
                frame = Frame("DATA", self.seq_num, 0, packet)
                
                # Guardar para posible reenvío
                self.last_frame_sent = frame
                self.last_destination = destination
                self.waiting_for_ack = True
                
                # Programar timeout
                self._schedule_timeout(simulator)
                
                print(f"[PAR-{self.machine_id}] Enviando frame seq={self.seq_num}")
                
                return {
                    'action': 'send_frame',
                    'frame': frame,
                    'destination': destination
                }
        
        return {'action': 'no_action'}

    def handle_frame_arrival(self, frame: Frame) -> dict:
        """Decide qué hacer con un frame recibido."""
        
        if frame.type == "DATA":
            # Frame de datos recibido
            if frame.seq_num == self.expected_seq:
                # Secuencia correcta - entregar y enviar ACK
                print(f"[PAR-{self.machine_id}] Frame seq={frame.seq_num} correcto, enviando ACK")
                
                # Actualizar secuencia esperada
                self.expected_seq = 1 - self.expected_seq  # Alternar entre 0 y 1
                
                return {
                    'action': 'deliver_packet_and_send_ack',
                    'packet': frame.packet,
                    'ack_seq': frame.seq_num
                }
            else:
                # Secuencia incorrecta - enviar NAK
                print(f"[PAR-{self.machine_id}] Frame seq={frame.seq_num} incorrecto (esperaba {self.expected_seq}), enviando NAK")
                
                return {
                    'action': 'send_nak',
                    'nak_seq': self.expected_seq
                }
        
        elif frame.type == "ACK":
            # ACK recibido
            if self.waiting_for_ack and frame.ack_num == self.seq_num:
                # ACK correcto - avanzar secuencia
                print(f"[PAR-{self.machine_id}] ACK seq={frame.ack_num} recibido correctamente")
                
                self.seq_num = 1 - self.seq_num  # Alternar entre 0 y 1
                self.waiting_for_ack = False
                self.timeout_event_scheduled = False
                
                return {'action': 'continue_sending'}
            else:
                # ACK incorrecto o no esperado
                print(f"[PAR-{self.machine_id}] ACK seq={frame.ack_num} incorrecto o no esperado")
                return {'action': 'no_action'}
        
        elif frame.type == "NAK":
            # NAK recibido - reenviar
            if self.waiting_for_ack:
                print(f"[PAR-{self.machine_id}] NAK recibido, reenviando frame")
                return {'action': 'retransmit'}
            else:
                print(f"[PAR-{self.machine_id}] NAK recibido pero no esperado")
                return {'action': 'no_action'}
        
        return {'action': 'no_action'}

    def handle_frame_corruption(self, frame: Frame) -> dict:
        """Decide qué hacer con un frame corrupto."""
        print(f"[PAR-{self.machine_id}] Frame corrupto recibido")
        
        # En PAR, frame corrupto se trata como no recibido
        # Si esperábamos un DATA, no enviamos nada (timeout se encargará)
        # Si esperábamos un ACK, timeout se encargará del reenvío
        return {'action': 'no_action'}

    def handle_timeout(self, simulator) -> dict:
        """Maneja evento de timeout."""
        if self.waiting_for_ack and self.last_frame_sent:
            print(f"[PAR-{self.machine_id}] TIMEOUT - Reenviando frame seq={self.last_frame_sent.seq_num}")
            
            # Reprogramar nuevo timeout
            self._schedule_timeout(simulator)
            
            return {
                'action': 'send_frame',
                'frame': self.last_frame_sent,
                'destination': self.last_destination
            }
        
        return {'action': 'no_action'}

    def _schedule_timeout(self, simulator):
        """Programa un evento de timeout."""
        if not self.timeout_event_scheduled:
            timeout_event = Event(
                EventType.TIMEOUT,
                simulator.get_current_time() + self.timeout_duration,
                self.machine_id
            )
            simulator.schedule_event(timeout_event)
            self.timeout_event_scheduled = True
            print(f"[PAR-{self.machine_id}] Timeout programado en {self.timeout_duration}s")

    def get_stats(self) -> dict:
        """Retorna estadísticas del protocolo."""
        return {
            'protocol': 'PAR',
            'current_seq': self.seq_num,
            'expected_seq': self.expected_seq,
            'waiting_for_ack': self.waiting_for_ack,
            'timeout_duration': self.timeout_duration
        }