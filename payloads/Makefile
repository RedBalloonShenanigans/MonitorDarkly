PAYLOADS=grab_pixel \
	 memcpy \
	 sdram_read \
	 sdram_write \
	 transfer_clut \
	 exfil \
	 funtenna \
	 show_debug_irq \

all: $(PAYLOADS)

%.o: %.s
	as86 -1 -o $@ $<

$(PAYLOADS): %: %.o
	ld86 -o $@ $<

clean:
	rm -f $(PAYLOADS) *.o

.PHONY: all

