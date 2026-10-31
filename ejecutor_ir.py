# ejecutor_ir.py
# Ejecutor sencillo de IR: comprueba que el optimizador conserva el comportamiento.
# Reproduce la semántica de la máquina didáctica de las guías:
#   - int: Python int con límite de 4096 bits; real: float finito (binary64)
#   - división por cero y valores no finitos son errores de ejecución
#   - un bool vale True/False aquí (la máquina lo guarda como 0/1)
# Ejecuta la IR en orden (no tiene saltos) y devuelve salidas, memoria final y error, si lo hubo.

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ir_nodos import Constante, Temporal

LIMITE_BITS_ENTERO = 4096  # debe coincidir con LIMITE_BITS_ENTERO del optimizador


# Fallos que indican una IR mal formada (defecto del compilador), no un error del programa del usuario.
FALLOS_DE_IR = ("variable_sin_valor", "temporal_sin_valor", "tipo_invalido", "operacion_desconocida")


@dataclass
class FalloEjecucion:
    """Error ocurrido al ejecutar. `tipo` es uno de:
    division_por_cero, entero_fuera_de_rango, real_no_finito, conversion_a_real   (errores de la máquina)
    variable_sin_valor, temporal_sin_valor, tipo_invalido, operacion_desconocida (IR mal formada: defecto del compilador)
    """

    tipo: str
    linea: int
    mensaje: str


@dataclass
class ResultadoEjecucion:
    salidas: List[Any] = field(default_factory=list)
    memoria: Dict[str, Any] = field(default_factory=dict)   # variable -> valor final
    fallo: Optional[FalloEjecucion] = None
    instrucciones: int = 0                                  # instrucciones IR ejecutadas


class _Fallo(Exception):
    def __init__(self, tipo: str, mensaje: str):
        self.tipo = tipo
        self.mensaje = mensaje


def _tipo_de(valor: Any) -> str:
    # bool antes que int: en Python True es instancia de int.
    if isinstance(valor, bool):
        return "bool"
    if isinstance(valor, int):
        return "int"
    if isinstance(valor, float):
        return "real"
    return type(valor).__name__


def _comprobar_rango(valor: Any) -> None:
    if _tipo_de(valor) == "int" and valor.bit_length() > LIMITE_BITS_ENTERO:
        raise _Fallo("entero_fuera_de_rango", f"entero de más de {LIMITE_BITS_ENTERO} bits")


def _exigir(valor: Any, tipo: str, donde: str) -> None:
    if _tipo_de(valor) != tipo:
        raise _Fallo("tipo_invalido", f"{donde}: se esperaba {tipo} y llegó {_tipo_de(valor)} ({valor!r})")


def ejecutar_ir(cuadruplas: list) -> ResultadoEjecucion:
    """Ejecuta la IR. No modifica la lista recibida."""
    res = ResultadoEjecucion()
    temporales: Dict[str, Any] = {}

    def valor(operando) -> Any:
        if isinstance(operando, Constante):
            _comprobar_rango(operando.valor)
            return operando.valor
        if isinstance(operando, Temporal):
            if operando.nombre not in temporales:
                raise _Fallo("temporal_sin_valor", f"el temporal {operando.nombre} no tiene valor")
            return temporales[operando.nombre]
        raise _Fallo("tipo_invalido", f"operando no válido: {operando!r}")

    for c in cuadruplas:
        res.instrucciones += 1
        try:
            op = c.op

            if op == "CONST":
                _exigir(valor(c.arg1), c.tipo, "CONST")
                temporales[c.resultado.nombre] = c.arg1.valor

            elif op == "LOAD":
                nombre = c.arg1.nombre
                if nombre not in res.memoria:
                    raise _Fallo("variable_sin_valor", f"se leyó '{nombre}' antes de guardarle un valor")
                v = res.memoria[nombre]
                _exigir(v, c.tipo, f"LOAD {nombre}")
                temporales[c.resultado.nombre] = v

            elif op == "COPY":
                v = valor(c.arg1)
                _exigir(v, c.tipo, "COPY")
                temporales[c.resultado.nombre] = v

            elif op == "I2F":
                v = valor(c.arg1)
                _exigir(v, "int", "I2F")
                try:
                    temporales[c.resultado.nombre] = float(v)
                except OverflowError:
                    raise _Fallo("conversion_a_real", "el entero es demasiado grande para un real") from None

            elif op in ("ADD", "SUB", "MUL", "DIV"):
                a, b = valor(c.arg1), valor(c.arg2)
                _exigir(a, c.tipo, f"{op} arg1")
                _exigir(b, c.tipo, f"{op} arg2")
                if op == "DIV":
                    if b == 0:
                        raise _Fallo("division_por_cero", "división entre cero")
                    try:
                        r = a / b
                    except OverflowError:
                        raise _Fallo("real_no_finito", "el cociente no es representable") from None
                else:
                    r = {"ADD": a + b, "SUB": a - b, "MUL": a * b}[op]
                if c.tipo == "int":
                    _comprobar_rango(r)
                elif c.tipo == "real" and not math.isfinite(r):
                    raise _Fallo("real_no_finito", "el resultado real no es finito")
                temporales[c.resultado.nombre] = r

            elif op == "STORE":
                v = valor(c.arg1)
                _exigir(v, c.tipo, f"STORE {c.resultado.nombre}")
                res.memoria[c.resultado.nombre] = v

            elif op == "PRINT":
                v = valor(c.arg1)
                _exigir(v, c.tipo, "PRINT")
                res.salidas.append(v)

            else:
                raise _Fallo("operacion_desconocida", f"operación '{op}'")

        except _Fallo as f:
            res.fallo = FalloEjecucion(f.tipo, c.linea, f.mensaje)
            break

    return res


def _clave(v: Any) -> Tuple[str, Any]:
    # Se compara (tipo, valor): sin esto, 1 == 1.0 == True ocultaría una diferencia de tipo.
    return (_tipo_de(v), v)


def equivalentes(a: ResultadoEjecucion, b: ResultadoEjecucion) -> Tuple[bool, List[str]]:
    """Compara dos ejecuciones: mismas salidas, misma memoria final y el mismo error
    (clase y línea fuente). Devuelve (son_equivalentes, motivos_de_diferencia)."""
    motivos: List[str] = []

    if [_clave(v) for v in a.salidas] != [_clave(v) for v in b.salidas]:
        motivos.append(f"salidas distintas: {formatear(a.salidas)} vs {formatear(b.salidas)}")

    if {k: _clave(v) for k, v in a.memoria.items()} != {k: _clave(v) for k, v in b.memoria.items()}:
        motivos.append(f"memoria final distinta: {a.memoria} vs {b.memoria}")

    fa = (a.fallo.tipo, a.fallo.linea) if a.fallo else None
    fb = (b.fallo.tipo, b.fallo.linea) if b.fallo else None
    if fa != fb:
        motivos.append(f"error distinto: {fa} vs {fb}")

    return (not motivos, motivos)


def formatear_valor(v: Any) -> str:
    """Un valor legible: true/false para bool, el resto como en Python (2.0, 7.5, 14)."""
    return ("true" if v else "false") if isinstance(v, bool) else repr(v)


def formatear(valores) -> str:
    """Lista de valores legibles, por ejemplo [7.5, 14]."""
    return "[" + ", ".join(formatear_valor(v) for v in valores) + "]"