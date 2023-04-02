const max_len = 1048576;

$(function() {
    $("#code").keyup(function() {
        if (this.value.length > max_len) {
            swal("超过长度上限！", "最多提交" + max_len + "个字符", "error");
            this.value = this.value.substring(0, max_len);
        }
    });

    var submit_options = {
        beforeSerialize: function() {
            if ($("#lang").val() == "auto_detect") {
                var detected_type = "cpp";
                var tmp_code = $("#code").val();
                if (tmp_code.indexOf("http") == 0 || tmp_code.indexOf("git") == 0)
                    var detected_type = "git";
                else if (tmp_code.search("module") != -1 && tmp_code.search("endmodule") != -1)
                    var detected_type = "Verilog";
                $("#lang").val(detected_type);
            }
        },
        beforeSubmit: function() {
            $("input").attr("disabled", "disabled");
        },
        success: function(response_text) {
            if (response_text === "0") {
                swal("Success", "提交成功", "success");
                setTimeout(function() {
                    window.location.replace('/OnlineJudge/status');
                }, 500);
            } else
                swal("Oops", "提交失败，网络故障！", "error");
        }
    };
    $("#problem_submit_form").ajaxForm(submit_options);

    document.getElementById('submit-button').removeAttribute('disabled')
});
