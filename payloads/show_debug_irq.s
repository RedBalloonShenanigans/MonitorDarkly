old_int EQU 0x600
int_offset EQU 0x30
int_number EQU 12

.text
export _main

_main:
	pusha

	mov [0x3a5a], #0x0000

	# save interrupt
	mov ax, [int_offset]
	mov [old_int], ax
	mov ax, [int_offset+2]
	mov [old_int+2], ax

	# overwrite interrupt
	call get_redirect_address
	mov [int_offset], ax
	mov [int_offset+2], bx

	# enable irq method for breakpoint & set breakpoint range
	mov [0xd7c0], #0x11
	mov [0xd7c2], #0x0
	mov [0xd7c4], #0xf000

	# unmask interrupt in OCM
	or [0xc828], #0x0004

	# unmask interrupt in 186
	mov ax, [0xfa28]
	and al, #0xEF
	mov [0xfa28], ax

	# trigger
	mov [0xf000], #0x10

	# re-mask it
	and [0xc828], #0xFFFB
	mov [0xd7c0], #0x0000


	# restore old handler
	mov ax, [old_int]
	mov [int_offset], ax
	mov ax, [old_int+2]
	mov [int_offset+2], ax

	popa
	retf

get_redirect_address:
        call return_address
isr:
	pusha

	# show we were here
	mov [0x3a5a], #0xcafe

	# clear status register
	mov [0xc838], #0x0004
	
	# send EOI (end of interrupt)
	mov [0xfa22], #int_number
	popa
	iret
return_address:
        pop ax
        mov bx, cs  ; or #0?
        ret

