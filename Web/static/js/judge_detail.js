function code_highlight(x)
{
	$(function(){
        $.ajax({
            type: "POST",
            dataType: "text",
            data: {submit_id: x},
            url: "/api/code",
            success: function (response_text)
            {
                $("#judge_detail_code_highlighted").text(response_text);
                hljs.initHighlighting();
            },
        });
    });
}