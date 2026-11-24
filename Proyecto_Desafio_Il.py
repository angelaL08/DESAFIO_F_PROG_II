import datetime
import hashlib
import os
import sys

# ==== SECCIÓN 1: CONFIGURACIÓN Y CONSTANTES =================================================
ENTIDAD = "Municipalidad Distrital de Víctor Larco Herrera"
CARPETA = os.path.dirname(os.path.abspath(__file__))        # los archivos se guardan junto al programa
ARCH_USUARIOS = os.path.join(CARPETA, "usuarios.txt")
ARCH_CIUDADANOS = os.path.join(CARPETA, "ciudadanos.txt")
ARCH_TRAMITES = os.path.join(CARPETA, "tramites.txt")
ARCH_SEGUIMIENTO = os.path.join(CARPETA, "seguimiento.txt")
ARCH_NOTIFICACIONES = os.path.join(CARPETA, "notificaciones.txt")
CARPETA_CARGOS = os.path.join(CARPETA, "cargos")
SEP = "|"                                                    # separador de campos en los .txt
     

    # 1. Validar nombre (no permite vacíos ni números) 

    while True: 

        remitente = input("Ingrese nombres y apellidos del remitente: ") 

        tiene_numero = False 

        for caracter in remitente: 

            if caracter.isdigit(): 

                tiene_numero = True 

                break 

        if tiene_numero or remitente.strip() == "": 

            print("Error: El nombre del remitente no puede estar vacío ni contener números.") 

        else: 

            break 

    # 2. Validar DNI/RUC  (solo números y exacto 8 u 11 dígitos) 

    while True: 

        identificacion = input("Ingrese DNI (8 dígitos) o RUC (11 dígitos): ") 

        if identificacion.isdigit() and (len(identificacion) == 8 or len(identificacion) == 11): 

            break 

        print("Error: La identificación debe contener solo números y tener exactamente 8 (DNI) u 11 (RUC) dígitos.") 

    # 3. Validar folios de inmediato (número entero positivo) 

    while True: 

        try: 

            folios = int(input("Ingrese cantidad de folios: ")) 

            if folios > 0: 

                break 

            else: 

                print("Error: La cantidad de folios debe ser mayor a 0.") 

        except ValueError: 

            print("Error: Ingrese un valor numérico válido para los folios.") 

    # 4. Resto de campos u opciones 

    tipo_doc = input("Ingrese tipo de documento (Solicitud/Oficio/Carta): ") 

    asunto = input("Ingrese asunto del trámite: ") 

    area_destino = input("Ingrese área de destino: ") 

    # Uso de datetime para fechas

    fecha_actual = datetime.date.today().strftime("%Y-%m-%d") 

    nuevo_exp = { 

        "codigo": codigo, 

        "remitente": remitente, 

        "identificacion": identificacion, 

        "tipoDoc": tipo_doc, 

        "asunto": asunto, 

        "areaDestino": area_destino, 

        "folios": folios, 

        "fecha": fecha_actual 

    } 

    lista_expedientes.append(nuevo_exp) 

    print(f"\n¡Expediente registrado exitosamente con fecha {fecha_actual}!") 


def buscar_expediente(lista_expedientes, codigo_buscado): 

    encontrado = False 

    for exp in lista_expedientes: 

        if exp["codigo"] == codigo_buscado: 

            print("\n--- EXPEDIENTE ENCONTRADO ---") 

            print(f"Código: {exp['codigo']}") 

            print(f"Remitente: {exp['remitente']}") 

            print(f"Identificación (DNI/RUC): {exp['identificacion']}") 

            print(f"Fecha de Registro: {exp['fecha']}") 

            print(f"Tipo: {exp['tipoDoc']} | Folios: {exp['folios']}") 

            print(f"Asunto: {exp['asunto']}") 

            print(f"Área Destino: {exp['areaDestino']}") 

            encontrado = True 

            break 

    if not encontrado: 

        print("No se encontró ningún expediente con el código ingresado.") 

 

def ver_historial(lista_expedientes): 

    print(f"\n--- HISTORIAL DE EXPEDIENTES (Total: {len(lista_expedientes)}) ---") 

    if len(lista_expedientes) == 0: 

        print("No hay expedientes registrados.") 

    else: 

        for i, exp in enumerate(lista_expedientes, 1): 

            print(f"{i}. Código: {exp['codigo']} | Remitente: {exp['remitente']} | DNI/RUC: {exp['identificacion']} | Fecha: {exp['fecha']}") 

 
# --- EJECUTAR MENÚ DE GESTIÓN DE EXPEDIENTES --- 

if __name__ == "__main__": 

    expedientes = [] 

    while True: 

        print("\n--- GESTIÓN DE EXPEDIENTES ---") 

        print("1. Registrar expediente") 

        print("2. Buscar expediente") 

        print("3. Ver historial y total de registros") 

        print("4. Salir") 

        opcion = input("Seleccione una opción: ") 

         
        if opcion == "1": 

            registrar_expediente(expedientes) 

        elif opcion == "2": 

            codigo = input("Ingrese el código a buscar: ") 

            buscar_expediente(expedientes, codigo) 

        elif opcion == "3": 

            ver_historial(expedientes) 

        elif opcion == "4": 

            print("Saliendo del programa...") 

            break 

        else: 

            print("Opción no válida. Intente nuevamente.")
# Validación avanzada            
