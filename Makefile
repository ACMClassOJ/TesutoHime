USER_DOCS = \
	Web/templates/admin_doc.html \
	Web/templates/problem_format_doc.html \
	Web/templates/data_doc.html \
	Web/templates/package_sample.html

.PHONY: all
all: user-docs

.PHONY: user-docs
user-docs: $(USER_DOCS)

Web/templates/admin_doc.html: docs/user/admin_doc.html
	@echo "{% extends 'base.html' %} {% set page='管理界面使用指南' %} {% block content %}" > '$@'
	@echo "<div class=\"card card-body\">" >> '$@'
	@cat $< >> '$@'
	@echo "</div>" >> '$@'
	@echo "{% endblock %}" >> '$@'

Web/templates/problem_format_doc.html: docs/user/problem_format_doc.html
	@echo "{% extends 'base.html' %} {% set page='题面格式规范' %} {% block content %}" > '$@'
	@echo "<div class=\"card card-body\">" >> '$@'
	@cat $< >> '$@'
	@echo "</div>" >> '$@'
	@echo "{% endblock %}" >> '$@'

Web/templates/data_doc.html: docs/user/data_doc.html
	@echo "{% extends 'base.html' %} {% set page='数据格式规范' %} {% block content %}" > '$@'
	@echo "<div class=\"card card-body\">" >> '$@'
	@cat $< >> '$@'
	@echo "</div>" >> '$@'
	@echo "{% endblock %}" >> '$@'

Web/templates/package_sample.html: docs/user/package_sample.html
	@echo "{% extends 'base.html' %} {% set page='数据包样例' %} {% block content %}" > '$@'
	@echo "<div class=\"card card-body\">" >> '$@'
	@cat $< >> '$@'
	@echo "</div>" >> '$@'
	@echo "{% endblock %}" >> '$@'

docs/user/%.html.raw: docs/user/%.md
	pandoc '$<' -t html -o '$@'

docs/user/%.html: docs/user/%.html.raw
	sed 's/admin_doc.md/admin-doc/g;s/data_doc.md/data-doc/g;s/package_sample.md/package-sample/g;s/problem_format_doc.md/problem-format-doc/g' $< > $@

.PHONY: clean
clean:
	@echo 'WARNING: This will remove the html file of user docs in Web/!'
	@echo 'If you want to keep the documents on the web page available,'
	@echo 'you should execute `make user-docs` before using the web page.'
	rm -f $(USER_DOCS)
	rm -f docs/user/*.html
	rm -f docs/user/*.html.raw
