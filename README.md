# Liberador de espacio

Aplicación web para detectar archivos duplicados en carpetas o unidades locales y liberar espacio de forma segura mediante un sistema de cuarentena, sin necesidad de instalar programas en la computadora del usuario ni subir archivos pesados a la nube.

---

## Características principales

* **Cero instalaciones en el cliente:** Accede directamente a carpetas locales, discos secundarios (`D:\`, `E:\`) y memorias USB desde el navegador mediante la **File System Access API**.
* **Privacidad y velocidad:** Los archivos nunca se suben al servidor. El navegador filtra primero por tamaño en bytes y calcula las huellas digitales **SHA-256** localmente; a la API solo se envían metadatos ligeros (`ruta`, `tamaño` y `hash`).
* **Detección exacta:** Encuentra copias idénticas de cualquier formato (imágenes, videos, documentos, ejecutables, etc.), sin importar si tienen nombres distintos o están en diferentes subcarpetas.
* **Protección de sistema y copias:**
  * Ignora automáticamente carpetas críticas del sistema y de desarrollo (`Windows`, `Program Files`, `AppData`, `.git`, `node_modules`, `_CUARENTENA`, entre otras).
  * Impide seleccionar y eliminar todas las copias de un mismo archivo, garantizando que siempre se conserve al menos una versión original.
* **Cuarentena reversible:** Mueve los duplicados seleccionados a una carpeta `_CUARENTENA/<AAAAMMDD_HHMMSS>/` dentro de la unidad elegida, conservando su estructura original para poder recuperarlos antes de vaciarla definitivamente.

---

## Arquitectura del sistema

El proyecto utiliza una arquitectura híbrida dividida entre el navegador del usuario y un backend *stateless* en Python:

```text
+-------------------------------------------------------------------+
|                     PC DEL USUARIO (Navegador)                    |
|                                                                   |
|  [ Carpeta / Disco Local ]                                        |
|          |  1. Permiso explícito de lectura/escritura             |
|          v                                                        |
|  [ static/index.html ]                                            |
|     |-- 2. Descarta archivos con tamaño único                     |
|     |-- 3. Calcula hash SHA-256 local (Web Crypto API)            |
|     |                                                             |
|     |   4. POST /api/escanear (solo JSON con metadatos) --------->+
|     |   5. Recibe grupos y validación de cuarentena <-------------+
|     |                                                             |
|     +-- 6. Mueve archivos a "_CUARENTENA" o vacía la carpeta      |
+-------------------------------------------------------------------+
                                                                    |
                                                       HTTPS (JSON) |
                                                                    v
                                            +-------------------------------+
                                            |   SERVIDOR EN RENDER (Nube)   |
                                            |                               |
                                            |  [ FastAPI: main + escaner ]  |
                                            |  - Filtra rutas protegidas    |
                                            |  - Agrupa hashes idénticos    |
                                            |  - Calcula espacio a liberar  |
                                            |  - Valida reglas de seguridad |
                                            +-------------------------------+
```

---

## Requisitos y compatibilidad

* **Navegadores soportados:** Navegadores de escritorio basados en Chromium (**Google Chrome**, **Microsoft Edge**, **Brave**, **Opera**) ejecutándose bajo **HTTPS** o `localhost`. *(No compatible con Firefox, Safari ni dispositivos móviles debido al soporte de la File System Access API).*
* **Restricciones del sistema operativo:** Por políticas de seguridad del navegador, Windows bloquea la selección de la raíz completa del disco del sistema (`C:\`). Sin embargo, permite seleccionar cualquier subcarpeta dentro de `C:\` (como `Documentos`, `Descargas` o `Imágenes`) y la raíz completa de discos secundarios (`D:\`, `E:\`) o memorias USB.

---

## Estructura del proyecto

```text
liberador-espacio/
├── static/
│   └── index.html        # Interfaz web, recorrido local y cálculo SHA-256 en el navegador
├── main.py               # API REST con FastAPI (endpoints de escaneo y validación)
├── escaner.py            # Lógica de agrupación, filtros de seguridad y modo CLI
├── pruebas.py            # Pruebas unitarias automatizadas
├── requirements.txt      # Dependencias de Python (fastapi, uvicorn)
├── Dockerfile            # Imagen Docker con Python 3.13 y puerto dinámico para Render
└── docker-compose.yml    # Configuración opcional para ejecución local con Compose
```

---

## Ejecución local con Docker

1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/juanromero411-wq/liberador-espacio.git](https://github.com/juanromero411-wq/liberador-espacio.git)
   cd liberador-espacio
   ```

2. **Construir la imagen:**
   ```bash
   docker build -t liberador .
   ```

3. **Iniciar el servidor:**
   ```bash
   docker run --rm -p 8000:8000 liberador
   ```

4. Abrir **`http://localhost:8000`** en Chrome o Edge.

---

## Pruebas automatizadas

Para ejecutar las pruebas unitarias usando el contenedor de Docker sin instalar Python en el sistema anfitrión:

```bash
docker run --rm -v "${PWD}:/app" liberador python pruebas.py
```

---

## Despliegue en Render

El repositorio está preparado para despliegue continuo (*Auto-Deploy*) desde la rama `main` mediante Docker. Incluye un `render.yaml` (Blueprint) con toda la configuración:

* **Runtime:** `Docker` (usa el `Dockerfile` de la raíz).
* **Puerto:** Render inyecta la variable `PORT` y uvicorn escucha en ella; en local se usa `8000` por defecto.
* **Health check:** `GET /api/salud` responde `{"estado": "ok"}`.
* **Proxy:** uvicorn acepta las cabeceras `X-Forwarded-*` del balanceador de Render.
* **Seguridad:** el contenedor se ejecuta con un usuario sin privilegios.
* **Variables de entorno adicionales:** No requiere configuración manual.

Opciones para crear el servicio:

1. **Blueprint:** en Render, *New > Blueprint*, conecta el repositorio de GitHub y Render leerá `render.yaml`.
2. **Manual:** *New > Web Service*, conecta el repositorio, elige *Language: Docker*, rama `main` y en *Health Check Path* escribe `/api/salud`.

Render sirve la app bajo HTTPS, requisito de la File System Access API.

---

## Guía de uso

1. Abre la aplicación web en **Chrome** o **Edge** (`https://liberador-espacio.onrender.com` o `http://localhost:8000`).
2. Haz clic en **Elegir carpeta o disco**, selecciona la ruta que deseas analizar y acepta el permiso de edición en el navegador.
3. Pulsa **Escanear** para listar los grupos de archivos duplicados ordenados por mayor espacio recuperable.
4. Marca manualmente las copias que deseas retirar o usa **Seleccionar copias automáticamente** (conservará siempre el primer archivo de cada grupo).
5. Haz clic en **Mover a cuarentena** para trasladar los archivos a `_CUARENTENA`. Si deseas liberar el espacio definitivamente en el disco, pulsa **Vaciar definitivamente**
6. en el banner superior