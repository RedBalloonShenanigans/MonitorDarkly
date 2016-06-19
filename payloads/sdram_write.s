.text
export _main

src_sgment EQU 0xadad
src_off EQU 0xacac
height EQU 0xaeae
width EQU 0xafaf
stride EQU 0xbdbd
reg_hi EQU 0xbcbc
reg_lo EQU 0xbebe

_main:
    push bp
    mov bp, sp
    push si
    push ds

    push #width; have seen same as width
    push #0 ;
    push #0 ;
    push #0x0 ; may be expand
    push #src_sgment ; src_seg
    push #src_off ; src_off
    push #0 ; sram_off
    push #height ; height
    push #width ; width
    push #stride ; stride
    push #reg_hi ; sdram_hi 
    push #reg_lo ; sdram lo 
    call $f000:$de
    add sp, #0x18
    mov si, ax
    mov ax, #0
    mov ds, ax
    mov [0x600], si

    pop ds
    pop si
    pop bp
    retf
