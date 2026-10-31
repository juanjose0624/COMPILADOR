"""
generador.py
Generador de código destino (backend): traduce la IR al ensamblador educativo .asm
de la guía de generación de código (registros R0-R7, memoria simbólica, PC desde 0).

Estrategia reproducible de la guía (corrección primero, sin asignador de registros):
  para cada instrucción IR -> cargar el primer operando en R0, el segundo en R1,
  operar, y guardar el resultado en la celda propia del temporal.
  - Constantes: MOV Rn, #valor      (los reales conservan el punto: #2.0, nunca #2)
  - LOAD de una celda:  LD (int/bool) o LDF (real) según el tipo de la celda
  - ADD SUB MUL (int)  /  ADDF SUBF MULF DIVF (real); I2F convierte int -> real
  - STORE: ST/STF celda, registro  (celda primero, registro después)
  - PRINT: OUT R0

Compatible con ir_nodos.py, generar_ir.py, validador_ir.py y optimizador.py.
"""

import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ir_nodos import Cuadrupla, Constante, Variable, Temporal, ProgramaIR
from validador_ir import validar_ir


@dataclass
class ResultadoCodigo:
    """Resultado del backend (interfaz propuesta por la guía)."""

    texto_asm: str
    # PC de cada instrucción (desde 0; las directivas y comentarios no cuentan) -> línea fuente.
    mapa_lineas: Dict[int, int] = field(default_factory=dict)
    # Línea del archivo .asm (desde 1) -> línea fuente. Sirve para ubicar errores del editor.
    mapa_lineas_asm: Dict[int, int] = field(default_factory=dict)
    # Nombre en la IR/programa (variable o temporal) -> nombre de su celda en .data.
    mapa_nombres: Dict[str, str] = field(default_factory=dict)


def _ascii(texto: str) -> str:
    """Los comentarios del .asm se escriben solo en ASCII, para que ninguna codificación los rompa."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def _tipo_simbolo(simbolos: Any, nombre: str) -> Optional[str]:
    """Tipo declarado de una variable (acepta {nombre: 'int'}, objetos con .tipo o dicts)."""
    if not simbolos or nombre not in simbolos:
        return None
    s = simbolos[nombre]
    if isinstance(s, str):
        return s
    if isinstance(s, dict):
        return s.get("tipo")
    return getattr(s, "tipo", None)


def _es_real(tipo: Optional[str]) -> bool:
    # bool se guarda como entero 0/1: solo "real" usa celdas y operaciones F.
    return tipo == "real"


def _inmediato(constante: Constante) -> str:
    """Texto de un inmediato. Un real siempre lleva punto o exponente; bool es 0/1."""
    valor = constante.valor
    if constante.tipo == "bool":
        return "#1" if valor else "#0"
    if constante.tipo == "real":
        return "#" + repr(float(valor))  # repr siempre incluye '.' o exponente
    return f"#{int(valor)}"


def generar_codigo(cuadruplas, tabla_simbolos: Any = None) -> str:
    """Devuelve el texto .asm. (Compatible con la versión anterior; para los mapas de
    líneas y nombres usar generar_codigo_detallado.)"""
    return generar_codigo_detallado(cuadruplas, tabla_simbolos).texto_asm


def generar_codigo_detallado(programa, tabla_simbolos: Any = None) -> ResultadoCodigo:
    """Traduce la IR a ensamblador. `programa` puede ser una lista de cuádruplas o un ProgramaIR
    (en ese caso sus declaraciones hacen de tabla de símbolos si no se entrega otra)."""

    if isinstance(programa, ProgramaIR):
        cuadruplas = programa.instrucciones
        if tabla_simbolos is None:
            tabla_simbolos = programa.declaraciones
    else:
        cuadruplas = programa

    if not isinstance(cuadruplas, list):
        raise TypeError("generar_codigo esperaba una lista de cuadruplas o un ProgramaIR.")

    # La IR se valida antes de generar: no se genera código a partir de IR mal formada.
    validar_ir(cuadruplas, tabla_simbolos or None)

    # ------------------------------------------------------------------ nombres y tipos
    # Tipos de variables: la tabla semántica (incluye variables declaradas aunque la
    # optimización haya quitado instrucciones) o, si falta, lo que dice la propia IR.
    tipos_var: Dict[str, str] = {}
    if tabla_simbolos:
        for nombre in tabla_simbolos:
            tipos_var[nombre] = _tipo_simbolo(tabla_simbolos, nombre)
    for c in cuadruplas:
        if c.op == "LOAD":
            tipos_var.setdefault(c.arg1.nombre, c.tipo)
        elif c.op == "STORE":
            tipos_var.setdefault(c.resultado.nombre, c.tipo)

    tipos_temp: Dict[str, str] = {}
    for c in cuadruplas:
        if isinstance(c.resultado, Temporal):
            tipos_temp[c.resultado.nombre] = c.tipo

    # Celdas: id1, id2, ... para variables (nunca chocan con registros, mnemónicos ni con
    # el nombre de un temporal) y el propio nombre IR (t1, t2, ...) para temporales.
    celda_var = {nombre: f"id{i}" for i, nombre in enumerate(tipos_var, start=1)}
    mapa_nombres: Dict[str, str] = dict(celda_var)
    for nombre in tipos_temp:
        mapa_nombres[nombre] = nombre

    def celda(operando) -> str:
        return celda_var[operando.nombre] if isinstance(operando, Variable) else operando.nombre

    # ------------------------------------------------------------------ sección .data
    datos: List[str] = []
    for nombre, tipo in tipos_var.items():
        datos.append(f"; {celda_var[nombre]} = {nombre} ({tipo})")
        datos.append(f"{celda_var[nombre]}: " + (".float 0.0" if _es_real(tipo) else ".int 0"))
    if tipos_temp:
        datos.append("; Celdas auxiliares de los temporales de la IR")
        for nombre, tipo in tipos_temp.items():
            datos.append(f"{nombre}: " + (".float 0.0" if _es_real(tipo) else ".int 0"))

    # ------------------------------------------------------------------ sección .text
    # Cada fila: (texto, línea fuente, ¿es instrucción?)
    filas: List[tuple] = []

    def emitir(texto: str, linea: int) -> None:
        filas.append((f"    {texto}", linea, True))

    def cargar(registro: str, operando, linea: int) -> None:
        """Deja el valor de un operando (constante o temporal) en el registro."""
        if isinstance(operando, Constante):
            emitir(f"MOV {registro}, {_inmediato(operando)}", linea)
        else:
            mnemonico = "LDF" if _es_real(tipos_temp[operando.nombre]) else "LD"
            emitir(f"{mnemonico} {registro}, {celda(operando)}", linea)

    def guardar_temporal(resultado: Temporal, linea: int) -> None:
        mnemonico = "STF" if _es_real(tipos_temp[resultado.nombre]) else "ST"
        emitir(f"{mnemonico} {celda(resultado)}, R0", linea)

    for indice, c in enumerate(cuadruplas, start=1):
        filas.append((f"    ; {indice}: {_ascii(str(c))}", None, False))
        linea = c.linea
        op = c.op

        if op == "CONST":
            cargar("R0", c.arg1, linea)
            guardar_temporal(c.resultado, linea)

        elif op == "LOAD":
            mnemonico = "LDF" if _es_real(tipos_var[c.arg1.nombre]) else "LD"
            emitir(f"{mnemonico} R0, {celda(c.arg1)}", linea)
            guardar_temporal(c.resultado, linea)

        elif op == "COPY":
            cargar("R0", c.arg1, linea)
            guardar_temporal(c.resultado, linea)

        elif op == "I2F":
            cargar("R0", c.arg1, linea)  # el origen es un entero
            emitir("I2F R0, R0", linea)
            guardar_temporal(c.resultado, linea)

        elif op in ("ADD", "SUB", "MUL", "DIV"):
            cargar("R0", c.arg1, linea)
            cargar("R1", c.arg2, linea)
            mnemonico = op + ("F" if _es_real(c.tipo) else "")
            emitir(f"{mnemonico} R0, R0, R1", linea)
            guardar_temporal(c.resultado, linea)

        elif op == "STORE":
            cargar("R0", c.arg1, linea)
            mnemonico = "STF" if _es_real(tipos_var[c.resultado.nombre]) else "ST"
            emitir(f"{mnemonico} {celda(c.resultado)}, R0", linea)

        elif op == "PRINT":
            cargar("R0", c.arg1, linea)
            emitir("OUT R0", linea)

        else:  # el validador ya rechaza operadores desconocidos; esto es solo una red de seguridad
            raise ValueError(f"Operación IR no soportada: {op} (cuadrupla {indice}, línea {c.linea}).")

    filas.append(("    HALT", None, True))

    # ------------------------------------------------------------------ ensamblado del texto
    lineas: List[str] = [
        "; Codigo generado por el compilador (ensamblador educativo)",
        ".data",
    ]
    lineas.extend(datos)
    lineas.append(".text")

    mapa_lineas: Dict[int, int] = {}
    mapa_lineas_asm: Dict[int, int] = {}
    pc = 0
    for texto, linea_fuente, es_instruccion in filas:
        lineas.append(texto)
        if es_instruccion:
            if linea_fuente is not None:
                mapa_lineas[pc] = linea_fuente
                mapa_lineas_asm[len(lineas)] = linea_fuente
            pc += 1

    return ResultadoCodigo(
        texto_asm="\n".join(lineas) + "\n",
        mapa_lineas=mapa_lineas,
        mapa_lineas_asm=mapa_lineas_asm,
        mapa_nombres=mapa_nombres,
    )