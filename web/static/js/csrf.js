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
