# validador_ir.py
# Valida una lista de cuádruplas (op, arg1, arg2, resultado, tipo, linea) contra el
# contrato de la Guía de código intermedio y optimización (secciones 1 y 4).
# Se ejecuta ANTES de optimizar y de nuevo DESPUÉS de cada pase: la IR mal formada
# se rechaza, no se espera que el optimizador la arregle.

import math
from ir_nodos import Temporal, Variable, Constante

TIPOS = {"int", "real", "bool"}
ARITMETICAS = {"ADD", "SUB", "MUL", "DIV"}
OPERADORES_VALIDOS = {"CONST", "LOAD", "COPY", "I2F", "STORE", "PRINT"} | ARITMETICAS

# Valores: un temporal o una constante. Una Variable NUNCA se usa directamente como
# operando de cálculo: se lee con LOAD y se escribe con STORE.
VALOR = (Temporal, Constante)

# Forma de cada operación: (clases permitidas en arg1, en arg2, en resultado).
# None significa "debe quedar vacío".
FORMAS = {
    "CONST": ((Constante,), None, (Temporal,)),
    "LOAD":  ((Variable,),  None, (Temporal,)),
    "COPY":  ((Temporal,),  None, (Temporal,)),
    "I2F":   (VALOR,        None, (Temporal,)),
    "ADD":   (VALOR, VALOR, (Temporal,)),
    "SUB":   (VALOR, VALOR, (Temporal,)),
    "MUL":   (VALOR, VALOR, (Temporal,)),
    "DIV":   (VALOR, VALOR, (Temporal,)),
    "STORE": (VALOR,        None, (Variable,)),   # arg1 = valor, resultado = variable destino
    "PRINT": (VALOR,        None, None),          # sin resultado: tiene efecto observable
}


class ErrorIR(Exception):
    """Incumplimiento del contrato de la IR. Sigue el formato común de diagnóstico
    (fase, linea, mensaje); la IR no tiene columna, así que queda en None."""

    def __init__(self, mensaje, linea=None):
        self.fase = "ir"
        self.linea = linea
        self.columna = None
        self.mensaje = mensaje
        super().__init__(f"Error IR [Línea {linea}]: {mensaje}")


def _nombre(x):
    """Nombre estable de un Temporal o Variable (no depende de __str__)."""
    return getattr(x, "nombre", str(x))


def _tipo_simbolo(simbolos, nombre):
    """Tipo declarado de una variable. Acepta {nombre: 'int'}, {nombre: objeto con .tipo}
    o {nombre: {'tipo': ...}}. Ajustar aquí si tu tabla de símbolos guarda otra cosa."""
    s = simbolos[nombre]
    if isinstance(s, str):
        return s
    if isinstance(s, dict):
        return s.get("tipo")
    return getattr(s, "tipo", None)


def _validar_constante(k, linea):
    """El valor de la constante debe corresponder a su tipo (bool NO es int aquí)."""
    if k.tipo not in TIPOS:
        raise ErrorIR(f"Constante con tipo desconocido '{k.tipo}'.", linea)
    v = k.valor
    if k.tipo == "int" and (not isinstance(v, int) or isinstance(v, bool)):
        raise ErrorIR(f"Constante int con valor no entero: {v!r}.", linea)
    if k.tipo == "real":
        # float estricto: el backend necesita escribir #2.0, no #2
        if not isinstance(v, float) or not math.isfinite(v):
            raise ErrorIR(f"Constante real con valor no real finito: {v!r}.", linea)
    if k.tipo == "bool" and not isinstance(v, bool):
        raise ErrorIR(f"Constante bool con valor no booleano: {v!r}.", linea)


def validar_ir(cuadruplas, simbolos=None):
    """
    Comprueba los invariantes de la guía:
      1. Operador conocido y línea de origen presente.
      2. Forma de cada operación (qué va en arg1, arg2 y resultado).
      3. Cada temporal se define una sola vez y antes de usarse.
      4. Temporales sin colisión con nombres de variables.
      5. Las variables existen en la tabla semántica (si se entrega `simbolos`).
      6. Tipos coherentes; DIV siempre real; I2F solo int -> real;
         bool solo en CONST, LOAD, COPY, STORE y PRINT.
    Devuelve True o lanza ErrorIR con la línea de la instrucción culpable.
    No modifica la IR.
    """
    # Nombres de variables presentes (tabla semántica + las que usa la IR) para detectar colisiones.
    variables = set(simbolos) if simbolos is not None else set()
    for c in cuadruplas:
        if isinstance(c.arg1, Variable):
            variables.add(_nombre(c.arg1))
        if isinstance(c.resultado, Variable):
            variables.add(_nombre(c.resultado))

    definidos = {}  # nombre de temporal -> tipo

    def tipo_de(operando, linea):
        if isinstance(operando, Temporal):
            return definidos[_nombre(operando)]
        return operando.tipo  # Constante (ya validada)

    def tipo_variable(var, linea):
        nombre = _nombre(var)
        if simbolos is None:
            return None  # sin tabla no se puede comprobar
        if nombre not in simbolos:
            raise ErrorIR(f"Variable '{nombre}' no existe en la tabla de símbolos.", linea)
        return _tipo_simbolo(simbolos, nombre)

    for c in cuadruplas:
        linea = getattr(c, "linea", None)

        # 1. Línea de origen y operador
        if not isinstance(linea, int) or isinstance(linea, bool) or linea < 1:
            raise ErrorIR(f"La instrucción '{c.op}' no conserva una línea de origen válida.", linea)
        if c.op not in OPERADORES_VALIDOS:
            raise ErrorIR(f"Operador desconocido '{c.op}'.", linea)
        if c.tipo not in TIPOS:
            raise ErrorIR(f"Tipo desconocido '{c.tipo}' en {c.op}.", linea)

        # 2. Forma de la operación
        for campo, valor, permitido in zip(
            ("arg1", "arg2", "resultado"),
            (c.arg1, c.arg2, c.resultado),
            FORMAS[c.op],
        ):
            if permitido is None:
                if valor is not None:
                    raise ErrorIR(f"{c.op}: {campo} debe quedar vacío, pero contiene '{valor}'.", linea)
            elif not isinstance(valor, permitido):
                esperado = " o ".join(k.__name__ for k in permitido)
                raise ErrorIR(f"{c.op}: {campo} debe ser {esperado}, no '{valor}'.", linea)

        # 3. Usos: todo temporal leído debe estar definido; las constantes deben ser coherentes
        for arg in (c.arg1, c.arg2):
            if isinstance(arg, Temporal) and _nombre(arg) not in definidos:
                raise ErrorIR(f"Temporal '{_nombre(arg)}' utilizado sin previa definición.", linea)
            if isinstance(arg, Constante):
                _validar_constante(arg, linea)

        # 4. Tipos, por operación
        if c.op == "CONST":
            if c.arg1.tipo != c.tipo:
                raise ErrorIR(f"CONST declara {c.tipo} pero su constante es {c.arg1.tipo}.", linea)

        elif c.op == "LOAD":
            t_var = tipo_variable(c.arg1, linea)
            if t_var is not None and t_var != c.tipo:
                raise ErrorIR(f"LOAD {c.tipo} de '{_nombre(c.arg1)}', que está declarada {t_var}.", linea)

        elif c.op == "COPY":
            if tipo_de(c.arg1, linea) != c.tipo:
                raise ErrorIR(f"COPY {c.tipo} de un valor {tipo_de(c.arg1, linea)}.", linea)

        elif c.op == "I2F":
            if tipo_de(c.arg1, linea) == "bool":
                raise ErrorIR("I2F no admite bool: bool no se usa como número.", linea)
            if tipo_de(c.arg1, linea) != "int" or c.tipo != "real":
                raise ErrorIR(
                    f"I2F convierte int a real; recibió {tipo_de(c.arg1, linea)} y declara {c.tipo}.", linea)

        elif c.op in ARITMETICAS:
            t1, t2 = tipo_de(c.arg1, linea), tipo_de(c.arg2, linea)
            if "bool" in (c.tipo, t1, t2):
                raise ErrorIR(f"{c.op}: bool no participa en operaciones aritméticas.", linea)
            if not (t1 == t2 == c.tipo):
                raise ErrorIR(
                    f"{c.op}: tipos incompatibles (arg1 {t1}, arg2 {t2}, operación {c.tipo}); "
                    "faltan conversiones I2F.", linea)
            if c.op == "DIV" and c.tipo != "real":
                raise ErrorIR("DIV siempre es real: convertir ambos operandos con I2F antes.", linea)

        elif c.op == "STORE":
            t_val = tipo_de(c.arg1, linea)
            t_var = tipo_variable(c.resultado, linea)
            if t_val != c.tipo:
                raise ErrorIR(f"STORE {c.tipo} de un valor {t_val}.", linea)
            if t_var is not None and t_var != c.tipo:
                raise ErrorIR(
                    f"STORE {c.tipo} en '{_nombre(c.resultado)}', declarada {t_var}; "
                    "la promoción int -> real debe hacerse antes con I2F.", linea)

        elif c.op == "PRINT":
            if tipo_de(c.arg1, linea) != c.tipo:
                raise ErrorIR(f"PRINT {c.tipo} de un valor {tipo_de(c.arg1, linea)}.", linea)

        # 5. Definición del resultado temporal: una sola vez, sin chocar con variables
        if isinstance(c.resultado, Temporal):
            nombre = _nombre(c.resultado)
            if nombre in definidos:
                raise ErrorIR(f"Temporal '{nombre}' redefinido ilegalmente.", linea)
            if nombre in variables:
                raise ErrorIR(f"Temporal '{nombre}' colisiona con una variable del mismo nombre.", linea)
            definidos[nombre] = c.tipo

    return True