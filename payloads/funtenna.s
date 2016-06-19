

.text
export _main
 _main:

        #cli
zero:
        mov ax, #0
        mov bx, #0
abc:
        #mov [0xca1c], #0xfffe
        #mov [0xca1e], #0xffff
        #mov [0xca20], #0xffff
        #mov [0xca22], #0xffff
        #mov [0xca24], #0xffff
        mov [0xca26], #0xffff
        #and [0xca1c], #1
        #mov [0xca1e], #0
        #mov [0xca20], #0
        #mov [0xca22], #0
        #mov [0xca24], #0
        mov [0xca26], #0
        inc bx
        cmp bx, #10000
        jl abc
        mov bx, #0
        inc ax
        cmp ax, #300
        jl abc
one:
        mov ax, #0
        mov bx, #0
def:
        nop
        nop
        nop
        nop
        inc bx
        cmp bx, #10000
        jl def
        #jmp zero
        mov bx, #0
        inc ax
        cmp ax, #600
        jl def
        jmp zero


