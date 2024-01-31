; {
  const contestTypeEl = document.querySelector('#contest-type')
  contestTypeEl.addEventListener('change', () => {
    const switches = [
      [true, false, true],
      [false, false, false],
      [true, false, true],
    ][contestTypeEl.value]
    ; ['#ranked', '#rank-penalty', '#rank-partial-score'].forEach((x, i) => {
      if (switches[i]) {
        document.querySelector(x).setAttribute('checked', 'checked')
      } else {
        document.querySelector(x).removeAttribute('checked')
      }
    })
  })
}
