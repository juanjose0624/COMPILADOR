# Proyecto Final: Compilador

**Materia:** Compiladores
**Programa académico:** Ingeniería Informática

## Integrantes

* Juan Jose Sepulveda Alvarez
* Sebastian Sierra Velez
* Dayana Rosario

## 1. Descripción

Compilador en Python para un lenguaje sencillo con tipos `int`, `real` y `bool`. Recibe el texto de un programa y recorre cinco fases hasta producir un archivo en ensamblador educativo (`.asm`):

```text
texto fuente
   │  lexico.py
   ▼
tokens ── sintactico.py ──▶ AST ── semantico.py ──▶ AST con tipos + tabla de símbolos
                                                        │  generar_ir.py
                                                        ▼
                                          IR (cuádruplas) ── validador_ir.py
                                                        │  optimizador.py
                                                        ▼
                                              IR optimizada ── generador.py ──▶ programa_generado.asm
```

Cada fase solo usa lo que produjo la anterior. Además, `ejecutor_ir.py` ejecuta la IR directamente para comprobar que el optimizador no cambia el comportamiento del programa.

## 2. El lenguaje

```text
programa    → sentencia*
sentencia   → declaracion | asignacion | salida
declaracion → ("int" | "real" | "bool") ID "=" expresion ";"
asignacion  → ID "=" expresion ";"
salida      → "print" "(" expresion ")" ";"
expresion   → termino (("+" | "-") termino)*
termino     → factor (("*" | "/") factor)*
factor      → NUM_INT | NUM_REAL | BOOL | ID | "(" expresion ")"
```

Reglas de tipos:

* Precedencia habitual y asociatividad izquierda (`10 - 3 - 2` es `(10 - 3) - 2`).
* `+`, `-`, `*`: el resultado es `real` si algún operando es `real`; si no, `int`.
* `/` siempre produce `real`.
* Se permite `int → real` (promoción implícita); no se permite `real → int`.
* `bool` no participa en operaciones aritméticas.
* Toda variable debe declararse (con valor inicial) antes de usarse y no puede declararse dos veces.
* La división por cero **no** es un error semántico: se detecta al ejecutar.

Límites del lenguaje: sin operadores unarios, comparaciones, condicionales, ciclos, funciones, cadenas ni bloques. El lexer ignora comentarios de línea que empiezan con `#` (extensión propia; no forma parte de la gramática anterior).

## 3. Estructura del proyecto

| Archivo | Función |
| --- | --- |
| `main.py` | Punto de entrada: pide el programa, ejecuta las fases, muestra resultados y guarda el `.asm`. |
| `tokens.py` | Clase `Token` (tipo, lexema, línea, columna). |
| `lexico.py` | Análisis léxico: texto → lista de tokens terminada en `EOF`. |
| `ast_nodos.py` | Nodos del árbol de sintaxis abstracta. |
| `sintactico.py` | Parser descendente recursivo: tokens → AST. |
| `semantico.py` | Tabla de símbolos, verificación de tipos y anotación `tipo_inferido`. |
| `ir_nodos.py` | `Cuadrupla`, operandos (`Constante`, `Temporal`, `Variable`) y `ProgramaIR`. |
| `generar_ir.py` | AST tipado → cuádruplas. |
| `validador_ir.py` | Comprueba el contrato de la IR. |
| `optimizador.py` | Optimizaciones locales seguras sobre la IR. |
| `ejecutor_ir.py` | Ejecuta la IR y compara ejecuciones. |
| `generador.py` | IR → ensamblador educativo (`.asm`). |
| `errores.py` | Excepciones por fase (`ErrorLexico`, `ErrorSintactico`, `ErrorSemantico`, `ErrorIR`). |
| `test/test_compilador.py` | 20 pruebas del analizador (sintáctico y semántico). |
| `pruebas_equivalencia.py` | 21 pruebas de equivalencia IR original vs IR optimizada. |

## 4. Requisitos y ejecución

* Python 3.10 o superior (se usó 3.13). El compilador usa solo la biblioteca estándar.

Ejecutar el compilador desde la carpeta raíz:

```bash
python main.py
```

El programa pregunta si el código se escribe en consola (termina con una línea `FIN`) o se carga desde un `.txt` (se puede pegar la ruta con comillas). También acepta la ruta como argumento: `python main.py programa.txt`.

Ejemplo de entrada y salida esperada:

```text
int cantidad = 3;
real total = cantidad * 2.5;
int x = 2 + 3 * 4;
print(total);
print(x);
```

Muestra el AST, la IR generada (17 instrucciones), la IR optimizada (10), la verificación de equivalencia, la salida simulada del programa (`7.5` y `14`), la memoria final y el ensamblador. El archivo `programa_generado.asm` se guarda en la carpeta desde la que se ejecuta.

Ejecutar las pruebas:

```bash
python test/test_compilador.py
python pruebas_equivalencia.py
```

Los módulos pueden importarse sin ejecutar la demostración: `main.py` solo corre bajo `if __name__ == "__main__"`.

## 5. Interfaces de cada módulo

| Función | Recibe | Devuelve |
| --- | --- | --- |
| `analizar_lexico(texto)` | `str` | `list[Token]` (último token `EOF`) |
| `analizar_sintaxis(tokens)` | lista de tokens | `Programa` (AST) |
| `analizar_semantica(ast)` | `Programa` | `ResultadoSemantico`: `ast`, `tabla_simbolos` (nombre → tipo) y `ubicaciones` (nombre → línea, columna); cada expresión queda con `tipo_inferido` |
| `generar_ir(ast, tabla)` | AST tipado y tabla | `list[Cuadrupla]` (`generar_programa_ir` devuelve un `ProgramaIR`) |
| `validar_ir(cuadruplas, simbolos=None)` | IR | `True` o lanza `ErrorIR` |
| `optimizar_ir(cuadruplas, simbolos=None)` | IR | IR optimizada (no modifica la original) |
| `generar_codigo(cuadruplas, tabla)` | IR y tabla | texto `.asm` (`generar_codigo_detallado` agrega mapas de líneas y nombres) |
| `ejecutar_ir(cuadruplas)` | IR | `ResultadoEjecucion`: salidas, memoria final, fallo, instrucciones ejecutadas |
| `equivalentes(a, b)` | dos ejecuciones | `(bool, motivos)` |

### Contrato de la IR

Cada instrucción es una cuádrupla `(op, arg1, arg2, resultado, tipo, linea)`. Operaciones: `CONST`, `LOAD`, `COPY`, `I2F`, `ADD`, `SUB`, `MUL`, `DIV`, `STORE`, `PRINT`.

* Cada temporal se define una sola vez y antes de usarse; su nombre no choca con el de una variable.
* Las variables solo se leen con `LOAD` y se escriben con `STORE`.
* En una operación, ambos operandos tienen el tipo de la operación; `DIV` siempre es `real` y `I2F` convierte `int` a `real`.
* `bool` solo aparece en `CONST`, `LOAD`, `COPY`, `STORE` y `PRINT`.
* Toda instrucción conserva la línea del programa fuente.

Ejemplo (`real total = cantidad * 2.5;`):

```text
t2 = load int cantidad
t3 = const real 2.5
t4 = i2f real t2
t5 = mul real t4, t3
store real total, t5
```

### Formato de errores

Todos los errores heredan de `ErrorCompilador` y informan fase, línea, columna (la IR no tiene columna) y mensaje. `main.py` los captura y muestra sin traceback.

## 6. Optimizador: transformaciones y justificación

El optimizador valida la IR de entrada, aplica los pases, revalida y **repite hasta que no haya cambios, con un tope de 10 iteraciones**.

| Transformación | Cuándo se aplica | Por qué es segura | Qué se evita |
| --- | --- | --- | --- |
| Propagación de constantes | Un temporal definido por `CONST` se usa en otra instrucción. | Los temporales se definen una vez y no cambian. | Nunca se propaga el valor de una **variable**: puede haber cambiado con un `STORE`. |
| Propagación de copias | `t2 = copy t1` | `t1` conserva su valor siempre. | — |
| `COPY` de constante → `CONST` | Tras propagar, la copia ya es una constante. | Mismo valor. | — |
| Plegado de constantes | `ADD`, `SUB`, `MUL` y `DIV` con ambos operandos constantes. | El resultado es el mismo que calcularía la máquina. | No se pliega si el divisor es 0, si un entero supera 4096 bits o si un real no es finito: el error debe verse al ejecutar. `I2F` nunca se pliega. |
| Eliminación de código muerto | Un `CONST`, `COPY` o `LOAD` cuyo temporal no se usa (recorrido hacia atrás). | No tienen efectos ni pueden fallar. | No se eliminan `ADD/SUB/MUL/DIV/I2F` (pueden fallar), `STORE` ni `PRINT`. |

### Equivalencia comprobada

`pruebas_equivalencia.py` ejecuta 20 programas con `ejecutor_ir.py`, antes y después de optimizar, y compara salidas, memoria final y el error (clase y línea). Resultado: 21/21 pruebas correctas (la última es una prueba negativa que comprueba que un optimizador defectuoso sí sería detectado). Los programas cubren precedencia, promoción, reasignación, constantes plegables, división por cero, enteros fuera de rango, reales desbordados y conversión imposible a real.

### Contraejemplos de optimización insegura

1. **Propagar una variable.** En `int x = 2; int a = x; x = 9; int b = x;` reemplazar el segundo `LOAD x` por el valor 2 haría que `b` valga 2 en lugar de 9. Por eso solo se propagan temporales.
2. **Eliminar una división sin uso.** En `real x = 10 / 0; print(1);` quitar la división como "código muerto" haría que el programa imprima `1` en vez de fallar en la línea 1.

Ambos casos están en las pruebas de equivalencia.

## 7. Generación de código

Estrategia sencilla y correcta primero: para cada instrucción IR se carga el primer operando en `R0`, el segundo en `R1`, se opera y el resultado se guarda en la celda propia del temporal.

* Constantes: `MOV Rn, #valor` (los reales conservan el punto: `#2.0`; `bool` es `#1` o `#0`).
* `LD`/`ST` para celdas `int` y `bool`; `LDF`/`STF` para celdas `real`.
* `ADD SUB MUL` para enteros; `ADDF SUBF MULF DIVF` para reales; `I2F R0, R0` convierte.
* `PRINT` → `OUT R0`. El programa termina con `HALT`.
* Las variables se guardan en celdas `id1`, `id2`, …, para que nunca choquen con registros o mnemónicos; los temporales conservan su nombre (`t1`, `t2`, …).

## 8. Alcance y limitaciones

* El `.asm` generado **no se ha ejecutado en la máquina virtual del laboratorio** (la aplicación no estaba disponible). El comportamiento se comprobó ejecutando la IR con `ejecutor_ir.py`. Quedan por verificar en la máquina real detalles como los inmediatos negativos (`#-3`) y los reales en notación científica.
* Los enteros se limitan a 4096 bits y los reales a valores finitos, como en la máquina didáctica.
* Un error de ejecución (por ejemplo, dividir por cero) no se rechaza al compilar: el programa compila y falla al ejecutarse. `main.py` lo informa en la salida simulada.
* No se implementan optimizaciones globales, asignación de registros ni saltos.

## 9. Decisiones de diseño

* El parser no revisa tipos; el semántico anota `tipo_inferido` en cada expresión para que el generador de IR no repita la inferencia.
* La conversión `int → real` se decide al generar la IR (instrucción `I2F`), antes de elegir la operación del backend.
* La IR se valida antes y después de optimizar: una IR mal formada se rechaza, no se corrige.
* El optimizador copia la IR en lugar de modificarla, y ante la duda conserva la instrucción.

## 10. Conclusión

El proyecto implementa un compilador completo de cinco fases, desde el texto fuente hasta ensamblador educativo, con 20 pruebas del analizador y 21 pruebas de equivalencia que respaldan el comportamiento del optimizador.
