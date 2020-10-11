function post_join(x)  {
    $(function(){
        $.ajax({
            type: "POST",
            dataType: "text",
            data: {contest_id: x},
            url: "/join",
            success: function (response_text)  {
                if(response_text == "0")  {
                    swal("Success","报名成功","success");
                    location.reload();
                }
                else {
                    swal("Error","谁让你玩OJ的？花Q！","error");
                    location.reload();
                }
            },
        });
    });
}