
# lexico.py
# Implementa el analizador léxico del compilador.
# Examina el código fuente carácter por carácter y lo divide
# en tokens que representan los elementos del lenguaje.
#
# FUNCIONES PRINCIPALES:
# - Reconocer números enteros y reales.
# - Identificar nombres de variables y palabras reservadas.
# - Reconocer operadores y símbolos del lenguaje.
# - Ignorar espacios, tabulaciones y saltos de línea.
# - Detectar caracteres no permitidos.
# - Registrar la línea y columna de cada token.
# - Agregar el token EOF al finalizar el análisis.
#
# DEPENDENCIAS:
# - tokens.py: definición de la estructura Token.
# - errores.py: definición de los errores del compilador.
#
# RESULTADO:
# Devuelve una lista de tokens para el analizador sintáctico.

import re
from typing import List

from tokens import Token
from errores import ErrorCompilador


# Reconoce espacios, comentarios, saltos de línea,
# números, identificadores, operadores y caracteres inválidos.
PATRON_TOKEN = re.compile(
    r"""
    (?P<ESPACIO>[ \t\r]+)
    |(?P<SALTO>\n)
    |(?P<NUM_REAL>[0-9]+\.[0-9]+)
    |(?P<NUM_INT>[0-9]+)
    |(?P<ID>[a-zA-Z_][a-zA-Z_0-9]*)
    |(?P<OPERADOR>[+\-*/=;()])
    |(?P<INVALIDO>.)
    """,
    re.VERBOSE,
)


# Palabras reservadas del lenguaje.
PALABRAS_RESERVADAS = {
    "int": "int",
    "real": "real",
    "bool": "bool",
    "print": "print",
    "true": "BOOL",
    "false": "BOOL",
}


def analizar_lexico(codigo_fuente: str) -> List[Token]:
    """Convierte el código fuente en una lista de tokens."""

    tokens = []
    linea = 1
    columna = 1
    posicion = 0

    while posicion < len(codigo_fuente):
        coincidencia = PATRON_TOKEN.match(codigo_fuente, posicion)

        if coincidencia is None:
            raise ErrorCompilador(
                "lexico",
                linea,
                columna,
                "No se pudo reconocer el siguiente elemento.",
            )

        tipo = coincidencia.lastgroup
        lexema = coincidencia.group()
        columna_inicial = columna

        # Ignorar espacios y tabulaciones.
        if tipo == "ESPACIO":
            columna += len(lexema)

        # Actualizar línea y columna después de un salto de línea.
        elif tipo == "SALTO":
            linea += 1
            columna = 1

        # Rechazar caracteres que no pertenecen al lenguaje.
        elif tipo == "INVALIDO":
            raise ErrorCompilador(
                "lexico",
                linea,
                columna,
                f"Carácter no válido: {lexema!r} (U+{ord(lexema):04X}).",
            )

        else:
            if tipo == "ID":
                tipo = PALABRAS_RESERVADAS.get(lexema, "ID")

            elif tipo == "OPERADOR":
                # El parser espera símbolos como '+', '=', ';', '('.
                tipo = lexema

            tokens.append(
                Token(
                    tipo=tipo,
                    lexema=lexema,
                    linea=linea,
                    columna=columna_inicial,
                )
            )

            columna += len(lexema)

        posicion = coincidencia.end()

    # Agregar el token de fin de entrada.
    tokens.append(
        Token(
            tipo="EOF",
            lexema="",
            linea=linea,
            columna=columna,
        )
    )

    return tokens
