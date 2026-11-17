from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from escaner import (
    CARPETAS_PROTEGIDAS,
    CUARENTENA,
    agrupar_duplicados_desde_metadatos,
    esta_protegida,
)

# Este archivo es la "recepción" del servidor: atiende lo que pide la página web
# y responde con cada uno de los servicios de la aplicación.
app = FastAPI(title="Liberador de espacio")

# Ubicación de la página web que ve el usuario.
INDEX = Path(__file__).resolve().parent / "static" / "index.html"


# Ficha de un archivo que envía la página: dónde está, cuánto pesa y su huella digital.
# Nunca se envía el archivo en sí, solo estos datos.
class ArchivoMeta(BaseModel):
    ruta: str
    tamano: int
    hash: str


# Lo que la página manda al pedir un escaneo: la carpeta elegida y la lista de fichas.
class PedidoEscaneoWeb(BaseModel):
    carpeta: str
    archivos: list[ArchivoMeta]


# Un grupo de archivos idénticos: el tamaño de cada copia y dónde está cada una.
class GrupoDuplicados(BaseModel):
    tamano: int
    rutas: list[str]


# Lo que la página manda antes de mover archivos: los grupos encontrados
# y los archivos que el usuario marcó para enviar a la cuarentena.
class PedidoValidarCuarentena(BaseModel):
    grupos: list[GrupoDuplicados]
    elegidas: list[str]


# Servicio de inicio: entrega la página web cuando alguien entra a la aplicación.
@app.get("/")
def inicio():
    return FileResponse(INDEX)


# Servicio de salud: responde "estoy funcionando".
# Render lo consulta para saber que la aplicación sigue encendida.
@app.get("/api/salud")
def salud():
    return {"estado": "ok"}


# Servicio de configuración: le dice a la página qué carpetas no debe tocar nunca
# y cómo se llama la carpeta de cuarentena.
@app.get("/api/config")
def configuracion():
    return {
        "cuarentena": CUARENTENA,
        "protegidas": sorted(CARPETAS_PROTEGIDAS),
    }


# Servicio de escaneo: recibe la lista de archivos, junta los que son idénticos
# y calcula cuánto espacio se puede liberar.
@app.post("/api/escanear")
def escanear(p: PedidoEscaneoWeb):
    # Si la carpeta elegida es del sistema (por ejemplo Windows), se rechaza.
    if esta_protegida(p.carpeta):
        raise HTTPException(400, "Esa carpeta está protegida y no se puede escanear")

    # Arma los grupos de archivos repetidos y pone primero los que más espacio ocupan.
    grupos = agrupar_duplicados_desde_metadatos([a.model_dump() for a in p.archivos])
    grupos.sort(key=lambda g: g[0] * (len(g[1]) - 1), reverse=True)

    # Espacio recuperable: lo que ocupan todas las copias, sin contar el original.
    recuperable = sum(t * (len(r) - 1) for t, r in grupos)
    return {
        "grupos": [{"tamano": t, "rutas": r} for t, r in grupos],
        "recuperable": recuperable,
    }


# Servicio de validación: antes de mover archivos a la cuarentena,
# revisa que todo esté en orden y, si lo está, da el permiso.
@app.post("/api/validar-cuarentena")
def validar_cuarentena(p: PedidoValidarCuarentena):
    elegidas = set(p.elegidas)
    conocidas = {r for g in p.grupos for r in g.rutas}

    # Regla 1: solo se pueden mover archivos que aparecieron en el último escaneo.
    if not elegidas or not elegidas <= conocidas:
        raise HTTPException(400, "Solo se pueden mover archivos del último escaneo")

    # Regla 2: nunca se mueve nada que esté en una carpeta protegida.
    for ruta in elegidas:
        if esta_protegida(ruta):
            raise HTTPException(400, f"Ruta protegida no permitida: {ruta}")

    # Regla 3: siempre debe quedar al menos una copia de cada archivo.
    for g in p.grupos:
        if all(r in elegidas for r in g.rutas):
            raise HTTPException(400, "Debes conservar al menos una copia de cada grupo")

    # Todo en orden: se da el permiso con el nombre de la subcarpeta (fecha y hora)
    # donde quedarán guardados estos archivos dentro de la cuarentena.
    return {
        "lote": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "cuarentena": CUARENTENA,
    }
