int_adr EQU 0x0000 ;0xabab
our_int EQU 06500
lookup_base EQU 0x6504
int_table EQU 0x6004
old_int EQU 0x6000
first_int EQU 0x50
last_int EQU 0x50

mod_int EQU 0x30

baud_115200 EQU 136
baud_1000000 EQU 16
baudrate EQU baud_1000000

clut_high EQU 0x0000
clut_low EQU 0x7000

ram_start EQU 0
ram_end EQU 0x8000
clut_start EQU 0xF000
clut_end EQU 0xF800

.text
export _main
 _main:
        jmp near start_here
#=======================================================================
# This function takes one argument but not on the stack, in AH
# It also expects DS == 0 and modifies AX, BX and CX
# TIMING - Do not move this function!!!
#-----------------------------------------------------------------------
send_byte:
        cli
# 8-bit counter
        mov bx, #0
# Start bit
        mov [0xca1e], #0
        mov cx, #0
start:
        add cx, #1
        cmp cx, #baudrate
        jl  start
next:
        add     bx, #1
        shr     ah, 1
        jc      one
zero:
        mov [0xca1e], #0
        jmp done
one:
        mov [0xca1e], #0xffff
        jmp done
nothing:
        # For timing purposes
        nop
        nop
done:
# Hold bit
        mov cx, #0
hold:
        add cx, #1
        cmp cx, #baudrate
        jl  hold
        cmp bx, #8
        jl  next
# Stop bit
        mov [0xca1e], #0xffff
        mov cx, #0
stop:
        add cx, #1
        cmp cx, #baudrate * 4
        jl  stop
end_send_byte:
        sti
        ret
#=======================================================================
# This is a normal function function that prints a 0 terminated string
# arg[0] -> Lower address word
# arg[1] -> Upper address word
#-----------------------------------------------------------------------
print_string:
        push bp
        mov bp, sp
        pusha
        mov si, [bp+4]
        mov dx, [bp+6]
        mov es, dx
# Send this byte
continue:
        eseg
        movb ah, [si]
        inc si
        movb al, #0
        cmpb ah, #0
        je end_print_string
        call send_byte
        jmp continue
end_print_string:
        popa
        pop bp
        ret
#=======================================================================
# This is a normal function function that prints a new line
# No arguments required
#-----------------------------------------------------------------------
# This is a "fake" function, it doesn't do much
print_new_line:
        pusha
        movb ah, #0x0D
        call send_byte
        movb ah, #0x0A
        call send_byte
        popa
        ret
#=======================================================================
# This function prints a test string
#-----------------------------------------------------------------------
test_string:
        pusha
        # Always in CS = 0
        push #0
        call skip_this
.asciz  "Test!"
skip_this:
        call print_string
        add sp, #4
        call print_new_line
        popa
        ret
#=======================================================================
# This function prints does a hex dump in ASCII mode
# arg[0] -> Lower start address word
# arg[1] -> Lower end address word
# arg[2] -> Upper address word for both
#-----------------------------------------------------------------------
hex_dump:
        push bp
        mov bp, sp
        pusha
        mov dx, #0
        mov ds, dx
        # Start at high
        mov [0xca1e], #0xffff
        mov di, #0
        mov dx, [bp+8]
        mov si, [bp+4]
        mov es, dx
next_byte:
        eseg
        movb al, [si]
        # Do the upper nibble first
        shrb al, #4
        movb ah, #0
to_ascii:
        cmp al, #10
        jl number
letter:
        addb al, #0x37
        jmp verify
number:
        addb al, #0x30
verify:
        cmpb ah, #0
        jne print_it
        shl ax, #8
        eseg
        movb al, [si]
        # Now the lower nibble
        andb al, #0x0F
        jmp to_ascii
print_it:
        cmp di, #64
        jl go_hex
        mov di, #0
        push ax
        call print_new_line
        pop ax
go_hex:
        inc di
        call send_byte
        shl ax, #8
        call send_byte
        movb ah, #0x20
        call send_byte
        inc si
        cmp si, [bp+6]
        jne next_byte
        call print_new_line
end_hex_dump:
        popa
        pop bp
        ret
#=======================================================================
# This function 
#-----------------------------------------------------------------------
hijack:
        push bp
        mov bp, sp
        pusha
        call get_redirect_address
        # Now let's modify the firmware
        # Call $F000:0252 == 9A 52 02 00 F0
        # And we want 9A XX XX YY YY where X is now BX and Y is this DS
        # Start the loop
        mov dx, #0xA000
        mov ds, dx
        mov si, #0
keep_going:
        movb cl, [si]
        cmpb cl, #0x9A
        jne increment
        mov cx, [si+1]
        cmp cx, #0x252
        jne increment
        mov cx, [si+3]
        cmp cx, #0xF000
        jne increment
        mov [si+1], ax
        mov [si+3], bx
increment:
        inc si
        cmp si, #0x100
        jne keep_going
        mov si, #0
        inc dx
        mov ds, dx
        cmp dx, #0xB800
        jne keep_going
        popa
        pop bp
        ret
#=======================================================================
# This function will modify ax and bx to insert respectively the least 
# significant address and most significant address bytes of the function
# thant follows
#-----------------------------------------------------------------------
get_redirect_address:
        call return_address
this_function:
        #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        # Stuff goes here
        push bp
        mov bp, sp
        pusha
        
        call test_string
        
        popa
        iret
        retf
        #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
return_address:
        pop ax
        mov bx, cs  ; or #0?
        ret
#***********************************************************************
# Code starts here....
#***********************************************************************
start_here:
        pusha

        push #0x3c ;15 * 4
        push #0x100
        push #clut_high
        push #clut_low - 4
        push #0
        push #1
        push #2
        call $F000:$0255
        add sp, #14

	call test_string

	popa
	retf

        mov cx, #0
        mov ds, cx
        
        # Preserve old interrupt
        mov cx, [mod_int]
        mov dx, [mod_int+2]
        
        call get_redirect_address
        mov [mod_int], ax
        mov [mod_int+2], bx
        
        # Set breakpoint range
        mov [0xd7c2], #0x0
        mov [0xd7c4], #0xf000
        # Enable interrupt
        mov [0xd7c0], #0x11
	# unmask interrupt
	or [0xc828], #0x0004
        
        # Trigger change
        mov [0xf000], #10
        
        # Disable interrupt
        mov [0xd7c0], #0
        
        # Restore
        mov [mod_int], cx
        mov [mod_int+2], dx
        
        call test_string
        
        popa
        retf

        jmp interrupt
        pusha
        
        mov cx, #0
        mov ds, cx
        #mov [0x5000], #0xAA
        
        mov [0xd7c0], #0x11
        #mov [0xd7c0], #0x09
        mov [0xd7c2], #0x0
        mov [0xd7c4], #0xf000
        #mov [0xd7c4], #0x04a0
        mov [0xd7c6], #0x0
        mov [0xd7c8], #0x5000
        
        call test_string
        push #0x0000
        push #0x1000
        push #0x0000
        call hex_dump
        add sp, #6

        popa
        retf

interrupt:
        call test_string
        iret
        




        # End flag
        nop
        nop
        nop
        nop
        nop
        nop
        nop
        nop
