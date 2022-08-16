CC=gcc
CFLAGS=-O2 -Wall -Wextra

all: runner test mem du
	strip runner
	strip test
	strip mem

test: test.o
	ld test.o -o test
test.o: test.s
	as test.s -o test.o

clean:
	rm -f runner test test.o

du:
	./build-du
