; .ORIG x3000

; HELLO:   .STRINGZ "Hello!"
; HELLO_ADDR:  .FILL x3000

; LD R0, HELLO_ADDR
; PUTS

; HALT


.ORIG x3000

        LEA R0, HELLO
        PUTS
        HALT

HELLO:  .STRINGZ "Hello!\n"




; 0xE022,  # TRAP x22 (PUTS) - print string
; 0xF025,  # TRAP x25 (HALT) - halt program
; 0x0048,  # 'H'
; 0x0065,  # 'e'
; 0x006C,  # 'l'
; 0x006C,  # 'l'
; 0x006F,  # 'o'
; 0x0000,  # null terminator