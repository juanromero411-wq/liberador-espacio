import os
import shutil
import string
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from escaner import CUARENTENA, buscar_duplicados, esta_protegida

app = FastAPI(title="Liberador de espacio")


ultimo_escaneo = []



def listar_discos():
    """Discos disponibles: en Windows las unidades (C:, D:, USB...);
    en Docker, las carpetas montadas dentro de RAIZ_DISCOS (por defecto /mnt)."""
    if os.name == "nt":
        return [f"{l}:\\" for l in string.ascii_uppercase if os.path.exists(f"{l}:\\")]
    base = os.getenv("RAIZ_DISCOS", "/mnt")
    if not os.path.isdir(base):
        return []
    return sorted(
        os.path.join(base, d) for d in os.listdir(base)
        if os.path.isdir(os.path.join(base, d))
    )


def esta_dentro(ruta, base):
    ruta = os.path.normcase(os.path.realpath(ruta))
    base = os.path.normcase(os.path.realpath(base))
    try:
        return os.path.commonpath([ruta, base]) == base
    except ValueError:
        return False


def disco_de(ruta):
    for disco in listar_discos():
        if esta_dentro(ruta, disco):
            return disco
    return None


def carpeta_cuarentena(disco):
    return os.path.join(disco, CUARENTENA)


def tamano_carpeta(carpeta):
    total = 0
    for raiz, _, archivos in os.walk(carpeta):
        for nombre in archivos:
            try:
                total += os.path.getsize(os.path.join(raiz, nombre))
            except OSError:
                pass
    return total



class PedidoEscaneo(BaseModel):
    disco: str
    subcarpeta: str = ""


class PedidoRutas(BaseModel):
    rutas: list[str]


class PedidoDisco(BaseModel):
    disco: str



@app.get("/")
def inicio():
    return FileResponse("static/index.html")


@app.get("/api/discos")
def discos():
    return [
        {"ruta": d, "cuarentena": tamano_carpeta(carpeta_cuarentena(d))}
        for d in listar_discos()
    ]


@app.post("/api/escanear")
def escanear(p: PedidoEscaneo):
    global ultimo_escaneo
    if p.disco not in listar_discos():
        raise HTTPException(400, "Disco no válido")

    carpeta = os.path.realpath(os.path.join(p.disco, p.subcarpeta))
    if disco_de(carpeta) != p.disco:
        raise HTTPException(400, "La carpeta debe estar dentro del disco elegido")
    if not os.path.isdir(carpeta):
        raise HTTPException(400, "La carpeta no existe")
    if esta_protegida(carpeta):
        raise HTTPException(400, "Esa carpeta está protegida y no se puede escanear")

    grupos = buscar_duplicados(carpeta)
    grupos.sort(key=lambda g: g[0] * (len(g[1]) - 1), reverse=True)
    ultimo_escaneo = grupos

    recuperable = sum(t * (len(r) - 1) for t, r in grupos)
    return {
        "grupos": [{"tamano": t, "rutas": r} for t, r in grupos],
        "recuperable": recuperable,
    }


@app.post("/api/cuarentena")
def a_cuarentena(p: PedidoRutas):
    global ultimo_escaneo
    elegidas = set(p.rutas)
    conocidas = {r for _, rutas in ultimo_escaneo for r in rutas}

    if not elegidas or not elegidas <= conocidas:
        raise HTTPException(400, "Solo se pueden mover archivos del último escaneo")
    for _, rutas in ultimo_escaneo:
        if all(r in elegidas for r in rutas):
            raise HTTPException(400, "Debes conservar al menos una copia de cada grupo")

    lote = datetime.now().strftime("%Y%m%d_%H%M%S")
    movidas, tamano_total, errores = set(), 0, []

    for ruta in elegidas:
        disco = disco_de(ruta)
        if disco is None or esta_protegida(ruta):
            errores.append(ruta)
            continue
        try:
            tamano = os.path.getsize(ruta)
            destino = os.path.join(
                carpeta_cuarentena(disco), lote, os.path.relpath(ruta, disco)
            )
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            shutil.move(ruta, destino)
            movidas.add(ruta)
            tamano_total += tamano
        except OSError:
            errores.append(ruta)

    ultimo_escaneo = [
        (t, [r for r in rutas if r not in movidas]) for t, rutas in ultimo_escaneo
    ]
    ultimo_escaneo = [(t, rs) for t, rs in ultimo_escaneo if len(rs) > 1]

    return {"movidos": len(movidas), "tamano": tamano_total, "errores": errores}


@app.post("/api/vaciar")
def vaciar(p: PedidoDisco):
    if p.disco not in listar_discos():
        raise HTTPException(400, "Disco no válido")
    carpeta = carpeta_cuarentena(p.disco)
    if not os.path.isdir(carpeta):
        return {"liberado": 0}
    tamano = tamano_carpeta(carpeta)
    shutil.rmtree(carpeta, ignore_errors=True)
    return {"liberado": tamano}