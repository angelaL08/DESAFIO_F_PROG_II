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
     
# Campos de cada archivo, en el orden en que se guardan en cada línea
CAMPOS_USUARIO = ["dni", "apellidos", "nombres", "clave", "rol"]
CAMPOS_CIUDADANO = ["identificacion", "remitente", "telefono", "correo"]
CAMPOS_TRAMITE = ["codigo", "fecha", "hora", "identificacion", "remitente", "motivo",
                  "descripcion", "tipoDoc", "areaDestino", "folios", "usuario", "estado"]
CAMPOS_SEGUIMIENTO = ["codigo", "estado", "fecha", "hora", "observacion", "usuario"]

ROLES = ["Administrador", "Mesa de Partes", "Funcionario"]
TIPOS = ["Solicitud", "Oficio", "Carta", "Informe", "Reclamo"]
MOTIVOS = ["Pago de fraccionamiento", "Exoneración de multa", "Reclamo", "Solicitud de licencia",
           "Constancia o certificado", "Permiso o autorización", "Información pública"]
AREAS = ["Gerencia Municipal", "Desarrollo Urbano", "Obras Públicas",
         "Rentas y Tributaciones", "Secretaría General", "Servicios a la Ciudad"]
CRITERIOS = ["Código", "Fecha", "Remitente", "Estado"]
# Área que normalmente atiende cada motivo: se ofrece como sugerencia al registrar
AREA_POR_MOTIVO = {"Pago de fraccionamiento": "Rentas y Tributaciones",
                   "Exoneración de multa": "Rentas y Tributaciones", "Reclamo": "Secretaría General",
                   "Solicitud de licencia": "Desarrollo Urbano",
                   "Constancia o certificado": "Secretaría General",
                   "Permiso o autorización": "Obras Públicas", "Información pública": "Secretaría General"}

# Máquina de estados: cada estado indica a cuáles puede pasar (los finales no pasan a ninguno)
ESTADOS = ["Registrado", "Observado", "Subsanado", "Aprobado", "Concluido", "Rechazado"]
ESTADOS_FINALES = ["Aprobado", "Concluido", "Rechazado"]
TRANSICIONES = {
    "Registrado": ["Observado", "Aprobado", "Concluido", "Rechazado"],
    "Observado": ["Subsanado", "Rechazado"],
    "Subsanado": ["Observado", "Aprobado", "Concluido", "Rechazado"],
    "Aprobado": [], "Concluido": [], "Rechazado": [],
}
MIGRAR_ESTADOS = {"Derivado": "Registrado", "En atención": "Registrado", "Atendido": "Concluido"}
MOTIVOS_OBSERVACION = ["Falta DNI legalizado", "Falta comprobante de pago TUA o TR",
                       "Documentación incompleta o ilegible"]
MOTIVOS_RECHAZO = ["Identidad no acreditada, documento de un tercero",
                   "Documentación falsa o adulterada", "Incumplimiento insubsanable de requisitos"]
AVISOS = []   # mensajes de la carga de archivos, se muestran en la pantalla de acceso

# ==== SECCIÓN 2: INTERFAZ DE CONSOLA ========================================================
class Cancelado(Exception):
    """Se lanza cuando el usuario escribe X: aborta la operación en curso."""

def limpiar_pantalla():
    if sys.stdout.isatty():
        os.system("cls" if os.name == "nt" else "clear")
    else: print("\n\n")

def pausa():
    input("\n  Presione ENTER para continuar...")

def titulo(texto, cancelable=False):
    print(f"\n  {texto.upper()}\n  " + "=" * len(texto))
    if cancelable: print("  Escriba X en cualquier momento para cancelar.")
    print()

def seccion(texto):
    print(f"\n  {texto}\n  " + "-" * len(texto))

def plural(n, singular, forma_plural=""):
    """plural(2, 'expediente') da '2 expedientes'; plural(1, ...) da '1 expediente'."""
    return f"{n} {singular}" if n == 1 else f"{n} {forma_plural or singular + 's'}"

def leer(mensaje):
    """input() que permite cancelar la operación escribiendo X (lanza Cancelado)."""
    texto = input(mensaje)
    if texto.strip().upper() == "X": raise Cancelado
    return texto

def leer_tecla():
    """Lee una tecla sin mostrarla (Windows, Linux y Mac)."""
    if os.name == "nt":
        import msvcrt
        return msvcrt.getwch()
    import termios, tty
    fd, viejo = sys.stdin.fileno(), termios.tcgetattr(sys.stdin.fileno())
    try:
        tty.setcbreak(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, viejo)

def leer_clave(mensaje):
    """Pide la clave mostrando * por cada letra; sin terminal real (editores) usa input normal."""
    texto = ""
    if not sys.stdin.isatty(): texto = input(mensaje)
    else:
        print(mensaje, end="", flush=True)
        while (c := leer_tecla()) not in ("\r", "\n"):
            if c in ("\x00", "\xe0"): leer_tecla()          # teclas especiales de Windows
            elif c in ("\x08", "\x7f") and texto: texto = texto[:-1]; print("\b \b", end="", flush=True)
            elif c >= " " and c != "\x7f": texto += c; print("*", end="", flush=True)
        print()
    if texto.strip().upper() == "X": raise Cancelado
    return texto

# ==== SECCIÓN 3: VALIDACIÓN Y ENTRADA DE DATOS ==============================================
# ---------- Utilidades de texto y fecha ----------
def solo_digitos(texto):
    """True si el texto no está vacío y todos sus caracteres son dígitos."""
    return texto != "" and all(c in "0123456789" for c in texto)

def limpiar(texto):
    """Quita espacios sobrantes y evita que el separador | rompa los archivos."""
    return " ".join(texto.replace(SEP, "/").split())

def sin_tildes(texto):
    """José pasa a jose: sirve para comparar sin distinguir tildes ni mayúsculas."""
    return texto.lower().translate(str.maketrans("áéíóúüñ", "aeiouun"))

def ahora():
    d = datetime.datetime.now()
    return d.strftime("%Y-%m-%d"), d.strftime("%H:%M")

def parsear_fecha(texto):
    """Acepta AAAA-MM-DD, DD/MM/AAAA, DD-MM-AAAA o solo el día del mes actual."""
    texto = texto.strip()
    if solo_digitos(texto) and len(texto) <= 2:
        hoy = datetime.date.today()
        try:
            return datetime.date(hoy.year, hoy.month, int(texto)).strftime("%Y-%m-%d")
        except ValueError:
            return None
    for formato in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
        try:
            return datetime.datetime.strptime(texto, formato).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None

def dias_desde(fecha):
    """Días transcurridos desde una fecha AAAA-MM-DD hasta hoy."""
    try:
        return (datetime.date.today() - datetime.date.fromisoformat(fecha)).days
    except ValueError:
        return 0

def es_correo_valido(correo):
    if " " in correo or correo.count("@") != 1 or ".." in correo: return False
    usuario, dominio = correo.split("@")
    extension = dominio.split(".")[-1]
    return usuario != "" and "." in dominio and not dominio.startswith(".") and len(extension) >= 2 and extension.isalpha()

# ---------- Campos de texto y números ----------
def pedir_texto(mensaje, minimo=1):
    while True:
        valor = limpiar(leer(mensaje))
        if len(valor) >= minimo: return valor
        print(f"  Error: escriba al menos {minimo} caracteres.")

def pedir_nombre(mensaje):
    """Nombre con solo letras, mínimo 3. Se guarda con la primera letra en mayúscula."""
    while True:
        valor = limpiar(leer(mensaje))
        if sum(c.isalpha() for c in valor) >= 3 and all(c.isalpha() or c in " .'-" for c in valor):
            return valor.title()
        print("  Error: use solo letras, mínimo 3, sin números.")

def pedir_digitos(mensaje, largos, error):
    """Pide un número de solo dígitos cuya longitud esté en la lista 'largos'."""
    while True:
        valor = leer(mensaje).strip()
        if solo_digitos(valor) and len(valor) in largos: return valor
        print(error)

def pedir_dni(mensaje="DNI de 8 dígitos: "):
    return pedir_digitos(mensaje, [8], "  Error: el DNI debe tener exactamente 8 dígitos.")

def pedir_identificacion():
    return pedir_digitos("DNI de 8 dígitos o RUC de 11 dígitos del remitente: ", [8, 11],
                         "  Error: solo números, 8 dígitos para DNI u 11 para RUC.")

def pedir_telefono():
    return pedir_digitos("Teléfono de contacto, solo números: ", [7, 8, 9],
                         "  Error: el teléfono debe tener entre 7 y 9 dígitos.")

def pedir_correo():
    while True:
        valor = leer("Correo electrónico de contacto: ").strip().lower()
        if es_correo_valido(valor): return valor
        print("  Error: correo inválido. Ejemplo: nombre@dominio.com")

def pedir_folios():
    while True:
        valor = leer("Cantidad de fojas o folios: ").strip()
        if solo_digitos(valor) and int(valor) > 0: return int(valor)
        print("  Error: ingrese un número entero mayor a 0.")

def pedir_fecha(mensaje, por_defecto=None):
    """Pide una fecha. Si se da por_defecto, Enter la devuelve sin preguntar más."""
    while True:
        texto = leer(mensaje).strip()
        if texto == "" and por_defecto is not None: return por_defecto
        fecha = parsear_fecha(texto)
        if fecha: return fecha
        print("  Error: fecha inválida. Use el día, como 18, o DD/MM/AAAA.")

def pedir_periodo():
    """Devuelve (desde, hasta, texto). Enter en 'Desde' abarca todo el historial."""
    print("  Periodo a analizar. Enter para todo el historial.\n")
    desde = pedir_fecha("Desde, por ejemplo 17 o 17/11/2026: ", "")
    if desde == "": return "0000-00-00", "9999-99-99", "todo el historial"
    hasta = pedir_fecha("Hasta, Enter para la misma fecha: ", desde)
    if hasta < desde:
        desde, hasta = hasta, desde
    return desde, hasta, f"del {desde} al {hasta}"

# ---------- Confirmaciones y menús de opciones ----------
def confirmar(pregunta):
    return sin_tildes(leer(f"{pregunta} s/n: ").strip()) in ["s", "si"]

def pedir_numero_opcion(cantidad, indicacion="", permitir_vacio=False):
    """Pide un número de 1 a cantidad. Devuelve 0 si se permite Enter y se presionó."""
    while True:
        eleccion = leer(f"Seleccione una opción{indicacion}: ").strip()
        if eleccion == "" and permitir_vacio: return 0
        if solo_digitos(eleccion) and 1 <= int(eleccion) <= cantidad: return int(eleccion)
        print("  Opción no válida.")

def submenu(opciones):
    """Muestra opciones numeradas y devuelve el número elegido."""
    for i, op in enumerate(opciones, 1): print(f"  {i}. {op}")
    print()
    return pedir_numero_opcion(len(opciones))

def elegir(pregunta, opciones, otro=False, por_defecto=""):
    """Menú que devuelve el texto elegido. otro=True permite escribir otro valor."""
    print(f"\n{pregunta}")
    lista = opciones + (["Otro, escribir"] if otro else [])
    for i, op in enumerate(lista, 1): print(f"  {i}. {op}" + ("   <- sugerida" if op == por_defecto else ""))
    n = pedir_numero_opcion(len(lista), ", Enter para la sugerida" if por_defecto else "", por_defecto != "")
    if n == 0: return por_defecto
    if otro and n == len(lista): return pedir_texto("Escriba el valor: ")
    return lista[n - 1]

# ==== SECCIÓN 4: ARCHIVOS Y PERSISTENCIA ====================================================
def cargar_archivo(nombre, campos, numericos=()):
    """Lee un archivo y devuelve una lista de diccionarios. Avisa de las líneas dañadas."""
    lista, omitidas = [], 0
    try:
        with open(nombre, "r", encoding="utf-8-sig") as f:
            for linea in f:
                if linea.strip() == "": continue
                partes = linea.rstrip("\r\n").split(SEP)
                if len(partes) != len(campos) or not all(solo_digitos(partes[campos.index(c)]) for c in numericos):
                    omitidas += 1
                    continue
                reg = dict(zip(campos, partes))        # une cada campo con su valor
                for c in numericos: reg[c] = int(reg[c])
                lista.append(reg)
    except FileNotFoundError:
        pass                                           # primera vez: el archivo aún no existe
    except (OSError, UnicodeDecodeError) as error:
        AVISOS.append(f"No se pudo leer {os.path.basename(nombre)}: {error}")
    if omitidas > 0:
        AVISOS.append(f"{plural(omitidas, 'línea dañada', 'líneas dañadas')} en {os.path.basename(nombre)} fueron ignoradas.")
    return lista

def guardar_archivo(nombre, campos, lista):
    """Guarda en un archivo temporal y luego lo reemplaza, para no perder datos si algo falla."""
    try:
        with open(nombre + ".tmp", "w", encoding="utf-8") as f:
            for reg in lista:
                f.write(SEP.join(str(reg[c]) for c in campos) + "\n")
        os.replace(nombre + ".tmp", nombre)
    except OSError as error:
        print(f"  Error al guardar {os.path.basename(nombre)}: {error}")

def cargar_todo():
    """Carga los cuatro archivos y los junta en un solo diccionario 'bd'."""
    bd = {"usuarios": cargar_archivo(ARCH_USUARIOS, CAMPOS_USUARIO),
          "ciudadanos": cargar_archivo(ARCH_CIUDADANOS, CAMPOS_CIUDADANO),
          "tramites": cargar_archivo(ARCH_TRAMITES, CAMPOS_TRAMITE, ["codigo", "folios"]),
          "seguimiento": cargar_archivo(ARCH_SEGUIMIENTO, CAMPOS_SEGUIMIENTO, ["codigo"])}
    for reg in bd["tramites"] + bd["seguimiento"]:         # convierte estados de versiones anteriores
        reg["estado"] = MIGRAR_ESTADOS.get(reg["estado"], reg["estado"])
    for u in bd["usuarios"]:
        if u["rol"] not in ROLES: u["rol"] = "Mesa de Partes"
    return bd

def guardar_todo(bd):
    guardar_archivo(ARCH_USUARIOS, CAMPOS_USUARIO, bd["usuarios"])
    guardar_archivo(ARCH_CIUDADANOS, CAMPOS_CIUDADANO, bd["ciudadanos"])
    guardar_archivo(ARCH_TRAMITES, CAMPOS_TRAMITE, bd["tramites"])
    guardar_archivo(ARCH_SEGUIMIENTO, CAMPOS_SEGUIMIENTO, bd["seguimiento"])

def escribir_texto(ruta, lineas):
    """Escribe un archivo de texto, creando la carpeta si hace falta. Devuelve True si pudo."""
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("\n".join(lineas) + "\n")
        return True
    except OSError as error:
        print(f"  No se pudo escribir {os.path.basename(ruta)}: {error}")
        return False

# ==== SECCIÓN 5: SEGURIDAD Y ACCESO =========================================================
def cifrar(dni, clave):
    """Convierte la clave en un texto cifrado (PBKDF2). La clave real nunca se guarda."""
    sal = (dni + ":mesa-de-partes").encode("utf-8")
    return "pbkdf2$" + hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), sal, 100000).hex()

def clave_correcta(usuario, clave):
    """Compara la clave escrita con la guardada. Actualiza cuentas con el cifrado antiguo."""
    if usuario["clave"].startswith("pbkdf2$"): return usuario["clave"] == cifrar(usuario["dni"], clave)
    antiguo = hashlib.sha256((usuario["dni"] + ":" + clave).encode("utf-8")).hexdigest()
    if usuario["clave"] == antiguo:
        usuario["clave"] = cifrar(usuario["dni"], clave)
        return True
    return False

def buscar_usuario(bd, dni):
    for u in bd["usuarios"]:
        if u["dni"] == dni: return u
    return None

def nombre_usuario(bd, dni):
    u = buscar_usuario(bd, dni)
    return f"{u['nombres']} {u['apellidos']}" if u else dni

def pedir_clave_nueva(mensaje):
    """Pide una clave de mínimo 6 caracteres y la repetición para confirmarla."""
    while True:
        clave = leer_clave(mensaje)
        if len(clave) < 6: print("  Error: la clave debe tener al menos 6 caracteres.")
        elif leer_clave("Repita la clave: ") != clave: print("  Error: las claves no coinciden.")
        else: return clave

def login(bd):
    """Da 3 intentos. Devuelve el usuario o None."""
    titulo("Iniciar sesión", cancelable=True)
    for restantes in [2, 1, 0]:
        dni = leer("DNI: ").strip()
        clave = leer_clave("Clave: ")
        u = buscar_usuario(bd, dni)
        if u and clave_correcta(u, clave):
            guardar_todo(bd)       # guarda la actualización de cifrado, si la hubo
            return u
        print(f"  DNI o clave incorrectos. Intentos restantes: {restantes}\n")
    print("  Demasiados intentos fallidos.")
    return None

# ==== SECCIÓN 6: DATOS BASE: BÚSQUEDA, FILTROS, ORDENAMIENTO, SEGUIMIENTO, AVISOS Y CARGO ====
# ---------- Ciudadanos: remitentes conocidos ----------
def buscar_ciudadano(bd, identificacion):
    """Busca al remitente por DNI o RUC, también en expedientes de versiones anteriores."""
    for c in bd["ciudadanos"]:
        if c["identificacion"] == identificacion: return c
    for t in reversed(bd["tramites"]):
        if t["identificacion"] == identificacion:
            return {"identificacion": identificacion, "remitente": t["remitente"], "telefono": "", "correo": ""}
    return None

def guardar_ciudadano(bd, ciudadano):
    """Reemplaza al ciudadano si ya existe, o lo agrega si es nuevo."""
    for i, c in enumerate(bd["ciudadanos"]):
        if c["identificacion"] == ciudadano["identificacion"]:
            bd["ciudadanos"][i] = ciudadano
            return
    bd["ciudadanos"].append(ciudadano)

# ---------- Búsqueda y filtros de expedientes ----------
def buscar_codigo(lista, texto):
    """Búsqueda secuencial por número de expediente. Acepta 1, N° 1 o EXP-1."""
    digitos = "".join(c for c in texto if c in "0123456789")
    for t in lista:
        if digitos != "" and t["codigo"] == int(digitos): return t
    return None

def pedir_expediente(bd, permitir_ultimo=True):
    """Pide un número de expediente. Con permitir_ultimo, Enter elige el último registrado."""
    ultimo = bd["tramites"][-1] if bd["tramites"] and permitir_ultimo else None
    if ultimo:
        texto = leer(f"Número de expediente, o Enter para el último registrado N° {ultimo['codigo']}: ").strip()
    else: texto = leer("Número de expediente, por ejemplo 1: ").strip()
    if texto == "" and ultimo: return ultimo
    t = buscar_codigo(bd["tramites"], texto)
    if not t: print("  No se encontró ese expediente.")
    return t

def siguiente_codigo(bd):
    """El código es autonumérico: el mayor existente más uno."""
    return max([0] + [t["codigo"] for t in bd["tramites"]]) + 1

def filtrar_por_fecha(lista, desde, hasta):
    return [t for t in lista if desde <= t["fecha"] <= hasta]

def filtrar_por_estado(lista, estado):
    return [t for t in lista if t["estado"] == estado]

def filtrar_pendientes(lista):
    """Expedientes que todavía no están en un estado final."""
    return [t for t in lista if t["estado"] not in ESTADOS_FINALES]

# ---------- Ordenamiento burbuja ----------
def valor_orden(item, criterio):
    """Devuelve el dato por el que se compara un elemento según el criterio de orden."""
    if criterio == "Código": return item["codigo"]
    if criterio == "Fecha": return (item["fecha"], item["hora"], item["codigo"])
    if criterio == "Remitente": return sin_tildes(item["remitente"])
    if criterio == "Estado": return ESTADOS.index(item["estado"]) if item["estado"] in ESTADOS else 99
    return item[0] if criterio == "Clave" else item[1]   # pares (clave, cantidad) de los reportes

def ordenar_burbuja(lista, criterio, descendente=False):
    """Ordenamiento burbuja: compara vecinos y los intercambia. Se detiene si ya no hay cambios."""
    copia = lista[:]
    n = len(copia)
    for i in range(n - 1):
        hubo_cambio = False
        for j in range(n - 1 - i):
            a, b = valor_orden(copia[j], criterio), valor_orden(copia[j + 1], criterio)
            if (a < b) if descendente else (a > b):
                copia[j], copia[j + 1] = copia[j + 1], copia[j]
                hubo_cambio = True
        if not hubo_cambio: break
    return copia

# ---------- Seguimiento, notificaciones y cargo de recepción ----------
def agregar_seguimiento(bd, codigo, estado, observacion, usuario):
    """Añade una línea al historial (seguimiento.txt): quién, cuándo y qué pasó."""
    fecha, hora = ahora()
    bd["seguimiento"].append({"codigo": codigo, "estado": estado, "fecha": fecha, "hora": hora,
                              "observacion": limpiar(observacion), "usuario": usuario["dni"]})

def contacto_de(bd, t):
    """Devuelve (teléfono, correo) del remitente, o 'sin registrar' si faltan."""
    cit = buscar_ciudadano(bd, t["identificacion"])
    telefono = cit["telefono"] if cit and cit["telefono"] != "" else "sin registrar"
    correo = cit["correo"] if cit and cit["correo"] != "" else "sin registrar"
    return telefono, correo

def notificar(bd, t, mensaje):
    """Genera la notificación al administrado y la guarda en notificaciones.txt."""
    telefono, correo = contacto_de(bd, t)
    fecha, hora = ahora()
    linea = SEP.join([fecha, hora, f"Exp. N° {t['codigo']}", correo, telefono, t["estado"], limpiar(mensaje)])
    try:
        with open(ARCH_NOTIFICACIONES, "a", encoding="utf-8") as f:     # "a" = añadir al final
            f.write(linea + "\n")
    except OSError as error:
        print(f"  Aviso: no se pudo guardar la notificación: {error}")
    return telefono, correo

def generar_cargo(t, usuario):
    """Crea el cargo de recepción que se entrega al ciudadano. Devuelve la ruta o None."""
    ruta = os.path.join(CARPETA_CARGOS, f"cargo_expediente_{t['codigo']}.txt")
    datos = [("Expediente N°", t["codigo"]), ("Fecha y hora", f"{t['fecha']} {t['hora']}"),
             ("Remitente", t["remitente"]), ("DNI o RUC", t["identificacion"]),
             ("Documento", t["tipoDoc"]), ("Motivo", t["motivo"]), ("Folios", t["folios"]),
             ("Área destino", t["areaDestino"]),
             ("Recibido por", f"{usuario['nombres']} {usuario['apellidos']}")]
    lineas = [ENTIDAD.upper(), "CARGO DE RECEPCIÓN DE DOCUMENTOS", "=" * 56, ""]
    lineas += [f"{etiqueta:<14}: {valor}" for etiqueta, valor in datos]
    lineas += ["", "Conserve este cargo: con el N° de expediente puede consultar su trámite."]
    return ruta if escribir_texto(ruta, lineas) else None

# ==== SECCIÓN 7: PRESENTACIÓN: FICHA, HISTORIAL Y TABLAS ====================================
def mostrar_ficha(bd, t):
    """Muestra todos los datos de un expediente, con el tiempo que lleva en trámite."""
    telefono, correo = contacto_de(bd, t)
    if t["estado"] in ESTADOS_FINALES:
        movimientos = [s for s in bd["seguimiento"] if s["codigo"] == t["codigo"]]
        tiempo = "Cerrado el " + (movimientos[-1]["fecha"] if movimientos else t["fecha"])
    else:
        dias = dias_desde(t["fecha"])
        tiempo = "Ingresó hoy" if dias == 0 else plural(dias, "día") + " en trámite"
    filas = [("Fecha y hora", f"{t['fecha']} {t['hora']}"), ("Tiempo", tiempo),
             ("Estado actual", t["estado"]), None,
             ("Remitente", t["remitente"]),
             ("DNI" if len(t["identificacion"]) == 8 else "RUC", t["identificacion"]),
             ("Teléfono", telefono), ("Correo", correo), None,
             ("Tipo documento", t["tipoDoc"]), ("Motivo", t["motivo"]),
             ("Descripción", t["descripcion"]), ("Fojas o folios", t["folios"]),
             ("Área actual", t["areaDestino"]), ("Registrado por", nombre_usuario(bd, t["usuario"]))]
    borde = "  " + "=" * 58
    print(f"{borde}\n  EXPEDIENTE N° {t['codigo']}\n{borde}")
    for fila in filas:
        if fila is None: print()
        else: print(f"  {fila[0]:<14} : {fila[1]}")
    print(borde)

def mostrar_historial(bd, codigo):
    """Muestra todos los movimientos del expediente, tomados de seguimiento.txt."""
    print(f"\n  HISTORIAL DEL EXPEDIENTE N° {codigo}\n  " + "-" * 70)
    movimientos = [s for s in bd["seguimiento"] if s["codigo"] == codigo]
    for s in movimientos:
        print(f"\n  {s['fecha']} {s['hora']}   {s['estado']}   por {nombre_usuario(bd, s['usuario'])}")
        print(f"      {s['observacion']}")
    if not movimientos: print("\n  Sin movimientos.")
    print("\n  " + "-" * 70)

def pantalla_expediente(bd, t, con_historial=True):
    """Limpia la pantalla y muestra la ficha del expediente, con su historial si se pide."""
    limpiar_pantalla()
    print()
    mostrar_ficha(bd, t)
    if con_historial:
        mostrar_historial(bd, t["codigo"])

def mostrar_tabla(lista, con_dias=False):
    if not lista:
        print("  Sin resultados.")
        return
    ancho = 95 if con_dias else 91
    print(f"  {'N°':<6}{'Fecha':<12}{'Remitente':<24}{'DNI o RUC':<13}{'Estado':<12}{'Área':<24}" + ("Días" if con_dias else ""))
    print("  " + "-" * ancho)
    for t in lista:
        fila = (f"  {t['codigo']:<6}{t['fecha']:<12}{t['remitente'][:22]:<24}"
                f"{t['identificacion']:<13}{t['estado']:<12}{t['areaDestino'][:22]:<24}")
        print(fila + (str(dias_desde(t["fecha"])) if con_dias else ""))
    print("  " + "-" * ancho + f"\n  Total: {plural(len(lista), 'expediente')}")

def detalle_desde_resultados(bd, resultados, con_dias=False):
    """Permite abrir la ficha completa, con historial, de uno de los resultados."""
    if len(resultados) == 1:
        leer("\n  Presione ENTER para ver el detalle completo, o X para volver...")
        pantalla_expediente(bd, resultados[0])
        return
    while resultados:
        entrada = leer("\n  Escriba el N° para ver el detalle, o Enter para volver: ").strip()
        if entrada == "": return
        t = buscar_codigo(resultados, entrada)
        if not t:
            print("  Ese expediente no está en los resultados.")
            continue
        pantalla_expediente(bd, t)
        leer("\n  Presione ENTER para volver al listado, o X para ir al menú...")
        limpiar_pantalla()
        print()
        mostrar_tabla(resultados, con_dias)

def mostrar_resultados(bd, resultados, texto_titulo, con_dias=False):
    """Pantalla estándar de resultados: título, tabla y posibilidad de abrir un detalle."""
    limpiar_pantalla()
    titulo(texto_titulo)
    mostrar_tabla(resultados, con_dias)
    detalle_desde_resultados(bd, resultados, con_dias)

# ==== SECCIÓN 8: OPCIÓN 1: REGISTRO DE EXPEDIENTES ==========================================
def pedir_remitente(bd):
    """Paso 1. Si el DNI o RUC ya existe, autocompleta el nombre. Devuelve el ciudadano."""
    seccion("1. Datos del remitente")
    identificacion = pedir_identificacion()
    existente = buscar_ciudadano(bd, identificacion)
    if existente:
        print(f"\n  Remitente encontrado: {existente['remitente']}. Sus datos se autocompletaron.")
        return existente.copy()              # copia: no se modifica nada hasta confirmar
    if len(identificacion) == 11: remitente = pedir_texto("Razón social del remitente: ")
    else: remitente = pedir_nombre("Nombres y apellidos del remitente: ")
    return {"identificacion": identificacion, "remitente": remitente, "telefono": "", "correo": ""}

def pedir_contacto(ciudadano):
    """Paso 2. Teléfono y correo son obligatorios. Si ya existen, se pide confirmarlos."""
    seccion("2. Datos de contacto")
    if ciudadano["telefono"] != "" and ciudadano["correo"] != "":
        print(f"  Teléfono: {ciudadano['telefono']}\n  Correo  : {ciudadano['correo']}\n")
        if confirmar("¿Siguen siendo correctos estos datos?"): return
    ciudadano["telefono"] = pedir_telefono()
    ciudadano["correo"] = pedir_correo()

def permitir_registro(bd, identificacion, fecha, motivo, tipo):
    """Avisa si ya existe un expediente igual hoy. Devuelve False si no se quiere duplicar."""
    for t in bd["tramites"]:
        if (t["identificacion"], t["fecha"], t["motivo"], t["tipoDoc"]) == (identificacion, fecha, motivo, tipo):
            print(f"\n  Atención: ya existe el expediente N° {t['codigo']} con los mismos datos hoy.")
            return confirmar("¿Registrar de todos modos?")
    return True

def registrar_expediente(bd, usuario):
    """Opción 1: pide los datos en 4 pasos, muestra un resumen y guarda solo al confirmar."""
    titulo("Registrar expediente", cancelable=True)
    fecha, hora = ahora()                                  # fecha y hora automáticas
    print(f"  Fecha y hora automáticas: {fecha} {hora}\n  Registrado por: {usuario['nombres']} {usuario['apellidos']}")
    ciudadano = pedir_remitente(bd)
    pedir_contacto(ciudadano)
    seccion("3. Documento y trámite")
    tipo = elegir("Tipo de documento:", TIPOS)
    motivo = elegir("Motivo del trámite:", MOTIVOS, otro=True)
    descripcion = pedir_texto("\nDescripción detallada del motivo: ")
    seccion("4. Destino y folios")
    area = elegir("Área de destino:", AREAS, otro=True, por_defecto=AREA_POR_MOTIVO.get(motivo, ""))
    folios = pedir_folios()
    if not permitir_registro(bd, ciudadano["identificacion"], fecha, motivo, tipo):
        print("\n  Registro cancelado.")
        return

    seccion("Resumen del registro")
    print(f"  Remitente : {ciudadano['remitente']}, {ciudadano['identificacion']}")
    print(f"  Contacto  : {ciudadano['telefono']}, {ciudadano['correo']}")
    print(f"  Documento : {tipo}, {motivo}\n  Área      : {area}\n  Folios    : {folios}\n")
    if not confirmar("¿Confirmar el registro?"):
        print("\n  Registro cancelado. No se guardó nada.")
        return

 

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
