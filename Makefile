USER_DOCS = \
	web/templates/admin_doc.html \
	web/templates/problem_format_doc.html \
	web/templates/data_doc.html \
	web/templates/package_sample.html

.PHONY: all
all: judger2-sandbox-targets user-docs

.PHONY: help
help:
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@echo '  all                      Build all targets.'
	@echo '  user-docs                Build user documents.'
	@echo '  judger2-sandbox-targets  Build sandbox tools.'
	@echo '  clean                    Remove all generated files.'
	@echo '  clean-docs               Remove all generated user documents.'
	@echo '  help                     Show this help message.'
	@echo '  install                  Install systemd service files.'

.PHONY: user-docs
user-docs: $(USER_DOCS)

web/templates/admin_doc.html: docs/user/admin_doc.html
	@echo "{% extends 'base.html' %} {% set page='管理界面使用指南' %} {% block content %}" > '$@'
	@echo "<div class=\"card card-body\">" >> '$@'
	@cat $< >> '$@'
	@echo "</div>" >> '$@'
	@echo "{% endblock %}" >> '$@'

web/templates/problem_format_doc.html: docs/user/problem_format_doc.html
	@echo "{% extends 'base.html' %} {% set page='题面格式规范' %} {% block content %}" > '$@'
	@echo "<div class=\"card card-body\">" >> '$@'
	@cat $< >> '$@'
	@echo "</div>" >> '$@'
	@echo "{% endblock %}" >> '$@'

web/templates/data_doc.html: docs/user/data_doc.html
	@echo "{% extends 'base.html' %} {% set page='数据格式规范' %} {% block content %}" > '$@'
	@echo "<div class=\"card card-body\">" >> '$@'
	@cat $< >> '$@'
	@echo "</div>" >> '$@'
	@echo "{% endblock %}" >> '$@'

web/templates/package_sample.html: docs/user/package_sample.html
	@echo "{% extends 'base.html' %} {% set page='数据包样例' %} {% block content %}" > '$@'
	@echo "<div class=\"card card-body\">" >> '$@'
	@cat $< >> '$@'
	@echo "</div>" >> '$@'
	@echo "{% endblock %}" >> '$@'

docs/user/%.html.raw: docs/user/%.md
	pandoc '$<' -t html -o '$@'

docs/user/%.html: docs/user/%.html.raw
	sed 's/admin_doc.md/admin-doc/g;s/data_doc.md/data-doc/g;s/package_sample.md/package-sample/g;s/problem_format_doc.md/problem-format-doc/g' $< > $@

.PHONY: judger2-sandbox-targets
judger2-sandbox-targets:
	$(MAKE) -C judger2/sandbox

.PHONY: clean
clean: clean-docs
	$(MAKE) -C judger2/sandbox clean

.PHONY: clean-docs
clean-docs:
	@echo 'WARNING: This will remove the html file of user docs in web/!'
	@echo 'If you want to keep the documents on the web page available,'
	@echo 'you should execute `make user-docs` before using the web page.'
	rm -f $(USER_DOCS)
	rm -f docs/user/*.html
	rm -f docs/user/*.html.raw

.PHONY: install
install: etc/judger2.service etc/ojweb_uwsgi.service etc/ojweb.service \
         etc/scheduler2.service
	sudo install -Dt /usr/local/lib/systemd/system -m644 $^
