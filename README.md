# Liberador de espacio

Aplicación web que encuentra **archivos duplicados** en un disco y permite liberar espacio de forma segura.

## Problema

Con el tiempo, los discos se llenan de archivos repetidos (fotos, videos, descargas). Encontrarlos a mano es lento y borrar por error es riesgoso.

## Qué hace

- Lista los discos disponibles y permite elegir uno (y opcionalmente una subcarpeta).
- Detecta duplicados exactos: agrupa por tamaño y compara la huella SHA-256 del contenido.
- Muestra los grupos de duplicados y el espacio que se podría recuperar.
- El usuario marca cuáles copias quitar.
- No borra directamente: mueve las copias a una carpeta `_CUARENTENA` (reversible) y solo libera espacio al vaciarla.

## Seguridad

- Siempre se conserva al menos una copia de cada grupo (lo valida el servidor).
- Solo se pueden mover archivos que aparecieron en el último escaneo.
- Nunca escanea ni toca `Windows`, `Program Files`, `ProgramData`, `AppData`, etc.

## Estructura

```
escaner.py        Lógica de búsqueda de duplicados
main.py           API (FastAPI)
static/index.html Interfaz web
pruebas.py        Genera archivos de prueba
requirements.txt  Dependencias
```

## Ejecutar (sin Docker)

```
py -m pip install -r requirements.txt
py -m uvicorn main:app --reload
```

Abrir http://localhost:8000

## Probar con datos de ejemplo

```
py pruebas.py
py escaner.py prueba
```

## Docker

Próximamente.