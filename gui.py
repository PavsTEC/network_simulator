"""
Interfaz Gráfica para el Simulador de Protocolos de Red.
Muestra animación de paquetes viajando entre máquinas con información al hover.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import math
from typing import Dict, List, Optional, Tuple
from simulation.simulator import Simulator
from protocols.protocol_interface import ProtocolInterface
from protocols.utopia import UtopiaProtocol
from protocols.stop_and_wait import StopAndWaitProtocol
from protocols.par import PARProtocol
from protocols.sliding_window import SlidingWindowProtocol
from protocols.go_back_n import GoBackNProtocol
from protocols.selective_repeat import SelectiveRepeatProtocol


class PacketAnimation:
    """Representa un paquete animado en tránsito."""

    def __init__(self, canvas, frame, start_pos, end_pos, duration=1.0):
        self.canvas = canvas
        self.frame = frame
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.duration = duration
        self.start_time = time.time()
        self.circle_id = None
        self.text_id = None
        self.completed = False
        self.paused = False
        self.elapsed_when_paused = 0.0

        # Información del frame
        self.info_text = self._create_info_text()

        # Crear elementos visuales
        self._create_packet()

    def _create_info_text(self) -> str:
        """Crea el texto informativo del paquete."""
        info = f"Tipo: {self.frame.type}\n"
        info += f"Seq: {self.frame.seq_num}\n"
        info += f"Ack: {self.frame.ack_num}\n"

        if self.frame.packet:
            info += f"Data: {self.frame.packet.data}\n"

        if hasattr(self.frame, 'corrupted_by_physical') and self.frame.corrupted_by_physical:
            info += "⚠️ CORRUPTO"

        return info

    def _create_packet(self):
        """Crea la representación visual del paquete."""
        x, y = self.start_pos

        # Color según tipo de frame
        if hasattr(self.frame, 'corrupted_by_physical') and self.frame.corrupted_by_physical:
            color = "#FF4444"  # Rojo para corruptos
        elif self.frame.type == "DATA":
            color = "#4CAF50"  # Verde para DATA
        elif self.frame.type == "ACK":
            color = "#2196F3"  # Azul para ACK
        elif self.frame.type == "NAK":
            color = "#FF9800"  # Naranja para NAK
        else:
            color = "#9E9E9E"  # Gris por defecto

        # Dibujar círculo
        radius = 12
        self.circle_id = self.canvas.create_oval(
            x - radius, y - radius,
            x + radius, y + radius,
            fill=color,
            outline="#333333",
            width=2,
            tags=("packet",)
        )

        # Etiqueta del tipo
        label = self.frame.type[0]  # D, A, N
        self.text_id = self.canvas.create_text(
            x, y,
            text=label,
            fill="white",
            font=("Arial", 10, "bold"),
            tags=("packet",)
        )

        # Bind hover events
        self.canvas.tag_bind(self.circle_id, "<Enter>", self._on_hover)
        self.canvas.tag_bind(self.circle_id, "<Leave>", self._on_leave)
        self.canvas.tag_bind(self.text_id, "<Enter>", self._on_hover)
        self.canvas.tag_bind(self.text_id, "<Leave>", self._on_leave)

        self.tooltip = None

    def _on_hover(self, event):
        """Muestra tooltip con información del paquete."""
        if self.tooltip is None:
            x, y = event.x_root, event.y_root
            self.tooltip = tk.Toplevel(self.canvas)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x+10}+{y+10}")

            label = tk.Label(
                self.tooltip,
                text=self.info_text,
                background="#FFFFCC",
                relief="solid",
                borderwidth=1,
                font=("Courier", 9),
                justify="left",
                padx=5,
                pady=5
            )
            label.pack()

    def _on_leave(self, event):
        """Oculta el tooltip."""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def pause(self):
        """Pausa la animación."""
        if not self.paused:
            self.paused = True
            self.elapsed_when_paused = time.time() - self.start_time

    def resume(self):
        """Reanuda la animación."""
        if self.paused:
            self.paused = False
            self.start_time = time.time() - self.elapsed_when_paused

    def update(self) -> bool:
        """
        Actualiza la posición del paquete.

        Returns:
            True si la animación continúa, False si terminó
        """
        if self.completed:
            return False

        # Si está pausada, no actualizar posición
        if self.paused:
            return True

        elapsed = time.time() - self.start_time
        progress = min(elapsed / self.duration, 1.0)

        # Interpolación lineal
        x = self.start_pos[0] + (self.end_pos[0] - self.start_pos[0]) * progress
        y = self.start_pos[1] + (self.end_pos[1] - self.start_pos[1]) * progress

        # Actualizar posición
        if self.circle_id and self.text_id:
            coords = self.canvas.coords(self.circle_id)
            if coords:
                center_x = (coords[0] + coords[2]) / 2
                center_y = (coords[1] + coords[3]) / 2
                dx = x - center_x
                dy = y - center_y

                self.canvas.move(self.circle_id, dx, dy)
                self.canvas.move(self.text_id, dx, dy)

        if progress >= 1.0:
            self.completed = True
            self._cleanup()
            return False

        return True

    def _cleanup(self):
        """Limpia los elementos visuales."""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

        if self.circle_id:
            self.canvas.delete(self.circle_id)
        if self.text_id:
            self.canvas.delete(self.text_id)


class NetworkSimulatorGUI:
    """Interfaz gráfica principal del simulador."""

    def __init__(self, root):
        self.root = root
        self.root.title("Simulador de Protocolos de Red")
        self.root.geometry("1200x800")
        self.root.configure(bg="#f0f0f0")

        # Variables
        self.simulator: Optional[Simulator] = None
        self.running = False
        self.paused = False
        self.animations: List[PacketAnimation] = []
        self.packet_count = 0
        self.delivered_count = 0

        # Rastreo de últimos paquetes por máquina
        self.last_sent = {"A": None, "B": None}
        self.last_received = {"A": None, "B": None}

        # Tooltips de máquinas
        self.machine_tooltips = {"A": None, "B": None}

        # Protocolos disponibles
        self.protocols = {
            "Utopia": UtopiaProtocol,
            "Stop and Wait": StopAndWaitProtocol,
            "PAR": PARProtocol,
            "Sliding Window": SlidingWindowProtocol,
            "Go-Back-N": GoBackNProtocol,
            "Selective Repeat": SelectiveRepeatProtocol
        }

        # Crear UI
        self._create_ui()

        # Iniciar loop de animación
        self._animation_loop()

    def _create_ui(self):
        """Crea todos los elementos de la interfaz."""
        # Frame superior - Controles
        control_frame = tk.Frame(self.root, bg="#2c3e50", padx=10, pady=10)
        control_frame.pack(side=tk.TOP, fill=tk.X)

        # Título
        title = tk.Label(
            control_frame,
            text="🌐 Simulador de Protocolos de Red",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title.pack(pady=5)

        # Frame de configuración
        config_frame = tk.Frame(control_frame, bg="#2c3e50")
        config_frame.pack(pady=10)

        # Selección de protocolo
        tk.Label(config_frame, text="Protocolo:", bg="#2c3e50", fg="white", font=("Arial", 10)).grid(row=0, column=0, padx=5, sticky="e")
        self.protocol_var = tk.StringVar(value="Stop and Wait")
        protocol_combo = ttk.Combobox(
            config_frame,
            textvariable=self.protocol_var,
            values=list(self.protocols.keys()),
            state="readonly",
            width=20
        )
        protocol_combo.grid(row=0, column=1, padx=5)

        # Vincular evento de cambio de protocolo
        protocol_combo.bind("<<ComboboxSelected>>", self._on_protocol_change)

        # Tasa de error (compartida)
        tk.Label(config_frame, text="Tasa de Error:", bg="#2c3e50", fg="white", font=("Arial", 10)).grid(row=0, column=2, padx=5, sticky="e")
        self.error_var = tk.StringVar(value="0.1")
        tk.Entry(config_frame, textvariable=self.error_var, width=10).grid(row=0, column=3, padx=5)

        # Delay (compartido)
        tk.Label(config_frame, text="Delay (s):", bg="#2c3e50", fg="white", font=("Arial", 10)).grid(row=0, column=4, padx=5, sticky="e")
        self.delay_var = tk.StringVar(value="1.0")
        tk.Entry(config_frame, textvariable=self.delay_var, width=10).grid(row=0, column=5, padx=5)

        # Intervalo (compartido)
        tk.Label(config_frame, text="Intervalo (s):", bg="#2c3e50", fg="white", font=("Arial", 10)).grid(row=0, column=6, padx=5, sticky="e")
        self.interval_var = tk.StringVar(value="2.0")
        tk.Entry(config_frame, textvariable=self.interval_var, width=10).grid(row=0, column=7, padx=5)

        # Tamaño de ventana (para GBN y SR) - inicialmente oculto
        self.window_label = tk.Label(config_frame, text="Ventana N:", bg="#2c3e50", fg="white", font=("Arial", 10))
        self.window_size_var = tk.StringVar(value="4")
        self.window_entry = tk.Entry(config_frame, textvariable=self.window_size_var, width=10)

        # Botones de control
        button_frame = tk.Frame(control_frame, bg="#2c3e50")
        button_frame.pack(pady=10)

        self.start_btn = tk.Button(
            button_frame,
            text="▶️ Iniciar",
            command=self._start_simulation,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12, "bold"),
            padx=20,
            pady=5
        )
        self.start_btn.grid(row=0, column=0, padx=5)

        self.pause_btn = tk.Button(
            button_frame,
            text="⏸️ Pausar",
            command=self._toggle_pause,
            bg="#FF9800",
            fg="white",
            font=("Arial", 12, "bold"),
            padx=20,
            pady=5,
            state=tk.DISABLED
        )
        self.pause_btn.grid(row=0, column=1, padx=5)

        self.stop_btn = tk.Button(
            button_frame,
            text="⏹️ Detener",
            command=self._stop_simulation,
            bg="#F44336",
            fg="white",
            font=("Arial", 12, "bold"),
            padx=20,
            pady=5,
            state=tk.DISABLED
        )
        self.stop_btn.grid(row=0, column=2, padx=5)

        # Frame central - Canvas de animación
        canvas_frame = tk.Frame(self.root, bg="white", relief=tk.SUNKEN, borderwidth=2)
        canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(canvas_frame, bg="#ecf0f1", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Dibujar máquinas
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self._draw_machines()

        # Frame inferior - Estadísticas
        stats_frame = tk.Frame(self.root, bg="#34495e", padx=10, pady=10)
        stats_frame.pack(side=tk.BOTTOM, fill=tk.X)

        stats_inner = tk.Frame(stats_frame, bg="#34495e")
        stats_inner.pack()

        self.stats_labels = {}
        labels = [
            ("Enviados:", "sent"),
            ("Entregados:", "delivered"),
            ("En tránsito:", "transit"),
            ("Estado:", "status")
        ]

        for i, (text, key) in enumerate(labels):
            tk.Label(stats_inner, text=text, bg="#34495e", fg="white", font=("Arial", 10, "bold")).grid(row=0, column=i*2, padx=5, sticky="e")
            label = tk.Label(stats_inner, text="0", bg="#34495e", fg="#3498db", font=("Arial", 10, "bold"))
            label.grid(row=0, column=i*2+1, padx=5, sticky="w")
            self.stats_labels[key] = label

        self.stats_labels["status"].config(text="⏹️ Detenido", fg="#95a5a6")

        # Ocultar campo de ventana inicialmente (protocolo por defecto es Stop and Wait)
        self._on_protocol_change()

    def _draw_machines(self):
        """Dibuja las máquinas A y B en el canvas."""
        width = self.canvas.winfo_width() or 1200
        height = self.canvas.winfo_height() or 600

        self.machine_a_pos = (width * 0.2, height * 0.5)
        self.machine_b_pos = (width * 0.8, height * 0.5)

        # Limpiar canvas
        self.canvas.delete("machine")

        # Máquina A
        self._draw_machine(self.machine_a_pos, "Máquina A", "#3498db")

        # Máquina B
        self._draw_machine(self.machine_b_pos, "Máquina B", "#e74c3c")

        # Línea de conexión
        self.canvas.create_line(
            self.machine_a_pos[0] + 60, self.machine_a_pos[1],
            self.machine_b_pos[0] - 60, self.machine_b_pos[1],
            fill="#95a5a6",
            width=3,
            dash=(10, 5),
            tags="machine"
        )

    def _draw_machine(self, pos, label, color):
        """Dibuja una máquina en la posición especificada."""
        x, y = pos
        machine_id = "A" if "A" in label else "B"

        # Cuerpo de la máquina (rectángulo redondeado simulado)
        body_id = self.canvas.create_rectangle(
            x - 60, y - 40,
            x + 60, y + 40,
            fill=color,
            outline="#2c3e50",
            width=3,
            tags=("machine", f"machine_{machine_id}")
        )

        # Pantalla
        screen_id = self.canvas.create_rectangle(
            x - 40, y - 25,
            x + 40, y + 10,
            fill="#ecf0f1",
            outline="#2c3e50",
            width=2,
            tags=("machine", f"machine_{machine_id}")
        )

        # Teclado
        for i in range(3):
            for j in range(4):
                self.canvas.create_rectangle(
                    x - 35 + j * 18, y + 15 + i * 6,
                    x - 35 + j * 18 + 15, y + 15 + i * 6 + 4,
                    fill="#2c3e50",
                    outline="",
                    tags=("machine", f"machine_{machine_id}")
                )

        # Etiqueta
        label_id = self.canvas.create_text(
            x, y - 60,
            text=label,
            font=("Arial", 14, "bold"),
            fill="#2c3e50",
            tags=("machine", f"machine_{machine_id}")
        )

        # Agregar hover events
        self.canvas.tag_bind(f"machine_{machine_id}", "<Enter>", lambda e, m=machine_id: self._show_machine_tooltip(e, m))
        self.canvas.tag_bind(f"machine_{machine_id}", "<Leave>", lambda e, m=machine_id: self._hide_machine_tooltip(m))

    def _on_canvas_resize(self, event):
        """Maneja el redimensionamiento del canvas."""
        self._draw_machines()

    def _show_machine_tooltip(self, event, machine_id):
        """Muestra tooltip con información de la máquina."""
        if self.machine_tooltips[machine_id] is None:
            x, y = event.x_root, event.y_root

            # Crear texto del tooltip
            info_lines = [f"Máquina {machine_id}"]

            if self.last_sent[machine_id]:
                info_lines.append(f"Último enviado: {self.last_sent[machine_id]}")
            else:
                info_lines.append("Último enviado: -")

            if self.last_received[machine_id]:
                info_lines.append(f"Último recibido: {self.last_received[machine_id]}")
            else:
                info_lines.append("Último recibido: -")

            info_text = "\n".join(info_lines)

            tooltip = tk.Toplevel(self.canvas)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x+10}+{y+10}")

            label = tk.Label(
                tooltip,
                text=info_text,
                background="#FFFFCC",
                relief="solid",
                borderwidth=1,
                font=("Courier", 9),
                justify="left",
                padx=5,
                pady=5
            )
            label.pack()

            self.machine_tooltips[machine_id] = tooltip

    def _hide_machine_tooltip(self, machine_id):
        """Oculta el tooltip de la máquina."""
        if self.machine_tooltips[machine_id]:
            self.machine_tooltips[machine_id].destroy()
            self.machine_tooltips[machine_id] = None

    def _on_protocol_change(self, event=None):
        """Muestra/oculta el campo de ventana según el protocolo seleccionado."""
        protocol_name = self.protocol_var.get()

        # Mostrar campo de ventana solo para Go-Back-N y Selective Repeat
        if protocol_name in ["Go-Back-N", "Selective Repeat"]:
            self.window_label.grid(row=0, column=8, padx=5, sticky="e")
            self.window_entry.grid(row=0, column=9, padx=5)
        else:
            self.window_label.grid_remove()
            self.window_entry.grid_remove()

    def _start_simulation(self):
        """Inicia la simulación."""
        try:
            # Obtener configuración
            protocol_name = self.protocol_var.get()
            protocol_class = self.protocols[protocol_name]

            error_rate = float(self.error_var.get())
            delay = float(self.delay_var.get())
            interval = float(self.interval_var.get())
            window_size = int(self.window_size_var.get())

            # Validar
            if not (0 <= error_rate <= 1):
                messagebox.showerror("Error", "La tasa de error debe estar entre 0.0 y 1.0")
                return

            if delay < 0 or interval < 0:
                messagebox.showerror("Error", "Los tiempos deben ser no negativos")
                return

            if not (2 <= window_size <= 8):
                messagebox.showerror("Error", "El tamaño de ventana debe estar entre 2 y 8")
                return

            # Crear simulador con callback y window_size
            self.simulator = Simulator(gui_callback=self._handle_simulator_event, window_size=window_size)
            self.simulator.add_machine("A", protocol_class, error_rate=error_rate, transmission_delay=delay)
            self.simulator.add_machine("B", protocol_class, error_rate=error_rate, transmission_delay=delay)
            self.simulator.start_simulation()

            # Resetear contadores
            self.packet_count = 0
            self.delivered_count = 0
            self._update_stats()

            # Actualizar UI
            self.running = True
            self.paused = False
            self.start_btn.config(state=tk.DISABLED)
            self.pause_btn.config(state=tk.NORMAL, text="⏸️ Pausar")
            self.stop_btn.config(state=tk.NORMAL)
            self.stats_labels["status"].config(text="▶️ Ejecutando", fg="#4CAF50")

            # Iniciar thread de simulación
            self.sim_config = {
                'interval': interval,
                'protocol_name': protocol_name
            }
            threading.Thread(target=self._simulation_loop, daemon=True).start()

            messagebox.showinfo("Iniciado", f"Simulación iniciada con protocolo: {protocol_name}")

        except ValueError as e:
            messagebox.showerror("Error", f"Valores inválidos: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al iniciar simulación: {e}")

    def _toggle_pause(self):
        """Pausa o reanuda la simulación."""
        if self.simulator:
            if self.paused:
                self.simulator.resume_simulation()
                self.paused = False
                self.pause_btn.config(text="⏸️ Pausar")
                self.stats_labels["status"].config(text="▶️ Ejecutando", fg="#4CAF50")
                # Reanudar todas las animaciones
                for anim in self.animations:
                    anim.resume()
            else:
                self.simulator.pause_simulation()
                self.paused = True
                self.pause_btn.config(text="▶️ Reanudar")
                self.stats_labels["status"].config(text="⏸️ Pausado", fg="#FF9800")
                # Pausar todas las animaciones
                for anim in self.animations:
                    anim.pause()

    def _stop_simulation(self):
        """Detiene la simulación."""
        self.running = False
        if self.simulator:
            self.simulator.stop_simulation()

        # Limpiar todas las animaciones
        for anim in self.animations:
            anim._cleanup()
        self.animations.clear()

        # Resetear rastreo de paquetes
        self.last_sent = {"A": None, "B": None}
        self.last_received = {"A": None, "B": None}

        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.stats_labels["status"].config(text="⏹️ Detenido", fg="#95a5a6")

    def _simulation_loop(self):
        """Loop principal de la simulación (corre en thread separado)."""
        index_a = 0  # Índice para A->B
        index_b = 0  # Índice para B->A
        next_send_time_a = 0.0
        next_send_time_b = self.sim_config['interval'] / 2  # Desfasar envíos
        start_time = time.time()
        last_pause_time = 0.0
        total_paused_time = 0.0

        # Detectar si el protocolo es bidireccional
        protocol_instance = self.simulator._machines["A"].protocol
        is_bidirectional = protocol_instance.is_bidirectional()

        while self.running and self.simulator:
            if not self.paused:
                # Calcular tiempo real transcurrido (excluyendo pausas)
                real_time = time.time() - start_time - total_paused_time

                # Enviar paquete A -> B (números)
                if not self.paused and real_time >= next_send_time_a:
                    data = str(index_a)
                    success = self.simulator.send_data("A", "B", data)

                    if success:
                        self.packet_count += 1
                        self._update_stats()
                        index_a += 1

                    next_send_time_a = real_time + self.sim_config['interval']

                # Enviar paquete B -> A (números, solo si es bidireccional)
                if not self.paused and is_bidirectional and real_time >= next_send_time_b:
                    data = str(index_b)
                    success = self.simulator.send_data("B", "A", data)

                    if success:
                        self.packet_count += 1
                        self._update_stats()
                        index_b += 1

                    next_send_time_b = real_time + self.sim_config['interval']

                # Procesar eventos pendientes cuyo tiempo haya llegado (solo si no está pausado)
                if not self.paused:
                    self.simulator.run_simulation_step(real_time)

            else:
                # Si acaba de pausar, registrar el tiempo
                if last_pause_time == 0.0:
                    last_pause_time = time.time()

            # Si se reanuda después de pausa, actualizar tiempo pausado
            if not self.paused and last_pause_time > 0.0:
                total_paused_time += time.time() - last_pause_time
                last_pause_time = 0.0

            time.sleep(0.05)  # Sleep corto para verificar eventos frecuentemente

    def add_packet_animation(self, frame, start_machine, end_machine, duration=1.0):
        """
        Agrega una animación de paquete.

        Args:
            frame: Frame a animar
            start_machine: 'A' o 'B'
            end_machine: 'A' o 'B'
            duration: Duración de la animación en segundos
        """
        start_pos = self.machine_a_pos if start_machine == "A" else self.machine_b_pos
        end_pos = self.machine_b_pos if end_machine == "B" else self.machine_a_pos

        # Ajustar posiciones para que salgan/lleguen del borde de las máquinas
        offset = 60
        if start_machine == "A":
            start_pos = (start_pos[0] + offset, start_pos[1])
            end_pos = (end_pos[0] - offset, end_pos[1])
        else:
            start_pos = (start_pos[0] - offset, start_pos[1])
            end_pos = (end_pos[0] + offset, end_pos[1])

        animation = PacketAnimation(self.canvas, frame, start_pos, end_pos, duration)
        self.animations.append(animation)

    def _animation_loop(self):
        """Loop de actualización de animaciones."""
        # Actualizar todas las animaciones
        self.animations = [anim for anim in self.animations if anim.update()]

        # Actualizar estadísticas
        if self.running:
            self._update_stats()

        # Programar siguiente actualización
        self.root.after(16, self._animation_loop)  # ~60 FPS

    def _handle_simulator_event(self, event_type, data):
        """
        Maneja eventos del simulador.

        Args:
            event_type: Tipo de evento ('packet_sent', 'packet_delivered')
            data: Datos del evento
        """
        if event_type == 'packet_sent':
            # Actualizar último enviado
            frame = data['frame']
            from_machine = data['from']
            if frame.packet:
                self.last_sent[from_machine] = frame.packet.data

            # Crear animación del paquete
            self.add_packet_animation(
                data['frame'],
                data['from'],
                data['to'],
                data['duration']
            )
        elif event_type == 'packet_delivered':
            # Actualizar último recibido
            packet = data['packet']
            machine_id = data['machine_id']
            self.last_received[machine_id] = packet.data

            self.delivered_count += 1

    def _update_stats(self):
        """Actualiza las estadísticas mostradas."""
        self.stats_labels["sent"].config(text=str(self.packet_count))
        self.stats_labels["delivered"].config(text=str(self.delivered_count))
        self.stats_labels["transit"].config(text=str(len(self.animations)))


def main():
    """Función principal."""
    root = tk.Tk()
    app = NetworkSimulatorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
