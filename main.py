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

app = FastAPI(title="Liberador de espacio")

INDEX = Path(__file__).resolve().parent / "static" / "index.html"


class ArchivoMeta(BaseModel):
    ruta: str
    tamano: int
    hash: str


class PedidoEscaneoWeb(BaseModel):
    carpeta: str
    archivos: list[ArchivoMeta]


class GrupoDuplicados(BaseModel):
    tamano: int
    rutas: list[str]


class PedidoValidarCuarentena(BaseModel):
    grupos: list[GrupoDuplicados]
    elegidas: list[str]


@app.get("/")
def inicio():
    return FileResponse(INDEX)


@app.get("/api/salud")
def salud():
    return {"estado": "ok"}


@app.get("/api/config")
def configuracion():
    return {
        "cuarentena": CUARENTENA,
        "protegidas": sorted(CARPETAS_PROTEGIDAS),
    }


@app.post("/api/escanear")
def escanear(p: PedidoEscaneoWeb):
    if esta_protegida(p.carpeta):
        raise HTTPException(400, "Esa carpeta está protegida y no se puede escanear")

    grupos = agrupar_duplicados_desde_metadatos([a.model_dump() for a in p.archivos])
    grupos.sort(key=lambda g: g[0] * (len(g[1]) - 1), reverse=True)

    recuperable = sum(t * (len(r) - 1) for t, r in grupos)
    return {
        "grupos": [{"tamano": t, "rutas": r} for t, r in grupos],
        "recuperable": recuperable,
    }


@app.post("/api/validar-cuarentena")
def validar_cuarentena(p: PedidoValidarCuarentena):
    elegidas = set(p.elegidas)
    conocidas = {r for g in p.grupos for r in g.rutas}

    if not elegidas or not elegidas <= conocidas:
        raise HTTPException(400, "Solo se pueden mover archivos del último escaneo")

    for ruta in elegidas:
        if esta_protegida(ruta):
            raise HTTPException(400, f"Ruta protegida no permitida: {ruta}")

    for g in p.grupos:
        if all(r in elegidas for r in g.rutas):
            raise HTTPException(400, "Debes conservar al menos una copia de cada grupo")

    return {
        "lote": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "cuarentena": CUARENTENA,
    }