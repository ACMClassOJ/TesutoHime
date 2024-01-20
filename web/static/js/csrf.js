$.ajaxPrefilter(function (options) {
  if (/post/i.test(options.type)) {
    if (!options.headers) options.headers = {}
    options.headers['X-Acmoj-Is-Csrf'] = 'no'
  }
})
