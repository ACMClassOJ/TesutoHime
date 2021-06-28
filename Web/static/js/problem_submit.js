const max_len = 65536;

$(function () {
    $("#shared").change(function () {
        localStorage.setItem("share", $(this).is(":checked"));
        console.log(this);
    });
    $("#code").keyup(function () {
        if (this.value.length > max_len) {
            swal("超过长度上限！", "最多提交" + max_len + "个字符", "error");
            this.value = this.value.substring(0, max_len);
        }
    });

    var submit_options = {
        beforeSubmit: function(){
            $("input").attr("disabled", "disabled");
        },
        success: function(response_text){
            if (response_text === "0") 
            {
                swal("Success", "提交成功", "success");
                setTimeout(function () {
                    window.location.replace('/status');
                }, 500);
            }
            else
                swal("Oops", "提交失败，网络故障！", "error");
            }
    };
    $("#problem_submit_form").ajaxForm(submit_options);
});
