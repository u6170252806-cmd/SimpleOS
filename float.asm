; float.asm
; Calculate area of circle (πr²)
; it is listed in the simple os file system when first boot
LOADI R0, 3.14159     ; π
LOADI R1, 5.0         ; radius
FMUL R0, R1           ; π * r
FMUL R0, R1           ; π * r * r
HALT
