const max_len = 1048576;

function detectLangage (code, languagesAllowed) {
    const defaultLanguage = languagesAllowed.includes('python') ? 'python' : languagesAllowed[0]
    const detectors = [
        [ 'git', /^(https?:\/\/|git)/i ],
        [ 'verilog', /endmodule/ ],
        [ 'cpp', /\([^)]*\)[^:{'"=]*{/ ],
    ]
    for (const [ language, re ] of detectors) {
        if (languagesAllowed.includes(language) && code.match(re)) return language
    }
    return defaultLanguage
}

$(function() {
    $("#code").keyup(function() {
        if (this.value.length > max_len) {
            swal("超过长度上限！", "最多提交" + max_len + "个字符", "error");
            this.value = this.value.substring(0, max_len);
        }
    });

    const form = document.getElementById('problem-submit-form')
    form.addEventListener('submit', function () {
        const el = document.querySelector('#lang')
        if (el.value == 'autodetect') {
            const languagesAllowed = Array.from(el.options).map(x => x.value).filter(x => x != 'autodetect')
            const code = document.querySelector('#code').value
            el.value = detectLangage(code, languagesAllowed)
        }
    })

    document.getElementById('submit-button').removeAttribute('disabled')
});
