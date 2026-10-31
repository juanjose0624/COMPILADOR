; Codigo generado por el compilador (ensamblador educativo)
.data
; id1 = cantidad (int)
id1: .int 0
; id2 = total (real)
id2: .float 0.0
; id3 = x (int)
id3: .int 0
; Celdas auxiliares de los temporales de la IR
t2: .int 0
t4: .float 0.0
t5: .float 0.0
t11: .float 0.0
t12: .int 0
.text
    ; 1: store int cantidad, 3    ; linea 1
    MOV R0, #3
    ST id1, R0
    ; 2: t2 = load int cantidad    ; linea 2
    LD R0, id1
    ST t2, R0
    ; 3: t4 = i2f real t2    ; linea 2
    LD R0, t2
    I2F R0, R0
    STF t4, R0
    ; 4: t5 = mul real t4, 2.5    ; linea 2
    LDF R0, t4
    MOV R1, #2.5
    MULF R0, R0, R1
    STF t5, R0
    ; 5: store real total, t5    ; linea 2
    LDF R0, t5
    STF id2, R0
    ; 6: store int x, 14    ; linea 3
    MOV R0, #14
    ST id3, R0
    ; 7: t11 = load real total    ; linea 4
    LDF R0, id2
    STF t11, R0
    ; 8: print real t11    ; linea 4
    LDF R0, t11
    OUT R0
    ; 9: t12 = load int x    ; linea 5
    LD R0, id3
    ST t12, R0
    ; 10: print int t12    ; linea 5
    LD R0, t12
    OUT R0
    HALT
