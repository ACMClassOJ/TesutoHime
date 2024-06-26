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
    const updateDisplayTitle = () => document.getElementById('problem-title').textContent = $('#iptTitle').val()
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
            tocm: true,
            tex: false,
            flowChart: true,
            sequenceDiagram: true,
            atLink: false,
            emailLink: true,
            pageBreak: true
        })
    }

    const reloadDescription = () => $.ajax({
        dataType: 'text',
        url: getUrl('description'),
        success: response_text => {
            const main_json = JSON.parse(response_text)
            new_or_modify_content_in_editormd('iptDescription', main_json['description'])
            new_or_modify_content_in_editormd('iptInput', main_json['input'])
            new_or_modify_content_in_editormd('iptOutput', main_json['output'])
            new_or_modify_content_in_editormd('iptExampleInput', main_json['example_input'])
            new_or_modify_content_in_editormd('iptExampleOutput', main_json['example_output'])
            new_or_modify_content_in_editormd('iptDataRange', main_json['data_range'])
        },
        error: () => alert('无法获取题面，请刷新重试'),
    })
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
        const data = $(this).serializeObject()
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
        let type = $('#iptSpjType');
        if (type.val() === '3') {
            swal('Error', 'scorers are not supported (for now)', 'error')
            throw new Error('invalid spj')
        }
        return JSON.stringify({
            Groups,
            Details,
            CompileTimeLimit: Number($('#iptCompileTime').val()),
            SPJ: Number(type.val()),
            Scorer: type.val() === '3' ? 1 : 0,
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
        let type = $('#iptSpjType')
        let spj = $('#iptSpj')
        let scorer = $('#iptScorer')
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
        if (type.val() === 1 || type.val() === 2 && spj.val() !== null && spj.val() !== '') {
            spj = spj[0].files[0]
            folder.file(spj.name, spj)
        }
        if (type.val() === 3 && scorer.val() !== null && scorer.val() !== '') {
            scorer = scorer[0].files[0]
            folder.file(scorer.name, scorer)
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
