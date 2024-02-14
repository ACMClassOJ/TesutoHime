// csrf
$.ajaxPrefilter(function (options) {
  if (/post/i.test(options.type)) {
    if (!options.headers) options.headers = {}
    options.headers['X-Acmoj-Is-Csrf'] = 'no'
  }
})
; (function () {
  var _fetch = fetch
  window.fetch = function fetch (...args) {
    if (
      args.length < 2 ||
      typeof args[1] !== 'object' ||
      !/post/i.test(args[1].method)
    ) {
      return _fetch(...args)
    }
    if (!args[1].headers) args[1].headers = {}
    args[1].headers['X-Acmoj-Is-Csrf'] = 'no'
    return _fetch(...args)
  }
})()


// popover
$("[data-toggle='popover']").popover().click(function () {
  setTimeout(() => $(this).popover('hide'), 2000)
})


// width toggle
const widthToggleEl = document.getElementById('width-toggle')
if (widthToggleEl) {
  let fullwidth = localStorage.fullwidth === 'true' ? true : false
  const containers = document.querySelectorAll('.container')
  const sync = () => {
    localStorage.fullwidth = String(fullwidth)
    for (const container of containers) {
      if (fullwidth) {
        container.classList.add('fullwidth')
      } else {
        container.classList.remove('fullwidth')
      }
    }
  }
  sync()
  widthToggleEl.addEventListener('click', () => {
    fullwidth = !fullwidth
    sync()
  })
}
