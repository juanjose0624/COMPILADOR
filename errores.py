# errores.py
# Errores del compilador, uno por fase. Todos heredan de ErrorCompilador, así que main.py
# puede capturar la clase base y mostrar el diagnóstico sin imprimir un traceback.

from typing import Optional


class ErrorCompilador(Exception):
    """Excepción base para los errores del compilador."""

    def __init__(
        self,
        fase: str,
        linea: Optional[int],
        columna: Optional[int],
        mensaje: str,
    ):
        self.fase = fase
        self.linea = linea
        self.columna = columna
        self.mensaje = mensaje

        # La IR solo conoce la línea, no la columna: se muestra solo lo que existe.
        ubicacion = ", ".join(
            texto
            for texto in (
                f"Línea {linea}" if linea is not None else None,
                f"Columna {columna}" if columna is not None else None,
            )
            if texto
        )
        cabecera = f"[{fase.upper()}]"

        super().__init__(
            f"{cabecera} {ubicacion}: {mensaje}" if ubicacion else f"{cabecera} {mensaje}"
        )

    def diagnostico(self) -> str:
        """Formato común de diagnóstico de la guía: fase, línea, columna y mensaje."""
        campos = [
            ("fase", self.fase),
            ("linea", self.linea),
            ("columna", self.columna),
            ("mensaje", self.mensaje),
        ]
        return "\n".join(f"{nombre}: {valor}" for nombre, valor in campos if valor is not None)


class ErrorLexico(ErrorCompilador):
    """Representa errores durante el análisis léxico."""

    def __init__(self, linea: int, columna: int, mensaje: str):
        super().__init__("lexico", linea, columna, mensaje)


class ErrorSintactico(ErrorCompilador):
    """Representa errores durante el análisis sintáctico."""

    def __init__(self, linea: int, columna: int, mensaje: str):
        super().__init__("sintactico", linea, columna, mensaje)


class ErrorSemantico(ErrorCompilador):
    """Representa errores durante el análisis semántico."""

    def __init__(self, linea: int, columna: int, mensaje: str):
        super().__init__("semantico", linea, columna, mensaje)


class ErrorIR(ErrorCompilador):
    """Representa un incumplimiento del contrato de la representación intermedia.

    La IR solo conserva la línea de origen, por eso no recibe columna.
    Un ErrorIR producido por el optimizador indica un defecto del optimizador."""

    def __init__(self, mensaje: str, linea: Optional[int] = None):
        super().__init__("ir", linea, None, mensaje)