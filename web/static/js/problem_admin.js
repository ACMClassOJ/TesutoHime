$.fn.serializeObject = function () {
    const data = {}
    this.serializeArray().forEach(function (e) {
        data[e.name] = e.value
    })
    return data
}

const getUrl = name => document.querySelector(`link[rel='${name}']`).href

const uploadData = async (file, progressBar) => {
    try {
        const res = await fetch(getUrl('upload-url'))
        if (res.status !== 200) {
            swal('Error', '无法获取上传链接', 'error')
            return
        }
        const url = (await res.text()).trim()

        const xhr = new XMLHttpRequest()
        progressBar.value = 0
        xhr.open('PUT', url, true)
        xhr.upload.onprogress = xhr.onprogress = event => {
            const progress = event.loaded / event.total
            progressBar.value = progress
        }
        xhr.onreadystatechange = async () => {
            if (xhr.readyState !== 4) return
            if (xhr.status === 413) {
                swal('Error', '您选择的数据包过大。一般情况下，请不要使用大文件来卡 log 的复杂度。如果您确实需要上传如此大的数据包，请联系 OJ 运维组。', 'error')
                return
            }
            if (xhr.status !== 200) {
                swal('Error', `未知错误: ${xhr.status}`, 'error')
                return
            }
            progressBar.removeAttribute('value')
            try {
                const res = await fetch(getUrl('update-plan'), { method: 'POST' })
                if (res.status !== 200) {
                    swal('Error', `未知错误: ${res.status}`, 'error')
                    return
                }
                const msg = await res.text()
                if (msg !== 'ok') {
                    swal('Error', msg, 'error')
                    return
                }
                swal('Success', msg, 'success');
            } finally {
                progressBar.value = 0
            }
        }
        xhr.onerror = event => {
            swal('Error', `未知错误: ${event}`, 'error')
        }
        xhr.send(file)
    } catch (e) {
        swal('Error', `未知错误: ${e}`, 'error')
    }
}


$(() => {
    // overview
    const updateDisplayTitle = () => document.querySelector('.problem__title').textContent = $('#iptTitle').val()
    $('#iptTitle').on('change', updateDisplayTitle)
    $('#iptTitle').on('keyup', updateDisplayTitle)

    // description
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        editormd.defaults.theme = 'dark'
        editormd.defaults.previewTheme = 'dark'
        editormd.defaults.editorTheme = 'pastel-on-dark'
    }

    const editors = {}
    function new_or_modify_content_in_editormd(editormd_name, content) {
        editors[editormd_name] = editormd(editormd_name, {
            width: '100%',
            height: 400,
            path: getUrl('editor.md-lib'),
            toolbarIcons: () => [
                'undo', 'redo', '|',
                'bold', 'del', 'italic', 'quote', '|',
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6', '|',
                'list-ul', 'list-ol', 'hr', '|',
                'link', 'reference-link', 'image', 'code', 'preformatted-text', 'code-block', 'table', 'html-entities', 'pagebreak', '|',
                'watch', 'preview', 'fullscreen', 'clear', 'search', '||',
                'help', 'info',
            ],
            markdown: content,
            autoFocus: false,
            placeholder: '支持 Markdown 及 HTML 格式，支持留空。',
            codeFold: true,
            searchReplace: true,
            htmlDecode: 'style,script,iframe|onclick,title,onmouseover,onmouseout,style',
            taskList: true,
            tocm: false,
            tex: false,
            flowChart: false,
            sequenceDiagram: false,
            atLink: false,
            emailLink: true,
            pageBreak: true
        })
    }

    // example container IDs
    const Examples = {
        examples: [],
        nextExample: 0,
        el: document.getElementById('examples-container'),
        clear () {
            this.examples = []
            this.el.innerHTML = ''
        },
        add (obj) {
            const id = `example-${this.nextExample++}`
            this.examples.push(id)

            const el = document.createElement('div')
            el.id = id
            el.classList.add('card', 'card-body', 'mb-3', 'border-grey')
            el.innerHTML =
`
<div class="mb-3">
    <label for="${id}-name">样例名称</label>
    <input class="example__name form-control" type="text" id="${id}-name" placeholder="可不填">
</div>
<div class="row">
    <div class="col-md-6 mb-3">
        <label for="${id}-input">输入</label>
        <textarea class="example__input form-control" rows="5" id="${id}-input" placeholder="请仅填写输入内容，解释性文本在下方描述处填写"></textarea>
    </div>
    <div class="col-md-6 mb-3">
        <label for="${id}-output">输出</label>
        <textarea class="example__output form-control" rows="5" id="${id}-output" placeholder="请仅填写输出内容，解释性文本在下方描述处填写"></textarea>
    </div>
</div>
<label for="${id}-description">样例描述<i class="fab fa-markdown ml-2" title="Markdown 格式"></i></label>
<div class="example__description" id="${id}-description">
    <textarea style="display: none"></textarea>
</div>
<div>
    <button class="example__delete btn btn-outline-primary float-right">删除样例</button>
</div>
`

            const getChild = name => el.querySelector(`.example__${name}`)
            for (const field of [ 'name', 'input', 'output' ]) {
                getChild(field).value = obj[field] || ''
            }
            const descriptionEl = getChild('description')
            setTimeout(() => new_or_modify_content_in_editormd(descriptionEl.id, obj.description || ''), 100)
            getChild('delete').addEventListener('click', e => {
                e.preventDefault()
                if (!confirm('确认删除样例？')) return
                this.delete(id)
            })

            this.el.appendChild(el)
        },
        delete (id) {
            const el = document.getElementById(id)
            el.parentElement.removeChild(el)
            this.examples = this.examples.filter(x => x !== id)
        },
        getName (id) {
            return document.getElementById(id).querySelector('.example__name').value
        },
        setName (id, content) {
            document.getElementById(id).querySelector('.example__name').value = content
        },
        exportOne (id) {
            const el = document.getElementById(id)
            const getChild = name => el.querySelector(`.example__${name}`)
            const obj = {}
            for (const field of [ 'name', 'input', 'output' ]) {
                obj[field] = getChild(field).value || null
            }
            obj.description = getChild('description').querySelector('textarea').value || null
            return obj
        },
        export () {
            return this.examples.map(x => this.exportOne(x))
        },
    }
    document.getElementById('examples-add').addEventListener('click', e => {
        e.preventDefault()
        if (Examples.examples.length === 1) {
            if (!Examples.getName(Examples.examples[0])) {
                Examples.setName(Examples.examples[0], '样例 1')
            }
        }
        const name = Examples.examples.length === 0 ? '' : `样例 ${Examples.examples.length + 1}`
        Examples.add({ name })
    })

    document.getElementById('example-input-output-container').addEventListener('toggle', e => {
        if (e.currentTarget.open) {
            for (const el of e.currentTarget.getElementsByClassName('init_editormd')) {
                editors[el.id].recreate()
            }
        }
    })

    const reloadDescription = async () => {
        try {
            const desc = await (await fetch(getUrl('description'))).json()
            for (const el of document.getElementsByClassName('init_editormd')) {
                const key = el.querySelector('textarea').name
                new_or_modify_content_in_editormd(el.id, desc[key])
            }
            Examples.clear()
            for (const obj of desc.examples) {
                Examples.add(obj)
            }
        } catch (e) {
            alert(`无法获取题面，请刷新重试（${e}）`)
        }
    }
    document.getElementById('description-tab-btn').addEventListener('click', () => setTimeout(reloadDescription, 500))

    setInterval(function() {
        $('.markdown-body').each(function() {
            renderMathInElement(
                $(this)[0],
                {
                    delimiters: [
                        {left: '$$', right: '$$', display: true},
                        {left: '$', right: '$', display: false},
                        {left: '\\(', right: '\\)', display: false},
                    ],
                }
            )
        })
    }, 1000)

    $('#form-description').submit(function (e) {
        e.preventDefault()
        e.stopPropagation()
        const examples = Examples.export()
        Examples.clear()
        const data = $(this).serializeObject()
        data.examples = examples
        fetch(getUrl('description'), {
            method: 'put',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        }).then(res => {
            if (!res.ok) {
                swal(`Error ${res.status}`, res.statusText, 'error')
            } else {
                swal('Success', '', 'success')
            }
            reloadDescription()
        })
    })

    const descriptionFields = [
        ['description', '题目描述'],
        ['input', '输入格式'],
        ['output', '输出格式'],
        ['examples', '样例'],
        ['data_range', '数据范围'],
    ]

    const getTitle = () => document.querySelector('h1 .problem__title').textContent
    const importFromMarkdown = md => {
        md = md.replace(/\r\n/g, '\n')

        const messages = []
        let currentField = null
        let currentValue = []
        const record = {}
        /** @type {string[]} */
        const lines = md.trim().split('\n')

        const endField = () => {
            if (!currentField) return
            record[currentField[0]] = currentValue.join('\n').trim()
            currentField = null
            currentValue = []
        }

        const setField = line => {
            if (!/^##[^#]/.test(line)) return null
            const m = /^##\s*(.+)$/.exec(line)
            if (!m) return null
            const type = m[1]
            const field = descriptionFields.find(x => x[1] === type)
            if (!field) {
                messages.push([ 'warning', `未识别的二级标题：${type}` ])
                return null
            }

            if (currentField) {
                const newIndex = descriptionFields.indexOf(field)
                const currentIndex = descriptionFields.indexOf(currentField)
                if (newIndex === currentIndex || field[0] in record) {
                    messages.push([ 'error', `字段「${field[1]}」重复` ])
                } else if (newIndex < currentIndex) {
                    messages.push([ 'error', `字段「${field[1]}」应在「${currentField[1]}」之前` ])
                } else {
                    endField()
                }
            }

            messages.push([ 'info', `已解析字段「${field[1]}」` ])
            currentField = field
            return field
        }

        try {
            // the main part
            for (const line of lines) {
                // first line
                if (currentField === null) {
                    if (line.trim() === '') continue
                    if (/^##[^#]/.test(line)) {
                        const field = setField(line)
                        if (!field) {
                            throw new Error(`无法解析首行：${line}`)
                        }
                    } else if (/^#[^#]/.test(line)) {
                        const actual = line.substring(1).trim()
                        const expected = getTitle()
                        if (actual !== expected) {
                            messages.push([ 'warning', `题面标题「${actual}」与题目标题「${expected}」不匹配` ])
                        }
                    } else {
                        throw new Error(`无法解析首行：${line}`)
                    }
                    continue
                }

                if (!setField(line)) {
                    // not a field line
                    currentValue.push(line)
                }
            }

            endField()

            // parsing examples
            if ('examples' in record) {
                /** @type {string[]} */
                const lines = record.examples.split('\n')
                const examples = []
                let currentExample = {}
                let currentField = null
                let pending = false
                let currentValue = []

                const endField = () => {
                    let value = currentValue.join('\n')
                    if (currentField === 'description') {
                        value = value.trim()
                    } else {
                        if (value === '') value = null
                    }
                    if (currentField in currentExample) {
                        const name = currentExample.name || '（无名）'
                        messages.push([ 'error', `测试样例「${name}」中描述重复` ])
                    }
                    currentExample[currentField] = value
                    currentField = currentField === 'output' ? 'description' : null
                    pending = false
                    currentValue = []
                }

                const endExample = () => {
                    if (Object.keys(currentExample).length === 0) return
                    const name = currentExample.name || '（无名）'
                    if (!currentExample.input && !currentExample.output) {
                        messages.push([ 'warning', `测试样例「${name}」既没有输入也没有输出` ])
                    }
                    for (const key of [ 'name', 'input', 'output', 'description' ]) {
                        if (!currentExample[key]) {
                            currentExample[key] = null
                        }
                    }
                    messages.push([ 'info', `已解析样例「${name}」` ])
                    examples.push(currentExample)
                    currentExample = {}
                }

                const parseHeader = line => {
                    if (!/^####?[^#]/.test(line)) return null
                    const m = /^(####?)\s*(.+)$/.exec(line)
                    if (!m) return null
                    const lvl = m[1].length
                    const type = m[2]
                    const field = {
                        输入: 'input',
                        输出: 'output',
                    }[type]
                    if (lvl > 3 && !field) return null
                    if (currentExample.name && lvl === 3 && field) {
                        messages.push([ 'warning', `在样例「${currentExample.name}」中，输入/输出标题层级错误` ])
                    }
                    if (!currentExample.name && (Object.keys(currentExample).length > 0 || currentField) && !field) return null
                    // [ is field?, field or example title ]
                    return [ Boolean(field), field || type ]
                }

                for (const line of lines) {
                    if (currentField === 'input' || currentField === 'output') {
                        if (line.startsWith('```')) {
                            if (pending) {
                                pending = false
                            } else {
                                endField()
                            }
                        } else {
                            if (pending) {
                                if (/^[（(]?(无|null|none)[)）]?$/i.test(line.trim())) {
                                    pending = false
                                    endField()
                                } else if (line.trim() !== '') {
                                    messages.push([ 'error', `输入/输出前的垃圾行：${line}` ])
                                }
                            } else {
                                currentValue.push(line)
                            }
                        }
                        continue
                    }

                    // not inside input or output
                    const hdr = parseHeader(line)
                    if (!hdr) {
                        if (!currentField) {
                            if (line.trim() !== '') {
                                currentField = 'description'
                                currentValue.push(line)
                            }
                        } else {
                            currentValue.push(line)
                        }
                        continue
                    }
                    const [ isField, field ] = hdr
                    if (currentField) endField()
                    if (isField) {
                        currentField = field
                        pending = true
                    } else {
                        endExample()
                        currentExample.name = field
                    }
                }

                endField()
                endExample()

                if (examples.length > 1 && examples.some(x => !x.name)) {
                    messages.push([ 'warning', '有多组测试样例，但有的测试样例没有名称' ])
                }
                record.examples = examples
            } // 'examples' in record

            if (Object.keys(record).length === 0) {
                throw new Error('文件为空')
            }
        } catch (e) {
            messages.push([ 'error', String(e) ])
        }

        const showResult = () => {
            let icon = 'success'
            let title = '导入成功'
            if (messages.some(x => x[0] === 'warning')) {
                icon = 'warning'
                title = '导入部分成功'
            }
            if (messages.some(x => x[0] === 'error')) {
                icon = 'error'
                title = '导入失败'
            }

            const content = document.createElement('div')
            if (icon !== 'error') {
                content.innerHTML = '<p>请检查下方题面导入是否正确，<strong>并点击页面底部「保存」按钮</strong>以完成导入。</p><p>导入信息：</p>'
            }
            for (const msg of messages) {
                const p = document.createElement('p')
                if (msg[0] === 'warning') {
                    p.innerHTML = '<strong class="text-warning">警告：</strong>'
                } else if (msg[0] === 'error') {
                    p.innerHTML = '<strong class="text-danger">错误：</strong>'
                }
                const span = document.createElement('span')
                span.textContent = msg[1]
                p.appendChild(span)
                content.appendChild(p)
            }

            swal({ icon, title, content })
        }

        if (messages.some(x => x[0] === 'error')) {
            showResult()
            return
        }

        // modify DOM
        const descriptionForm = document.getElementById('form-description')
        for (const [ key, _name ] of descriptionFields) {
            if (key === 'examples') {
                Examples.clear()
                if (record.examples) {
                    for (const ex of record.examples) {
                        Examples.add(ex)
                    }
                }
                continue
            }
            const el = descriptionForm.querySelector(`textarea[name="${key}"]`).parentElement
            new_or_modify_content_in_editormd(el.id, record[key] || null)
        }

        showResult()
    }
    const descriptionImportInput = document.getElementById('description-import-input')
    document.getElementById('description-import').addEventListener('click', e => {
        e.preventDefault()
        descriptionImportInput.click()
    })
    descriptionImportInput.addEventListener('change', e => {
        e.preventDefault()
        const file = descriptionImportInput.files[0]
        descriptionImportInput.value = null
        if (!file) return
        const reader = new FileReader()
        reader.addEventListener('error', () => {
            alert('无法读取所选的文件')
        })
        reader.addEventListener('load', () => {
            importFromMarkdown(reader.result)
        })
        reader.readAsText(file)
    })

    const exportToMarkdown = () => {
        let md = `# ${getTitle()}\n\n`
        const formEl = document.getElementById('form-description')
        for (const [ key, name ] of descriptionFields) {
            if (key === 'examples') {
                const examples = Examples.export()
                if (examples.length > 0) {
                    md += `## ${name}\n\n`
                }
                for (const ex of examples) {
                    if (ex.name) md += `### ${ex.name}\n\n`
                    const headerLevel = ex.name ? '####' : '###'
                    if (ex.input || ex.output) {
                        const wrapCode = code => code ? '```\n' + code + '\n```' : '（无）'
                        md += `${headerLevel} 输入\n\n${wrapCode(ex.input)}\n\n`
                        md += `${headerLevel} 输出\n\n${wrapCode(ex.output)}\n\n`
                    }
                    if (ex.description) {
                        md += ex.description
                        md += '\n\n'
                    }
                }
                continue
            }
            const value = formEl.querySelector(`textarea[name="${key}"]`).value
            if (value.trim() !== '') {
                md += `## ${name}\n\n${value}\n\n`
            }
        }
        return md
    }
    document.getElementById('description-export').addEventListener('click', e => {
        e.preventDefault()
        const md = exportToMarkdown()
        const blob = new Blob([md], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const el = document.createElement('a')
        el.href = url
        el.download = 'description.md'
        el.click()
    })


    // data-gui
    function extract_limit() {
        let tableDetails = $('#tableDetails');
        let config = {};
        config['length'] = tableDetails.children().length;
        config['mem'] = [];
        config['time'] = [];
        config['disk'] = [];
        tableDetails.children().each(function (i, e) {
            let d = e.children;
            config['time'].push(parseInt(d[2].innerHTML.replace('<br>', '')));
            config['mem'].push(parseInt(d[3].innerHTML.replace('<br>', '')));
            config['disk'].push(parseInt(d[4].innerHTML.replace('<br>', '')));
        });
        return config;
    }

    function uploadLimit (limit) {
        fetch(getUrl('limit'), {
            method: 'put',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(limit),
        }).then(res => {
            if (!res.ok) {
                swal(`Error ${res.status}`, res.statusText, 'error')
            }
        })
    }

    function generateConfig() {
        let tableGroups = $('#tableGroups'), tableDetails = $('#tableDetails')
        const Groups = []
        tableGroups.children().each(function (i, e) {
            let d = e.children
            Groups.push({
                GroupID: Number(d[0].innerHTML.replace('<br>', '')),
                GroupName: d[1].innerHTML.replace('<br>', ''),
                GroupScore: Number(d[2].innerHTML.replace('<br>', '')),
                TestPoints: d[3].innerHTML.replace('<br>', '').split(',').map(Number),
            })
        })
        const Details = []
        tableDetails.children().each(function (i, e) {
            let d = e.children
            Details.push({
                ID: Number(d[0].innerHTML.replace('<br>', '')),
                Dependency: Number(d[1].innerHTML.replace('<br>', '')),
                TimeLimit: Number(d[2].innerHTML.replace('<br>', '')),
                MemoryLimit: Number(d[3].innerHTML.replace('<br>', '')),
                DiskLimit: Number(d[4].innerHTML.replace('<br>', '')),
                ValgrindTestOn: $(d[5]).find('input').is(':checked'),
            })
        });
        const spj = {}
        for (const key of [ 'Compile', 'Run', 'Check' ]) {
            spj[key] = $(`#ipt${key}Type`).val()
        }
        return JSON.stringify({
            Groups,
            Details,
            CompileTimeLimit: Number($('#iptCompileTime').val()),
            SPJ: spj,
            Scorer: 0,
        }, null, 2)
    }

    $('#btn-download-config').click(e => {
        e.preventDefault()
        const conf = generateConfig()
        const file = new Blob([ conf ], { type: 'application/json' })
        const url = URL.createObjectURL(file)
        const a = document.createElement('a')
        a.href = url
        a.download = 'config.json'
        a.click()
    })

    $('#btnAddGroupsRow').click(function () {
        let t = $('#tableGroups'), r = t.find('tr:last').clone(), td = r.children();
        if (!isNaN(td.eq(1).html())) {
            td.eq(1).html(parseInt(td.eq(1).html()) + 1);
        }
        if (!isNaN(td.last().html())) {
            td.last().html(parseInt(td.last().html()) + 1);
        }
        td.first().html(parseInt(td.first().html()) + 1);
        t.append(r);
    });
    $('#btnRemoveGroupsRow').click(function () {
        $('#tableGroups').children().last().remove();
    });
    $('#btnAddDetailsRow').click(function () {
        let t = $('#tableDetails'), r = t.find('tr:last').clone(), td = r.children();
        td.eq(1).html(parseInt(td.eq(1).html()) === parseInt(td.first().html()) - 1 && td.eq(1).html() !== '0' ? td.first().html() : 0);
        td.first().html(parseInt(td.first().html()) + 1);
        t.append(r);
    });
    $('#btnRemoveDetailsRow').click(function () {
        $('#tableDetails').children().last().remove();
    });
    $('#btnClearConfig').click(function () {
        $('#iptConfig').val('');
    });
    $('#formData').submit(function (e) {
        e.preventDefault()
        e.stopPropagation()
        uploadLimit(extract_limit())
        const zip = new JSZip();
        const folder = zip.folder(problemId);
        let data_files = $('#iptData')
        let description_md = $('#iptDescriptionMd')
        let spj = $('#iptSpj')
        // let config = $('#iptConfig');
        if (data_files.val() !== null && data_files.val() !== '') {
            data_files = data_files[0].files
            $(data_files).each(function (index, file) {
                folder.file(file.name, file)
            })
        }
        if (description_md.val() !== null && description_md.val() !== '') {
            description_md = description_md[0].files[0]
            folder.file(description_md.name, description_md)
        }
        if (spj.val() !== null && spj.val() !== '') {
            for (const file of spj[0].files) {
                folder.file(file.name, file)
            }
        }
        folder.file('config.json', generateConfig())
        zip.generateAsync({ type: 'blob' }).then(blob => {
            return uploadData(blob, document.getElementById('data-gui-progress'))
        })
    })

    const zipError = (message, doUpload) => {
        var jszip_error_text = document.createElement('p')
        jszip_error_text.innerHTML = message + '<br> 无法从压缩包中提取 config.json，因此无法更新网页上的时空磁盘限制（运行时）。'
                                             + '<br> 参考下方链接来测试压缩包是否符合规范。'
                                             + '<br> 此警告不会影响数据包上传与评测。'
                                             + '<br> 是否继续上传？'
        swal({
            icon: 'warning',
            title: '压缩包不符合规范',
            content: jszip_error_text,
            buttons: {
                test_zip: {
                  text: '测试链接',
                  value: 'test_zip',
                },
                cancel: true,
                confirm: true,
            },
            timer: 5000,
        }).then(value => {
            if(value == 'test_zip') {
                window.open('https://stuk.github.io/jszip/documentation/examples/read-local-file-api.html')
            } else if (value) {
                console.log(value)
                doUpload()
            }
        })
    }

    // data-zip
    $('#formDataZipUpload').submit(function (e) {
        e.preventDefault()
        e.stopPropagation()
        const file = $('#iptDataZipUpload').prop('files')[0]

        const doUpload = () => {
            const progressBar = document.getElementById('data-upload-progress')
            uploadData(file, progressBar)
        }

        JSZip.loadAsync(file).then(function (zip) {
            const filename = problemId + '/config.json'
            const config = zip.file(filename)
            if (!config) {
                zipError(`在 zip 文件中没有找到 ${filename}，是否使用了错误的题号或数据包？`, doUpload)
                return
            }
            config.async('string').then(function (config) {
                let config_json
                try {
                    config_json = JSON.parse(config)
                } catch (e) {
                    zipError(`无法解析 config.json: ${e}`, doUpload)
                    return
                }
                let limit_config = {}
                limit_config.length = config_json.Details.length
                limit_config.mem = []
                limit_config.time = []
                limit_config.disk = []
                limit_config.file = []
                config_json.Details.forEach(function (item) {
                    limit_config.time.push(item.TimeLimit)
                    limit_config.mem.push(item.MemoryLimit)
                    if('DiskLimit' in item) limit_config.disk.push(item.DiskLimit)
                    if('FileNumberLimit' in item) limit_config.file.push(item.FileNumberLimit)
                });
                uploadLimit(limit_config)
                doUpload()
            })
        }, e => zipError(e.message, doUpload))
    });


    // picbed
    $('#formPicUpload').submit(function (e) {
        e.preventDefault();
        e.stopPropagation();
        $('#btnPicUpload').attr('disabled', 'disabled');
        /** @type {File} */
        const image = document.getElementById('iptPicUpload').files[0]
        if (!image) return
        ; (async () => {
            try {
                if (!image.type.startsWith('image/')) {
                    throw new Error('不是图片')
                }
                if (image.size === 0) {
                    throw new Error('您正在上传一个空文件')
                }
                const urlRes = await fetch(getUrl('pic-url'), {
                    method: 'POST',
                    body: new URLSearchParams({
                        length: image.size,
                        type: image.type,
                    }),
                })
                if (urlRes.status === 413) {
                    throw new Error('文件过大')
                }
                if (urlRes.status !== 200) {
                    throw new Error('无法获取上传链接')
                }
                const url = (await urlRes.text()).trim()
                const res = await fetch(url, {
                    method: 'PUT',
                    body: image,
                    headers: { 'Content-Type': image.type },
                })
                if (res.status !== 200) {
                    throw new Error(`网络错误: ${res.status}`)
                }
                const displayUrl = new URL(url, location.href)
                displayUrl.search = ''
                var swal_content = document.createElement('p')
                swal_content.innerHTML = `
                    <img src="${displayUrl}" style="width: 33%"><br>
                    <pre id='swal_content_url'>${displayUrl}</pre>
                    <pre id='swal_content_html'>&lt;img src=&quot;${displayUrl}&quot; style=&quot;width: 100%&quot;&gt;</pre>
                `
                swal_config = {
                    title: '上传成功',
                    icon: 'success',
                    content: swal_content,
                    buttons: {
                        copy_url: {
                            text: '复制链接',
                            value: 'copy_url',
                            className: 'copy_url',
                            closeModal: false
                        },
                        copy_html: {
                            text: '复制html',
                            value: 'copy_html',
                            className: 'copy_html',
                            closeModal: false
                        },
                        close: {
                            text: '关闭',
                            value: 'close',
                        },
                    }
                }
                swal(swal_config)
                $('.swal-modal').css('width', '70%')
                document.getElementsByClassName('copy_url')[0].setAttribute('data-clipboard-target', '#swal_content_url')
                new ClipboardJS(document.getElementsByClassName('copy_url')[0])
                document.getElementsByClassName('copy_html')[0].setAttribute('data-clipboard-target', '#swal_content_html')
                new ClipboardJS(document.getElementsByClassName('copy_html')[0])
            } catch (e) {
                swal('Error', String(e), 'error')
            } finally {
                var upload_input_bar = $('#iptPicUpload');
                upload_input_bar.after(upload_input_bar.clone().val(''))
                upload_input_bar.remove()
                $('#btnPicUpload').removeAttr('disabled')
            }
        })()
    })

    // judge
    for (const id of ['#form-overview', '#form-rejudge', '#form-void', '#form-abort']) {
        $(id).ajaxForm(function (ret_json) {
            if (ret_json.e < 0) {
                swal('Error ' + ret_json.e, ret_json.msg, 'error')
            } else {
                swal('Success', ret_json.msg, 'success')
            }
        })
    }
})
