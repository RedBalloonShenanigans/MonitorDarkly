.text
export _main

reg_start EQU 0x3a5a
segment EQU 0xadad
offset EQU 0xacac
len EQU 6

_main:
	push bp
	mov bp, sp
	push es
	push si
	push di
	mov cx, #len
	mov dx, #segment
	mov ax, ds
	mov es, ax
	mov ds, dx
	mov di, #reg_start
	mov si, #offset
	rep 
	movsw
	mov ds, ax
	pop di
	pop si
	pop es
	pop bp
	retf
