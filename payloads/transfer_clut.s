.text
export _main

clut_high EQU 0xadad
clut_low EQU 0xacac
clut_offset EQU 0xaeae
max_colors EQU 256

_main:
    pusha

    push #max_colors * 4 ;15 * 4
    push #clut_offset
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
