import os

os.makedirs("prueba/sub", exist_ok=True)

open("prueba/a.txt", "w").write("hola mundo")
open("prueba/a_copia.txt", "w").write("hola mundo")
open("prueba/sub/a_otra_copia.txt", "w").write("hola mundo")
open("prueba/b.txt", "w").write("contenido distinto")
open("prueba/c.txt", "w").write("hola mundp")

print("Carpeta de prueba creada")