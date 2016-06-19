.text
export _main

dst_seg EQU 0xadad
dst_offset EQU 0xacac
src_seg EQU 0xabab
src_offset EQU 0xaeae
len EQU 0xafaf

_main:
    push bp
    mov bp, sp
    push ds
    push es
    push si
    push di

_setup_es_ds:
    mov ax, #dst_seg
    mov es, ax
    mov ax, #src_seg
    mov ds, ax

    mov si, #src_offset
    mov di, #dst_offset
    mov cx, #len
    shr cx, 1
    cld
    rep
    movsw

    pop di
    pop si
    pop es
    pop ds
    pop bp
    retf
