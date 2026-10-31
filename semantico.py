# semantico.py
# Implementa el analizador semántico del compilador.
# Recibe el Árbol de Sintaxis Abstracta (AST) generado por
# el analizador sintáctico y comprueba que las instrucciones
# respeten las reglas semánticas del lenguaje.
#
# FUNCIONES PRINCIPALES:
# - Validar los tipos de datos permitidos: int, real y bool.
# - Detectar variables duplicadas o no declaradas.
# - Construir y mantener la tabla de símbolos.
# - Verificar la compatibilidad de tipos en declaraciones
#   y asignaciones.
# - Inferir los tipos de las expresiones y anotarlos en el AST.
# - Detectar operaciones aritméticas inválidas.
# - Registrar las ubicaciones de las declaraciones.
#
# DEPENDENCIAS:
# - ast_nodos.py: definición de los nodos del AST.
# - errores.py: definición de los errores semánticos.
#
# RESULTADO:
# Devuelve el AST analizado, la tabla de símbolos y las
# ubicaciones de las variables declaradas.

from dataclasses import dataclass, field
from typing import Dict, Tuple

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
from errores import ErrorSemantico


@dataclass
class ResultadoSemantico:
    """Resultado del análisis semántico.

    tabla_simbolos: nombre -> tipo declarado (se mantiene como str para no romper
                    a quien ya la consume: main.py, generador de IR, validador).
    ubicaciones:    nombre -> (linea, columna) de la declaración.
    Además, cada nodo de expresión del AST queda anotado con `tipo_inferido`.
    """

    ast: Programa
    tabla_simbolos: Dict[str, str]
    ubicaciones: Dict[str, Tuple[int, int]] = field(default_factory=dict)


class AnalizadorSemantico:
    """Verifica declaraciones, tipos y expresiones del programa."""

    TIPOS_VALIDOS = {"int", "real", "bool"}

    def __init__(self):
        self.tabla_simbolos: Dict[str, str] = {}
        self.ubicaciones: Dict[str, Tuple[int, int]] = {}

    def analizar(self, ast: Programa) -> ResultadoSemantico:
        """Analiza todas las sentencias en orden."""

        # Cada análisis empieza con la tabla limpia.
        self.tabla_simbolos = {}
        self.ubicaciones = {}

        for sentencia in ast.sentencias:
            try:
                self.visitar(sentencia)
            except RecursionError:
                # Expresiones con cientos de operandos encadenados producen un
                # árbol muy profundo. Se informa como error, no como traceback.
                raise ErrorSemantico(
                    sentencia.linea,
                    sentencia.columna,
                    "Expresión demasiado anidada o extensa para analizarla.",
                ) from None

        return ResultadoSemantico(
            ast=ast,
            tabla_simbolos=self.tabla_simbolos.copy(),
            ubicaciones=self.ubicaciones.copy(),
        )

    def visitar(self, nodo: NodoAST) -> None:
        """Procesa una sentencia según su tipo."""

        if isinstance(nodo, Declaracion):
            self.visitar_declaracion(nodo)

        elif isinstance(nodo, Asignacion):
            self.visitar_asignacion(nodo)

        elif isinstance(nodo, Salida):
            self.visitar_salida(nodo)

        else:
            raise ErrorSemantico(
                nodo.linea,
                nodo.columna,
                "Sentencia desconocida en el análisis semántico.",
            )

    def visitar_declaracion(self, nodo: Declaracion) -> None:
        """Valida una declaración y registra la variable."""

        if nodo.tipo_declarado not in self.TIPOS_VALIDOS:
            raise ErrorSemantico(
                nodo.linea,
                nodo.columna,
                f"Tipo de dato desconocido: '{nodo.tipo_declarado}'.",
            )

        if nodo.nombre in self.tabla_simbolos:
            linea_prev, col_prev = self.ubicaciones[nodo.nombre]
            raise ErrorSemantico(
                nodo.linea,
                nodo.columna,
                f"La variable '{nodo.nombre}' ya fue declarada "
                f"(línea {linea_prev}, columna {col_prev}).",
            )

        # Validar primero la expresión inicializadora.
        tipo_expr = self.inferir_tipo(nodo.inicializador)

        self.verificar_compatibilidad(
            nodo.tipo_declarado,
            tipo_expr,
            nodo.linea,
            nodo.columna,
            "declaración",
        )

        # Registrar solo después de validar correctamente.
        self.tabla_simbolos[nodo.nombre] = nodo.tipo_declarado
        self.ubicaciones[nodo.nombre] = (nodo.linea, nodo.columna)

    def visitar_asignacion(self, nodo: Asignacion) -> None:
        """Valida una asignación a una variable existente."""

        if nodo.nombre not in self.tabla_simbolos:
            raise ErrorSemantico(
                nodo.linea,
                nodo.columna,
                f"La variable '{nodo.nombre}' no ha sido declarada.",
            )

        tipo_destino = self.tabla_simbolos[nodo.nombre]
        tipo_expr = self.inferir_tipo(nodo.expresion)

        self.verificar_compatibilidad(
            tipo_destino,
            tipo_expr,
            nodo.linea,
            nodo.columna,
            "asignación",
        )

    def visitar_salida(self, nodo: Salida) -> None:
        """Comprueba que la expresión de salida sea válida."""

        self.inferir_tipo(nodo.expresion)

    def inferir_tipo(self, expresion: NodoAST) -> str:
        """Devuelve el tipo de una expresión y lo anota en el nodo.

        El generador de IR lee `tipo_inferido` para decidir dónde insertar I2F
        y qué tipo lleva cada operación; sin esta anotación tendría que volver
        a inferir los tipos.
        """

        tipo = self._calcular_tipo(expresion)
        expresion.tipo_inferido = tipo
        return tipo

    def _calcular_tipo(self, expresion: NodoAST) -> str:
        """Aplica las reglas de tipos; los hijos se infieren (y anotan) con inferir_tipo."""

        if isinstance(expresion, Literal):
            if expresion.tipo_literal not in self.TIPOS_VALIDOS:
                raise ErrorSemantico(
                    expresion.linea,
                    expresion.columna,
                    f"Tipo de literal desconocido: "
                    f"'{expresion.tipo_literal}'.",
                )

            return expresion.tipo_literal

        if isinstance(expresion, Referencia):
            if expresion.nombre not in self.tabla_simbolos:
                raise ErrorSemantico(
                    expresion.linea,
                    expresion.columna,
                    f"La variable '{expresion.nombre}' "
                    "no ha sido declarada.",
                )

            return self.tabla_simbolos[expresion.nombre]

        if isinstance(expresion, Binaria):
            tipo_izq = self.inferir_tipo(expresion.izquierdo)
            tipo_der = self.inferir_tipo(expresion.derecho)

            # Solo se permiten los cuatro operadores aritméticos.
            if expresion.operador not in ("+", "-", "*", "/"):
                raise ErrorSemantico(
                    expresion.linea,
                    expresion.columna,
                    f"Operador desconocido: '{expresion.operador}'.",
                )

            # Ningún operador aritmético admite booleanos.
            if tipo_izq == "bool" or tipo_der == "bool":
                raise ErrorSemantico(
                    expresion.linea,
                    expresion.columna,
                    f"El operador '{expresion.operador}' "
                    "no admite operandos de tipo 'bool'.",
                )

            # La división siempre produce un real.
            if expresion.operador == "/":
                return "real"

            # Para +, - y *, basta con que un operando sea real
            # para que el resultado sea real.
            if tipo_izq == "real" or tipo_der == "real":
                return "real"

            return "int"

        raise ErrorSemantico(
            expresion.linea,
            expresion.columna,
            "Expresión desconocida durante la inferencia de tipos.",
        )

    def verificar_compatibilidad(
        self,
        tipo_destino: str,
        tipo_expr: str,
        linea: int,
        columna: int,
        contexto: str,
    ) -> None:
        """Comprueba si el tipo de una expresión es compatible."""

        if tipo_destino == tipo_expr:
            return

        # Se permite int -> real.
        if tipo_destino == "real" and tipo_expr == "int":
            return

        raise ErrorSemantico(
            linea,
            columna,
            f"Tipos incompatibles en {contexto}: "
            f"no se puede usar un valor de tipo '{tipo_expr}' "
            f"en una variable de tipo '{tipo_destino}'.",
        )


def analizar_semantica(ast: Programa) -> ResultadoSemantico:
    """Punto de entrada del análisis semántico."""

    analizador = AnalizadorSemantico()
    return analizador.analizar(ast)