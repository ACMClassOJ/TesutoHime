USER_DOCS_SRCS = $(shell find docs/user -name '*.md')
USER_DOCS = $(subst docs/user,web/help,$(USER_DOCS_SRCS:.md=.html))

.PHONY: all
all: judger2-sandbox-targets user-docs

.PHONY: judger2
judger2: judger2-sandbox-targets judger2-checker

.PHONY: help
help:
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@echo '  all                      Build all targets.'
	@echo '  user-docs                Build user documents.'
	@echo '  judger2-sandbox-targets  Build sandbox tools.'
	@echo '  judger2-checker          Build checker.'
	@echo '  judger2                  Build all judger2 targets.'
	@echo '  clean                    Remove all generated files.'
	@echo '  clean-docs               Remove all generated user documents.'
	@echo '  clean-judger2            Remove all generated judger2 files.'
	@echo '  help                     Show this help message.'
	@echo '  install                  Install systemd service files.'

.PHONY: user-docs
user-docs: $(USER_DOCS)

$(USER_DOCS): web/help/%.html: docs/user/%.md
	pandoc '$<' -t html -o '$@' --columns=2147483647
	sed -i -E 's/\.md([#"])/\1/g' '$@'


.PHONY: judger2-sandbox-targets
judger2-sandbox-targets:
	$(MAKE) -C judger2/sandbox

.PHONY: judger2-checker
judger2-checker:
	judger2/checker/scripts/build

.PHONY: clean
clean: clean-docs clean-judger2

.PHONY: clean-judger2
clean-judger2:
	$(MAKE) -C judger2/sandbox clean
	judger2/checker/scripts/clean

.PHONY: clean-docs
clean-docs:
	@echo 'WARNING: This will remove the html file of user docs in web/!'
	@echo 'If you want to keep the documents on the web page available,'
	@echo 'you should execute `make user-docs` before using the web page.'
	rm -f $(USER_DOCS)

.PHONY: install
install: etc/judger2.service etc/ojweb_uwsgi.service etc/ojweb.service \
         etc/scheduler2.service
	sudo install -Dt /usr/local/lib/systemd/system -m644 $^
