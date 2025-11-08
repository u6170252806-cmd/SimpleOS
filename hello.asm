; hello.asm
; it is listed in the file system of simpleOS when first boot
LOADI R0, 1           ; syscall 1 = WRITE
LOADI R1, 1           ; file descriptor 1 = stdout
LOADI R2, message     ; address of message
LOADI R3, 13          ; message length
SYSCALL R0            ; make system call
HALT                  ; exit

message:
.string "Hello, World!\n"
