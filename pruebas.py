import os

os.makedirs("prueba/sub", exist_ok=True)

open("prueba/a.txt", "w").write("hola mundo")
open("prueba/a_copia.txt", "w").write("hola mundo")
open("prueba/sub/a_otra_copia.txt", "w").write("hola mundo")
open("prueba/b.txt", "w").write("contenido distinto")
open("prueba/c.txt", "w").write("hola mundp")

print("Carpeta de prueba creada")


from escaner import agrupar_duplicados_desde_metadatos

def probar_metadatos_web():
    datos = [
        {"ruta": "Fotos/img1.jpg", "tamano": 5000, "hash": "abc123"},
        {"ruta": "Fotos/copia/img1.jpg", "tamano": 5000, "hash": "abc123"},
        {"ruta": "Fotos/unica.jpg", "tamano": 3000, "hash": "xyz789"},
        {"ruta": ".git/config", "tamano": 5000, "hash": "abc123"},  # Protegida, debe ignorarse
    ]
    resultado = agrupar_duplicados_desde_metadatos(datos)
    assert len(resultado) == 1
    tamano, rutas = resultado[0]
    assert tamano == 5000
    assert rutas == ["Fotos/img1.jpg", "Fotos/copia/img1.jpg"]
    print("Prueba web superada correctamente.")

if __name__ == "__main__":
    probar_metadatos_web()