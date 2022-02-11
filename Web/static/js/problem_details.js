$(function(){
    $.ajax({
        type: "POST",
        dataType: "text",
        data: {problem_id: $("#problem_id").text()},
        url: "/OnlineJudge/api/get_detail",
        success: function (response_text)
        {
            var main_json = JSON.parse(response_text);
            if (main_json['Description'] == "None") $("#problem_details_description_header").html("");
            else $("#problem_details_description").html(marked(main_json['Description']));
            if (main_json['Input'] == "None") $("#problem_details_input_header").html("");
            else $("#problem_details_input").html(marked(main_json['Input']));
            if (main_json['Output'] == "None") $("#problem_details_output_header").html("");
            else $("#problem_details_output").html(marked(main_json['Output']));
            if (main_json['Example_Input'] == "None") $("#problem_details_example_input_header").html("");
            else $("#problem_details_example_input").html(marked(main_json['Example_Input']));
            if (main_json['Example_Output'] == "None") $("#problem_details_example_output_header").html("");
            else $("#problem_details_example_output").html(marked(main_json['Example_Output']));
            if (main_json['Data_Range'] == "None") $("#problem_details_data_range_header").html("");
            else $("#problem_details_data_range").html(marked(main_json['Data_Range']));
            renderMathInElement(document.body,
                {
                    delimiters: [
                        {left: "$$", right: "$$", display: true},
                        {left: "$", right: "$", display: false},
                        {left: "\\(", right: "\\)", display: false}
                    ]
                }
            );
            hljs.initHighlighting();
            $("pre").wrap('<div style="position: relative;"></div>');
            $("pre").each(function(index, element){
                $(this).find("code").eq(0).attr('id', 'code_highlighted_' + index);
                var copy_button = $('<button class="btn btn-primary btn-sm" style="position: absolute; top: 0; right: 0;">复制</button>');
                copy_button.attr('id', 'copy_button_' + index);
                copy_button.attr('data-clipboard-target', '#code_highlighted_' + index);
                copy_button.appendTo($(this));
                new ClipboardJS(document.getElementById('copy_button_' + index));
            });
        },
    });
});
