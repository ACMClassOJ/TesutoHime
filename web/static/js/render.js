; {
  const attachmentsEl = document.querySelectorAll('li.attachment')
  let preprocess = src => src
  if (attachmentsEl.length > 0) {
    const attachments = {}
    for (const el of attachmentsEl) {
      const name = el.querySelector('.attachment__name').textContent
      attachments[name] = el.innerHTML.trim()
    }

    preprocess = src => src.replace(/\[attachment](.+?)\[\/attachment]/g, (_text, name) => {
      const attachment = attachments[name]
      if (attachment) return attachment
      const escapedName = name.replace(/[<>&"']/g, t => `&#${t.codePointAt(0)};`)
      return `<strong class="text-red">错误：题目附件 ${escapedName} 不存在</strong>`
    })
  }

  const sanitize = function (text) {
    return DOMPurify.sanitize(text, { FORCE_BODY: true })
  }
  const render = function (text) {
    return sanitize(marked(preprocess(text)))
  }

  const elementsToRender = document.querySelectorAll('script[language="text/markdown"]')
  for (const el of elementsToRender) {
    const div = document.createElement('div')
    div.classList.add('rendered')
    div.innerHTML = render(JSON.parse(el.innerHTML))
    el.parentElement.replaceChild(div, el)
  }

  renderMathInElement(document.body, {
    delimiters: [
      {left: "$$", right: "$$", display: true},
      {left: "$", right: "$", display: false},
      {left: "\\(", right: "\\)", display: false},
      {left: "\\begin{equation}", right: "\\end{equation}", display: true},
      {left: "\\begin{align}", right: "\\end{align}", display: true},
      {left: "\\begin{align*}", right: "\\end{align*}", display: true},
      {left: "\\begin{alignat}", right: "\\end{alignat}", display: true},
      {left: "\\begin{gather}", right: "\\end{gather}", display: true},
      {left: "\\begin{CD}", right: "\\end{CD}", display: true},
      {left: "\\[", right: "\\]", display: true},
    ],
  })
  hljs.initHighlighting()

  $("pre").wrap('<div class="code-wrapper" style="position: relative;"></div>')
  $("pre").each(function(index, element){
    $(this).find("code").eq(0).attr('id', 'code_highlighted_' + index);
    var copy_button = $('<button class="btn btn-primary btn-sm" style="position: absolute; top: 0; right: 0;">复制</button>');
    copy_button.attr('id', 'copy_button_' + index);
    copy_button.attr('data-clipboard-target', '#code_highlighted_' + index);
    copy_button.appendTo($(this));
    new ClipboardJS(document.getElementById('copy_button_' + index));
  })

  if (window.Han) {
    for (const el of document.querySelectorAll('.rendered')) {
      Han(el).render()
    }
  }

  for (const el of document.getElementsByClassName('card--contest__description')) {
      const rendered = el.querySelector('.rendered')
      if (!rendered) continue
      if (rendered.getBoundingClientRect().height > el.getBoundingClientRect().height + 1) {
          el.classList.add('truncated')
      }
  }
}
