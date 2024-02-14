$(function () {
    var ajaxForms = [ '#formRejudge', '#formRejudge2', '#formDisableJudge', '#formDisableJudge2', '#form-abort', '#form-abort-2' ]
    var ajaxButtons = [ '#btnRejudge', '#btnRejudge2', '#btnDisableJudge', '#btnDisableJudge2', '#btnAbortJudge', '#btnAbortJudge2' ]
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
