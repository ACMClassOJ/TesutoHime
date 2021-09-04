$(function() {
    var submit_options = {
        success: function(response_text) {
            if (response_text == "0") 
            {
                swal("Success", "提交成功", "success");
                setTimeout(function() {
                    window.location.replace('/OnlineJudge/status');
                }, 500);
            }
            else
                swal("Oops", "提交失败，网络故障！", "error");
        }
    };
    $("#quiz_submit_form").ajaxForm(submit_options);
});