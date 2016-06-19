.text
export _main

reg_start EQU 0x3a5a
irom_start EQU 0xadad
offset EQU 0xacac
len EQU 6
_main:

pusha

mov ax, #0
mov ds, ax 
mov si, 0xd6d8
or si, #2
mov 0xd6d8, si

mov si, 0xd390
or si, #0x200
mov 0xd390, si

push #0x4000
push #0x24a ; vertical coord
push #0x50b ; horizontal coord
call $a7fa:$14
add sp, #6
popa
retf
