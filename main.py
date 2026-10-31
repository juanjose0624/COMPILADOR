import os
import sys
from pathlib import Path

from tokens import Token
from lexico import analizar_lexico
from sintactico import analizar_sintaxis
from semantico import analizar_semantica
from generar_ir import generar_ir
from validador_ir import validar_ir
from optimizador import optimizar_ir
from generador import generar_codigo
from ejecutor_ir import ejecutar_ir, equivalentes, formatear_valor, FALLOS_DE_IR
from errores import ErrorCompilador
from ast_nodos import (
    Programa,
    Declaracion,
    Asignacion,
    Salida,
    Literal,
    Referencia,
    Binaria,
)


def mostrar_titulo(texto: str) -> None:
    print("\n" + "=" * 60)
    print(f" {texto}")
    print("=" * 60)


def mostrar_error(error: ErrorCompilador) -> None:
    """Muestra un error de cualquier fase; la IR no tiene columna y no se imprime."""
    print(f"Fase:    {error.fase}")
    if error.linea is not None:
        print(f"Linea:   {error.linea}")
    if error.columna is not None:
        print(f"Columna: {error.columna}")
    print(f"Error:   {error.mensaje}")


def mostrar_arbol(
    nodo, prefijo: str = "", es_ultimo: bool = True, raiz: bool = True
) -> None:
    """Muestra el arbol de sintaxis abstracta."""
    if isinstance(nodo, Programa):
        etiqueta = "Programa"
        hijos = nodo.sentencias
    elif isinstance(nodo, Declaracion):
        etiqueta = f"Declaracion: {nodo.tipo_declarado} {nodo.nombre}"
        hijos = [nodo.inicializador]
    elif isinstance(nodo, Asignacion):
        etiqueta = f"Asignacion: {nodo.nombre}"
        hijos = [nodo.expresion]
    elif isinstance(nodo, Salida):
        etiqueta = "Salida: print"
        hijos = [nodo.expresion]
    elif isinstance(nodo, Binaria):
        etiqueta = f"Operador: {nodo.operador}"
        hijos = [nodo.izquierdo, nodo.derecho]
    elif isinstance(nodo, Literal):
        etiqueta = f"Literal: {nodo.valor!r} [{nodo.tipo_literal}]"
        hijos = []
    elif isinstance(nodo, Referencia):
        etiqueta = f"Referencia: {nodo.nombre}"
        hijos = []
    else:
        etiqueta = type(nodo).__name__
        hijos = []

    if raiz:
        print(etiqueta)
    else:
        conector = "└── " if es_ultimo else "├── "
        print(prefijo + conector + etiqueta)

    nuevo_prefijo = (
        prefijo if raiz
        else prefijo + ("    " if es_ultimo else "│   ")
    )

    for indice, hijo in enumerate(hijos):
        mostrar_arbol(
            hijo,
            prefijo=nuevo_prefijo,
            es_ultimo=(indice == len(hijos) - 1),
            raiz=False,
        )


def leer_archivo(ruta: str) -> str | None:
    """Lee el codigo fuente y rechaza archivos vacios."""
    ruta = os.path.expandvars(
        os.path.expanduser(ruta.strip().strip('"').strip("'"))
    )

    if not ruta:
        print("[ERROR] No se escribio ninguna ruta.")
        return None

    archivo_path = Path(ruta)

    if not archivo_path.is_file():
        print(f"[ERROR] No se encontro el archivo: {archivo_path}")
        return None

    try:
        try:
            contenido = archivo_path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            contenido = archivo_path.read_text(encoding="cp1252")
    except (OSError, UnicodeError) as error:
        print(f"[ERROR] No se pudo leer el archivo: {error}")
        return None

    print(f"[INFO] Archivo: {archivo_path.resolve()}")
    print(f"[INFO] Caracteres leidos: {len(contenido)}")

    if not contenido.strip():
        print("[ERROR] El archivo existe, pero no contiene codigo.")
        return None

    return contenido


def leer_desde_consola() -> str:
    """Lee codigo hasta que se escriba FIN en una linea aparte."""
    print("\nEscribe el programa que deseas analizar.")
    print("Cuando termines, escribe FIN en una linea separada.\n")

    lineas = []

    while True:
        try:
            linea = input()
        except EOFError:
            break

        if linea.strip().upper() == "FIN":
            break

        lineas.append(linea)

    return "\n".join(lineas)


def obtener_codigo_fuente() -> str | None:
    """Obtiene el codigo desde un archivo o desde la consola."""
    if len(sys.argv) > 1:
        ruta = " ".join(sys.argv[1:])
        codigo = leer_archivo(ruta)

        if codigo is not None:
            print(
                f"[APROBADO] Archivo cargado "
                f"({len(codigo.splitlines())} lineas)."
            )

        return codigo

    print("Como deseas ingresar el programa?")
    print("  1. Escribirlo en la consola")
    print("  2. Cargarlo desde un archivo .txt")
    opcion = input("Opcion (1/2): ").strip()

    if opcion == "2":
        print(r"Ejemplo: C:\Users\Juan\Downloads\programa.txt")
        print("Tambien puedes usar una ruta como ~/Downloads/programa.txt")

        ruta = input("Ruta del archivo: ")
        codigo = leer_archivo(ruta)

        if codigo is not None:
            print(
                f"[APROBADO] Archivo cargado "
                f"({len(codigo.splitlines())} lineas)."
            )

        return codigo

    if opcion == "1":
        codigo = leer_desde_consola()
        if not codigo.strip():
            print("[ERROR] No se introdujo ningun codigo.")
            return None
        return codigo

    print("[ERROR] Opcion no valida. Selecciona 1 o 2.")
    return None


def ejecutar_compilacion(tokens: list[Token]) -> bool:
    """Ejecuta las cinco fases del compilador."""
    mostrar_titulo("INICIO DEL PROCESO DE COMPILACION")

    try:
        # Fase 1: analisis sintactico
        print("\n[FASE 1 DE 5] ANALISIS SINTACTICO")
        print("  Verificando la estructura del programa...")

        ast = analizar_sintaxis(tokens)

        if not ast.sentencias:
            print("[ERROR] El programa no contiene ninguna sentencia.")
            return False

        print("  [APROBADO] Analisis sintactico completado.")
        print("  [APROBADO] Arbol AST generado correctamente.")
        print("\n  ARBOL DE SINTAXIS ABSTRACTA (AST)")
        print("  " + "-" * 40)
        mostrar_arbol(ast)

        # Fase 2: analisis semantico
        print("\n[FASE 2 DE 5] ANALISIS SEMANTICO")
        print("  Verificando declaraciones, tipos y expresiones...")

        resultado_semantico = analizar_semantica(ast)
        tabla = resultado_semantico.tabla_simbolos

        print("  [APROBADO] Analisis semantico completado.")
        print("  [APROBADO] No se encontraron errores semanticos.")

        # Fase 3: generacion de IR
        print("\n[FASE 3 DE 5] GENERACION DE CODIGO INTERMEDIO (IR)")
        print("  Traduciendo AST tipado a cuadruplas IR...")

        cuadruplas = generar_ir(resultado_semantico.ast, tabla)
        validar_ir(cuadruplas, tabla)

        print("  [APROBADO] Cuadruplas IR generadas y validadas.")
        print("\n  CUADRUPLAS IR (GENERADAS)")
        print("  " + "-" * 40)

        for instruccion in cuadruplas:
            print(f"  {instruccion}")

        # Fase 4: optimizacion y comprobacion de equivalencia
        print("\n[FASE 4 DE 5] OPTIMIZACION DE LA IR")
        print("  Aplicando optimizaciones...")
        cuadruplas_optimizadas = optimizar_ir(cuadruplas, tabla)

        print("  [APROBADO] Optimizacion completada.")
        print(
            f"  Instrucciones IR: {len(cuadruplas)} -> "
            f"{len(cuadruplas_optimizadas)}"
        )
        print("\n  CUADRUPLAS IR (OPTIMIZADAS)")
        print("  " + "-" * 40)

        for instruccion in cuadruplas_optimizadas:
            print(f"  {instruccion}")

        print("\n  VERIFICACION DE EQUIVALENCIA (ejecutor de IR)")
        original = ejecutar_ir(cuadruplas)
        optimizada = ejecutar_ir(cuadruplas_optimizadas)

        for etiqueta, ejecucion in (("original", original), ("optimizada", optimizada)):
            if ejecucion.fallo and ejecucion.fallo.tipo in FALLOS_DE_IR:
                print(
                    f"  [ERROR] La IR {etiqueta} es invalida al ejecutarla: "
                    f"{ejecucion.fallo.mensaje}"
                )
                return False

        iguales, motivos = equivalentes(original, optimizada)
        if not iguales:
            print("  [ERROR] La optimizacion cambio el comportamiento del programa:")
            for motivo in motivos:
                print(f"    - {motivo}")
            return False

        print("  [APROBADO] La IR optimizada se comporta igual que la original.")

        # Fase 5: generacion de ensamblador
        print("\n[FASE 5 DE 5] GENERACION DE ENSAMBLADOR (.ASM)")
        codigo_asm = generar_codigo(cuadruplas_optimizadas, tabla)

        if not isinstance(codigo_asm, str) or not codigo_asm.strip():
            raise RuntimeError("El generador no produjo codigo ensamblador.")

        ruta_asm = Path.cwd() / "programa_generado.asm"
        ruta_asm.write_text(codigo_asm, encoding="utf-8")

        print("  [APROBADO] Codigo ensamblador generado.")
        print(f"  [GUARDADO] Archivo ASM: {ruta_asm.resolve()}")

        # Resumen
        mostrar_titulo("RESULTADO FINAL")
        print("[EXITO] El programa supero todas las fases.")
        print(f"Total de sentencias: {len(resultado_semantico.ast.sentencias)}")

        print("\nTABLA DE SIMBOLOS")
        print("-" * 40)

        if tabla:
            for variable, tipo in tabla.items():
                print(f"  {variable:<20} tipo: {tipo}")
        else:
            print("  No hay variables declaradas.")

        print("\nSALIDA DEL PROGRAMA (simulada con el ejecutor de IR)")
        print("-" * 40)

        if optimizada.salidas:
            for valor in optimizada.salidas:
                print(f"  {formatear_valor(valor)}")
        elif not optimizada.fallo:
            print("  (el programa no imprime nada)")

        if optimizada.fallo:
            print(
                f"  [ERROR DE EJECUCION] {optimizada.fallo.mensaje} "
                f"(linea {optimizada.fallo.linea})"
            )
            print("  El programa compila bien: este error ocurriria al ejecutarlo.")

        if optimizada.memoria:
            print("\nMEMORIA FINAL DE LAS VARIABLES")
            print("-" * 40)
            for variable in tabla:
                if variable in optimizada.memoria:
                    print(f"  {variable:<20} = {formatear_valor(optimizada.memoria[variable])}")

        print("\nCODIGO ENSAMBLADOR DESTINO (.ASM)")
        print("-" * 40)
        print(codigo_asm)

        print("\n" + "=" * 60)
        print(" COMPILACION Y BACKEND FINALIZADOS CORRECTAMENTE")
        print("=" * 60)
        return True

    except ErrorCompilador as error:
        # Incluye ErrorSintactico, ErrorSemantico y ErrorIR (todos heredan de ErrorCompilador).
        mostrar_titulo("COMPILACION DETENIDA")
        mostrar_error(error)
        print("[DETENIDO] No se ejecutaran las fases posteriores.")
        return False

    except Exception as error:
        mostrar_titulo("ERROR INTERNO")
        print(f"Tipo de error: {type(error).__name__}")
        print(f"Detalle: {error}")
        print("Revisa los modulos del compilador.")
        return False


def main() -> None:
    """Punto de entrada del compilador."""
    mostrar_titulo("COMPILADOR: PIPELINE COMPLETO")

    codigo_fuente = obtener_codigo_fuente()

    if codigo_fuente is None or not codigo_fuente.strip():
        print("\n[DETENIDO] No se obtuvo un codigo fuente valido.")
        return

    try:
        print("\n[PREPARACION] Analisis lexico")
        tokens = analizar_lexico(codigo_fuente)
        print(f"[APROBADO] Se reconocieron {len(tokens) - 1} tokens.")
    except ErrorCompilador as error:
        mostrar_titulo("ERROR LEXICO")
        mostrar_error(error)
        print("[DETENIDO] No se puede continuar.")
        return

    ejecutar_compilacion(tokens)


if __name__ == "__main__":
    main()