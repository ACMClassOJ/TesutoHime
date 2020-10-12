function post_join(x)  {
    $(function(){
        $.ajax({
            type: "POST",
            dataType: "text",
            data: {contest_id: x},
            url: "/join",
            success: function (response_text)  {
                    location.reload();
            },
        });
    });
}