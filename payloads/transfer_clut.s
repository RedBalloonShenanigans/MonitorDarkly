.text
export _main

clut_high EQU 0xadad
clut_low EQU 0xacac
max_colors EQU 256

_main:
    pusha

    push #max_colors * 4 ;15 * 4
    push #0x0       ; offset in the clut structure
    push #clut_high
    mov ax, #clut_low
    push ax
    push #0
    push #1
    push #2
    call $F000:$0255
    add sp, #14

	popa
	retf
