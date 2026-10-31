# ir_nodos.py
# Contrato de la representación intermedia (guía de código intermedio y optimización):
#   cuádrupla extendida (op, arg1, arg2, resultado, tipo, linea)
#   operandos distinguibles: Constante(valor, tipo), Temporal(nombre), Variable(nombre)

from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional


# Los operandos son inmutables: el optimizador comparte los mismos objetos entre la IR
# original y la optimizada, y así ningún módulo puede alterar una por accidente.
@dataclass(frozen=True)
class Constante:
    valor: Any
    tipo: str

    def __str__(self):
        # Igual que en el lenguaje fuente: true / false (no True / False).
        # OJO: esto es solo para mostrar. El backend NO debe emitir inmediatos con str():
        # bool -> 1 / 0, y los reales deben conservar el punto (#2.0).
        if self.tipo == "bool":
            return "true" if self.valor else "false"
        return str(self.valor)


@dataclass(frozen=True)
class Variable:
    nombre: str

    def __str__(self):
        return self.nombre


@dataclass(frozen=True)
class Temporal:
    nombre: str

    def __str__(self):
        return self.nombre


@dataclass
class Cuadrupla:
    op: str
    arg1: Optional[Any] = None
    arg2: Optional[Any] = None
    resultado: Optional[Any] = None
    tipo: Optional[str] = None
    linea: int = 0  # el validador rechaza 0: toda instrucción debe conservar su línea de origen

    def __str__(self):
        a1 = "" if self.arg1 is None else str(self.arg1)
        a2 = "" if self.arg2 is None else str(self.arg2)
        res = "" if self.resultado is None else str(self.resultado)
        t = self.tipo or "?"

        # Formas legibles del contrato: t1 = const int 2 / t5 = mul real t4, 2.5 / store real total, t5
        if self.op in ("CONST", "LOAD", "COPY", "I2F"):
            texto = f"{res} = {self.op.lower()} {t} {a1}"
        elif self.op in ("ADD", "SUB", "MUL", "DIV"):
            texto = f"{res} = {self.op.lower()} {t} {a1}, {a2}"
        elif self.op == "STORE":
            texto = f"store {t} {res}, {a1}"
        elif self.op == "PRINT":
            texto = f"print {t} {a1}"
        else:
            texto = f"{self.op} {a1}, {a2}, {res} {t}"

        return f"{texto}    ; línea {self.linea}"


@dataclass
class ProgramaIR:
    """Programa en IR: las declaraciones originales (nombre -> tipo) más las instrucciones.

    Las declaraciones se conservan aunque el optimizador quite instrucciones: el backend
    las necesita para reservar la memoria (.data). Su forma {nombre: tipo} sirve también
    como `simbolos` para validar_ir y optimizar_ir.
    """

    declaraciones: Dict[str, str] = field(default_factory=dict)
    instrucciones: List[Cuadrupla] = field(default_factory=list)

    def con_instrucciones(self, nuevas: List[Cuadrupla]) -> "ProgramaIR":
        """Programa nuevo con las mismas declaraciones y otras instrucciones
        (por ejemplo, la salida del optimizador). No modifica este objeto."""
        return replace(self, declaraciones=dict(self.declaraciones), instrucciones=list(nuevas))

    def __str__(self):
        return "\n".join(str(c) for c in self.instrucciones)