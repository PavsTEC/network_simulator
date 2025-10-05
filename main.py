"""
Simulador de Protocolos de Red - Versin Modular
Este main puede funcionar con cualquier protocolo que implemente ProtocolInterface.
"""

import time
import importlib
import sys
import threading
from typing import Type, Optional
from simulation.simulator import Simulator
from protocols.protocol_interface import ProtocolInterface


def get_available_protocols() -> dict:
    """
    Descubre automticamente todos los protocolos disponibles.
    
    Returns:
        Dict con {nombre: clase_protocolo} de todos los protocolos disponibles
    """
    available_protocols = {}
    
    # Lista de protocolos conocidos - se puede expandir fcilmente
    protocol_modules = [
        'utopia',
        'stop_and_wait',
        'par',
        'sliding_window',
        'go_back_n',
        'selective_repeat',
    ]
    
    for module_name in protocol_modules:
        try:
            # Importar dinmicamente el mdulo del protocolo
            module = importlib.import_module(f'protocols.{module_name}')
            
            # Buscar clases que hereden de ProtocolInterface
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, ProtocolInterface) and 
                    attr != ProtocolInterface):
                    
                    # Crear una instancia temporal para obtener el nombre
                    temp_instance = attr("temp")
                    protocol_name = temp_instance.get_protocol_name()
                    available_protocols[protocol_name] = attr
                    
        except ImportError as e:
            print(f"[Warning] No se pudo cargar protocolo {module_name}: {e}")
            continue
    
    return available_protocols


def select_protocol() -> Optional[Type[ProtocolInterface]]:
    """
    Permite al usuario seleccionar un protocolo de los disponibles.
    
    Returns:
        Clase del protocolo seleccionado o None si se cancela
    """
    available_protocols = get_available_protocols()
    
    if not available_protocols:
        print(" No se encontraron protocolos disponibles.")
        return None
    
    print("\n Protocolos Disponibles:")
    print("=" * 40)
    
    protocol_list = list(available_protocols.items())
    for i, (name, protocol_class) in enumerate(protocol_list, 1):
        print(f"  {i}. {name}")
    
    print(f"  0. Salir")
    
    while True:
        try:
            choice = input(f"\nSelecciona un protocolo (1-{len(protocol_list)}, 0 para salir): ").strip()
            
            if choice == '0':
                return None
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(protocol_list):
                selected_protocol = protocol_list[choice_num - 1][1]
                protocol_name = protocol_list[choice_num - 1][0]
                print(f" Protocolo seleccionado: {protocol_name}")
                return selected_protocol, protocol_name
            else:
                print(f" Opcin invlida. Ingresa un nmero entre 1 y {len(protocol_list)}.")
                
        except (ValueError, KeyboardInterrupt):
            print(" Entrada invlida. Intenta nuevamente.")


def get_window_size(protocol_name: str) -> int:
    """
    Pregunta al usuario el tamaño de ventana para protocolos GBN y SR.

    Args:
        protocol_name: Nombre del protocolo

    Returns:
        Tamaño de ventana seleccionado
    """
    if protocol_name in ['Go-Back-N', 'Selective Repeat']:
        print(f"\n Configuracin de ventana para {protocol_name}:")
        try:
            window_size = int(input("Tamao de ventana N (2-8) [4]: ").strip() or "4")
            if 2 <= window_size <= 8:
                print(f" Tamao de ventana: {window_size}")
                return window_size
            else:
                print(" Valor fuera de rango. Usando valor por defecto N=4")
                return 4
        except ValueError:
            print(" Entrada invlida. Usando valor por defecto N=4")
            return 4
    return 4  # Valor por defecto


def configure_simulation() -> dict:
    """
    Permite al usuario configurar los parmetros de la simulacin.
    
    Returns:
        Dict con la configuracin de la simulacin
    """
    print("\n  Configuracin de la Simulacin:")
    print("=" * 40)
    
    config = {}
    
    # Configuracin de mquinas
    try:
        config['machine_a_error_rate'] = float(input("Tasa de error mquina A (0.0-1.0) [0.1]: ").strip() or "0.1")
        config['machine_a_delay'] = float(input("Retardo transmisin mquina A (segundos) [1.0]: ").strip() or "1.0")

        config['machine_b_error_rate'] = float(input("Tasa de error mquina B (0.0-1.0) [0.1]: ").strip() or "0.1")
        config['machine_b_delay'] = float(input("Retardo transmisin mquina B (segundos) [1.0]: ").strip() or "1.0")

        config['send_interval'] = float(input("Intervalo entre envos (segundos) [2.0]: ").strip() or "2.0")
        
        # Validaciones
        for key in ['machine_a_error_rate', 'machine_b_error_rate']:
            if not 0.0 <= config[key] <= 1.0:
                raise ValueError(f"Tasa de error debe estar entre 0.0 y 1.0")
        
        for key in ['machine_a_delay', 'machine_b_delay', 'send_interval']:
            if config[key] < 0:
                raise ValueError(f"Los tiempos deben ser no negativos")
                
    except ValueError as e:
        print(f" Error en configuracin: {e}")
        print(" Usando valores por defecto...")
        config = {
            'machine_a_error_rate': 0.1,
            'machine_a_delay': 1.0,
            'machine_b_error_rate': 0.1,
            'machine_b_delay': 1.0,
            'send_interval': 2.0
        }
    
    return config


def command_listener(sim: Simulator):
    """
    Thread que escucha comandos del usuario durante la simulacin.

    Args:
        sim: Instancia del simulador
    """
    print("\n Comandos disponibles:")
    print("   'p' o 'pause'  - Pausar simulacin")
    print("   'r' o 'resume' - Reanudar simulacin")
    print("   's' o 'status' - Mostrar estado")
    print("   'q' o 'quit'   - Salir\n")

    while True:
        try:
            command = input().strip().lower()

            if command in ['p', 'pause']:
                sim.pause_simulation()
            elif command in ['r', 'resume']:
                sim.resume_simulation()
            elif command in ['s', 'status']:
                if sim.is_paused():
                    print("\n Estado:   PAUSADA")
                else:
                    print("\n Estado:   EJECUTANDO")
            elif command in ['q', 'quit']:
                print("\n Saliendo de la simulacin...")
                sim.stop_simulation()
                break
            elif command:
                print(f"\n Comando desconocido: '{command}'")
                print(" Usa: p (pause), r (resume), s (status), q (quit)")

        except EOFError:
            break
        except Exception as e:
            print(f"\n  Error en comando: {e}")


def run_simulation(protocol_class: Type[ProtocolInterface], config: dict, window_size: int = 4):
    """
    Ejecuta la simulacin con el protocolo y configuracin especificados.

    Args:
        protocol_class: Clase del protocolo a usar
        config: Configuracin de la simulacin
        window_size: Tamaño de ventana para GBN y SR
    """
    protocol_name = protocol_class("temp").get_protocol_name()

    print(f"\n Iniciando Simulacin - Protocolo {protocol_name}")
    print("=" * 60)

    # Crear simulador principal con window_size
    sim = Simulator(window_size=window_size)

    # Registrar mquinas
    sim.add_machine("A", protocol_class,
                   error_rate=config['machine_a_error_rate'],
                   transmission_delay=config['machine_a_delay'])
    sim.add_machine("B", protocol_class,
                   error_rate=config['machine_b_error_rate'],
                   transmission_delay=config['machine_b_delay'])

    # Mostrar configuracin
    print(f"\n Configuracin:")
    print(f"  Protocolo: {protocol_name}")
    print(f"  Mquina A: error_rate={sim.get_machine_error_rate('A')}, delay={sim.get_machine_transmission_delay('A')}s")
    print(f"  Mquina B: error_rate={sim.get_machine_error_rate('B')}, delay={sim.get_machine_transmission_delay('B')}s")
    print(f"  Intervalo de envo: {config['send_interval']}s")

    # Verificar si el protocolo es bidireccional
    temp_instance = protocol_class("temp")
    is_bidirectional = temp_instance.is_bidirectional()

    if is_bidirectional:
        print(f"\n Protocolo bidireccional detectado")
        print(f"   A -> B: Enviando nmeros (0, 1, 2...)")
        print(f"   B -> A: Enviando nmeros (0, 1, 2...)")
    else:
        print(f"\n Iniciando envo de datos: A -> B")

    # Iniciar thread para escuchar comandos
    command_thread = threading.Thread(target=command_listener, args=(sim,), daemon=True)
    command_thread.start()

    # Inicializar el simulador una sola vez
    sim.start_simulation()

    index_a = 0
    index_b = 0
    last_send_time_a = time.time()
    last_send_time_b = time.time() + config['send_interval'] / 2  # Desfasar

    try:
        while sim._running:
            current_time = time.time()

            if not sim.is_paused():
                # Enviar A -> B (números)
                if current_time - last_send_time_a >= config['send_interval']:
                    data = str(index_a)
                    success = sim.send_data("A", "B", data)

                    if success:
                        print(f"\n[Main]  A->B: '{data}' ({index_a + 1})")
                        index_a += 1

                    last_send_time_a = current_time

                # Enviar B -> A (números, solo si es bidireccional)
                if is_bidirectional and current_time - last_send_time_b >= config['send_interval']:
                    data = str(index_b)
                    success = sim.send_data("B", "A", data)

                    if success:
                        print(f"[Main]  B->A: '{data}' ({index_b + 1})")
                        index_b += 1

                    last_send_time_b = current_time

                # Procesar eventos generados
                sim.run_simulation()

            time.sleep(0.1)  # Sleep ms corto para mejor respuesta

    except KeyboardInterrupt:
        print(f"\n[Main]   Simulacin detenida por usuario")
    finally:
        sim.stop_simulation()
        print("\n Simulacin completada!")


def main():
    """Funcin principal del simulador modular."""
    print(" Simulador de Protocolos de Red - Versin Modular")
    print("=" * 55)
    
    try:
        # Seleccionar protocolo
        result = select_protocol()
        if result is None:
            print(" Simulacin cancelada por el usuario.")
            return

        protocol_class, protocol_name = result

        # Obtener tamaño de ventana para GBN y SR
        window_size = get_window_size(protocol_name)

        # Configurar simulacin
        config = configure_simulation()

        # Ejecutar simulacin
        run_simulation(protocol_class, config, window_size)
        
    except KeyboardInterrupt:
        print("\n Simulacin cancelada por el usuario.")
    except Exception as e:
        print(f"\n Error inesperado: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()