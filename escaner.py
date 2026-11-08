import hashlib
import os
import sys
from collections import defaultdict
from pathlib import Path

CUARENTENA = "_CUARENTENA"

# Carpetas que nunca se escanean ni se tocan
CARPETAS_PROTEGIDAS = {
    "windows", "program files", "program files (x86)", "programdata",
    "$recycle.bin", "system volume information", "appdata",
    ".git", "node_modules", CUARENTENA.lower(),
}


def esta_protegida(ruta):
    return any(parte.lower() in CARPETAS_PROTEGIDAS for parte in Path(ruta).parts)


def formato(cantidad):
    for unidad in ["B", "KB", "MB", "GB"]:
        if cantidad < 1024 or unidad == "GB":
            return f"{cantidad:.1f} {unidad}"
        cantidad /= 1024


def calcular_hash(ruta, bloque=1024 * 1024):
    sha = hashlib.sha256()
    with open(ruta, "rb") as archivo:
        while True:
            datos = archivo.read(bloque)
            if not datos:
                break
            sha.update(datos)
    return sha.hexdigest()


def agrupar_por_tamano(carpeta):
    grupos = defaultdict(list)
    for raiz, carpetas, archivos in os.walk(carpeta):
        # No entrar a carpetas protegidas (sistema, cuarentena, etc.)
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


if __name__ == "__main__":
    carpeta = sys.argv[1] if len(sys.argv) > 1 else "."
    if not os.path.isdir(carpeta):
        print("La carpeta no existe:", carpeta)
        sys.exit(1)
    print("Escaneando:", carpeta)
    mostrar_reporte(buscar_duplicados(carpeta))