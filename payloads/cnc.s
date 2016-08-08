MAIN_INPUT_STATUS EQU 0xc832
IMP_H_ACT_START EQU 0xccdc
IMP_V_ACT_START_ODD EQU 0xcce0
IMP_CONTROL EQU 0xcc82
IMP_PIXGRAB_H EQU 0xce32
IMP_PIXGRAB_V EQU 0xce34
IMP_PIXGRAB_RED EQU 0xce36
IMP_PIXGRAB_GRN EQU 0xce38
IMP_PIXGRAB_BLU EQU 0xce3a
ODP_PIXGRAB_CTRL EQU 0xd6d8
ODP_PIXGRAB_H EQU 0xd6da
ODP_PIXGRAB_V EQU 0xd6dc

old_int EQU 0x5000
state EQU 0x5004
cur_size EQU 0x5006
length EQU 0x5008
old_blue_val EQU 0x500a
pixel_pos EQU 0x500c
buffer_offset EQU 0x0000
buffer_segment EQU 0x4000

int_number EQU 15

state_scanning EQU 0
state_get_length EQU 1
state_reading EQU 2
state_processing EQU 3

#h_offset EQU 0x2a2
#v_offset EQU 0x2aa
h_offset EQU 782
v_offset EQU 106 
width EQU 100

cmd_sram_start EQU 0xc000
cmd_sram_end EQU 0xc800
control_struct_size EQU 40

.text
export _main

_main:
	pusha
	push ds
	mov ax, #0
	mov ds, ax

	call init_cursor_tracking

	mov [state], #0
	mov [cur_size], #0
	mov [pixel_pos], #0

	# set pixel grab registers
	call set_pixel_pos
	# enable pixel grab
	or [IMP_CONTROL], #0x20

	# save interrupt, if we haven't already overwritten it
	cmp [int_number*4+2], #0
	beq overwrite_interrupt
	mov ax, [int_number*4]
	mov [old_int], ax
	mov ax, [int_number*4+2]
	mov [old_int+2], ax

	overwrite_interrupt:
	call get_isr_redirect_address
	mov [int_number*4], ax
	mov [int_number*4+2], bx

	overwrite_main_loop:
	# A0B1:02DA is normally "call jump_to_main_func"
	# our hook will do that instead
	# overwrite it with a long jump to our hook
	call get_main_loop_redirect_address
	mov cx, #0xa0b1
	mov ds, cx
	movb [0x02da], #0xEA ; long jump
	mov [0x02db], ax ; offset
	mov [0x02dd], bx ; segment

	pop ds
	popa
	retf

set_pixel_pos:
	mov ax, [IMP_H_ACT_START]
	add ax, #h_offset
	add ax, [pixel_pos]
	mov [IMP_PIXGRAB_H], ax
	mov ax, [IMP_V_ACT_START_ODD]
	add ax, #v_offset
	mov [IMP_PIXGRAB_V], ax
	ret


##############
# ISR
#
# This ISR is the "bottom-level" handler. It hooks the vsync interrupt, waiting
# for the right pixel value. It then scans across the screen, reading pixel
# values into the buffer. Each pixel is three consecutive bytes. The first two
# bytes are the signature (they must be R and G of the pixel), the next two are
# the length, and the rest are copied into the buffer and interpreted by the
# main loop hook.
##############

handle_pixel:
	push es

	# grab pixel value
	mov ax, [IMP_PIXGRAB_RED]
	shr ax, #2
	mov bx, [IMP_PIXGRAB_GRN]
	shr bx, #2
	mov ah, bl
	mov bx, [IMP_PIXGRAB_BLU]
	shr bx, #2

	# switch on the current state
	cmp [state], #state_scanning
	beq scan_pixel
	cmp [state], #state_get_length
	beq get_length
	cmp [state], #state_reading
	beq read_pixel
	
	# state == processing
	# we're waiting on the main loop, so just return
	ret

	scan_pixel:
	cmp ax, #0x6bac
	bne handle_pixel_end
	mov [state], #state_get_length
	inc [pixel_pos]
	mov [old_blue_val], bl
	jmp handle_pixel_end

	get_length:
	mov [length], ax
	mov [state], #state_reading
	inc [pixel_pos]
	jmp handle_pixel_end

	read_pixel:
	mov cx, #buffer_segment
	mov es, cx
	mov di, [cur_size]
	cmp [pixel_pos], #0
	bne read_whole_pixel

	; In the first pixel, blue alternates to tell us when we've gotten a
	; new value.
	read_first_pixel:
	cmp bl, [old_blue_val]
	beq handle_pixel_end
	mov [old_blue_val], bl
	eseg
	mov buffer_offset[di], ax
	add di, #2
	jmp read_pixel_end

	; In the next 2 pixels, R, G, and B are all data.
	read_whole_pixel:
	eseg
	mov buffer_offset[di], ax
	eseg
	mov [di+buffer_offset+2], bl
	add di, #3

	read_pixel_end:
	mov [cur_size], di
	inc [pixel_pos]
	cmp [pixel_pos], #3
	bne dont_reset_pos
	mov [pixel_pos], #0
	dont_reset_pos:
	cmp di, [length]
	jb handle_pixel_end

	done_reading:
	mov [state], #state_processing
	mov [cur_size], #0
	mov [pixel_pos], #0


	handle_pixel_end:
	call set_pixel_pos
	pop es
	ret


get_isr_redirect_address:
        call return_address
isr:
	pusha
	push ds
	mov ax, #0
	mov ds, ax
	# test for vsync event
	test [MAIN_INPUT_STATUS], #0x800
	jz isr_end

	call handle_pixel

	isr_end:
	pop ds
	popa
	jmp far [old_int]
return_address:
        pop ax
        mov bx, cs
        ret

#######
# Main loop handling.
# 
# This stage kicks in when the ISR says its state is "done". It reads the rest
# of the command. There are four commands, identified by the first byte:
# 0. Write memory
# 1. Read/copy memory
# 2. Write and execute
# 3. Display image
#
# All four commands take an address, which consists of the next 3 bytes
# (because of the 24-bit address space). The write and execute commands are
# followed by a number of bytes to write to that address.
#
# All commands are followed by a trailer, which serves to make sure we've got
# a valid packet.
#######

# takes in a 3-byte address, and turns it into a segment and offset.
# input is ax and dl, output is ax (offset) and dx (segment).
decode_address:
	mov dh, dl
	mov dl, ah
	mov ah, #0
	ret

# Handle the write part of the write and write+execute commands
handle_write:
	push es
	push ds
	mov cx, [length]
	mov es, dx
	mov si, #buffer_segment
	mov ds, si
	mov si, #buffer_offset+4
	mov di, ax
	sub cx, #6 ; 4 for type + address, plus 2 for trailer

	rep
	movsb

	pop ds
	pop es
	ret

handle_packet:
	push ds
	push es
	mov ax, #0
	mov ds, ax
	mov ax, #buffer_segment
	mov es, ax

	# check trailer
	mov bx, [length]
	eseg
	cmp [bx+buffer_offset-2], #0xcab6
	bne handle_packet_end
	
	eseg
	mov ax, [buffer_offset+1]
	eseg
	mov dl, [buffer_offset+3]
	call decode_address

	eseg
	cmpb [buffer_offset], #0
	beq write_mem
	eseg
	cmpb [buffer_offset], #1
	beq read_mem
	eseg
	cmpb [buffer_offset], #2
	beq execute
	eseg
	cmpb [buffer_offset], #3
	beq cmd_upload_image
	eseg
	cmpb [buffer_offset], #4
	beq cursor_pos
	jmp handle_packet_end ; ignore unknown packet types

	write_mem:
	call handle_write
	jmp handle_packet_end

	read_mem:
	#TODO
	jmp handle_packet_end

	execute:
	call handle_write
	mov cx, ax
	# cx has code IP, dx has code segment
	call get_execute_after_address
	# ax has return IP, bx has return segment
	push bx
	push ax
	push dx
	push cx
	; don't actually return, just jump to specified address, and set things
	; up so that "retf" will return to execute_after.
	; This gets around indirect call needing to store the address in memory,
	; and is similar to what gprobe does.
	retf

	get_execute_after_address:
	call return_address
	execute_after:
	jmp handle_packet_end

	cmd_upload_image:
	# upload_image expects source in si:ds
	mov si, #buffer_offset
	add si, #1 ; for type
	mov ax, #buffer_segment
	mov ds, ax
	call upload_image
	jmp handle_packet_end

	cursor_pos:
	eseg
	mov ax, [buffer_offset+1] ; x coord
	eseg
	mov bx, [buffer_offset+3] ; y coord
	call handle_updated_cursor_pos

	handle_packet_end:
	pop es
	pop ds
	ret

get_main_loop_redirect_address:
	call return_address
main_loop_hook:
	pusha
	# do we have a packet?
	cmp [state], #state_processing
	bne main_loop_end

	# let's do it!
	call handle_packet

	mov [state], #state_scanning

	main_loop_end:
	popa
	call $a000:$0193 ; jump_to_main_func


#######
# OSD Image handling
#
# This code uploads an image to the SDRAM and displays it. The format is flat,
# and is designed to be as easy to upload as possible. The creator does most
# of the work of creating the CLUT, creating the control structure, etc.
#######

clear_osd_cmd_sram:
	push ax
	push cx
	push di
	push es

	cld
	mov cx, #(cmd_sram_end - cmd_sram_start) / 2
	mov ax, #0
	mov es, ax
	mov di, #cmd_sram_start
	
	rep
	stosw

	pop es
	pop di
	pop cx
	pop ax
	ret

# data address is in ds:si, offset is in ax
write_osd_cmd_data:
	push es
	push cx
	mov cx, #0
	mov es, bx
	mov di, #cmd_sram_start
	add di, ax
	mov cx, #control_struct_size / 2
	cld

	rep
	movsw

	pop cx
	pop es
	ret

# the main entrypoint
# data address is in ds:si
upload_image:
	push es
	mov ax, #0
	mov es, ax
	call clear_osd_cmd_sram

	# first: clut
	mov ax, [si] ; clut offset
	mov bx, [si+2] ; clut size
	add si, #4

	push bx

	push bx
	push ax
	push ds
	push si
	push #0
	push #1
	push #2
	call $f000:$255 ; upload_sdram_table
	add sp, #14

	pop bx

	# advance si across clut
	add si, bx

	# next up: sdram

	mov ax, [si] ; sdram size
	mov bx, [si+2] ; height
	mov cx, [si+4] ; width
	mov dx, [si+6] ; stride

	add si, #8

	push ax

	push cx; have seen same as width
	push #0 ;
	push #0 ;
	push #0x0 ; may be expand
	push ds ; src_seg
	push si ; src_off
	push #0 ; sram_off
	push bx ; height
	push cx ; width
	push dx ; stride
	push #0 ; sdram_hi 
	push #0 ; sdram lo 
	call $f000:$de ; sdram_write
	add sp, #0x18

	pop ax

	add si, ax

	# finally, the control structure

	mov ax, [si]
	add si, #2
	call write_osd_cmd_data

	pop es
	ret


#######
# Cursor position handling
#
# For now, we just place the OSD positioning tooltip where we think the cursor
# is
#######

; initialization
init_cursor_tracking:
	or [ODP_PIXGRAB_CTRL], #1
	or [0xd6d8], #2
	or [0xd390], #0x200
	ret

; entrypoint for when we get the cursor position from the computer
; ax is x coordinate, bx is y coordinate
handle_updated_cursor_pos:
	mov cx, ax
	shr cx, #1
	mov [0xc078+26], cx
	mov [0xc078+36], bx
	add ax, #0x5d
	add bx, #0x1f
	mov [ODP_PIXGRAB_H], ax
	mov [ODP_PIXGRAB_V], bx
	ret

