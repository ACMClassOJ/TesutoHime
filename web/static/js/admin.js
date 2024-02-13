$.fn.serializeObject = function () {
    let data = {};
    this.serializeArray().forEach(function (e) {
        if (e.value !== "")
            data[e.name] = e.value;
    });
    return data;
}

document.querySelector('#form-jump-problem').addEventListener('submit', e => {
  e.preventDefault()
  const id = document.getElementById('problem-id').value
  if (id === '' || isNaN(id)) return
  location = `/OnlineJudge/problem/${id}/admin`
})

let op;
$(function () {
    $("#btnAddUser").click(function () {
        op = 0;
    });
    $("#btnModifyUser").click(function () {
        op = 1;
    });
    $("#formUser").submit(function (e) {
        e.preventDefault();
        e.stopPropagation();
        let data = $(this).serializeObject();
        data.type = op;
        console.log(data);
        $.ajax({
            type: "POST",
            contentType: "application/json",
            url: "/OnlineJudge/admin/user",
            dataType: "json",
            data: JSON.stringify(data),
            complete: function (ret) {
                var ret_json = JSON.parse(ret.responseText);
                if(ret_json['e'] < 0)
                    swal("Error " + ret_json['e'], ret_json['msg'], "error");
                else
                    swal("Success", ret_json['msg'], "success");
            }
        });
    });

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
