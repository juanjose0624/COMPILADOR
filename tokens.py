
from dataclasses import dataclass


@dataclass
class Token:
    """Representa un token identificado durante el análisis léxico."""

    tipo: str
    lexema: str
    linea: int
    columna: int
