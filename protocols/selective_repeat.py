"""
Protocolo Selective Repeat (Repetición Selectiva)
- Comunicación bidireccional
- Ventana deslizante de tamaño N para emisión y recepción
- Reenvío selectivo de frames perdidos/corruptos
- ACKs individuales para cada frame
- Timeouts independientes por frame
"""

from models.frame import Frame
from models.events import Event, EventType
from protocols.protocol_interface import ProtocolInterface
from typing import Dict, Optional, List


class SelectiveRepeatProtocol(ProtocolInterface):
    """Protocolo Selective Repeat con ventanas deslizantes bidireccionales."""

    def __init__(self, machine_id: str, window_size: int = 4):
        """
        Inicializa el protocolo Selective Repeat.
        
        Args:
            machine_id: ID de la máquina
            window_size: Tamaño de la ventana deslizante (por defecto 4)
        """
        super().__init__(machine_id)
        
        # Configuración de ventanas
        self.window_size = window_size
        self.max_seq_num = 2 * window_size  # Espacio de secuencia debe ser >= 2*N
        
        # Ventana de envío
        self.send_base = 0  # Primer frame no confirmado
        self.next_seq_num = 0  # Próximo número de secuencia a usar
        self.send_window = {}  # {seq_num: {'frame': Frame, 'destination': str, 'timer_id': int}}
        
        # Ventana de recepción
        self.rcv_base = 0  # Número de secuencia esperado más bajo
        self.receive_window = {}  # {seq_num: Frame} - frames recibidos fuera de orden
        self.ack_sent = set()  # ACKs ya enviados para frames recibidos
        
        # Control de timeouts
        self.timeout_duration = 3.0
        self.next_timer_id = 0
        self.active_timers = {}  # {timer_id: seq_num}
        
        # Estadísticas
        self.frames_sent = 0
        self.frames_received = 0
        self.retransmissions = 0
        self.out_of_order_frames = 0

    def handle_network_layer_ready(self, network_layer, data_link_layer, simulator) -> dict:
        """Maneja cuando Network Layer tiene datos listos para enviar."""
        
        # Verificar si hay espacio en la ventana de envío
        if self._send_window_full():
            print(f"[SR-{self.machine_id}] Ventana de envío llena, no se pueden enviar más frames")
            return {'action': 'no_action'}
        
        if network_layer.has_data_ready():
            packet, destination = network_layer.get_packet()
            if packet and destination:
                # Crear frame DATA con número de secuencia
                frame = Frame("DATA", self.next_seq_num, 0, packet)
                
                # Agregar a ventana de envío
                timer_id = self._get_next_timer_id()
                self.send_window[self.next_seq_num] = {
                    'frame': frame,
                    'destination': destination,
                    'timer_id': timer_id
                }
                
                # Programar timeout para este frame
                self._schedule_timeout(simulator, self.next_seq_num, timer_id)
                
                print(f"[SR-{self.machine_id}] Enviando frame seq={self.next_seq_num} (ventana: {self.send_base}-{(self.send_base + self.window_size - 1) % self.max_seq_num})")
                
                # Avanzar número de secuencia
                self.next_seq_num = (self.next_seq_num + 1) % self.max_seq_num
                self.frames_sent += 1
                
                return {
                    'action': 'send_frame',
                    'frame': frame,
                    'destination': destination
                }
        
        return {'action': 'no_action'}

    def handle_frame_arrival(self, frame) -> dict:
        """Maneja la llegada de un frame válido."""
        
        if frame.type == "DATA":
            return self._handle_data_frame(frame)
        elif frame.type == "ACK":
            return self._handle_ack_frame(frame)
        
        return {'action': 'no_action'}

    def _handle_data_frame(self, frame) -> dict:
        """Maneja la llegada de un frame DATA."""
        seq_num = frame.seq_num
        self.frames_received += 1
        
        print(f"[SR-{self.machine_id}] Frame DATA seq={seq_num} recibido (ventana rcv: {self.rcv_base}-{(self.rcv_base + self.window_size - 1) % self.max_seq_num})")
        
        # Siempre enviar ACK para el frame recibido
        ack_response = {
            'action': 'send_ack_individual',
            'ack_seq': seq_num
        }
        
        # Verificar si está dentro de la ventana de recepción
        if self._in_receive_window(seq_num):
            if seq_num == self.rcv_base:
                # Frame esperado - entregar inmediatamente
                packets_to_deliver = [frame.packet]
                self.rcv_base = (self.rcv_base + 1) % self.max_seq_num
                
                # Verificar frames buffereados consecutivos
                while self.rcv_base in self.receive_window:
                    buffered_frame = self.receive_window.pop(self.rcv_base)
                    packets_to_deliver.append(buffered_frame.packet)
                    self.rcv_base = (self.rcv_base + 1) % self.max_seq_num
                
                print(f"[SR-{self.machine_id}] Entregando {len(packets_to_deliver)} paquete(s), nueva base rcv: {self.rcv_base}")
                
                return {
                    'action': 'deliver_packets_and_send_ack',
                    'packets': packets_to_deliver,
                    'ack_seq': seq_num
                }
            else:
                # Frame fuera de orden - bufferear
                self.receive_window[seq_num] = frame
                self.out_of_order_frames += 1
                print(f"[SR-{self.machine_id}] Frame seq={seq_num} buffereado (fuera de orden)")
                
                return ack_response
        else:
            # Frame fuera de ventana
            if self._already_received(seq_num):
                print(f"[SR-{self.machine_id}] Frame seq={seq_num} ya recibido (reenviar ACK)")
            else:
                print(f"[SR-{self.machine_id}] Frame seq={seq_num} fuera de ventana (ignorar)")
            
            return ack_response

    def _handle_ack_frame(self, frame) -> dict:
        """Maneja la llegada de un frame ACK."""
        ack_seq = frame.ack_num
        
        print(f"[SR-{self.machine_id}] ACK seq={ack_seq} recibido")
        
        # Verificar si el ACK corresponde a un frame en la ventana de envío
        if ack_seq in self.send_window:
            # Cancelar timeout y remover de ventana
            frame_info = self.send_window.pop(ack_seq)
            self._cancel_timeout(frame_info['timer_id'])
            
            print(f"[SR-{self.machine_id}] ACK seq={ack_seq} confirmado")
            
            # Si es el frame base, avanzar ventana
            if ack_seq == self.send_base:
                old_base = self.send_base
                # Avanzar base hasta el próximo frame no confirmado
                while self.send_base not in self.send_window and not self._send_window_empty():
                    self.send_base = (self.send_base + 1) % self.max_seq_num
                
                # Si ventana está vacía, avanzar base al próximo a enviar
                if self._send_window_empty():
                    self.send_base = self.next_seq_num
                
                print(f"[SR-{self.machine_id}] Ventana de envío avanzada: {old_base} -> {self.send_base}")
                
                # Intentar enviar más datos si hay
                return {'action': 'continue_sending'}
        else:
            print(f"[SR-{self.machine_id}] ACK seq={ack_seq} fuera de ventana o duplicado")
        
        return {'action': 'no_action'}

    def handle_frame_corruption(self, frame) -> dict:
        """Maneja un frame corrupto."""
        print(f"[SR-{self.machine_id}] Frame corrupto recibido - ignorando")
        # En Selective Repeat, frames corruptos se ignoran
        # El timeout se encargará del reenvío si era un DATA
        # Si era un ACK, el emisor reenviará por timeout
        return {'action': 'no_action'}

    def handle_timeout(self, simulator) -> dict:
        """Maneja eventos de timeout."""
        # El timeout viene con el timer_id en los datos del evento
        # Necesitamos implementar esto en el simulador para pasar el timer_id
        return {'action': 'no_action'}
    
    def handle_timeout_for_frame(self, timer_id: int, simulator) -> dict:
        """Maneja timeout para un frame específico."""
        if timer_id in self.active_timers:
            seq_num = self.active_timers.pop(timer_id)
            
            if seq_num in self.send_window:
                frame_info = self.send_window[seq_num]
                
                print(f"[SR-{self.machine_id}] TIMEOUT - Reenviando frame seq={seq_num}")
                self.retransmissions += 1
                
                # Reprogramar timeout
                new_timer_id = self._get_next_timer_id()
                frame_info['timer_id'] = new_timer_id
                self._schedule_timeout(simulator, seq_num, new_timer_id)
                
                return {
                    'action': 'send_frame',
                    'frame': frame_info['frame'],
                    'destination': frame_info['destination']
                }
        
        return {'action': 'no_action'}

    def _send_window_full(self) -> bool:
        """Verifica si la ventana de envío está llena."""
        return len(self.send_window) >= self.window_size

    def _send_window_empty(self) -> bool:
        """Verifica si la ventana de envío está vacía."""
        return len(self.send_window) == 0

    def _in_receive_window(self, seq_num: int) -> bool:
        """Verifica si un número de secuencia está dentro de la ventana de recepción."""
        window_end = (self.rcv_base + self.window_size - 1) % self.max_seq_num
        
        if self.rcv_base <= window_end:
            return self.rcv_base <= seq_num <= window_end
        else:  # Ventana wrapeada
            return seq_num >= self.rcv_base or seq_num <= window_end

    def _already_received(self, seq_num: int) -> bool:
        """Verifica si un frame ya fue recibido anteriormente."""
        # Frame ya recibido si está antes de la base de recepción
        if self.rcv_base == 0:
            return seq_num > (self.max_seq_num - self.window_size)
        else:
            return seq_num < self.rcv_base and seq_num >= (self.rcv_base - self.window_size) % self.max_seq_num

    def _get_next_timer_id(self) -> int:
        """Obtiene el próximo ID de timer."""
        timer_id = self.next_timer_id
        self.next_timer_id += 1
        return timer_id

    def _schedule_timeout(self, simulator, seq_num: int, timer_id: int):
        """Programa un timeout para un frame específico."""
        self.active_timers[timer_id] = seq_num
        
        timeout_event = Event(
            EventType.TIMEOUT,
            simulator.get_current_time() + self.timeout_duration,
            self.machine_id,
            {'timer_id': timer_id}  # Pasar timer_id en los datos del evento
        )
        simulator.schedule_event(timeout_event)

    def _cancel_timeout(self, timer_id: int):
        """Cancela un timeout (marcándolo como inactivo)."""
        if timer_id in self.active_timers:
            del self.active_timers[timer_id]

    def get_stats(self) -> dict:
        """Retorna estadísticas del protocolo."""
        stats = super().get_stats()
        stats.update({
            'window_size': self.window_size,
            'send_base': self.send_base,
            'next_seq_num': self.next_seq_num,
            'rcv_base': self.rcv_base,
            'send_window_size': len(self.send_window),
            'receive_buffer_size': len(self.receive_window),
            'frames_sent': self.frames_sent,
            'frames_received': self.frames_received,
            'retransmissions': self.retransmissions,
            'out_of_order_frames': self.out_of_order_frames,
            'active_timers': len(self.active_timers)
        })
        return stats

    def get_protocol_name(self) -> str:
        """Obtiene el nombre del protocolo."""
        return f"Selective Repeat (W={self.window_size})"

    def set_window_size(self, window_size: int):
        """Permite cambiar el tamaño de ventana (solo antes de iniciar)."""
        if self.send_window or self.receive_window:
            print(f"[SR-{self.machine_id}] No se puede cambiar tamaño de ventana durante transmisión")
            return False
        
        self.window_size = window_size
        self.max_seq_num = 2 * window_size
        print(f"[SR-{self.machine_id}] Tamaño de ventana actualizado a {window_size}")
        return True