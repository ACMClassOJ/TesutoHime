const formRealnameCreate = document.getElementById('form-realname-create')
const buttonImportCsv = document.getElementById('import-csv')
const realnameInput = document.getElementById('realname-data')
const fileCsv = document.getElementById('file-csv')

buttonImportCsv.addEventListener('click', e => {
  e.preventDefault()
  fileCsv.click()
})

fileCsv.addEventListener('change', () => {
  const file = fileCsv.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.addEventListener('error', () => {
    alert('无法读取所选的文件')
  })
  reader.addEventListener('load', () => {
    const buf = reader.result
    const decoder = new TextDecoder('utf-8', { fatal: true })
    try {
      realnameInput.value = decoder.decode(buf).replace(/\r/g, '')
    } catch (e) {
      try {
        const decoder = new TextDecoder('gb18030', { fatal: true })
        realnameInput.value = decoder.decode(buf).replace(/\r/g, '')
      } catch (e) {
        alert('无法解码所选的文件，请检查文件使用的编码格式 (推荐使用 UTF-8 编码)。')
      }
    }
  })
  reader.readAsArrayBuffer(file)
})

const isIntegral = str => str && /^\d+$/.test(str)

formRealnameCreate.addEventListener('submit', e => {
  const value = realnameInput.value.trim()
  if (!value) {
    e.preventDefault()
    return
  }
  const lines = value.split('\n')
  for (const line of lines) {
    const cols = line.split(',')
    if (cols.length === 1) {
      if (line.includes('，')) {
        alert(`请使用西文逗号 ',' 而非中文逗号 '，'`)
      } else {
        alert(`学工号 '${line}' 没有对应的姓名`)
      }
      e.preventDefault()
      return
    }
    if (!isIntegral(cols[0])) {
      alert(`学工号 '${cols[0]}' 不是一个数${isIntegral(cols[1]) ? `；姓名 '${cols[1]}' 似乎是一个学号。您是否填反了学号和姓名的顺序？` : '，请检查您输入的数据。'}`)
      e.preventDefault()
      return
    }
  }
})
