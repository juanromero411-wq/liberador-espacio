import hashlib
import os
import sys
from collections import defaultdict
from pathlib import Path

# Este archivo es el "cerebro" del proyecto: sabe reconocer archivos repetidos
# y qué carpetas no se deben tocar.

# Nombre de la carpeta donde se guardan los archivos antes de borrarlos,
# como una papelera de reciclaje.
CUARENTENA = "_CUARENTENA"

# Carpetas que nunca se escanean ni se tocan, para no dañar el sistema
# ni los programas instalados.
CARPETAS_PROTEGIDAS = {
    "windows", "program files", "program files (x86)", "programdata",
    "$recycle.bin", "system volume information", "appdata",
    ".git", "node_modules", CUARENTENA.lower(),
}


# Revisa si una ruta pasa por alguna carpeta protegida.
def esta_protegida(ruta):
    return any(parte.lower() in CARPETAS_PROTEGIDAS for parte in Path(ruta).parts)


# Convierte un tamaño en bytes a un texto fácil de leer, como "2.5 GB".
def formato(cantidad):
    for unidad in ["B", "KB", "MB", "GB"]:
        if cantidad < 1024 or unidad == "GB":
            return f"{cantidad:.1f} {unidad}"
        cantidad /= 1024


# Saca la "huella digital" de un archivo. Dos archivos con la misma huella
# son exactamente iguales, aunque tengan nombres distintos.
def calcular_hash(ruta, bloque=1024 * 1024):
    sha = hashlib.sha256()
    with open(ruta, "rb") as archivo:
        while True:
            datos = archivo.read(bloque)
            if not datos:
                break
            sha.update(datos)
    return sha.hexdigest()


# Recorre una carpeta y agrupa los archivos por tamaño. Solo los que pesan
# exactamente lo mismo pueden ser copias, así se evita revisar todo a fondo.
def agrupar_por_tamano(carpeta):
    grupos = defaultdict(list)
    for raiz, carpetas, archivos in os.walk(carpeta):
        carpetas[:] = [c for c in carpetas if c.lower() not in CARPETAS_PROTEGIDAS]
        for nombre in archivos:
            ruta = os.path.join(raiz, nombre)
            try:
                tamano = os.path.getsize(ruta)
            except OSError:
                continue
            if tamano > 0:
                grupos[tamano].append(ruta)
    return grupos


# Busca duplicados directamente en el computador donde corre el programa
# (versión de consola, sin la página web).
def buscar_duplicados(carpeta):
    duplicados = []
    for tamano, rutas in agrupar_por_tamano(carpeta).items():
        if len(rutas) < 2:
            continue
        por_hash = defaultdict(list)
        for ruta in rutas:
            try:
                por_hash[calcular_hash(ruta)].append(ruta)
            except OSError:
                continue
        for iguales in por_hash.values():
            if len(iguales) > 1:
                duplicados.append((tamano, iguales))
    return duplicados


# Función principal que usa la página web: recibe la lista de archivos
# (ruta, tamaño y huella) y junta en un mismo grupo los que son idénticos.
def agrupar_duplicados_desde_metadatos(archivos):
    """Recibe una lista de dicts {'ruta', 'tamano', 'hash'} desde el navegador
    y devuelve [(tamano, [rutas...]), ...] aplicando las mismas reglas de protección."""
    por_clave = defaultdict(list)
    vistas = set()

    for item in archivos:
        ruta = item["ruta"]
        tamano = item["tamano"]
        digest = item["hash"]

        # Se ignoran archivos vacíos, repetidos en la lista o en carpetas protegidas.
        if tamano <= 0 or not digest or ruta in vistas or esta_protegida(ruta):
            continue
        vistas.add(ruta)
        por_clave[(tamano, digest)].append(ruta)

    # Solo se devuelven los grupos que tienen dos copias o más.
    return [
        (tamano, rutas)
        for (tamano, _), rutas in por_clave.items()
        if len(rutas) > 1
    ]


# Muestra en pantalla el resultado de la versión de consola.
def mostrar_reporte(duplicados):
    if not duplicados:
        print("No se encontraron duplicados.")
        return
    recuperable = 0
    for n, (tamano, rutas) in enumerate(duplicados, start=1):
        print(f"\nGrupo {n}: {len(rutas)} archivos de {formato(tamano)} cada uno")
        for ruta in rutas:
            print("  -", ruta)
        recuperable += tamano * (len(rutas) - 1)
    print(f"\nEspacio que se podría liberar: {formato(recuperable)}")


# Punto de arranque de la versión de consola, por ejemplo: python escaner.py D:/Fotos
if __name__ == "__main__":
    carpeta = sys.argv[1] if len(sys.argv) > 1 else "."
    if not os.path.isdir(carpeta):
        print("La carpeta no existe:", carpeta)
        sys.exit(1)
    print("Escaneando:", carpeta)
    mostrar_reporte(buscar_duplicados(carpeta))
