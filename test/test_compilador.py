# test_compilador.py

import re
import sys
from pathlib import Path

# Agregar la carpeta principal del proyecto a la ruta de Python
CARPETA_PROYECTO = Path(__file__).resolve().parent.parent

if str(CARPETA_PROYECTO) not in sys.path:
    sys.path.insert(0, str(CARPETA_PROYECTO))

from lexico import analizar_lexico
from sintactico import analizar_sintaxis
from semantico import analizar_semantica
from errores import ErrorCompilador


# Archivo que contiene los 20 programas de prueba.
ARCHIVO_PROGRAMAS = Path(__file__).with_name("pruebas.txt")


# Resultado esperado para cada programa:
# "ok" = compilación correcta.
# "sintactico" = error sintáctico.
# "semantico" = error semántico.
PRUEBAS = [
    ("Operaciones y precedencia", "ok"),
    ("Uso de paréntesis", "ok"),
    ("Asociatividad de la resta", "ok"),
    ("División con resultado real", "ok"),
    ("Conversión de int a real", "ok"),
    ("Asignación y salida", "ok"),
    ("Declaración booleana", "ok"),
    ("Falta punto y coma", "sintactico"),
    ("Falta paréntesis de cierre", "sintactico"),
    ("Expresión inválida", "sintactico"),
    ("Variable no declarada", "semantico"),
    ("Variable declarada dos veces", "semantico"),
    ("Tipo incompatible en declaración", "semantico"),
    ("Operación aritmética con booleano", "semantico"),
    ("Referencia durante inicialización", "semantico"),
    ("División entre cero", "ok"),
    ("Programa vacío", "ok"),
    ("Texto sobrante al final", "sintactico"),
    ("Asignación con tipo incompatible", "semantico"),
    ("Error semántico en la segunda sentencia", "semantico"),
]


def cargar_programas():
    """Carga los programas conservando los bloques vacíos."""

    if not ARCHIVO_PROGRAMAS.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo: {ARCHIVO_PROGRAMAS}\n"
            "Crea pruebas.txt dentro de la carpeta test."
        )

    contenido = ARCHIVO_PROGRAMAS.read_text(encoding="utf-8")

    # Reconocer encabezados como ### PROGRAMA 1.
    patron = re.compile(
        r"^[ \t]*### PROGRAMA[ \t]+(\d+)[ \t]*$",
        re.MULTILINE | re.IGNORECASE,
    )

    encabezados = list(patron.finditer(contenido))

    if len(encabezados) != len(PRUEBAS):
        raise ValueError(
            f"Se esperaban {len(PRUEBAS)} programas, "
            f"pero se encontraron {len(encabezados)} encabezados.\n"
            "Verifica que existan los encabezados "
            "### PROGRAMA 1 hasta ### PROGRAMA 20."
        )

    programas = []

    for i, encabezado in enumerate(encabezados):
        numero = int(encabezado.group(1))

        if numero != i + 1:
            raise ValueError(
                f"Se esperaba PROGRAMA {i + 1}, "
                f"pero se encontró PROGRAMA {numero}."
            )

        inicio = encabezado.end()

        if i + 1 < len(encabezados):
            fin = encabezados[i + 1].start()
        else:
            fin = len(contenido)

        # Se conserva el bloque vacío del programa 17.
        codigo = contenido[inicio:fin].strip()
        programas.append(codigo)

    return programas


def compilar(codigo_fuente):
    """Ejecuta las fases léxica, sintáctica y semántica."""

    tokens = analizar_lexico(codigo_fuente)
    ast = analizar_sintaxis(tokens)
    resultado_semantico = analizar_semantica(ast)

    return resultado_semantico


def ejecutar_pruebas():
    """Ejecuta las pruebas y compara los resultados esperados."""

    try:
        programas = cargar_programas()
    except (OSError, ValueError) as error:
        print(f"\nERROR AL CARGAR LAS PRUEBAS: {error}")
        return False

    aprobadas = 0
    fallidas = 0

    print("=" * 65)
    print("PRUEBAS AUTOMATIZADAS DEL COMPILADOR")
    print("=" * 65)

    for numero, (codigo, prueba) in enumerate(
        zip(programas, PRUEBAS),
        start=1,
    ):
        nombre, esperado = prueba

        try:
            compilar(codigo)
            obtenido = "ok"
            tipo_error = "Ninguno"
            ubicacion = "No aplica"
            descripcion = "Compilación correcta."

        except ErrorCompilador as error:
            obtenido = error.fase.lower()

            tipo_error = {
                "lexico": "Léxico",
                "sintactico": "Sintáctico",
                "semantico": "Semántico",
            }.get(obtenido, error.fase)

            ubicacion = (
                f"Línea {error.linea}, columna {error.columna}"
            )
            descripcion = error.mensaje

        except Exception as error:
            obtenido = "inesperado"
            tipo_error = "Error interno"
            ubicacion = "No disponible"
            descripcion = f"{type(error).__name__}: {error}"

        if obtenido == esperado:
            aprobadas += 1
            estado = "APROBADA"
        else:
            fallidas += 1
            estado = "FALLIDA"

        print(f"\nPrueba {numero:02d}: {nombre}")
        print(f"Estado: {estado}")

        if esperado == "ok":
            print("Resultado esperado: Compilación correcta")
        else:
            print(f"Error esperado: {esperado.capitalize()}")

        print(f"Resultado obtenido: {obtenido.capitalize()}")
        print(f"Tipo de error: {tipo_error}")
        print(f"Ubicación: {ubicacion}")
        print(f"Descripción: {descripcion}")

    print("\n" + "=" * 65)
    print("RESUMEN DE LAS PRUEBAS")
    print("=" * 65)
    print(f"Total:     {len(PRUEBAS)}")
    print(f"Aprobadas: {aprobadas}")
    print(f"Fallidas:  {fallidas}")

    if fallidas == 0:
        print("\nTodas las pruebas pasaron.")
        return True

    print("\nHay pruebas que requieren revisión.")
    return False


if __name__ == "__main__":
    ejecutar_pruebas()