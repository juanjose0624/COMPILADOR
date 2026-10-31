# pruebas_equivalencia.py
# Comprueba que optimizar_ir conserva el comportamiento: ejecuta la IR original y la
# optimizada con el ejecutor de IR y compara salidas, memoria final y error (clase + línea).
# Uso:  python pruebas_equivalencia.py        (termina con código 1 si algo falla)

import sys

from lexico import analizar_lexico
from sintactico import analizar_sintaxis
from semantico import analizar_semantica
from generar_ir import generar_ir
from validador_ir import validar_ir
from optimizador import optimizar_ir
from ejecutor_ir import ejecutar_ir, equivalentes, formatear
from errores import ErrorCompilador

# Literales cerca de los límites de la máquina didáctica (4096 bits / reales finitos)
ENTERO_GRANDE = "1" + "0" * 1000          # ~3322 bits: válido solo; su cuadrado (~6644 bits) no
REAL_GRANDE = "1" + "0" * 308 + ".0"      # 1e308: multiplicado por 10.0 deja de ser finito
ENTERO_SIN_REAL = "1" + "0" * 400         # ~1329 bits: cabe como int, pero no se puede convertir a real

# (nombre, programa). Cubren las transformaciones y las trampas que pide la guía.
CASOS = [
    ("precedencia", "int x = 2 + 3 * 4; x = x - 1; print(x);"),
    ("asociatividad izquierda", "int x = 10 - 3 - 2; print(x);"),
    ("division produce real", "real x = 5 / 2; print(x);"),
    ("promocion en declaracion", "real x = 2; print(x);"),
    ("promocion en operacion", "int cantidad = 3; real total = cantidad * 2.5; print(total);"),
    ("reasignacion", "int x = 2; x = x + 1; x = x * 4; print(x); print(x - 2);"),
    ("load tras store (no propagar variables)",
     "int x = 2;\nint a = x;\nx = 9;\nint b = x;\nprint(a);\nprint(b);"),
    ("bool", "bool b = true; bool c = false; print(b); print(c);"),
    ("constantes plegables", "int x = (1 + 2) * (3 + 4) - 5; print(x);"),
    ("reales plegables", "real y = 2.5 * 4.0 - 1.5; print(y);"),
    ("division por cero sin uso", "real x = 10 / 0;\nprint(1);"),
    ("division por cero con salida previa", "print(7);\nreal x = 1.5 / 0.0;\nprint(8);"),
    ("division por cero tras cambios", "int a = 5;\nreal r = a / (a - 5);\nprint(r);"),
    ("entero fuera de rango", f"int a = {ENTERO_GRANDE};\nprint(1);\nint b = {ENTERO_GRANDE} * {ENTERO_GRANDE};\nprint(2);"),
    ("entero fuera de rango via variable", f"int a = {ENTERO_GRANDE};\nint b = a * a;\nprint(3);"),
    ("real desbordado", f"real r = {REAL_GRANDE} * 10.0;\nprint(1);"),
    ("conversion a real imposible", f"print(1);\nreal r = {ENTERO_SIN_REAL};\nprint(2);"),
    ("programa vacio", ""),
    ("variables con nombre de temporal", "int t1 = 3; real t2 = t1 * 2.5; print(t2);"),
    ("expresion mixta larga", "real a = 1.5; int n = 2; a = n * a + 1; print(a / 2); print(n * (n + 1));"),
]


def compilar(programa: str):
    r = analizar_semantica(analizar_sintaxis(analizar_lexico(programa)))
    ir = generar_ir(r.ast, r.tabla_simbolos)
    validar_ir(ir, r.tabla_simbolos)
    return r, ir


def probar(nombre: str, programa: str) -> bool:
    try:
        r, ir = compilar(programa)
    except ErrorCompilador as e:
        print(f"  [ERROR] {nombre}: el programa no compila ({e})")
        return False

    copia = list(ir)
    antes = [str(c) for c in ir]
    optimizada = optimizar_ir(ir, r.tabla_simbolos)

    ok = True
    problemas = []

    # 1. El optimizador no debe alterar la IR original.
    if [str(c) for c in ir] != antes or ir != copia:
        ok = False
        problemas.append("el optimizador modificó la IR original")

    # 2. Mismo comportamiento observable.
    a, b = ejecutar_ir(ir), ejecutar_ir(optimizada)
    iguales, motivos = equivalentes(a, b)
    if not iguales:
        ok = False
        problemas.extend(motivos)

    # 3. La IR no debe fallar por defectos del compilador (solo por errores de la máquina).
    for etiqueta, resultado in (("original", a), ("optimizada", b)):
        if resultado.fallo and resultado.fallo.tipo in (
            "variable_sin_valor", "temporal_sin_valor", "tipo_invalido", "operacion_desconocida"
        ):
            ok = False
            problemas.append(f"IR {etiqueta} inválida al ejecutar: {resultado.fallo.tipo} ({resultado.fallo.mensaje})")

    estado = "OK " if ok else "FALLA"
    detalle = f"error {a.fallo.tipo} (línea {a.fallo.linea})" if a.fallo else f"salidas {formatear(a.salidas)}"
    print(f"  [{estado}] {nombre:<42} {len(ir):>3} -> {len(optimizada):>3} instr.  {detalle}")
    for p in problemas:
        print(f"         - {p}")
    return ok


def verificar_que_las_pruebas_detectan_errores() -> bool:
    """Prueba negativa: un 'optimizador' defectuoso debe ser detectado por la comparación."""
    r, ir = compilar("real x = 10 / 0;\nprint(1);")
    # Defecto simulado: quitar la división y el STORE que la usa (ocultar el error de ejecución).
    defectuosa = [c for c in ir if c.op not in ("DIV", "STORE")]
    iguales, _ = equivalentes(ejecutar_ir(ir), ejecutar_ir(defectuosa))
    detectado = not iguales
    print(f"  [{'OK ' if detectado else 'FALLA'}] un optimizador que oculta la división por cero es detectado")
    return detectado


if __name__ == "__main__":
    print("Equivalencia IR original vs IR optimizada")
    resultados = [probar(nombre, programa) for nombre, programa in CASOS]
    print("Prueba negativa")
    resultados.append(verificar_que_las_pruebas_detectan_errores())
    total, bien = len(resultados), sum(resultados)
    print(f"\n{bien}/{total} pruebas correctas")
    sys.exit(0 if bien == total else 1)