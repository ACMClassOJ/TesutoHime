CXXFLAGS += -Wall -O2

.PHONY: all
all: checker

.PHONY: clean
clean:
	rm -f checker

.PHONY: install
install: checker
	install -Dm755 checker /usr/bin/checker
