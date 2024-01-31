$.fn.serializeObject = function () {
    let data = {};
    this.serializeArray().forEach(function (e) {
        if (e.value !== "")
            data[e.name] = e.value;
    });
    return data;
}

let op;
$(function () {
    document.querySelector('#form-jump-problem').addEventListener('submit', e => {
        e.preventDefault()
        const id = document.getElementById('problem-id').value
        if (id === '' || isNaN(id)) return
        location = `/OnlineJudge/problem/${id}/admin`
    })

    var ajaxForms = [ '#formRealname' ]
    var ajaxButtons = [ '#btnAddRealname' ]
    // disable when submit
    for (btn of ajaxButtons) {
        $(btn).attr('onclick', 'setTimeout(() => this.disabled = true)');
    }
    for (form of ajaxForms) {
        $(form).ajaxForm(function (ret_json) {
            if(ret_json['e'] < 0)
                swal("Error " + ret_json['e'], ret_json['msg'], "error");
            else
                swal("Success", ret_json['msg'], "success");
            // enable when receive
            for (btn of ajaxButtons) {
                $(btn).removeAttr('disabled');
            }
        });
    }
});

