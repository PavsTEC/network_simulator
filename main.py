"""
Simulador de Protocolos de Red - Versión Modular
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
    Descubre automáticamente todos los protocolos disponibles.
    
    Returns:
        Dict con {nombre: clase_protocolo} de todos los protocolos disponibles
    """
    available_protocols = {}
    
    # Lista de protocolos conocidos - se puede expandir fácilmente
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
            # Importar dinámicamente el módulo del protocolo
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
        print("❌ No se encontraron protocolos disponibles.")
        return None
    
    print("\n📋 Protocolos Disponibles:")
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
                print(f"✅ Protocolo seleccionado: {protocol_list[choice_num - 1][0]}")
                return selected_protocol
            else:
                print(f"❌ Opción inválida. Ingresa un número entre 1 y {len(protocol_list)}.")
                
        except (ValueError, KeyboardInterrupt):
            print("❌ Entrada inválida. Intenta nuevamente.")


def configure_simulation() -> dict:
    """
    Permite al usuario configurar los parámetros de la simulación.
    
    Returns:
        Dict con la configuración de la simulación
    """
    print("\n⚙️  Configuración de la Simulación:")
    print("=" * 40)
    
    config = {}
    
    # Configuración de máquinas
    try:
        config['machine_a_error_rate'] = float(input("Tasa de error máquina A (0.0-1.0) [0.1]: ").strip() or "0.1")
        config['machine_a_delay'] = float(input("Retardo transmisión máquina A (segundos) [1.0]: ").strip() or "1.0")

        config['machine_b_error_rate'] = float(input("Tasa de error máquina B (0.0-1.0) [0.1]: ").strip() or "0.1")
        config['machine_b_delay'] = float(input("Retardo transmisión máquina B (segundos) [1.0]: ").strip() or "1.0")

        config['send_interval'] = float(input("Intervalo entre envíos (segundos) [2.0]: ").strip() or "2.0")
        
        # Validaciones
        for key in ['machine_a_error_rate', 'machine_b_error_rate']:
            if not 0.0 <= config[key] <= 1.0:
                raise ValueError(f"Tasa de error debe estar entre 0.0 y 1.0")
        
        for key in ['machine_a_delay', 'machine_b_delay', 'send_interval']:
            if config[key] < 0:
                raise ValueError(f"Los tiempos deben ser no negativos")
                
    except ValueError as e:
        print(f"❌ Error en configuración: {e}")
        print("🔄 Usando valores por defecto...")
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
    Thread que escucha comandos del usuario durante la simulación.

    Args:
        sim: Instancia del simulador
    """
    print("\n💡 Comandos disponibles:")
    print("   'p' o 'pause'  - Pausar simulación")
    print("   'r' o 'resume' - Reanudar simulación")
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
                    print("\n📊 Estado: ⏸️  PAUSADA")
                else:
                    print("\n📊 Estado: ▶️  EJECUTANDO")
            elif command in ['q', 'quit']:
                print("\n👋 Saliendo de la simulación...")
                sim.stop_simulation()
                break
            elif command:
                print(f"\n❌ Comando desconocido: '{command}'")
                print("💡 Usa: p (pause), r (resume), s (status), q (quit)")

        except EOFError:
            break
        except Exception as e:
            print(f"\n⚠️  Error en comando: {e}")


def run_simulation(protocol_class: Type[ProtocolInterface], config: dict):
    """
    Ejecuta la simulación con el protocolo y configuración especificados.

    Args:
        protocol_class: Clase del protocolo a usar
        config: Configuración de la simulación
    """
    protocol_name = protocol_class("temp").get_protocol_name()

    print(f"\n🚀 Iniciando Simulación - Protocolo {protocol_name}")
    print("=" * 60)

    # Crear simulador principal
    sim = Simulator()

    # Registrar máquinas
    sim.add_machine("A", protocol_class,
                   error_rate=config['machine_a_error_rate'],
                   transmission_delay=config['machine_a_delay'])
    sim.add_machine("B", protocol_class,
                   error_rate=config['machine_b_error_rate'],
                   transmission_delay=config['machine_b_delay'])

    # Mostrar configuración
    print(f"\n📊 Configuración:")
    print(f"  Protocolo: {protocol_name}")
    print(f"  Máquina A: error_rate={sim.get_machine_error_rate('A')}, delay={sim.get_machine_transmission_delay('A')}s")
    print(f"  Máquina B: error_rate={sim.get_machine_error_rate('B')}, delay={sim.get_machine_transmission_delay('B')}s")
    print(f"  Intervalo de envío: {config['send_interval']}s")

    # Verificar si el protocolo es bidireccional
    temp_instance = protocol_class("temp")
    is_bidirectional = temp_instance.is_bidirectional()

    if is_bidirectional:
        print(f"\n📤 Protocolo bidireccional detectado")
        print(f"   A -> B: Enviando letras (A, B, C...)")
        print(f"   B -> A: Enviando números (0, 1, 2...)")
    else:
        print(f"\n📤 Iniciando envío del abecedario: A -> B")

    # Iniciar thread para escuchar comandos
    command_thread = threading.Thread(target=command_listener, args=(sim,), daemon=True)
    command_thread.start()

    # Inicializar el simulador una sola vez
    sim.start_simulation()

    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    index_a = 0
    index_b = 0
    last_send_time_a = time.time()
    last_send_time_b = time.time() + config['send_interval'] / 2  # Desfasar

    try:
        while sim._running:
            current_time = time.time()

            if not sim.is_paused():
                # Enviar A -> B
                if current_time - last_send_time_a >= config['send_interval']:
                    letter = alphabet[index_a % len(alphabet)]
                    success = sim.send_data("A", "B", letter)

                    if success:
                        print(f"\n[Main] 📨 A->B: '{letter}' ({index_a + 1})")
                        index_a += 1

                    last_send_time_a = current_time

                # Enviar B -> A (solo si es bidireccional)
                if is_bidirectional and current_time - last_send_time_b >= config['send_interval']:
                    digit = str(index_b % 10)
                    success = sim.send_data("B", "A", digit)

                    if success:
                        print(f"[Main] 📨 B->A: '{digit}' ({index_b + 1})")
                        index_b += 1

                    last_send_time_b = current_time

                # Procesar eventos generados
                sim.run_simulation()

            time.sleep(0.1)  # Sleep más corto para mejor respuesta

    except KeyboardInterrupt:
        print(f"\n[Main] ⏹️  Simulación detenida por usuario")
    finally:
        sim.stop_simulation()
        print("\n✅ Simulación completada!")


def main():
    """Función principal del simulador modular."""
    print("🌐 Simulador de Protocolos de Red - Versión Modular")
    print("=" * 55)
    
    try:
        # Seleccionar protocolo
        protocol_class = select_protocol()
        if protocol_class is None:
            print("👋 Simulación cancelada por el usuario.")
            return
        
        # Configurar simulación
        config = configure_simulation()
        
        # Ejecutar simulación
        run_simulation(protocol_class, config)
        
    except KeyboardInterrupt:
        print("\n👋 Simulación cancelada por el usuario.")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()