# optimizador.py
# Optimizador independiente de la máquina sobre la lista de cuádruplas IR.
# Reglas de la guía que se respetan aquí:
#   - Valida la IR de entrada (no se acepta IR mal formada) y revalida tras cada iteración.
#   - No modifica la lista ni las cuádruplas originales: construye otras nuevas.
#   - Conserva el orden de PRINT y STORE; los temporales son inmutables, las variables no se propagan.
#   - No pliega ni elimina operaciones que puedan fallar en ejecución.
#   - Repite hasta que no haya cambios, con un tope documentado de iteraciones.

import math

from ir_nodos import Cuadrupla, Constante, Temporal
from validador_ir import validar_ir, ErrorIR

# Tope de iteraciones (la guía sugiere diez). Si se alcanza, se entrega la última IR válida.
MAX_ITERACIONES = 10

# Límite didáctico de la máquina para enteros. Debe coincidir con el de la máquina virtual:
# una operación cuyo resultado lo supere DEBE fallar al ejecutar, así que no se pliega.
LIMITE_BITS_ENTERO = 4096

ARITMETICAS = ("ADD", "SUB", "MUL", "DIV")

# Únicas instrucciones que se pueden retirar si su temporal no se usa:
#   CONST y COPY no tienen efectos ni errores; LOAD de una variable ya declarada solo lee.
# Se conservan ADD/SUB/MUL (pueden salir del rango), DIV (división por cero), I2F (entero
# gigante a real), STORE y PRINT (efectos observables).
ELIMINABLES = ("CONST", "COPY", "LOAD")


def _nombre(x):
    """Nombre estable de un Temporal (no depende de __str__)."""
    return getattr(x, "nombre", str(x))


def _plegar(op, tipo, v1, v2):
    """Calcula op(v1, v2) solo si la máquina también lo calcularía sin error.
    Devuelve el valor, o None si no es seguro plegar (la instrucción se conserva)."""
    try:
        if op == "ADD":
            res = v1 + v2
        elif op == "SUB":
            res = v1 - v2
        elif op == "MUL":
            res = v1 * v2
        else:  # DIV
            if v2 == 0:
                return None  # no anticipar ni ocultar la división por cero
            res = v1 / v2
    except (ZeroDivisionError, OverflowError, ValueError):
        return None

    if tipo == "int":
        if not isinstance(res, int) or res.bit_length() > LIMITE_BITS_ENTERO:
            return None  # el error de rango debe verse al ejecutar
    else:
        if not math.isfinite(res):
            return None  # Python devuelve inf sin avisar; la máquina lo rechaza
    return res


def _pase_adelante(cuadruplas):
    """Recorrido hacia adelante: propagación de constantes y copias + plegado.
    Devuelve (lista_nueva, hubo_cambios)."""
    equivalentes = {}  # nombre de temporal -> Constante, o Temporal del que es copia
    nuevas = []
    cambio = False

    def sustituir(operando):
        if isinstance(operando, Temporal) and _nombre(operando) in equivalentes:
            return equivalentes[_nombre(operando)]
        return operando

    for c in cuadruplas:
        arg1, arg2 = sustituir(c.arg1), sustituir(c.arg2)
        if arg1 is not c.arg1 or arg2 is not c.arg2:
            cambio = True

        op = c.op

        # Plegado: solo operaciones aritméticas con ambos operandos constantes.
        if op in ARITMETICAS and isinstance(arg1, Constante) and isinstance(arg2, Constante):
            res = _plegar(op, c.tipo, arg1.valor, arg2.valor)
            if res is not None:
                op, arg1, arg2 = "CONST", Constante(res, c.tipo), None
                cambio = True

        # COPY de una constante es en realidad un CONST (COPY exige un temporal).
        if op == "COPY" and isinstance(arg1, Constante):
            op = "CONST"
            cambio = True

        nueva = Cuadrupla(
            op=op, arg1=arg1, arg2=arg2,
            resultado=c.resultado, tipo=c.tipo, linea=c.linea,
        )

        # Solo los temporales son inmutables: aquí NUNCA se registran variables.
        if isinstance(nueva.resultado, Temporal) and nueva.op in ("CONST", "COPY"):
            equivalentes[_nombre(nueva.resultado)] = nueva.arg1

        nuevas.append(nueva)

    return nuevas, cambio


def _pase_atras(cuadruplas):
    """Recorrido hacia atrás: retira definiciones seguras sin usos.
    Al ir de atrás hacia adelante, una cadena de definiciones muertas cae en un solo pase."""
    vivos = set()
    resultado = []
    cambio = False

    for c in reversed(cuadruplas):
        if (
            isinstance(c.resultado, Temporal)
            and _nombre(c.resultado) not in vivos
            and c.op in ELIMINABLES
        ):
            cambio = True
            continue

        for arg in (c.arg1, c.arg2):
            if isinstance(arg, Temporal):
                vivos.add(_nombre(arg))
        resultado.append(c)

    resultado.reverse()
    return resultado, cambio


def optimizar_ir(cuadruplas, simbolos=None):
    """Devuelve una IR optimizada equivalente; la lista recibida no se modifica."""

    # No se acepta una IR mal formada con la esperanza de que el optimizador la arregle.
    validar_ir(cuadruplas, simbolos)

    actual = list(cuadruplas)

    for _ in range(MAX_ITERACIONES):
        actual, cambio_a = _pase_adelante(actual)
        actual, cambio_b = _pase_atras(actual)

        try:
            validar_ir(actual, simbolos)
        except ErrorIR as e:
            # Un fallo aquí es un defecto del optimizador, no del programa del usuario.
            raise ErrorIR(f"El optimizador produjo una IR inválida: {e.mensaje}", e.linea) from None

        if not (cambio_a or cambio_b):
            break

    return actual