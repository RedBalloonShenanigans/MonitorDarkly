PAYLOADS=$(patsubst %.s,%,$(wildcard *.s))

all: $(PAYLOADS)

%.o: %.s
	as86 -1 -o $@ $<

$(PAYLOADS): %: %.o
	ld86 -o $@ $<

clean:
	rm -f $(PAYLOADS) *.o

.PHONY: all clean

