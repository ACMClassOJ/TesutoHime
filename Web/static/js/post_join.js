function post_join(x)  {
    $(function(){
        $.ajax({
            type: "POST",
            dataType: "text",
            data: {contest_id: x},
            url: "/OnlineJudge/api/join",
            beforeSend: function () {
                $("#join_button_" + x).attr("disabled", "disabled");
            },
            success: function (response_text)  {
                    location.reload();
            },
        });
    });
}