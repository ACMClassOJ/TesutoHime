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
        },
    });
});
