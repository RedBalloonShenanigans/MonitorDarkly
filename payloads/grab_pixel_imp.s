.text
export _main

IMP_H_ACT_START EQU 0xccdc
IMP_V_ACT_START_ODD EQU 0xcce0
IMP_PIXGRAB_GRN EQU 0xce38
IMP_PIXGRAB_BLU EQU 0xce3a

x_coord EQU 0xacac
y_coord EQU 0xadad
mem_dump_addr EQU 0xaeae

_main:
	pusha

	push #0 ; rgb_channel (red)
	mov ax, #y_coord
	add ax, [IMP_V_ACT_START_ODD]
	push ax ; v_offset
	mov ax, #x_coord
	add ax, [IMP_H_ACT_START]
	push ax ; h_offset
	push #0 ; input_channel (IMP)
	call $a3df:$71bf ; grab_pixel_imp_ipp
	add sp, #8

	mov bx, #mem_dump_addr
	shr ax, #2
	mov [bx], ax ; red (return value)

	mov ax, [IMP_PIXGRAB_GRN]
	shr ax, #2
	mov [bx+2], ax

	mov ax, [IMP_PIXGRAB_BLU]
	shr ax, #2
	mov [bx+4], ax

	popa
	retf
