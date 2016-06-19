.text
export _main

clut_high EQU 0xadad
clut_low EQU 0xacac

_main:
    pusha

    push #0x3c ;15 * 4
    push #0x100
    push #clut_high
    mov ax, #clut_low
    sub ax, #4
    push ax
    push #0
    push #1
    push #2
    call $F000:$0255
    add sp, #14

	popa
	retf
