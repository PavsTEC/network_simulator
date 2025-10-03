#!/usr/bin/env python3
"""
Script de pruebas rápidas individuales para verificar protocolos específicos.
Permite probar un protocolo concreto con parámetros personalizados.
"""
import subprocess
import sys

def show_protocols():
    """Muestra los protocolos disponibles."""
    protocols = {
        1: "Utopia (Protocolo ideal)",
        2: "PAR (Positive ACK with Retransmission)", 
        3: "Stop and Wait",
        4: "Selective Repeat (Ventana deslizante bidireccional)"
    }
    
    print("📋 Protocolos Disponibles:")
    print("-" * 40)
    for num, name in protocols.items():
        print(f"  {num}. {name}")
    print("  0. Salir")
    return protocols

def get_user_input():
    """Obtiene configuración del usuario."""
    try:
        protocol = int(input("\n🔧 Selecciona protocolo (1-4, 0 para salir): "))
        if protocol == 0:
            return None
        if protocol not in [1, 2, 3, 4]:
            print("❌ Protocolo inválido")
            return None
            
        print(f"\n⚙️ Configuración para protocolo {protocol}:")
        error_a = float(input("   Tasa de error máquina A (0.0-1.0) [0.1]: ") or "0.1")
        delay_a = float(input("   Delay transmisión máquina A (segundos) [1.5]: ") or "1.5")
        error_b = float(input("   Tasa de error máquina B (0.0-1.0) [0.1]: ") or "0.1") 
        delay_b = float(input("   Delay transmisión máquina B (segundos) [1.5]: ") or "1.5")
        interval = float(input("   Intervalo entre envíos (segundos) [2.0]: ") or "2.0")
        
        return protocol, error_a, delay_a, error_b, delay_b, interval
        
    except (ValueError, KeyboardInterrupt):
        print("\n❌ Entrada inválida o cancelado por usuario")
        return None

def run_test(protocol, error_a, delay_a, error_b, delay_b, interval):
    """Ejecuta la prueba con los parámetros dados."""
    print(f"\n🚀 Ejecutando protocolo {protocol}...")
    print(f"   Errores: A={error_a}, B={error_b}")
    print(f"   Delays: A={delay_a}s, B={delay_b}s") 
    print(f"   Intervalo: {interval}s")
    print("\n   Presiona Ctrl+C para detener la simulación")
    print("   " + "="*45)
    
    # Preparar entrada
    input_data = f"{protocol}\n{error_a}\n{delay_a}\n{error_b}\n{delay_b}\n{interval}\n"
    
    try:
        # Ejecutar el simulador
        subprocess.run(
            ["python3", "main.py"],
            input=input_data,
            text=True
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Simulación detenida por usuario")
    except Exception as e:
        print(f"\n❌ Error ejecutando simulación: {e}")

def main():
    print("🧪 Pruebas Rápidas de Protocolos")
    print("=" * 40)
    
    while True:
        protocols = show_protocols()
        config = get_user_input()
        
        if config is None:
            print("\n👋 ¡Hasta luego!")
            break
            
        protocol, error_a, delay_a, error_b, delay_b, interval = config
        run_test(protocol, error_a, delay_a, error_b, delay_b, interval)
        
        # Preguntar si continuar
        try:
            continue_choice = input("\n¿Probar otro protocolo? (s/N): ").lower()
            if continue_choice not in ['s', 'si', 'sí', 'y', 'yes']:
                print("\n👋 ¡Hasta luego!")
                break
        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 ¡Hasta luego!")
        sys.exit(0)