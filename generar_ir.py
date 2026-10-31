# generar_ir.py
# Generador de IR: recorre el AST validado por el semántico en postorden y emite cuádruplas.
from ir_nodos import Constante, Variable, Temporal, Cuadrupla, ProgramaIR
from validador_ir import ErrorIR


class GeneradorIR:
    def __init__(self, tabla_simbolos=None):
        self.instrucciones = []
        self._contador_temp = 0
        # tabla_simbolos (opcional): dict nombre_variable -> tipo ("int", "real", "bool").
        # El generador también arma sus propias declaraciones mientras recorre, así que
        # funciona aunque no se le entregue la tabla.
        self.tabla_simbolos = dict(tabla_simbolos) if tabla_simbolos else {}
        self.declaraciones = {}
        self._reservados = set()

    def _nuevo_temporal(self) -> Temporal:
        # Un temporal nunca puede llamarse igual que una variable del programa
        # (el estudiante puede haber escrito `int t1 = 3;`): se saltan los nombres ocupados.
        while True:
            self._contador_temp += 1
            nombre = f"t{self._contador_temp}"
            if nombre not in self._reservados:
                return Temporal(nombre)

    def _tipo_variable(self, nombre, nodo):
        """Tipo declarado de una variable; si no se puede saber, falla en vez de adivinar."""
        tipo = (
            self.declaraciones.get(nombre)
            or self.tabla_simbolos.get(nombre)
            or getattr(nodo, "tipo_inferido", None)
        )
        if tipo is None:
            raise ErrorIR(f"No se conoce el tipo de la variable '{nombre}'.", nodo.linea)
        return tipo

    def generar(self, ast_programa) -> list:
        self.instrucciones = []
        self._contador_temp = 0
        self.declaraciones = {}
        # Nombres de variables del programa: las sentencias con `nombre` son declaraciones/asignaciones.
        self._reservados = set(self.tabla_simbolos) | {
            s.nombre for s in ast_programa.sentencias if hasattr(s, "nombre")
        }
        for sentencia in ast_programa.sentencias:
            self._visitar(sentencia)
        return self.instrucciones

    def _visitar(self, nodo):
        nombre_metodo = f"_visitar_{type(nodo).__name__}"
        metodo = getattr(self, nombre_metodo, self._error_visita)
        return metodo(nodo)

    def _error_visita(self, nodo):
        raise NotImplementedError(f"No hay método de visita para {type(nodo).__name__}")

    def _promover_a_real(self, valor, linea):
        """Emite una conversión I2F y devuelve el temporal con el valor real."""
        temp_conv = self._nuevo_temporal()
        self.instrucciones.append(Cuadrupla(
            op="I2F", arg1=valor, resultado=temp_conv, tipo="real", linea=linea
        ))
        return temp_conv

    def _visitar_Declaracion(self, nodo):
        val_expr, tipo_expr = self._visitar(nodo.inicializador)

        # Promoción implícita int -> real si el tipo declarado es real
        if nodo.tipo_declarado == "real" and tipo_expr == "int":
            val_expr = self._promover_a_real(val_expr, nodo.linea)
            tipo_expr = "real"

        var_destino = Variable(nodo.nombre)
        self.instrucciones.append(Cuadrupla(
            op="STORE", arg1=val_expr, resultado=var_destino,
            tipo=nodo.tipo_declarado, linea=nodo.linea
        ))
        # La variable existe desde aquí (después de generar su inicializador, igual que en el semántico).
        self.declaraciones[nodo.nombre] = nodo.tipo_declarado

    def _visitar_Asignacion(self, nodo):
        val_expr, tipo_expr = self._visitar(nodo.expresion)

        # El tipo del STORE es el de la variable destino, no el de la expresión.
        # El semántico ya validó compatibilidad y prohibió real -> int.
        tipo_destino = self._tipo_variable(nodo.nombre, nodo)

        if tipo_destino == "real" and tipo_expr == "int":
            val_expr = self._promover_a_real(val_expr, nodo.linea)

        var_destino = Variable(nodo.nombre)
        self.instrucciones.append(Cuadrupla(
            op="STORE", arg1=val_expr, resultado=var_destino,
            tipo=tipo_destino, linea=nodo.linea
        ))

    def _visitar_Salida(self, nodo):
        val_expr, tipo_expr = self._visitar(nodo.expresion)
        self.instrucciones.append(Cuadrupla(
            op="PRINT", arg1=val_expr, tipo=tipo_expr, linea=nodo.linea
        ))

    def _visitar_Binaria(self, nodo):
        izq_val, izq_tipo = self._visitar(nodo.izquierdo)
        der_val, der_tipo = self._visitar(nodo.derecho)

        # La división '/' siempre produce real en este lenguaje.
        # Si algún operando es real, la operación también es real.
        if nodo.operador == "/" or izq_tipo == "real" or der_tipo == "real":
            op_tipo = "real"
        else:
            op_tipo = izq_tipo

        # En una operación real, todo operando int se convierte antes.
        if op_tipo == "real":
            if izq_tipo == "int":
                izq_val = self._promover_a_real(izq_val, nodo.linea)
            if der_tipo == "int":
                der_val = self._promover_a_real(der_val, nodo.linea)

        resultado_temp = self._nuevo_temporal()
        op_map = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV"}
        op_ir = op_map.get(nodo.operador, "OP_DESCONOCIDA")

        self.instrucciones.append(Cuadrupla(
            op=op_ir, arg1=izq_val, arg2=der_val, resultado=resultado_temp,
            tipo=op_tipo, linea=nodo.linea
        ))

        return resultado_temp, op_tipo

    def _visitar_Literal(self, nodo):
        temp = self._nuevo_temporal()
        tipo = nodo.tipo_literal  # lo registró el parser; no se deduce con isinstance (bool es int en Python)
        self.instrucciones.append(Cuadrupla(
            op="CONST", arg1=Constante(nodo.valor, tipo), resultado=temp,
            tipo=tipo, linea=nodo.linea
        ))
        return temp, tipo

    def _visitar_Referencia(self, nodo):
        temp = self._nuevo_temporal()
        tipo = self._tipo_variable(nodo.nombre, nodo)
        self.instrucciones.append(Cuadrupla(
            op="LOAD", arg1=Variable(nodo.nombre), resultado=temp,
            tipo=tipo, linea=nodo.linea
        ))
        return temp, tipo


def generar_ir(ast_programa, tabla_simbolos=None) -> list:
    """Devuelve la lista de cuádruplas (compatible con validar_ir y optimizar_ir)."""
    generador = GeneradorIR(tabla_simbolos)
    return generador.generar(ast_programa)


def generar_programa_ir(ast_programa, tabla_simbolos=None) -> ProgramaIR:
    """Igual que generar_ir, pero devuelve un ProgramaIR con las declaraciones originales
    (nombre -> tipo), que el backend necesita para reservar memoria."""
    generador = GeneradorIR(tabla_simbolos)
    instrucciones = generador.generar(ast_programa)
    return ProgramaIR(declaraciones=dict(generador.declaraciones), instrucciones=instrucciones)