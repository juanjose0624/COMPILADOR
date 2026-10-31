# sintactico.py
# Implementa el analizador sintáctico descendente recursivo.
# Recibe los tokens generados por el analizador léxico,
# verifica que cumplan la gramática del lenguaje y construye
# un Árbol de Sintaxis Abstracta (AST).
#
# FUNCIONES PRINCIPALES:
# - Validar la secuencia de tokens y el fin de entrada (EOF).
# - Analizar declaraciones, asignaciones e instrucciones print.
# - Reconocer expresiones aritméticas respetando la precedencia.
# - Construir los nodos del AST.
# - Detectar y reportar errores sintácticos.
#
# DEPENDENCIAS:
# - tokens.py: definición de los tokens.
# - ast_nodos.py: definición de los nodos del AST.
# - errores.py: definición de los errores sintácticos.

from typing import List

from tokens import Token
from ast_nodos import (
    Programa,
    Declaracion,
    Asignacion,
    Salida,
    Literal,
    Referencia,
    Binaria,
    NodoAST,
)
from errores import ErrorSintactico


class Parser:
    """Analizador sintáctico descendente recursivo."""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

        if not self.tokens:
            raise ErrorSintactico(
                1, 1, "La lista de tokens está vacía; se esperaba EOF."
            )

        # EOF debe ser el último token.
        if self.tokens[-1].tipo != "EOF":
            ultimo = self.tokens[-1]
            raise ErrorSintactico(
                ultimo.linea,
                ultimo.columna,
                "La lista de tokens debe terminar con EOF.",
            )

        # No debe haber tokens después del primer EOF.
        for token in self.tokens[:-1]:
            if token.tipo == "EOF":
                raise ErrorSintactico(
                    token.linea,
                    token.columna,
                    "Se encontraron tokens después de EOF.",
                )

    def actual(self) -> Token:
        """Devuelve el token actual sin avanzar."""

        if self.pos < len(self.tokens):
            return self.tokens[self.pos]

        return self.tokens[-1]

    def avanzar(self) -> Token:
        """Consume el token actual sin avanzar más allá de EOF."""

        token = self.actual()

        if token.tipo != "EOF":
            self.pos += 1

        return token

    def consumir(self, tipo: str) -> Token:
        """Consume un token si coincide con el tipo esperado."""

        token = self.actual()

        if token.tipo == tipo:
            return self.avanzar()

        # Mensaje más claro que "Se esperaba 'ID'" para el usuario final.
        esperado = "un identificador (ID)" if tipo == "ID" else f"'{tipo}'"

        encontrado = (
            f"'{token.lexema}' (tipo {token.tipo})"
            if token.tipo != "EOF"
            else "fin de entrada (EOF)"
        )

        raise ErrorSintactico(
            token.linea,
            token.columna,
            f"Se esperaba {esperado}, pero se encontró {encontrado}.",
        )

    def parsear(self) -> Programa:
        """Analiza el programa completo hasta EOF."""

        inicio = self.actual()
        sentencias = []

        while self.actual().tipo != "EOF":
            sentencias.append(self.parsear_sentencia())

        # Consumir EOF confirma que el programa terminó correctamente.
        self.consumir("EOF")

        return Programa(
            linea=inicio.linea,
            columna=inicio.columna,
            sentencias=sentencias,
        )

    def parsear_sentencia(self) -> NodoAST:
        """Identifica y analiza una sentencia."""

        token = self.actual()

        if token.tipo in ("int", "real", "bool"):
            return self.parsear_declaracion()

        if token.tipo == "ID":
            return self.parsear_asignacion()

        if token.tipo == "print":
            return self.parsear_salida()

        encontrado = (
            f"'{token.lexema}'"
            if token.tipo != "EOF"
            else "fin de entrada"
        )

        raise ErrorSintactico(
            token.linea,
            token.columna,
            f"Sentencia inválida: se encontró {encontrado}.",
        )

    def parsear_declaracion(self) -> Declaracion:
        """Analiza declaraciones como: int x = 10;"""

        token_tipo = self.avanzar()
        tipo_decl = token_tipo.tipo  # coincide con el lexema: int, real o bool

        token_id = self.consumir("ID")
        nombre = token_id.lexema

        self.consumir("=")
        expresion = self.parsear_expresion()
        self.consumir(";")

        return Declaracion(
            linea=token_id.linea,
            columna=token_id.columna,
            tipo_declarado=tipo_decl,
            nombre=nombre,
            inicializador=expresion,
        )

    def parsear_asignacion(self) -> Asignacion:
        """Analiza asignaciones como: x = 10;"""

        token_id = self.consumir("ID")
        nombre = token_id.lexema

        self.consumir("=")
        expresion = self.parsear_expresion()
        self.consumir(";")

        return Asignacion(
            linea=token_id.linea,
            columna=token_id.columna,
            nombre=nombre,
            expresion=expresion,
        )

    def parsear_salida(self) -> Salida:
        """Analiza instrucciones como: print(x);"""

        token_print = self.consumir("print")

        self.consumir("(")
        expresion = self.parsear_expresion()
        self.consumir(")")
        self.consumir(";")

        return Salida(
            linea=token_print.linea,
            columna=token_print.columna,
            expresion=expresion,
        )

    def parsear_expresion(self) -> NodoAST:
        """Analiza sumas y restas, que tienen menor precedencia."""

        nodo = self.parsear_termino()

        while self.actual().tipo in ("+", "-"):
            token_operador = self.avanzar()
            derecho = self.parsear_termino()

            nodo = Binaria(
                linea=token_operador.linea,
                columna=token_operador.columna,
                operador=token_operador.lexema,
                izquierdo=nodo,
                derecho=derecho,
            )

        return nodo

    def parsear_termino(self) -> NodoAST:
        """Analiza multiplicaciones y divisiones."""

        nodo = self.parsear_factor()

        while self.actual().tipo in ("*", "/"):
            token_operador = self.avanzar()
            derecho = self.parsear_factor()

            nodo = Binaria(
                linea=token_operador.linea,
                columna=token_operador.columna,
                operador=token_operador.lexema,
                izquierdo=nodo,
                derecho=derecho,
            )

        return nodo

    def parsear_factor(self) -> NodoAST:
        """Analiza literales, referencias y expresiones entre paréntesis."""

        token = self.actual()

        if token.tipo == "NUM_INT":
            self.avanzar()

            try:
                valor = int(token.lexema)
            except ValueError:
                # Además de un lexema mal formado, Python 3.11+ rechaza
                # enteros de más de 4300 dígitos.
                raise ErrorSintactico(
                    token.linea,
                    token.columna,
                    f"Número entero inválido o demasiado grande: '{token.lexema[:20]}'.",
                ) from None

            return Literal(
                linea=token.linea,
                columna=token.columna,
                valor=valor,
                tipo_literal="int",
            )

        if token.tipo == "NUM_REAL":
            self.avanzar()

            try:
                valor = float(token.lexema)
            except ValueError:
                raise ErrorSintactico(
                    token.linea,
                    token.columna,
                    f"Número real inválido: '{token.lexema}'.",
                ) from None

            return Literal(
                linea=token.linea,
                columna=token.columna,
                valor=valor,
                tipo_literal="real",
            )

        if token.tipo == "BOOL":
            if token.lexema not in ("true", "false"):
                raise ErrorSintactico(
                    token.linea,
                    token.columna,
                    f"Booleano inválido: '{token.lexema}'.",
                )

            self.avanzar()

            return Literal(
                linea=token.linea,
                columna=token.columna,
                valor=(token.lexema == "true"),
                tipo_literal="bool",
            )

        if token.tipo == "ID":
            self.avanzar()

            return Referencia(
                linea=token.linea,
                columna=token.columna,
                nombre=token.lexema,
            )

        if token.tipo == "(":
            self.avanzar()
            expresion = self.parsear_expresion()
            self.consumir(")")
            return expresion

        encontrado = (
            f"'{token.lexema}'"
            if token.tipo != "EOF"
            else "fin de entrada"
        )

        raise ErrorSintactico(
            token.linea,
            token.columna,
            f"Se esperaba un factor válido, pero se encontró {encontrado}.",
        )


def analizar_sintaxis(tokens: List[Token]) -> Programa:
    """Punto de entrada del análisis sintáctico."""

    parser = Parser(tokens)

    try:
        return parser.parsear()
    except RecursionError:
        # Paréntesis anidados cientos de veces agotan la pila de Python.
        # Se informa como error sintáctico, no como traceback.
        token = parser.actual()
        raise ErrorSintactico(
            token.linea,
            token.columna,
            "Expresión demasiado anidada para poder analizarla.",
        ) from None