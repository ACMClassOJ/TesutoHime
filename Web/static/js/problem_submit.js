$(function () {
    $("#shared").change(function () {
        localStorage.setItem("share", $(this).is(":checked"));
    });
    $("#problem_submit_form").ajaxForm(function (response_text) {
        if (response_text === "0") {
            swal("Success", "提交成功", "success");
            setTimeout(function () {
                window.location.replace('/status');
            }, 500);
        } else
            swal("Oops", "提交失败，网络故障！", "error");
    });
});
