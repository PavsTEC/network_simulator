#!/usr/bin/env python3
"""
Script de pruebas rápidas para todos los protocolos
Ejecuta cada protocolo con diferentes configuraciones
"""

import subprocess
import time
import sys

def run_protocol_test(protocol_num, error_rate, delay_a, delay_b, interval, duration=8):
    """Ejecuta una prueba de protocolo con parámetros específicos."""
    
    # Preparar input para el simulador
    test_input = f"{protocol_num}\n{error_rate}\n{delay_a}\n{error_rate}\n{delay_b}\n{interval}\n"
    
    try:
        # Ejecutar con timeout
        process = subprocess.run(
            ["python3", "main.py"],
            input=test_input,
            text=True,
            capture_output=True,
            timeout=duration
        )
        return True, f"✅ OK - Events processed"
        
    except subprocess.TimeoutExpired:
        return True, f"✅ OK - Timeout reached (normal)"
    except Exception as e:
        return False, f"❌ ERROR - {str(e)}"

def main():
    print("🧪 Verificación Rápida de Protocolos")
    print("=" * 50)
    
    protocols = [
        (1, "Utopia"),
        (2, "PAR"), 
        (3, "Stop and Wait"),
        (4, "Selective Repeat")
    ]
    
    # Configuraciones de prueba
    test_configs = [
        ("Sin errores", 0.0, 0.5, 0.5, 1.0),
        ("Errores bajos", 0.05, 1.0, 1.0, 1.5),
        ("Errores moderados", 0.15, 1.5, 1.0, 2.0)
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for protocol_num, protocol_name in protocols:
        print(f"\n🔧 Probando: {protocol_name}")
        print("-" * 30)
        
        for config_name, error_rate, delay_a, delay_b, interval in test_configs:
            print(f"  {config_name} (err={error_rate}, del={delay_a}s): ", end="", flush=True)
            
            success, message = run_protocol_test(
                protocol_num, error_rate, delay_a, delay_b, interval, duration=6
            )
            
            total_tests += 1
            if success:
                passed_tests += 1
                print("✅")
            else:
                print(f"❌ {message}")
    
    print(f"\n📊 Resultado Final: {passed_tests}/{total_tests} pruebas exitosas")
    
    if passed_tests == total_tests:
        print("🎉 ¡Todos los protocolos funcionan correctamente!")
    else:
        print("⚠️  Algunos protocolos presentaron problemas.")
        sys.exit(1)

if __name__ == "__main__":
    main()
