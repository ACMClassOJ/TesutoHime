CC=stdenv/profiles/std/result/bin/gcc
CFLAGS=-O2 -Wall -Wextra

all: runner du nsjail stdenv
	strip runner

.PHONY: clean
clean:
	rm -f runner
	$(MAKE) -C stdenv clean

runner: runner.c stdenv
	$(CC) $(CFLAGS) $< -o $@

du:
	./build-du

nsjail:
	./build-nsjail

.PHONY: stdenv
stdenv:
	$(MAKE) -C stdenv
