
# ast_nodos.py

from dataclasses import dataclass
from typing import List, Union


@dataclass
class NodoAST:
    """Clase base de todos los nodos del árbol de sintaxis abstracta."""

    linea: int
    columna: int


@dataclass
class Programa(NodoAST):
    """Representa el programa completo."""

    sentencias: List[NodoAST]


@dataclass
class Declaracion(NodoAST):
    """Representa una declaración e inicialización de variable."""

    tipo_declarado: str
    nombre: str
    inicializador: NodoAST


@dataclass
class Asignacion(NodoAST):
    """Representa la asignación de un valor a una variable."""

    nombre: str
    expresion: NodoAST


@dataclass
class Salida(NodoAST):
    """Representa una instrucción print."""

    expresion: NodoAST


@dataclass
class Literal(NodoAST):
    """Representa un valor constante del programa."""

    valor: Union[int, float, bool]
    tipo_literal: str


@dataclass
class Referencia(NodoAST):
    """Representa una referencia a una variable."""

    nombre: str


@dataclass
class Binaria(NodoAST):
    """Representa una operación binaria entre dos expresiones."""

    operador: str
    izquierdo: NodoAST
    derecho: NodoAST
